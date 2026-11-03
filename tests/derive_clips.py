"""Build known-answer clips from real AI videos (for calibration on real picture content).

    python tests/derive_clips.py <real_clip_folder> <out_folder> [--limit 40]

For --limit source clips spread evenly over the folder (sorted by name) it writes H.264 MP4s at 15 fps:
  <name>__still.mp4        frame 0 held for 3 s                                   expected: still
  <name>__camzoom.mp4      a slow zoom-in + pan over frame 0 (a "Ken Burns" move)   expected: camera_only
  <name>__campan.mp4       a pan + small roll over frame 0                          expected: camera_only
  <name>__freeze.mp4       the real clip's first 0.8 s, then its frame frozen 2.2 s expected: partly_animated
  <name>__reenc.mp4        the real clip re-encoded with H.264                      expected: animated
The re-encode adds real codec noise to every clip.
"""

import argparse
import math
import sys
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_clips import EXTS, decode  # noqa: E402

FPS = 15
SECONDS = 3.0


def write_mp4(frames, path, fps=FPS, crf="23"):
    n, h, w, _ = frames.shape
    h2, w2 = h // 2 * 2, w // 2 * 2
    with av.open(str(path), mode="w") as out:
        s = out.add_stream("libx264", rate=Fraction(fps).limit_denominator(1001))
        s.width, s.height, s.pix_fmt = w2, h2, "yuv420p"
        s.options = {"crf": crf}
        for f in (frames[:, :h2, :w2] * 255).round().clamp(0, 255).to(torch.uint8).numpy():
            for p in s.encode(av.VideoFrame.from_ndarray(np.ascontiguousarray(f), format="rgb24")):
                out.mux(p)
        for p in s.encode():
            out.mux(p)


def camera_move(img, n, zoom_total, pan_x, pan_y, roll_total):
    """Render n frames of a camera move over one still image (H, W, 3). Moves are totals over the clip."""
    h, w, _ = img.shape
    src = img.permute(2, 0, 1)[None]
    yy, xx = torch.meshgrid(torch.linspace(-1, 1, h), torch.linspace(-1, 1, w), indexing="ij")
    out = []
    margin = 1.0 / (1.0 + zoom_total + abs(pan_x) + abs(pan_y) + abs(roll_total))  # stay inside the image
    for i in range(n):
        t = i / (n - 1)
        s = margin / (1 + zoom_total * t)
        a = roll_total * t
        c, sn = math.cos(a), math.sin(a)
        gx = s * (c * xx - sn * yy) + pan_x * t * margin
        gy = s * (sn * xx + c * yy) + pan_y * t * margin
        grid = torch.stack([gx, gy], -1)[None]
        out.append(F.grid_sample(src, grid, mode="bicubic", align_corners=True)[0].permute(1, 2, 0))
    return torch.stack(out).clamp(0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in Path(a.src).iterdir() if p.suffix.lower() in EXTS)
    done = 0
    for p in files[::max(1, len(files) // a.limit)]:
        if done >= a.limit:
            break
        try:
            clip, fps = decode(p)
        except Exception:  # still images and unreadable files are skipped
            continue
        if len(clip) < 24:
            continue
        n = int(FPS * SECONDS)
        first = clip[0]
        write_mp4(first[None].expand(n, -1, -1, -1), out / f"{p.stem}__still.mp4")
        write_mp4(camera_move(first, n, 0.15, 0.10, 0.0, 0.0), out / f"{p.stem}__camzoom.mp4")
        write_mp4(camera_move(first, n, 0.0, -0.25, 0.08, math.radians(3)), out / f"{p.stem}__campan.mp4")
        moving = clip[: max(2, round(0.8 * fps))]
        frozen = moving[-1:].expand(round(2.2 * fps), -1, -1, -1)
        write_mp4(torch.cat([moving, frozen]), out / f"{p.stem}__freeze.mp4", fps=fps)
        write_mp4(clip, out / f"{p.stem}__reenc.mp4", fps=fps)
        done += 1
    print(f"{done} source clips -> {done * 5} derived clips in {out}")


if __name__ == "__main__":
    main()
