"""The ComfyUI node: Motion Verdict."""

import os

from . import analysis, chart, report
from .preview import encode as encode_preview
from .store import PREVIEWS

PREVIEW_MODES = ("video + motion overlay", "video", "off")


class MotionVerdict:
    DESCRIPTION = (
        "Is the clip really animated, or is it only a camera move over a still picture? Removes the camera's "
        "global motion (pan, tilt, zoom, roll) and measures what still moves on its own. Verdict: animated / "
        "partly_animated / camera_only / still, plus an 'animated' BOOLEAN for gating seed batches, the "
        "subject-motion score, a timeline chart and a report (also as JSON). Optional in-memory preview on the "
        "node (256-1440 px, nothing saved to disk) with the moving parts tinted red. CPU friendly; works in API runs without a browser."
    )
    CATEGORY = "video/Motion Verdict"
    FUNCTION = "run"
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "STRING", "BOOLEAN", "FLOAT", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "verdict", "animated", "subject_motion", "timeline", "report", "json")
    OUTPUT_TOOLTIPS = (
        "The input images, unchanged (same object).",
        "animated, partly_animated, camera_only, still or unknown.",
        "True only when the verdict is 'animated'. Use it to keep or drop a seed.",
        "Mean % of the picture that moves on its own (camera motion removed).",
        "Timeline: green bars = own motion, blue line = camera speed, yellow dashes = min_area, "
        "bottom strip green/red = moving/not moving.",
        "Readable report.",
        "All numbers and the per-time-step timeline as JSON.",
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The clip as a frame batch (e.g. from VAE Decode or Get Video "
                                                "Components)."}),
                "fps": ("FLOAT", {"default": 16.0, "min": 1.0, "max": 240.0, "step": 0.01,
                                  "tooltip": "Frames per second of the clip (Wan: 16, LTX: 24/25, Hunyuan: 24)."}),
                "min_speed": ("FLOAT", {"default": 1.5, "min": 0.1, "max": 50.0, "step": 0.1,
                                        "tooltip": "A pixel moves 'on its own' when, after the camera motion is "
                                                   "removed, it moves faster than this % of the frame per "
                                                   "second. Raise it for grainy footage."}),
                "min_area": ("FLOAT", {"default": 0.3, "min": 0.01, "max": 50.0, "step": 0.01,
                                       "tooltip": "A moment counts as 'moving' when at least this % of the "
                                                  "(textured) picture moves on its own."}),
                "preview": (list(PREVIEW_MODES), {"default": PREVIEW_MODES[0],
                                                  "tooltip": "Preview on the node, encoded in memory (nothing is "
                                                             "saved). The overlay tints what moves on its own."}),
                "preview_size": ("INT", {"default": 512, "min": 256, "max": 1440, "step": 64,
                                         "tooltip": "Longest side of the preview in pixels (never larger than "
                                                    "the clip). Does not change the analysis."}),
                "save_report": ("BOOLEAN", {"default": False,
                                            "tooltip": "Also save the JSON report in ComfyUI's output folder "
                                                       "(output/motion_verdict/)."}),
            },
        }

    def run(self, images, fps, min_speed, min_area, preview, preview_size, save_report):
        overlay = preview == PREVIEW_MODES[0]
        res, masks = analysis.analyze(images, fps, min_speed, min_area, keep_masks=overlay)
        text = report.text(res, min_speed, min_area)
        data = report.as_json(res, min_speed, min_area)
        timeline = chart.timeline(res.step_moving, res.step_camera, min_area, analysis.CAMERA_MIN_SPEED,
                                  res.step_flat)
        info = {"verdict": res.verdict, "headline": report.HEADLINES[res.verdict], "report": text,
                "token": None, "saved": None}
        if preview != PREVIEW_MODES[2] and res.frames > 0:
            info["token"] = PREVIEWS.put(encode_preview(images, fps, preview_size, masks, res.step))
        if save_report:
            info["saved"] = save_json(data)
        return {"ui": {"motion_verdict": [info]},
                "result": (images, res.verdict, res.verdict == "animated", float(res.subject_motion), timeline,
                           text, data)}


def save_json(data):
    import folder_paths  # ComfyUI module; imported here so the analysis modules stay usable without ComfyUI

    out_dir = folder_paths.get_output_directory()
    folder, name, counter, subfolder, _ = folder_paths.get_save_image_path("motion_verdict/MotionVerdict", out_dir)
    os.makedirs(folder, exist_ok=True)
    filename = f"{name}_{counter:05}_.json"
    with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
        f.write(data)
    return {"filename": filename, "subfolder": subfolder, "type": "output"}
