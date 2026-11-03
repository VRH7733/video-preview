"""Known-answer tests for Motion Verdict. Runs without ComfyUI:

    python tests/test_motion_verdict.py          (or: python -m pytest tests)

Each test plants a known camera move and/or a known moving subject in a synthetic clip and checks the verdict
and the numbers. False-positive tests use clean, noisy and flickering clips.
"""

import io
import json
import math
import sys
import time
import traceback
from pathlib import Path

import av
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth  # noqa: E402
from motion_verdict import analysis, frames  # noqa: E402
from motion_verdict.chart import HEIGHT, WIDTH  # noqa: E402
from motion_verdict.node import MotionVerdict  # noqa: E402
from motion_verdict.store import PREVIEWS, PreviewStore  # noqa: E402

FPS = 16.0
MIN_SPEED, MIN_AREA = 1.5, 0.3  # node defaults
H, W = 360, 640


def run(images, fps=FPS, keep_masks=False):
    return analysis.analyze(images, fps, MIN_SPEED, MIN_AREA, keep_masks=keep_masks)


def per_second(v):
    return lambda i: v * i / FPS


def near(value, target, tol):
    assert abs(value - target) <= tol, f"{value:.3f} not within {tol} of {target}"


PATCH = synth.moving_patch(120, 200, (100, 120), 3)  # 100x120 px subject moving 3 px/frame


# ---------------------------------------------------------------- known answers: camera only

def test_still_clip_is_still():
    r, _ = run(synth.clip(n=49, h=H, w=W))
    assert r.verdict == "still", r.verdict
    near(r.subject_motion, 0, 0.01)
    near(r.camera_speed, 0, 0.1)


def test_pan_right_is_camera_only_with_correct_sign_and_speed():
    # content moves left 5% of the width per second  ->  camera pans right 5%/s
    r, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (-0.05 * W * i / FPS, 0, 1, 0)))
    assert r.verdict == "camera_only", r.verdict
    near(r.pan_x, 5.0, 0.25)
    near(r.pan_y, 0.0, 0.25)
    near(r.subject_motion, 0, 0.05)


def test_tilt_up_and_down():
    up, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0, 0.06 * H * i / FPS, 1, 0)))
    down, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0, -0.06 * H * i / FPS, 1, 0)))
    assert up.verdict == down.verdict == "camera_only"
    near(up.pan_y, 6.0, 0.3)
    near(down.pan_y, -6.0, 0.3)


def test_zoom_in_and_out():
    zin, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0, 0, 1.08 ** (i / FPS), 0)))
    zout, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0, 0, 1.08 ** (-i / FPS), 0)))
    assert zin.verdict == zout.verdict == "camera_only", (zin.verdict, zout.verdict)
    near(zin.zoom, 8.0, 0.4)
    near(zout.zoom, 100 * (1 / 1.08 - 1), 0.4)


def test_roll_sign():
    # content turns clockwise on screen (+rot) -> the camera rolls counter-clockwise (roll < 0)
    r, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0, 0, 1, math.radians(4) * i / FPS)))
    assert r.verdict == "camera_only", r.verdict
    near(r.roll, -4.0, 0.3)


def test_combined_camera_move_over_still_picture_8bit():
    v = synth.clip(n=49, h=H, w=W, cam=lambda i: (0.2 * W * i / FPS, 0.05 * H * i / FPS, 1.03 ** (i / FPS),
                                                  0.01 * i / FPS))
    r, _ = run((v * 255).round() / 255)
    assert r.verdict == "camera_only", r.verdict
    near(r.subject_motion, 0, 0.05)


# ---------------------------------------------------------------- known answers: own motion

def test_moving_subject_static_camera_is_animated():
    r, masks = run(synth.clip(n=49, h=H, w=W, subject=PATCH), keep_masks=True)
    assert r.verdict == "animated", r.verdict
    assert r.subject_motion > 1.0, r.subject_motion
    near(r.camera_speed, 0, 0.3)
    # the moving pixels are where the subject is (analysis frames are half size: 320x180)
    m = masks.float().mean(0)
    inside = m[50:120, 90:245].sum()
    assert inside / m.sum() > 0.9, float(inside / m.sum())


def test_moving_subject_with_pan_and_with_zoom():
    pan, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0.05 * W * i / FPS, 0, 1, 0), subject=PATCH))
    zoom, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0, 0, 1.05 ** (i / FPS), 0), subject=PATCH))
    assert pan.verdict == zoom.verdict == "animated", (pan.verdict, zoom.verdict)
    near(pan.pan_x, -5.0, 0.3)
    near(zoom.zoom, 5.0, 0.4)


