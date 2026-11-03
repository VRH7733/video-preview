"""H.264 preview of the clip, encoded in memory (nothing is written to disk).

Optionally the pixels that move on their own (camera motion removed) are tinted red.
"""

import io
from fractions import Fraction

import av
import torch
import torch.nn.functional as F

from . import frames

CRF = "28"
TINT = torch.tensor([1.0, 0.15, 0.1])
TINT_ALPHA = 0.55


def preview_size(height, width, long_side):
    """Preview size: longest side = long_side, never upscaled, even numbers (needed by yuv420p)."""
    scale = min(1.0, long_side / max(height, width))
    return max(2, int(height * scale) // 2 * 2), max(2, int(width * scale) // 2 * 2)


def _rgb(chunk):
    x = torch.nan_to_num(chunk.float(), nan=0.0, posinf=1.0, neginf=0.0).clamp(0, 1)
    if x.shape[-1] >= 3:
        return x[..., :3]
    return x[..., :1].expand(*x.shape[:-1], 3)


def encode(images, fps, long_side, masks=None, step=1):
    """IMAGE (N, H, W, C) -> MP4 bytes, longest side <= long_side. masks: (N - step, h, w) bool or None.

    Frames are shrunk and encoded one chunk at a time, so memory stays bounded at any preview size.
    """
    n, height, width, channels = images.shape
    ph, pw = preview_size(height, width, long_side)
    buf = io.BytesIO()
    rate = Fraction(float(fps)).limit_denominator(1001)
    with av.open(buf, mode="w", format="mp4",
                 options={"movflags": "frag_keyframe+empty_moov+default_base_moof"}) as out:
        stream = out.add_stream("libx264", rate=rate)
        stream.width, stream.height, stream.pix_fmt = pw, ph, "yuv420p"
        stream.options = {"crf": CRF, "preset": "veryfast"}
        chunk = frames.chunk_frames(height, width, channels)
        for i in range(0, n, chunk):
            x = _rgb(images[i:i + chunk]).permute(0, 3, 1, 2)
            x = F.interpolate(x, size=(ph, pw), mode="area").permute(0, 2, 3, 1)
            if masks is not None and len(masks):
                # frame j shows the mask of the pair centred on it
                pair = (torch.arange(i, i + x.shape[0]) - step // 2).clamp(0, len(masks) - 1)
                m = F.interpolate(masks[pair].float()[:, None], size=(ph, pw), mode="nearest")[:, 0, ..., None]
                x = x * (1 - TINT_ALPHA * m) + TINT * (TINT_ALPHA * m)
            rgb = (x * 255).round().to(torch.uint8).numpy()
            for f in rgb:
                for packet in stream.encode(av.VideoFrame.from_ndarray(f, format="rgb24")):
                    out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    return buf.getvalue()
