# Test results (2026-11-03)

Environment:
- Linux container, 4 CPU cores, no GPU (`--cpu`).
- ComfyUI 0.43.0, frontend 1.57.6, Python 3.13.18, torch 2.15.0 (CPU), av 19.0.2, numpy 2.5.4.

## 1. Unit / known-answer / edge-case tests: `python tests/test_motion_verdict.py`

```
PASS  test_still_clip_is_still  (1.3s)
PASS  test_pan_right_is_camera_only_with_correct_sign_and_speed  (1.5s)
PASS  test_tilt_up_and_down  (2.9s)
PASS  test_zoom_in_and_out  (2.9s)
PASS  test_roll_sign  (1.3s)
PASS  test_combined_camera_move_over_still_picture_8bit  (1.4s)
PASS  test_moving_subject_static_camera_is_animated  (1.3s)
PASS  test_moving_subject_with_pan_and_with_zoom  (2.6s)
PASS  test_small_subject_is_found  (1.3s)
PASS  test_motion_that_stops_is_partly_animated_with_a_stall  (1.4s)
PASS  test_clip_that_starts_moving_late_reports_the_stall_at_the_start  (1.5s)
PASS  test_noise_and_flicker_on_a_still_picture_are_still  (1.4s)
PASS  test_noise_on_camera_move_is_camera_only  (1.4s)
PASS  test_black_clip_is_still_with_a_note  (0.0s)
PASS  test_slow_drift_below_camera_threshold_is_still  (1.5s)
PASS  test_empty_and_single_frame  (0.0s)
PASS  test_two_frames  (0.1s)
PASS  test_odd_and_tiny_sizes  (0.0s)
PASS  test_portrait_clip  (0.9s)
PASS  test_channels_1_and_4_match_3  (1.5s)
PASS  test_nan_inf_counted_and_input_untouched  (0.6s)
PASS  test_chunked_conversion_is_identical  (0.1s)
PASS  test_long_clip_bounded_and_fast  (18.1s)
PASS  test_other_frame_rates  (4.0s)
PASS  test_node_outputs_and_passthrough  (0.8s)
PASS  test_node_preview_off_and_animated_flag_false  (0.7s)
PASS  test_preview_size_range_and_no_upscale  (2.7s)
PASS  test_preview_store_evicts_oldest  (0.0s)

28 passed, 0 failed, 59s
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
