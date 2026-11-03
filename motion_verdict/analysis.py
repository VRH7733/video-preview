"""Motion Verdict analysis: camera motion vs. motion of the scene itself, for a whole clip.

Pure torch, no ComfyUI imports. Entry point: analyze().
"""

import math
from dataclasses import dataclass, field

import torch

from . import camera, residual

ANALYSIS_LONG_SIDE = 320  # px; analysis frames are at most this big (motion of 1/320 of the frame is still seen)
STEP_SECONDS = 0.25  # frames are compared this far apart, so slow motion adds up above the noise floor
PAIR_CHUNK = 16  # frame pairs processed together (bounds memory; 16 vs 32 saves ~70 MB, 8 saves nothing more)

CAMERA_MIN_SPEED = 1.5  # % of the long side per second at the fastest frame corner = "the camera moves"
ANIMATED_SHARE = 0.5  # share of time steps with own motion needed for "animated"
PARTLY_SHARE = 0.15  # ... and for "partly_animated"
STALL_SECONDS = 1.0  # a still stretch at least this long is reported as a stall
LOW_TEXTURE = 0.02  # less than 2% textured pixels: the clip has too little detail to judge motion

VERDICTS = ("animated", "partly_animated", "camera_only", "still", "unknown")


@dataclass
class Result:
    verdict: str
    frames: int
    fps: float
    step: int  # frames between compared pairs
    analysis_size: tuple  # (h, w)
    subject_motion: float  # mean % of textured pixels that move on their own
    active_ratio: float  # share of time steps with own motion
    camera_speed: float  # median, % of the long side per second at the fastest corner
    pan_x: float  # camera pan, % of frame width per second, + = camera moves right
    pan_y: float  # camera tilt, % of frame height per second, + = camera moves up
    zoom: float  # % per second, + = zoom in
    roll: float  # degrees per second, + = camera rolls clockwise
    camera_inliers: float  # median share of tiles that agree with the camera fit
    textured: float  # mean share of textured pixels
    nonfinite: int  # NaN / Inf values found in the input (sanitised for the analysis only)
    stalls: list = field(default_factory=list)  # [(first_frame, last_frame), ...]
    step_time: list = field(default_factory=list)  # seconds, centre of each compared pair
    step_moving: list = field(default_factory=list)  # % moving per time step
    step_camera: list = field(default_factory=list)  # camera speed per time step
    step_flat: list = field(default_factory=list)  # True = too little detail in this time step
    notes: list = field(default_factory=list)


def step_frames(n, fps):
    return max(1, min(n - 1, round(fps * STEP_SECONDS)))


def stall_runs(active, step, fps):
    """Runs of inactive time steps that cover at least STALL_SECONDS. Returns frame ranges."""
    runs, start = [], None
    for i, a in enumerate(list(active) + [True]):
        if not a and start is None:
            start = i
        elif a and start is not None:
            first, last = start, i - 1 + step
            if (last - first) / fps >= STALL_SECONDS - 1e-9:
                runs.append((first, last))
            start = None
    return runs


def _median(x):
    return float(x.median()) if x.numel() else 0.0