def test_small_subject_is_found():
    # 36x64 px (1% of the frame) moving 2 px/frame
    r, _ = run(synth.clip(n=49, h=H, w=W, subject=synth.moving_patch(150, 300, (36, 64), 2)))
    assert r.verdict == "animated", (r.verdict, r.subject_motion)


def test_motion_that_stops_is_partly_animated_with_a_stall():
    moving = synth.clip(n=17, h=H, w=W, subject=PATCH)
    v = torch.cat([moving, moving[-1:].expand(32, -1, -1, -1)])  # moves 1 s, then frozen 2 s
    r, _ = run(v)
    assert r.verdict == "partly_animated", (r.verdict, r.active_ratio)
    assert len(r.stalls) == 1, r.stalls
    first, last = r.stalls[0]
    assert 13 <= first <= 17 and last == 48, r.stalls


def test_clip_that_starts_moving_late_reports_the_stall_at_the_start():
    moving = synth.clip(n=33, h=H, w=W, subject=PATCH)
    v = torch.cat([moving[:1].expand(20, -1, -1, -1), moving])  # still 1.25 s, then moving 2 s
    r, _ = run(v)
    assert r.verdict == "animated", r.verdict
    assert r.stalls and r.stalls[0][0] == 0 and 18 <= r.stalls[0][1] <= 23, r.stalls


# ---------------------------------------------------------------- false positives

def test_noise_and_flicker_on_a_still_picture_are_still():
    r, _ = run(synth.clip(n=49, h=H, w=W, noise=0.03, flicker=0.08))
    assert r.verdict == "still", (r.verdict, r.subject_motion)


def test_noise_on_camera_move_is_camera_only():
    r, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0, 0, 1.05 ** (i / FPS), 0), noise=0.03))
    assert r.verdict == "camera_only", (r.verdict, r.subject_motion)


def test_black_clip_is_still_with_a_note():
    r, _ = run(torch.zeros(20, 64, 96, 3))
    assert r.verdict == "still" and any("detail" in n for n in r.notes), (r.verdict, r.notes)


def test_slow_drift_below_camera_threshold_is_still():
    r, _ = run(synth.clip(n=49, h=H, w=W, cam=lambda i: (0.005 * W * i / FPS, 0, 1, 0)))  # 0.5%/s
    assert r.verdict == "still", (r.verdict, r.camera_speed)


# ---------------------------------------------------------------- edge cases

def test_empty_and_single_frame():
    for n in (0, 1):
        r, masks = run(torch.zeros(n, 32, 48, 3))
        assert r.verdict == "unknown" and r.notes and masks is None, (n, r.verdict)


def test_two_frames():
    v = synth.clip(n=2, h=H, w=W, cam=lambda i: (8 * i, 0, 1, 0))
    r, _ = run(v)
    assert r.step == 1 and r.verdict == "camera_only", (r.step, r.verdict)


def test_odd_and_tiny_sizes():
    for h, w in ((37, 53), (9, 11), (3, 5), (180, 1)):
        r, _ = run(torch.rand(12, h, w, 3))
        assert r.verdict in analysis.VERDICTS, (h, w, r.verdict)


def test_portrait_clip():
    r, _ = run(synth.clip(n=33, h=W, w=H, cam=lambda i: (0, 0.05 * W * i / FPS, 1, 0)))
    assert r.analysis_size == (320, 180) and r.verdict == "camera_only", (r.analysis_size, r.verdict)
    near(r.pan_y, 5.0, 0.3)


def test_channels_1_and_4_match_3():
    v3 = synth.clip(n=25, h=180, w=320, subject=PATCH)
    r3, _ = run(v3)
    r1, _ = run(v3[..., :1].contiguous())
    r4, _ = run(torch.cat([v3, torch.ones_like(v3[..., :1])], -1))
    assert r1.verdict == r3.verdict == r4.verdict == "animated"
    near(r1.subject_motion, r3.subject_motion, 1e-3)
    near(r4.subject_motion, r3.subject_motion, 1e-6)


def test_nan_inf_counted_and_input_untouched():
    v = synth.clip(n=25, h=180, w=320, subject=PATCH)
    v[3, 10:20, 10:20, 0] = float("nan")
    v[5, 0, 0, 1] = float("inf")
    before = v.clone()
    out = MotionVerdict().run(v, FPS, MIN_SPEED, MIN_AREA, "off", 512, False)["result"]
    assert out[0] is v
    assert torch.equal(torch.isnan(v), torch.isnan(before)) and torch.equal(v.nan_to_num(), before.nan_to_num())
    data = json.loads(out[6])
    assert data["clip"]["nonfinite_values"] == 101, data["clip"]
    assert math.isfinite(out[3])


