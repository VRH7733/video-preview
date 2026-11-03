"""Run Motion Verdict on every video file in a folder and print one line per clip.

    python tests/eval_clips.py <folder> [--min-speed 1.5] [--min-area 0.3] [--json out.json] [--sheets <dir>]

Decodes with PyAV (mp4, webm, mov, mkv, gif, animated webp) through the node's own streaming reader, so 4K and
long clips are shrunk frame by frame and never held at full size. fps is taken from the frame timestamps.
--sheets writes a contact sheet (8 frames) per clip, to check the verdicts by eye.
No ComfyUI needed.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import av
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motion_verdict import analysis, frames  # noqa: E402
from motion_verdict.video_source import VideoStream  # noqa: E402

EXTS = {".mp4", ".webm", ".mov", ".mkv", ".gif", ".webp", ".avi"}


def timestamp_fps(path):
    """fps from the median frame step (container rates of animated WebP / GIF are often wrong)."""
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        times = [f.time for f in c.decode(s)]
        rate = float(s.average_rate or 16)
    steps = [b - a for a, b in zip(times, times[1:]) if a is not None and b is not None and b > a]
    return 1.0 / float(np.median(steps)) if steps else rate


def decode(path, max_side=None):
    """Return (IMAGE tensor (N, H, W, 3) float 0..1, fps). With max_side the frames are shrunk while decoding."""
    stream = VideoStream(str(path))
    h, w = stream.height, stream.width
    if max_side:
        h, w = frames.analysis_size(h, w, max_side)
    return torch.cat(list(stream.chunks(h, w))), timestamp_fps(path)


def sheet(images, out):
    from PIL import Image  # only for writing the optional contact sheets

    idx = np.linspace(0, len(images) - 1, 8).round().astype(int)
    row = torch.cat([images[i] for i in idx], dim=1)
    Image.fromarray((row.numpy() * 255).astype(np.uint8)).save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--min-speed", type=float, default=1.5)
    ap.add_argument("--min-area", type=float, default=0.3)
    ap.add_argument("--json")
    ap.add_argument("--sheets")
    a = ap.parse_args()
    files = sorted(p for p in Path(a.folder).iterdir() if p.suffix.lower() in EXTS)
    if not files:
        print(f"No video files in {a.folder}")
        return
    rows = []
    for p in files:
        try:
            stream = VideoStream(str(p))
            fps = timestamp_fps(p)
            t = time.time()
            gray, nonfinite = stream.analysis_frames(analysis.ANALYSIS_LONG_SIDE)
        except Exception as e:  # report and continue with the next clip
            print(f"{p.name}: cannot decode ({type(e).__name__}: {e})")
            continue
        r, _ = analysis.analyze(gray, nonfinite, fps, a.min_speed, a.min_area)
        dt = time.time() - t
        rows.append({"file": p.name, "verdict": r.verdict, "subject_motion": round(r.subject_motion, 3),
                     "active_ratio": round(r.active_ratio, 3), "camera_speed": round(r.camera_speed, 2),
                     "pan_x": round(r.pan_x, 2), "pan_y": round(r.pan_y, 2), "zoom": round(r.zoom, 2),
                     "roll": round(r.roll, 2), "inliers": round(r.camera_inliers, 2), "frames": r.frames,
                     "fps": round(fps, 2), "stalls": r.stalls, "seconds": round(dt, 2)})
        print(f"{p.name:55s} {r.verdict:15s} own={r.subject_motion:6.2f}% active={r.active_ratio:4.2f} "
              f"cam={r.camera_speed:5.1f}%/s inl={r.camera_inliers:.2f} {r.frames}f@{fps:.0f} {dt:.2f}s")
        if a.sheets:
            Path(a.sheets).mkdir(parents=True, exist_ok=True)
            sheet(decode(p, max_side=256)[0], Path(a.sheets) / f"{p.stem}.png")
    counts = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    print(f"\n{len(rows)} clips: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
