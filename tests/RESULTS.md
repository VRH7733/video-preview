# Test results (2026-11-03)

Environment:
- Linux container, 4 CPU cores, no GPU (`--cpu`).
- ComfyUI 0.43.0, frontend 1.57.6, Python 3.13.18, torch 2.15.0 (CPU), av 19.0.2, numpy 2.5.4.

## 1. Unit / known-answer / edge-case tests: `python tests/test_motion_verdict.py`

```
PASS  test_still_clip_is_still  (1.4s)
PASS  test_pan_right_is_camera_only_with_correct_sign_and_speed  (1.2s)
PASS  test_tilt_up_and_down  (2.4s)
PASS  test_zoom_in_and_out  (2.3s)
PASS  test_roll_sign  (1.3s)
PASS  test_combined_camera_move_over_still_picture_8bit  (1.3s)
PASS  test_moving_subject_static_camera_is_animated  (1.1s)
PASS  test_moving_subject_with_pan_and_with_zoom  (2.5s)
PASS  test_small_subject_is_found  (1.3s)
PASS  test_motion_that_stops_is_partly_animated_with_a_stall  (1.1s)
PASS  test_clip_that_starts_moving_late_reports_the_stall_at_the_start  (1.2s)
PASS  test_noise_and_flicker_on_a_still_picture_are_still  (1.3s)
PASS  test_noise_on_camera_move_is_camera_only  (1.4s)
PASS  test_black_clip_is_still_with_a_note  (0.0s)
PASS  test_slow_drift_below_camera_threshold_is_still  (1.3s)
PASS  test_empty_and_single_frame  (0.0s)
PASS  test_two_frames  (0.1s)
PASS  test_odd_and_tiny_sizes  (0.0s)
PASS  test_portrait_clip  (0.9s)
PASS  test_channels_1_and_4_match_3  (1.4s)
PASS  test_nan_inf_counted_and_input_untouched  (0.6s)
PASS  test_chunked_conversion_is_identical  (0.1s)
PASS  test_long_clip_bounded_and_fast  (18.1s)
PASS  test_other_frame_rates  (4.5s)
PASS  test_node_outputs_and_passthrough  (0.9s)
PASS  test_node_preview_off_and_animated_flag_false  (0.7s)
PASS  test_preview_size_range_and_no_upscale  (2.1s)
PASS  test_video_input_streams_and_matches_images  (4.4s)
PASS  test_video_trim_window_is_honoured  (0.4s)
PASS  test_cropped_video_falls_back_to_comfy_decoder  (0.3s)
PASS  test_exactly_one_input_required  (0.0s)
PASS  test_video_stream_never_holds_full_size_frames  (28.5s)
PASS  test_preview_store_evicts_oldest  (0.0s)

33 passed, 0 failed, 84s
```

Speed on 4 CPU cores:
- 1,496 frames at 256×144: 18.4 s.
- A Wan-size clip (81 frames at 832×480): 2.7 s.

## 2. Real AI-generated clips: `python tests/eval_clips.py <folder>`

No `real_clips/` folder existed, so the clips came from ComfyUI's own template packages
(`comfyui_workflow_templates_media_*`). These ship animated-WebP thumbnails of example outputs of real video
models:

| Model family | Clips |
|---|---|
| Wan | 51 |
| LTX | 28 |
| Seedance | 24 |
| Kling | 21 |
| MiniMax / Hailuo | 18 |
| Vidu | 13 |
| PixVerse | 8 |
| Grok | 6 |
| HappyHorse | 6 |
| Gemini | 5 |
| Flux video | 4 |
| Luma | 4 |
| Runway | 4 |
| Hunyuan | 3 |
| other | 35 |

Clip properties:
- 300-512 px squares at 15-30 fps, ~62 frames on average.
- Edit, upscale, background-removal, lip-sync and 3-D turntable templates were excluded.

Result: **230 clips: animated 229, partly_animated 1.** Own motion: median 36.2%, minimum 0.14%.

The only non-`animated` clip is `video_wan_vace_outpainting-1`:
- The woman is almost motionless for the first 2.2 s, then opens her eyes and smiles.
- Verdict: `partly_animated`, stall frames 0-33. This matches the contact sheet.
- These showcase clips carry no ground-truth labels, so I count it as one disagreement with the assumption
  "every showcase clip is animated", not as a confirmed error.