def test_chunked_conversion_is_identical():
    v = synth.clip(n=30, h=180, w=320, subject=PATCH)
    whole, _ = frames.analysis_frames(v, 320)
    old = frames.CHUNK_PIXELS
    try:
        frames.CHUNK_PIXELS = 180 * 320 * 3 * 7  # 7 frames per chunk
        parts, _ = frames.analysis_frames(v, 320)
    finally:
        frames.CHUNK_PIXELS = old
    assert torch.equal(whole, parts)


def test_long_clip_bounded_and_fast():
    n = 1500  # ~94 s at 16 fps
    v = synth.clip(n=8, h=144, w=256, subject=synth.moving_patch(40, 60, (40, 50), 3)).repeat(n // 8, 1, 1, 1)
    t = time.time()
    r, masks = run(v)
    dt = time.time() - t
    assert masks is None and len(r.step_moving) == len(v) - r.step
    assert dt < 120, dt


def test_other_frame_rates():
    for fps in (8.0, 24.0, 30.0):
        v = synth.clip(n=int(fps * 3), h=180, w=320, cam=lambda i, f=fps: (-0.05 * 320 * i / f, 0, 1, 0))
        r, _ = run(v, fps=fps)
        assert r.verdict == "camera_only", (fps, r.verdict)
        near(r.pan_x, 5.0, 0.3)


# ---------------------------------------------------------------- node contract

def test_node_outputs_and_passthrough():
    v = synth.clip(n=33, h=180, w=320, subject=PATCH)
    out = MotionVerdict().run(v, FPS, MIN_SPEED, MIN_AREA, "video + motion overlay", 512, False)
    images, verdict, animated, subject, timeline, text, data = out["result"]
    assert images is v
    assert verdict == "animated" and animated is True and isinstance(subject, float)
    assert timeline.shape == (1, HEIGHT, WIDTH, 3) and timeline.dtype == torch.float32
    assert 0 <= float(timeline.min()) and float(timeline.max()) <= 1
    assert text.startswith("Motion Verdict: ANIMATED")
    parsed = json.loads(data)
    assert parsed["verdict"] == "animated" and len(parsed["timeline"]["moving_pct"]) == len(v) - parsed["clip"]["step_frames"]
    info = out["ui"]["motion_verdict"][0]
    clip = PREVIEWS.get(info["token"])
    with av.open(io.BytesIO(clip)) as c:
        s = c.streams.video[0]
        decoded = sum(1 for _ in c.decode(s))
        assert s.codec_context.name == "h264" and decoded == len(v)


def test_node_preview_off_and_animated_flag_false():
    v = synth.clip(n=33, h=180, w=320, cam=lambda i: (0, 0, 1.05 ** (i / FPS), 0))
    out = MotionVerdict().run(v, FPS, MIN_SPEED, MIN_AREA, "off", 512, False)
    assert out["ui"]["motion_verdict"][0]["token"] is None
    assert out["result"][1] == "camera_only" and out["result"][2] is False


def test_preview_size_range_and_no_upscale():
    def size_of(clip):
        with av.open(io.BytesIO(clip)) as c:
            s = c.streams.video[0]
            return s.width, s.height, sum(1 for _ in c.decode(s))

    big = synth.clip(n=9, h=1080, w=1920, subject=PATCH)
    for side, expect in ((1440, (1440, 810)), (256, (256, 144))):
        out = MotionVerdict().run(big, FPS, MIN_SPEED, MIN_AREA, "video + motion overlay", side, False)
        assert size_of(PREVIEWS.get(out["ui"]["motion_verdict"][0]["token"])) == (*expect, 9), side
    small = synth.clip(n=9, h=181, w=321)  # odd size, smaller than the preview: kept, rounded down to even
    out = MotionVerdict().run(small, FPS, MIN_SPEED, MIN_AREA, "video", 1440, False)
    assert size_of(PREVIEWS.get(out["ui"]["motion_verdict"][0]["token"])) == (320, 180, 9)


def test_preview_store_evicts_oldest():
    s = PreviewStore(max_items=2, max_bytes=10)
    a, b, c = s.put(b"aaaa"), s.put(b"bbbb"), s.put(b"cccc")
    assert s.get(a) is None and s.get(b) == b"bbbb" and s.get(c) == b"cccc"
    big = s.put(b"x" * 20)  # larger than the budget: kept alone
    assert s.get(big) is not None and s.get(b) is None


def main():
    tests = [(k, f) for k, f in globals().items() if k.startswith("test_") and callable(f)]
    failed = 0
    t0 = time.time()
    for name, fn in tests:
        t = time.time()
        try:
            fn()
            print(f"PASS  {name}  ({time.time() - t:.1f}s)")
        except Exception:
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed} passed, {failed} failed, {time.time() - t0:.0f}s")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
