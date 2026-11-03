"""Turn a ComfyUI IMAGE batch into small grayscale analysis frames, chunk by chunk."""

import torch
import torch.nn.functional as F

LUMA = (0.299, 0.587, 0.114)
CHUNK_PIXELS = 24_000_000  # full-size values read at once (~96 MB as float32)


def analysis_size(height, width, long_side):
    """Size of the analysis frames: longest side = long_side, never upscaled."""
    scale = min(1.0, long_side / max(height, width))
    return max(1, round(height * scale)), max(1, round(width * scale))


def chunk_frames(height, width, channels):
    return max(1, CHUNK_PIXELS // max(1, height * width * channels))


def to_gray(chunk):
    """(n, H, W, C) float -> (n, H, W) float32 luma in [0, 1] and the number of NaN/Inf values seen.

    C=1 or 2: first channel. C>=3: Rec.601 luma of the first three (alpha is ignored).
    """
    x = chunk.float()
    bad = int((~torch.isfinite(x)).sum())
    if bad:
        x = torch.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    x = x.clamp(0.0, 1.0)
    if x.shape[-1] >= 3:
        g = x[..., 0] * LUMA[0] + x[..., 1] * LUMA[1] + x[..., 2] * LUMA[2]
    else:
        g = x[..., 0]
    return g, bad


def analysis_frames(images, long_side):
    """IMAGE (N, H, W, C) -> (N, h, w) float32 gray frames and the NaN/Inf count.

    Only `chunk_frames` full-size frames are converted at a time, so the extra memory is bounded
    no matter how long the clip is. The input tensor is never modified.
    """
    n, height, width, channels = images.shape
    h, w = analysis_size(height, width, long_side)
    out = torch.empty((n, h, w), dtype=torch.float32)
    bad = 0
    step = chunk_frames(height, width, channels)
    for i in range(0, n, step):
        g, b = to_gray(images[i:i + step])
        bad += b
        if (h, w) != (height, width):
            g = F.interpolate(g[:, None], size=(h, w), mode="area")[:, 0]
        out[i:i + step] = g
    return out, bad