def analyze(gray, nonfinite, fps, min_speed, min_area, keep_masks=False):
    """Analyse a clip given as small gray analysis frames (N, h, w).

    Make them with frames.analysis_frames(IMAGE batch, ANALYSIS_LONG_SIDE) or
    video_source.VideoStream.analysis_frames(ANALYSIS_LONG_SIDE). nonfinite: NaN/Inf count found while making them.
    fps: frames per second. min_speed: % of the long side per second a pixel must move (after the camera is
    removed) to count. min_area: % of the textured picture that must move for a time step to count as "moving".
    Returns (Result, masks), where masks is (N-step, h, w) bool or None.
    """
    n = int(gray.shape[0])
    fps = float(fps)
    if n < 2:
        res = Result("unknown", n, fps, 0, tuple(gray.shape[1:3]), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                     nonfinite)
        res.notes.append("Need at least 2 frames to judge motion." if n == 1 else "The clip has no frames.")
        return res, None

    _, h, w = gray.shape
    long_side = float(max(h, w))
    step = step_frames(n, fps)
    per_second = fps / step
    speed_px = min_speed / 100.0 * long_side / per_second

    moving_share, textured, speed, inliers = [], [], [], []
    tx, ty, zoom, rot = [], [], [], []
    masks = [] if keep_masks else None
    starts = torch.arange(0, n - step)
    for i in range(0, len(starts), PAIR_CHUNK):
        idx = starts[i:i + PAIR_CHUNK]
        fa, fb = gray[idx], gray[idx + step]
        params, inl = camera.estimate(fa, fb)
        share, tex, mask = residual.residual_motion(fa, fb, params, speed_px)
        moving_share.append(share)
        textured.append(tex)
        inliers.append(inl)
        speed.append(camera.corner_speed(params, h, w))
        for acc, v in zip((tx, ty, zoom, rot), camera.decompose(params)):
            acc.append(v)
        if keep_masks:
            masks.append(mask)

    moving_share = torch.cat(moving_share) * 100
    textured = torch.cat(textured)
    cam_speed = torch.cat(speed) / long_side * 100 * per_second
    tx, ty, zoom, rot = (torch.cat(v) for v in (tx, ty, zoom, rot))
    low_texture = textured < LOW_TEXTURE
    active = (moving_share >= min_area) & ~low_texture
    active_ratio = float(active.float().mean())
    camera_speed = _median(cam_speed[~low_texture]) if bool((~low_texture).any()) else 0.0

    if active_ratio >= ANIMATED_SHARE:
        verdict = "animated"
    elif active_ratio >= PARTLY_SHARE:
        verdict = "partly_animated"
    elif camera_speed >= CAMERA_MIN_SPEED:
        verdict = "camera_only"
    else:
        verdict = "still"

    res = Result(
        verdict=verdict, frames=n, fps=fps, step=step, analysis_size=(h, w),
        subject_motion=float(moving_share.mean()), active_ratio=active_ratio, camera_speed=camera_speed,
        # content moving left (tx < 0) means the camera moves right; content moving down means the camera tilts up
        pan_x=float(-tx.mean() / w * 100 * per_second),
        pan_y=float(ty.mean() / h * 100 * per_second),
        zoom=float(torch.expm1(zoom.mean() * per_second) * 100),
        # content turning clockwise on screen (rot > 0, y axis down) means the camera rolls counter-clockwise
        roll=float(-math.degrees(float(rot.mean())) * per_second),
        camera_inliers=_median(torch.cat(inliers)), textured=float(textured.mean()), nonfinite=nonfinite,
        stalls=stall_runs(active.tolist(), step, fps) if verdict in ("animated", "partly_animated") else [],
        step_time=((starts.float() + step / 2) / fps).tolist(),
        step_moving=moving_share.tolist(), step_camera=cam_speed.tolist(), step_flat=low_texture.tolist(),
    )
    if bool(low_texture.all()):
        res.verdict = "still"
        res.notes.append("Almost no detail in the picture (flat or black frames); nothing can be seen moving.")
    elif bool(low_texture.any()):
        res.notes.append(f"{int(low_texture.sum())} of {len(low_texture)} time steps have almost no detail and "
                         f"were counted as not moving.")
    if nonfinite:
        res.notes.append(f"{nonfinite} NaN/Inf values in the input were replaced for the analysis "
                         f"(the passthrough output is unchanged).")
    if res.camera_inliers < 0.5 and verdict != "still":
        res.notes.append("Less than half of the picture agrees on one camera motion (large moving subject or "
                         "strong parallax); camera numbers are approximate.")
    if camera.tile_size(h, w) == 0:
        res.notes.append("Frames are very small; the camera motion could not be estimated (treated as static).")
    return res, (torch.cat(masks) if keep_masks else None)
