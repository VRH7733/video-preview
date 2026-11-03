"""Global (camera) motion between two frames as a 2-D affine transform.

Method:
1. Phase correlation of the whole frame for a coarse shift.
2. Phase correlation of a grid of overlapping tiles, after the second frame has been warped by the current
   estimate.
3. A robust (Tukey IRLS) least-squares fit of an affine motion field to the tile shifts. Tiles covering a moving
   subject disagree with the majority and get weight 0.
Steps 2 and 3 run twice.
4. A robust Gauss-Newton (Lucas-Kanade) polish of the affine on all pixels. Everything is batched over frame pairs; there is no Python loop over frames.

Motion model, in pixels, with coordinates centred on the frame centre:
    x_b = x_a + t + M @ x_a      t = (tx, ty), M = [[m11, m12], [m21, m22]]
A content point at x_a in frame a is found at x_b in frame b.
"""

import math

import torch
import torch.nn.functional as F

from .filters import blur, gradients

PEAK_MIN = 0.08  # phase-correlation peaks below this are treated as "no match" (pure noise peaks are ~0.02-0.05)
TUKEY_C = 4.685  # standard Tukey biweight constant (95% efficiency for Gaussian residuals)
RESID_FLOOR = 0.1  # px; keeps the robust scale from collapsing when all tiles agree perfectly
PASSES = 2


def _hann2(h, w):
    return torch.outer(torch.hann_window(h, periodic=True), torch.hann_window(w, periodic=True))


