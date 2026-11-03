"""What still moves after the camera motion is removed.

For each frame pair (a, b), frame b is warped onto frame a with the estimated camera transform. On the aligned
pair the normal-flow magnitude |dI/dt| * |grad I| / (|grad I|^2 + LAMBDA^2) is computed. That is the part of the
motion that is visible across edges. A pixel counts as "moving on its own" when this speed is above a threshold.
Isolated noisy pixels are removed with a 3x3 majority filter. Only textured pixels count: a flat sky cannot
show motion.
"""

import torch
import torch.nn.functional as F

from . import camera
from .filters import blur, gradients

# Gradient floor and regulariser (|grad I| per px, 0..1 scale). Chosen by a sweep on 195 clips derived from real
# AI videos (tests/derive_clips.py): at 0.004 / 0.01, H.264 shimmer on weak gradients read as up to 0.44 % "own
# motion" on camera-only clips; at 0.01 / 0.02 the worst camera-only clip shows 0.16 % (threshold 0.3 %) while every
# real clip still reads as animated. Larger values started to miss real subtle motion (see docs/DESIGN.md).
GRAD_MIN = 0.01  # below this a pixel is "untextured" (~2.5 grey levels per pixel in 8-bit)
LAMBDA = 0.02  # regulariser of the normal-flow division
MARGIN = 2  # px ignored at the frame border (blur + gradient support)


def residual_motion(frames_a, frames_b, params, speed_px):
    """Per pair: share of textured pixels moving on their own, plus the per-pixel moving mask.

    frames_a, frames_b: (K, h, w); params: (K, 6) camera motion a -> b; speed_px: threshold in px per pair.
    Returns moving_share (K,), textured_share (K,), moving mask (K, h, w) bool.
    """
    k, h, w = frames_a.shape
    if min(h, w) <= 2 * MARGIN + 2:
        empty = torch.zeros(k)
        return empty, empty.clone(), torch.zeros((k, h, w), dtype=torch.bool)
    aligned, inside = camera.warp(frames_b, params)
    a = blur(frames_a)
    b = blur(aligned)
    valid = inside.clone()
    valid[:, :MARGIN] = False
    valid[:, -MARGIN:] = False
    valid[:, :, :MARGIN] = False
    valid[:, :, -MARGIN:] = False
    # Remove global exposure change (gain and offset), so brightness flicker is not read as motion.
    vf = valid.float()
    cnt = vf.sum((1, 2), keepdim=True).clamp(min=1)
    ma = (a * vf).sum((1, 2), keepdim=True) / cnt
    mb = (b * vf).sum((1, 2), keepdim=True) / cnt
    sa = (((a - ma) ** 2 * vf).sum((1, 2), keepdim=True) / cnt).sqrt()
    sb = (((b - mb) ** 2 * vf).sum((1, 2), keepdim=True) / cnt).sqrt()
    b = (b - mb) * (sa / sb.clamp(min=1e-6)) + ma
    gxa, gya = gradients(a)
    gxb, gyb = gradients(b)
    gx, gy = (gxa + gxb) / 2, (gya + gyb) / 2
    gmag = torch.sqrt(gx ** 2 + gy ** 2)
    normal_flow = (b - a).abs() * gmag / (gmag ** 2 + LAMBDA ** 2)
    textured = valid & (gmag >= GRAD_MIN)
    raw = textured & (normal_flow >= speed_px)
    # 3x3 majority filter: a pixel stays "moving" only if at least 5 of its 9 neighbours are.
    votes = F.avg_pool2d(raw.float()[:, None], 3, stride=1, padding=1, count_include_pad=False)[:, 0]
    moving = raw & (votes >= 5 / 9 - 1e-6)
    n_tex = textured.float().sum((1, 2))
    share = moving.float().sum((1, 2)) / n_tex.clamp(min=1)
    return share, n_tex / float(h * w), moving