What this shows: no false `camera_only` / `still` on 230 real, animated AI clips.

What it does not show: performance on full-resolution user generations, or on real bad clips (none were
available).

## 3. Known-answer clips built from real AI frames: `tests/derive_clips.py` + `eval_clips.py`

Source: 39 of the clips above. All variants are re-encoded with libx264 (crf 23) at 15 fps.

| Variant | Expected | Result | Max own motion |
|---|---|---|---|
| frame 0 held 3 s | still | **39/39 still** | 0.00% |
| zoom-in 15% + pan over frame 0 (bicubic) | camera_only | **39/39 camera_only** | 0.08% |
| pan 25% + tilt 8% + roll 3° over frame 0 | camera_only | **39/39 camera_only** | 0.20% (threshold 0.3%) |
| real clip 0.8 s, then frozen 2.2 s | partly_animated | **39/39 partly_animated** | |
| real clip re-encoded | animated | **39/39 animated** | |

**195/195 correct.**

### How the gradient floor and regulariser were chosen

The sweep (camera fit cached, same 195 clips + 87 real clips + 4 synthetic checks):

| Settings | Errors (derived + real + synthetic) | Worst camera-only own motion | Weakest real clip |
|---|---|---|---|
| no polish, λ 0.01 / floor 0.004 | 2 + 0 + 0 = 2 | 0.44% | 1.60% |
| no polish, λ 0.02 / floor 0.006 | 1 + 0 + 1 = 2 | 0.16% | 0.79% |
| no polish, λ 0.02 / floor 0.01 | 1 + 0 + 0 = 1 | 0.16% | 0.91% |
| no polish, λ 0.03 / floor 0.01 | 3 + 1 + 1 = 5 | 0.08% | 0.38% |
| no polish, λ 0.04 / floor 0.015 | 3 + 1 + 1 = 5 | 0.04% | 0.20% |
| polish, λ 0.01 / floor 0.004 | 5 + 0 + 0 = 5 | 0.57% | 1.84% |
| polish, λ 0.02 / floor 0.006 | 1 + 0 + 1 = 2 | 0.20% | 0.93% |
| **polish, λ 0.02 / floor 0.01 (shipped)** | **0 + 0 + 0 = 0** | **0.20%** | **1.07%** |

"Real" in this sweep = every third real clip (87). The sweep's numbers come from the same code with the camera
fit cached. The tables in sections 2-3 come from the final, uncached run.

## 4. ComfyUI integration

- **Loader:** the package is loaded from `custom_nodes/` by ComfyUI's own loader.
  - `/object_info` lists 1,035 nodes: the 1,034 core nodes plus `MotionVerdict`, with no collision and no
    core node missing.
  - `/extensions` serves `motion_verdict.js`.
- **API, no browser:** `python tests/api_run.py mv_camzoom.mp4 mv_real.mp4 mv_still.mp4`. The workflow is
  Load Video → Get Video Components → Motion Verdict → Preview Any + Save Image, with `save_report` on.
  Each of the three runs returned:
  - `status=success`;
  - the node's `ui` verdict;
  - the Preview Any text starting "Motion Verdict: ...";
  - a saved `output/motion_verdict/MotionVerdict_0000N_.json`;
  - a saved timeline PNG.

  Verdicts: `camera_only`, `animated`, `still`, as expected.
- **UI:** `node tests/ui_run.js` in headless Chromium drives the real frontend.
  - It builds the graph, exports it to `examples/`, queues it, and waits for the verdict badge and the
    on-node `<video>` (blob URL, `readyState ≥ 2`).
  - Every console 404 came from ComfyUI's own requests (user.css, userdata, update check, template model
    downloads). None came from this node.

## 5. Preview: disk-free and 256-1440 px

- **No disk writes.**
  - A full ComfyUI run (Load Video → Get Video Components → Motion Verdict, `save_report` off) returned
    `success`.
  - The 204 KB preview MP4 was served from memory by `/motion_verdict/preview/<token>`.
  - `find / -xdev -newer <mark>` listed **no file created or changed anywhere on the disk** during the run
    (logs excluded), including ComfyUI's `temp/` and `output/`.