def phase_corr(a, b):
    """Shift of b relative to a, for batches (..., h, w). Returns dx, dy (px, sub-pixel) and the peak height."""
    h, w = a.shape[-2:]
    win = _hann2(h, w)
    a = (a - a.mean((-2, -1), keepdim=True)) * win
    b = (b - b.mean((-2, -1), keepdim=True)) * win
    cross = torch.conj(torch.fft.rfft2(a)) * torch.fft.rfft2(b)
    surface = torch.fft.irfft2(cross / (cross.abs() + 1e-9), s=(h, w)).flatten(-2)
    peak, idx = surface.max(-1)
    py, px = idx // w, idx % w

    def at(dy, dx):
        return surface.gather(-1, (((py + dy) % h) * w + (px + dx) % w).unsqueeze(-1)).squeeze(-1)

    def vertex(m, c, p):  # parabola through 3 samples -> sub-pixel offset of its top
        d = m - 2 * c + p
        safe = torch.where(d.abs() > 1e-9, d, torch.ones_like(d))
        return torch.where(d.abs() > 1e-9, 0.5 * (m - p) / safe, torch.zeros_like(d)).clamp(-0.5, 0.5)

    sy = vertex(at(-1, 0), peak, at(1, 0))
    sx = vertex(at(0, -1), peak, at(0, 1))
    dy = torch.where(py > h // 2, py - h, py).float() + sy
    dx = torch.where(px > w // 2, px - w, px).float() + sx
    return dx, dy, peak


def tile_size(h, w):
    """64 px tiles on normal analysis frames; smaller for tiny inputs. 0 = too small to estimate."""
    side = min(h, w)
    if side >= 96:
        return 64
    t = 2 ** int(math.floor(math.log2(side / 1.5))) if side >= 12 else 0
    return t if t >= 8 else 0


def tile_grid(h, w, t):
    """Overlapping tile origins (half-tile spacing) that cover the whole frame."""
    ny = max(2, round((h - t) / (t / 2)) + 1)
    nx = max(2, round((w - t) / (t / 2)) + 1)
    ys = torch.linspace(0, h - t, ny).round().long()
    xs = torch.linspace(0, w - t, nx).round().long()
    return ys, xs


def cut_tiles(x, ys, xs, t):
    """(K, h, w) -> (K, len(ys) * len(xs), t, t)."""
    ar = torch.arange(t)
    rows = ys[:, None] + ar[None]
    cols = xs[:, None] + ar[None]
    tiles = x[:, rows][:, :, :, cols]  # K, ny, t, nx, t
    return tiles.permute(0, 1, 3, 2, 4).reshape(x.shape[0], -1, t, t)


def centred_coords(h, w):
    yy, xx = torch.meshgrid(torch.arange(h, dtype=torch.float32) - (h - 1) / 2,
                            torch.arange(w, dtype=torch.float32) - (w - 1) / 2, indexing="ij")
    return xx, yy


def warp(b, params):
    """Sample frames b (K, h, w) at x_b = x + t + M x, i.e. bring frame b back onto frame a.

    Returns the warped frames and a mask of pixels whose source lies inside frame b.
    """
    k, h, w = b.shape
    xx, yy = centred_coords(h, w)
    tx, ty, m11, m12, m21, m22 = [params[:, i].view(k, 1, 1) for i in range(6)]
    xb = xx + tx + m11 * xx + m12 * yy
    yb = yy + ty + m21 * xx + m22 * yy
    sx, sy = max((w - 1) / 2, 0.5), max((h - 1) / 2, 0.5)
    grid = torch.stack([xb / sx, yb / sy], -1)
    out = F.grid_sample(b[:, None], grid, mode="bilinear", padding_mode="border", align_corners=True)[:, 0]
    inside = (xb.abs() <= (w - 1) / 2) & (yb.abs() <= (h - 1) / 2)
    return out, inside


def fit_affine(dx, dy, peak, cx, cy, iters=5):
    """Robust affine fit. dx, dy, peak: (K, T) tile shifts and peak heights; cx, cy: (T,) tile centres.

    Returns params (K, 6) = tx, ty, m11, m12, m21, m22 and the inlier share (K,) of usable tiles.
    """
    s = max(float(cx.abs().max()), float(cy.abs().max()), 1.0)  # scale coordinates for conditioning
    ux, uy = cx / s, cy / s
    one, zero = torch.ones_like(ux), torch.zeros_like(ux)
    rows_x = torch.stack([one, zero, ux, uy, zero, zero], -1)
    rows_y = torch.stack([zero, one, zero, zero, ux, uy], -1)
    design = torch.cat([rows_x, rows_y], 0)  # (2T, 6)
    target = torch.cat([dx, dy], 1)  # (K, 2T)
    n_tiles = dx.shape[1]
    w0 = torch.where(peak > PEAK_MIN, peak, torch.zeros_like(peak))
    w = w0
    ridge = torch.diag(torch.tensor([1e-6, 1e-6, 1e-3, 1e-3, 1e-3, 1e-3]))  # pulls M to 0 when tiles are few
    q = torch.zeros(dx.shape[0], 6)
    for _ in range(iters):
        ww = torch.cat([w, w], 1)
        ata = torch.einsum("ni,kn,nj->kij", design, ww, design) + ridge
        atb = torch.einsum("ni,kn,kn->ki", design, ww, target)
        q = torch.linalg.solve(ata, atb)
        res = target - q @ design.T
        r = torch.sqrt(res[:, :n_tiles] ** 2 + res[:, n_tiles:] ** 2)
        med = torch.where(w0 > 0, r, torch.full_like(r, float("nan"))).nanmedian(1).values.nan_to_num(0.0)
        c = TUKEY_C * (1.4826 * med + RESID_FLOOR)
        w = w0 * (1 - (r / c[:, None]) ** 2).clamp(min=0) ** 2
    params = q.clone()
    params[:, 2:] = q[:, 2:] / s
    usable = (w0 > 0).sum(1).clamp(min=1)
    inliers = (w > 0).sum(1) / usable
    inliers = torch.where((w0 > 0).sum(1) > 0, inliers, torch.zeros_like(inliers))
    return params, inliers


def estimate(frames_a, frames_b):
    """Affine camera motion from frames_a to frames_b, both (K, h, w). Returns params (K, 6) and inliers (K,)."""
    k, h, w = frames_a.shape
    t = tile_size(h, w)
    if t == 0:
        return torch.zeros(k, 6), torch.zeros(k)
    gx, gy, _ = phase_corr(frames_a, frames_b)
    params = torch.zeros(k, 6)
    params[:, 0], params[:, 1] = gx, gy
    ys, xs = tile_grid(h, w, t)
    cy = (ys.float() + t / 2 - h / 2)[:, None].expand(-1, len(xs)).reshape(-1)
    cx = (xs.float() + t / 2 - w / 2)[None, :].expand(len(ys), -1).reshape(-1)
    tiles_a = cut_tiles(frames_a, ys, xs, t)
    inliers = torch.zeros(k)
    for _ in range(PASSES):
        aligned, _ = warp(frames_b, params)
        dx, dy, peak = phase_corr(tiles_a, cut_tiles(aligned, ys, xs, t))
        delta, inliers = fit_affine(dx, dy, peak, cx, cy)
        params = params + delta  # small-motion composition; the second pass corrects the first
    return refine(frames_a, frames_b, params), inliers


def corner_speed(params, h, w):
    """Largest displacement of the four frame corners under params (K, 6), in pixels."""
    hx, hy = (w - 1) / 2, (h - 1) / 2
    corners = torch.tensor([[-hx, -hy], [hx, -hy], [-hx, hy], [hx, hy]])
    tx, ty, m11, m12, m21, m22 = params.T
    dxs = tx[:, None] + m11[:, None] * corners[:, 0] + m12[:, None] * corners[:, 1]
    dys = ty[:, None] + m21[:, None] * corners[:, 0] + m22[:, None] * corners[:, 1]
    return torch.sqrt(dxs ** 2 + dys ** 2).max(1).values


def decompose(params):
    """Readable camera terms per pair: content shift tx, ty (px), zoom (log scale), rotation (rad)."""
    tx, ty, m11, m12, m21, m22 = params.T
    det = ((1 + m11) * (1 + m22) - m12 * m21).clamp(min=1e-6)
    zoom = 0.5 * torch.log(det)
    rot = torch.atan2(m21 - m12, 2 + m11 + m22)
    return tx, ty, zoom, rot


def refine(frames_a, frames_b, params, iters=3):
    """Polish the affine estimate on all pixels (robust Gauss-Newton / Lucas-Kanade, batched).

    The tile fit is accurate to a few tenths of a pixel; fine texture turns even that much misalignment into
    apparent "motion". This step brings the registration error down by using every textured pixel. Pixels that
    disagree strongly (a moving subject) get weight 0 through the same Tukey weights as the tile fit.
    """
    k, h, w = frames_a.shape
    if tile_size(h, w) == 0:
        return params
    a = blur(frames_a)
    b_src = blur(frames_b)
    xx, yy = centred_coords(h, w)
    s = max(w, h) / 2
    ux, uy = (xx / s)[None], (yy / s)[None]
    for _ in range(iters):
        b, inside = warp(b_src, params)
        gx, gy = gradients(b)
        err = b - a
        jac = torch.stack([gx, gy, gx * ux, gx * uy, gy * ux, gy * uy], 1).flatten(2)  # (K, 6, P)
        e = err.flatten(1)
        valid = inside.flatten(1).float()
        med = torch.where(valid > 0, e.abs(), torch.full_like(e, float("nan"))).nanmedian(1).values.nan_to_num(0.0)
        c = TUKEY_C * (1.4826 * med + 1e-3)
        wgt = valid * (1 - (e / c[:, None]) ** 2).clamp(min=0) ** 2
        jw = jac * wgt[:, None]
        hess = torch.einsum("kip,kjp->kij", jw, jac) + 1e-6 * torch.eye(6)
        delta = -torch.linalg.solve(hess, torch.einsum("kip,kp->ki", jw, e))
        delta[:, 2:] = delta[:, 2:] / s
        params = params + delta
    return params
