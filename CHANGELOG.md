# Changelog

## 1.0.0 (unreleased)
First release of **Motion Verdict** (pack `comfyui-motion-verdict`, node id `MotionVerdict`).

- Removes the camera's global motion (robust affine fit: phase-correlated tiles, then a Gauss-Newton polish) and
  measures what still moves on its own (normal flow on the aligned frames).
- Verdict `animated` / `partly_animated` / `camera_only` / `still` / `unknown`, plus an `animated` BOOLEAN,
  a `subject_motion` FLOAT, a `timeline` IMAGE, a `report` STRING and a `json` STRING. Stalls (≥ 1 s without
  own motion) are listed with frame numbers.
- Camera numbers in the report: pan, tilt, zoom, roll, plus how much of the picture agrees with them.
- On-node preview, encoded to H.264 (crf 20) in memory (nothing saved, not even to `temp/`), 256-1440 px
  (`preview_size`). The default is the clean clip; `video + motion overlay` tints red what moves on its own.
- Input: an IMAGE batch, or a **VIDEO that is streamed**. FFmpeg shrinks each frame while decoding, so 4K and long
  clips never sit in memory at full size. Cropped / rotated VIDEOs fall back to ComfyUI's decoder. Passthrough
  `images` and `video` outputs.
- Optional `save_report`: the JSON also goes to `output/motion_verdict/`.
- Only torch, numpy and av. CPU only is fine. No network access.
