"""The ComfyUI node: Motion Verdict."""

import os

from . import analysis, chart, frames, report
from . import preview as clip_preview
from .store import PREVIEWS
from .video_source import VideoStream

PREVIEW_VIDEO, PREVIEW_OVERLAY, PREVIEW_OFF = "video", "video + motion overlay", "off"
PREVIEW_MODES = (PREVIEW_VIDEO, PREVIEW_OVERLAY, PREVIEW_OFF)


def streamable(video):
    """A VideoStream for a file-backed VIDEO, or None when ComfyUI's own decoder must be used.

    Streaming is used when the VIDEO exposes its file and trim window (VideoFromFile) and is neither cropped nor
    rotated. Those two cases are left to ComfyUI's decoder so the frames match exactly what other nodes see.
    """
    get_source = getattr(video, "get_stream_source", None)
    get_trim = getattr(video, "get_active_trim_window", None)
    if get_source is None or get_trim is None:
        return None
    stream = VideoStream(get_source(), *get_trim())
    if stream.rotated or tuple(video.get_dimensions()) != (stream.width, stream.height):
        return None
    return stream


class MotionVerdict:
    DESCRIPTION = (
        "Is the clip really animated, or is it only a camera move over a still picture? Removes the camera's "
        "global motion (pan, tilt, zoom, roll) and measures what still moves on its own. Verdict: animated / "
        "partly_animated / camera_only / still, plus an 'animated' BOOLEAN for gating seed batches, the "
        "subject-motion score, a timeline chart and a report (also as JSON). Takes an IMAGE batch, or a VIDEO "
        "that is streamed so 4K and long clips never sit in memory at full size. Optional in-memory preview on "
        "the node (256-1440 px, nothing saved to disk), clean or with the moving parts tinted red. CPU friendly; "
        "works in API runs without a browser."
    )
    CATEGORY = "video/Motion Verdict"
    FUNCTION = "run"
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE", "VIDEO", "STRING", "BOOLEAN", "FLOAT", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "video", "verdict", "animated", "subject_motion", "timeline", "report", "json")
    OUTPUT_TOOLTIPS = (
        "The images input, unchanged (same object); empty if a video was connected instead.",
        "The video input, unchanged (same object); empty if images were connected instead.",
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
                "fps": ("FLOAT", {"default": 16.0, "min": 1.0, "max": 240.0, "step": 0.01,
                                  "tooltip": "Frames per second of the images (Wan: 16, LTX: 24/25, Hunyuan: 24). "
                                             "A video input uses its own frame rate."}),
                "min_speed": ("FLOAT", {"default": 1.5, "min": 0.1, "max": 50.0, "step": 0.1,
                                        "tooltip": "A pixel moves 'on its own' when, after the camera motion is "
                                                   "removed, it moves faster than this % of the frame per "
                                                   "second. Raise it for grainy footage."}),
                "min_area": ("FLOAT", {"default": 0.3, "min": 0.01, "max": 50.0, "step": 0.01,
                                       "tooltip": "A moment counts as 'moving' when at least this % of the "
                                                  "(textured) picture moves on its own."}),
                "preview": (list(PREVIEW_MODES), {"default": PREVIEW_VIDEO,
                                                  "tooltip": "Preview on the node, encoded in memory (nothing is "
                                                             "saved). 'video' = the clean clip; the overlay mode "
                                                             "tints red what moves on its own."}),
                "preview_size": ("INT", {"default": 512, "min": 256, "max": 1440, "step": 64,
                                         "tooltip": "Longest side of the preview in pixels (never larger than "
                                                    "the clip). Does not change the analysis."}),
                "save_report": ("BOOLEAN", {"default": False,
                                            "tooltip": "Also save the JSON report in ComfyUI's output folder "
                                                       "(output/motion_verdict/)."}),
            },
            "optional": {
                "images": ("IMAGE", {"tooltip": "The clip as a frame batch (e.g. from VAE Decode). Connect this "
                                                "or video."}),
                "video": ("VIDEO", {"tooltip": "The clip as a VIDEO (e.g. from Load Video). It is streamed: each "
                                               "frame is shrunk while decoding, so 4K / long clips stay small in "
                                               "memory. Connect this or images."}),
            },
        }

    def run(self, fps, min_speed, min_area, preview, preview_size, save_report, images=None, video=None):
        if (images is None) == (video is None):
            raise ValueError("Motion Verdict: connect either 'images' or 'video' (exactly one).")
        source = images
        stream = None
        if video is not None:
            stream = streamable(video)
            if stream is None:  # cropped / rotated / in-memory VIDEO: let ComfyUI decode it
                parts = video.get_components()
                source, fps = parts.images, float(parts.frame_rate)
            else:
                fps = float(video.get_frame_rate())
        if stream is not None:
            gray, nonfinite = stream.analysis_frames(analysis.ANALYSIS_LONG_SIDE)
            height, width = stream.height, stream.width
        else:
            gray, nonfinite = frames.analysis_frames(source, analysis.ANALYSIS_LONG_SIDE)
            height, width = source.shape[1:3]

        overlay = preview == PREVIEW_OVERLAY
        res, masks = analysis.analyze(gray, nonfinite, fps, min_speed, min_area, keep_masks=overlay)
        text = report.text(res, min_speed, min_area)
        data = report.as_json(res, min_speed, min_area)
        timeline = chart.timeline(res.step_moving, res.step_camera, min_area, analysis.CAMERA_MIN_SPEED,
                                  res.step_flat)
        info = {"verdict": res.verdict, "headline": report.HEADLINES[res.verdict], "report": text,
                "token": None, "saved": None}
        if preview != PREVIEW_OFF and res.frames > 0:
            ph, pw = clip_preview.preview_size(height, width, preview_size)
            chunks = stream.chunks(ph, pw) if stream is not None else clip_preview.image_chunks(source, ph, pw)
            info["token"] = PREVIEWS.put(clip_preview.encode(chunks, fps, ph, pw, masks, res.step))
        if save_report:
            info["saved"] = save_json(data)
        return {"ui": {"motion_verdict": [info]},
                "result": (images, video, res.verdict, res.verdict == "animated", float(res.subject_motion),
                           timeline, text, data)}


def save_json(data):
    import folder_paths  # ComfyUI module; imported here so the analysis modules stay usable without ComfyUI

    out_dir = folder_paths.get_output_directory()
    folder, name, counter, subfolder, _ = folder_paths.get_save_image_path("motion_verdict/MotionVerdict", out_dir)
    os.makedirs(folder, exist_ok=True)
    filename = f"{name}_{counter:05}_.json"
    with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
        f.write(data)
    return {"filename": filename, "subfolder": subfolder, "type": "output"}
