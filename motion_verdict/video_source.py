"""Read a video file frame by frame, letting FFmpeg shrink every frame as it is decoded.

A 4K or very long clip therefore never exists at full size in memory: only small analysis and preview frames
are kept. Trim semantics follow ComfyUI's own decoder: frames with start <= pts < start + duration
(duration 0 = to the end). Pure PyAV + torch; no ComfyUI imports.
"""

import io

import av
import numpy as np
import torch

from . import frames

BATCH = 16  # already-shrunk frames turned into one tensor at a time


class VideoStream:
    def __init__(self, source, start=0.0, duration=0.0):
        """source: a path or a BytesIO. start / duration in seconds, as in ComfyUI's trim window."""
        self.source, self.start, self.duration = source, float(start), float(duration)
        with self._open() as c:
            s = c.streams.video[0]
            self.width, self.height = s.width, s.height
            self.fps = float(s.average_rate) if s.average_rate else 0.0
            first = next(c.decode(s), None)
            self.rotated = bool(first is not None and first.rotation)

    def _open(self):
        if isinstance(self.source, io.BytesIO):
            self.source.seek(0)
        return av.open(self.source)

    def chunks(self, height, width):
        """Yield (n, height, width, 3) float32 RGB chunks in 0..1; every frame is scaled by FFmpeg (area)."""
        with self._open() as c:
            s = c.streams.video[0]
            s.thread_type = "AUTO"
            start_pts = int(self.start / s.time_base)
            end_pts = int((self.start + self.duration) / s.time_base)
            if start_pts:
                c.seek(start_pts, stream=s)
            buf = []
            for f in c.decode(s):
                if f.pts is not None and f.pts < start_pts:
                    continue
                if self.duration and f.pts is not None and f.pts >= end_pts:
                    break
                buf.append(f.reformat(width=width, height=height, format="rgb24", interpolation="AREA").to_ndarray())
                if len(buf) == BATCH:
                    yield torch.from_numpy(np.stack(buf)).float() / 255.0
                    buf = []
            if buf:
                yield torch.from_numpy(np.stack(buf)).float() / 255.0

    def analysis_frames(self, long_side):
        """(N, h, w) gray analysis frames, same size rule and luma as frames.analysis_frames(). 8-bit input has
        no NaN/Inf, so the count is always 0."""
        h, w = frames.analysis_size(self.height, self.width, long_side)
        grays = [frames.to_gray(chunk)[0] for chunk in self.chunks(h, w)]
        return (torch.cat(grays) if grays else torch.empty((0, h, w))), 0