- **Preview size.** `test_preview_size_range_and_no_upscale`:
  - 1080p input → 1440×810 at 1440 and 256×144 at 256;
  - a 321×181 input stays 320×180 (no upscale; even sizes).
- **Cost.** 81 frames of 1080p take 7.1 s in total at 512 px and 10.4 s at 1440 px; the preview is 0.40 MB at
  1440 px. Peak memory did not rise above what building the 2 GB test clip itself had already used.
- **In the browser.** Headless Chromium, real UI, 1080p clip, `preview_size` 1440: the on-node `<video>` plays
  at 1440×810, 3.06 s, verdict `ANIMATED`, and only the moving patch is tinted.

## 6. Windows 10, ComfyUI Desktop (the user's PC), run by a local Claude session

Environment:
- ComfyUI 0.43.1 Desktop, standalone install "test", started with `--enable-manager --cpu --max-upload-size 1024`.
- Python 3.13.12, torch 2.12.0+rocm7.14.0, av 19.0.2, numpy 2.5.4.
- Code: commit 36281b5.

Results:
- **Unit tests: 28 passed, 0 failed** (253 s; the long-clip test took 94 s of its 120 s budget).
- **Node loading:** ComfyUI's loader took 0.1 s with no import errors.
- **`/object_info/MotionVerdict`:** HTTP 200, with the expected inputs and outputs.
- **API run** (`api_run.py`, port 8188, `example_with_audio.mp4`): `status=success`, verdict `animated`, Preview Any
  text, a saved JSON and a timeline PNG.
- **Real clips on that PC:**

  | Clip | Result |
  |---|---|
  | `example_with_audio.mp4` | `animated` |
  | `videoplayback.mp4` | `animated` |
  | `6319577-uhd_2160_3840_25fps.mp4` (4K portrait, 285 frames) | **failed**: the old test script decoded it into one 28 GB float tensor |

  That failure would also happen to users via *Load Video → Get Video Components*. It led to the streamed
  `video` input (section 7).

## 7. Streamed VIDEO input (after the Windows report)

- **Unit tests:** 5 new tests:
  - the same verdict as the IMAGE path, on an animated clip and on a camera-only clip;
  - the trim window (16 frames from 1 s);
  - the crop fallback to ComfyUI's decoder;
  - exactly one input required;
  - memory, measured in a separate process with a control.

  Result of the memory test on a 32-frame 2560×1440 clip with a 1440 px preview:
  - streamed VIDEO: **+247 MB**;
  - the same clip as an IMAGE batch: **+1,771 MB**.

  The control must exceed 75% of the 1,350 MB batch, so the test cannot pass with a broken measurement. It
  caught one: on Linux, `ru_maxrss` is inherited from the parent process, so the probe now reads `VmHWM`
  (Linux) or `peak_wset` (Windows).
- **4K portrait clip** (75 frames, 2160×3840, 25 fps; planted subject + 2 px/frame tilt):
  - `eval_clips.py` (streaming): `animated`, tilt 1.3%/s; 5.8 s wall time; peak memory of the whole script
    1,088 MB, against 7,119 MB for one full-size batch.
  - Real ComfyUI, *Load Video → Motion Verdict*: `success` in 5.0 s; the server's lifetime peak was 1,830 MB
    (idle before: 1,263 MB).
  - Real UI: the preview plays at 810×1440.
- **API, both input paths, real ComfyUI `VideoFromFile`:** `mv_camzoom` → `camera_only` / `camera_only`,
  `mv_real` → `animated` / `animated`, `mv_still` → `still` / `still` (video input / images input).
- **Same clips, streamed decoding** (`eval_clips.py` now uses the node's VIDEO reader, where FFmpeg does the
  shrinking):
  - Derived clips: **195/195 correct** again. Worst camera-only own motion: 0.000%, against 0.197% via the
    IMAGE path. FFmpeg's downscaler smooths slightly more (≈ 4 grey levels mean difference at 350 → 320 px).
  - Real clips: **0 verdict differences** against the IMAGE path on all 230 (229 `animated`, 1
    `partly_animated`).
  - Own motion via streaming = **0.98×** the IMAGE-path value (median), 0.93× at the 10th percentile. The extra
    smoothing removes codec shimmer, not real motion.
  - The 29 single-frame still images in the folder now decode and come back `unknown` (fewer than 2 frames).
