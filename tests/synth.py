"""Synthetic clips with known camera and subject motion (test helper, no ComfyUI needed)."""

import math

import torch
import torch.nn.functional as F


def texture(h, w, seed=0, power=0.9):
    """A natural-looking random texture (1/f noise), values 0..1."""
    g = torch.Generator().manual_seed(seed)
    noise = torch.rand(h, w, generator=g, dtype=torch.float64)
    spec = torch.fft.rfft2(noise)
    fy = torch.fft.fftfreq(h)[:, None]
    fx = torch.fft.rfftfreq(w)[None]
    spec = spec / (1e-3 + fx ** 2 + fy ** 2) ** power
    t = torch.fft.irfft2(spec, s=(h, w))
    return ((t - t.min()) / (t.max() - t.min())).float()


def render(scene, h, w, tx, ty, scale, rot):
    """View of `scene` (H, W) through a camera; the content moves by (tx, ty) px, scales and turns by rot (rad)."""
    yy, xx = torch.meshgrid(torch.arange(h, dtype=torch.float32), torch.arange(w, dtype=torch.float32),
                            indexing="ij")
    x = xx - (w - 1) / 2 - tx
    y = yy - (h - 1) / 2 - ty
    c, s = math.cos(-rot), math.sin(-rot)
    xs = (c * x - s * y) / scale
    ys = (s * x + c * y) / scale
    sh, sw = scene.shape
    grid = torch.stack([xs / ((sw - 1) / 2), ys / ((sh - 1) / 2)], -1)[None]
    return F.grid_sample(scene[None, None], grid, mode="bilinear", align_corners=True)[0, 0]


def clip(n=33, h=180, w=320, cam=lambda i: (0.0, 0.0, 1.0, 0.0), subject=None, noise=0.0, flicker=0.0,
         seed=0, channels=3, scene=None):
    """IMAGE batch (n, h, w, channels).

    cam(i) -> (tx, ty, scale, rot): content transform of frame i (camera motion, inverse sign).
    subject(i, frame) -> frame: paints a moving subject onto the rendered frame.
    flicker: +-gain alternating per frame. noise: Gaussian sigma.
    """
    scene = texture(h * 2, w * 2, seed) if scene is None else scene
    g = torch.Generator().manual_seed(seed + 1)
    out = []
    for i in range(n):
        f = render(scene, h, w, *cam(i))
        if subject is not None:
            f = subject(i, f)
        if flicker:
            f = f * (1 + flicker * (1 if i % 2 else -1))
        if noise:
            f = f + noise * torch.randn(f.shape, generator=g)
        out.append(f.clamp(0, 1))
    v = torch.stack(out)[..., None]
    return v.expand(-1, -1, -1, channels).contiguous() if channels > 1 else v


def moving_patch(y, x, size, vx, vy=0.0, seed=7):
    """A textured patch of `size` (h, w) whose top-left moves by (vx, vy) px per frame."""
    ph, pw = size
    patch = texture(ph, pw, seed, power=0.8)

    def paint(i, f):
        f = f.clone()
        x0 = int(round(x + vx * i)) % (f.shape[1] - pw)
        y0 = int(round(y + vy * i)) % (f.shape[0] - ph)
        f[y0:y0 + ph, x0:x0 + pw] = patch
        return f

    return paint
