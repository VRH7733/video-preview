"""Human-readable report and JSON for an analysis Result."""

import json

from . import analysis

SHOW_PAN = 0.3  # %/s; camera terms below these are shown as "none"
SHOW_ZOOM = 0.3  # %/s
SHOW_ROLL = 0.2  # degrees/s

HEADLINES = {
    "animated": "The scene itself moves (camera motion removed).",
    "partly_animated": "The scene moves only part of the time; see the stalls below.",
    "camera_only": "Only the camera moves: a camera move over a still picture (nothing moves on its own).",
    "still": "Nothing moves: no camera motion and no motion in the scene.",
    "unknown": "Not enough frames to judge.",
}


def camera_terms(r):
    terms = []
    if abs(r.pan_x) >= SHOW_PAN:
        terms.append(f"pan {'right' if r.pan_x > 0 else 'left'} {abs(r.pan_x):.1f}%/s")
    if abs(r.pan_y) >= SHOW_PAN:
        terms.append(f"tilt {'up' if r.pan_y > 0 else 'down'} {abs(r.pan_y):.1f}%/s")
    if abs(r.zoom) >= SHOW_ZOOM:
        terms.append(f"zoom {'in' if r.zoom > 0 else 'out'} {abs(r.zoom):.1f}%/s")
    if abs(r.roll) >= SHOW_ROLL:
        terms.append(f"roll {'clockwise' if r.roll > 0 else 'counter-clockwise'} {abs(r.roll):.1f} deg/s")
    return terms


def text(r, min_speed, min_area):
    lines = [f"Motion Verdict: {r.verdict.upper()}", HEADLINES[r.verdict]]
    if r.verdict != "unknown":
        dur = (r.frames - 1) / r.fps
        lines.append("")
        lines.append(f"Own motion (camera removed): {r.subject_motion:.2f}% of the picture on average, "
                     f"moving in {r.active_ratio * 100:.0f}% of the clip.")
        lines.append(f"  (a time step counts as moving when at least {min_area:g}% of the picture moves faster "
                     f"than {min_speed:g}% of the frame per second)")
        terms = camera_terms(r)
        moving = r.camera_speed >= analysis.CAMERA_MIN_SPEED
        lines.append(f"Camera: {', '.join(terms) if terms else 'no clear pan / tilt / zoom / roll'}; "
                     f"fastest corner {r.camera_speed:.1f}% of the frame per second "
                     f"({'moving' if moving else 'below the ' + str(analysis.CAMERA_MIN_SPEED) + '%/s camera threshold'}"
                     f"); {r.camera_inliers * 100:.0f}% of the picture agrees with one camera motion.")
        if r.stalls:
            parts = [f"frames {a}-{b} ({(b - a) / r.fps:.1f} s)" for a, b in r.stalls]
            lines.append(f"Stalls (nothing moves on its own for {analysis.STALL_SECONDS:g} s or more): "
                         + ", ".join(parts))
        lines.append(f"Clip: {r.frames} frames at {r.fps:g} fps ({dur:.2f} s); analysed at "
                     f"{r.analysis_size[1]}x{r.analysis_size[0]}, frames compared {r.step} apart.")
    for note in r.notes:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def as_json(r, min_speed, min_area):
    def rnd(xs, d=3):
        return [round(float(x), d) for x in xs]

    data = {
        "verdict": r.verdict,
        "animated": r.verdict == "animated",
        "subject_motion_pct": round(r.subject_motion, 4),
        "active_ratio": round(r.active_ratio, 4),
        "camera": {
            "speed_pct_per_s": round(r.camera_speed, 3),
            "moving": r.camera_speed >= analysis.CAMERA_MIN_SPEED,
            "pan_right_pct_per_s": round(r.pan_x, 3),
            "tilt_up_pct_per_s": round(r.pan_y, 3),
            "zoom_in_pct_per_s": round(r.zoom, 3),
            "roll_cw_deg_per_s": round(r.roll, 3),
            "inliers": round(r.camera_inliers, 3),
        },
        "stalls": [{"first_frame": a, "last_frame": b, "seconds": round((b - a) / r.fps, 3)} for a, b in r.stalls],
        "clip": {"frames": r.frames, "fps": r.fps, "step_frames": r.step,
                 "analysis_size": list(r.analysis_size), "textured": round(r.textured, 4),
                 "nonfinite_values": r.nonfinite},
        "settings": {"min_speed_pct_per_s": min_speed, "min_area_pct": min_area,
                     "camera_min_speed_pct_per_s": analysis.CAMERA_MIN_SPEED,
                     "animated_share": analysis.ANIMATED_SHARE, "partly_share": analysis.PARTLY_SHARE},
        "timeline": {"time_s": rnd(r.step_time), "moving_pct": rnd(r.step_moving),
                     "camera_pct_per_s": rnd(r.step_camera)},
        "notes": r.notes,
    }
    return json.dumps(data, indent=1)
