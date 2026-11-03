# Changelog

## 1.0.0 (unreleased)
First release of **Motion Verdict** (pack `comfyui-motion-verdict`, node id `MotionVerdict`).

- Removes the camera's global motion (robust affine fit: phase-correlated tiles, then a Gauss-Newton polish) and
  measures what still moves on its own (normal flow on the aligned frames).
- Verdict `animated` / `partly_animated` / `camera_only` / `still` / `unknown`, plus an `animated` BOOLEAN,
  a `subject_motion` FLOAT, a `timeline` IMAGE, a `report` STRING and a `json` STRING. Stalls (≥ 1 s without
  own motion) are listed with frame numbers.
- Camera numbers in the report: pan, tilt, zoom, roll, plus how much of the picture agrees with them.
- Optional on-node preview, encoded to H.264 in memory (nothing saved, not even to `temp/`), 256-1440 px
  (`preview_size`), with the parts that move on their own tinted red.
- Optional `save_report`: the JSON also goes to `output/motion_verdict/`.
- Only torch, numpy and av. CPU only is fine. No network access.
