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


def image_chunks(images, height, width):
    """Shrink an IMAGE batch (N, H, W, C) to (n, height, width, 3) RGB chunks, a few full-size frames at a time."""
    n, h, w, c = images.shape
    step = frames.chunk_frames(h, w, c)
    for i in range(0, n, step):
        x = torch.nan_to_num(images[i:i + step].float(), nan=0.0, posinf=1.0, neginf=0.0).clamp(0, 1)
        x = x[..., :3] if c >= 3 else x[..., :1].expand(*x.shape[:-1], 3)
        yield F.interpolate(x.permute(0, 3, 1, 2), size=(height, width), mode="area").permute(0, 2, 3, 1)


def encode(chunks, fps, height, width, masks=None, step=1):
    """Encode (n, height, width, 3) RGB chunks to MP4 bytes. masks: (N - step, h, w) bool from the analysis, or
    None. Each chunk is tinted, encoded and dropped, so memory stays bounded at any preview size."""
    buf = io.BytesIO()
    rate = Fraction(float(fps)).limit_denominator(1001)
    done = 0
    with av.open(buf, mode="w", format="mp4",
                 options={"movflags": "frag_keyframe+empty_moov+default_base_moof"}) as out:
        stream = out.add_stream("libx264", rate=rate)
        stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
        stream.options = {"crf": CRF, "preset": "veryfast"}
        for x in chunks:
            if masks is not None and len(masks):
                # frame j shows the mask of the pair centred on it; tint in place: x = x(1 - a m) + tint a m
                pair = (torch.arange(done, done + x.shape[0]) - step // 2).clamp(0, len(masks) - 1)
                m = F.interpolate(masks[pair].float()[:, None], size=(height, width), mode="nearest")[:, 0, ..., None]
                m.mul_(TINT_ALPHA)
                x.mul_(1 - m).add_(m * TINT)
                del m
            done += x.shape[0]
            for f in x.mul_(255).round_().to(torch.uint8).numpy():
                for packet in stream.encode(av.VideoFrame.from_ndarray(f, format="rgb24")):
                    out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    return buf.getvalue()
