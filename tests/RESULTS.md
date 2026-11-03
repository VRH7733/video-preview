# Test results (2026-11-03)

Environment:
- Linux container, 4 CPU cores, no GPU (`--cpu`).
- ComfyUI 0.43.0, frontend 1.57.6, Python 3.13.18, torch 2.15.0 (CPU), av 19.0.2, numpy 2.5.4.

## 1. Unit / known-answer / edge-case tests: `python tests/test_motion_verdict.py`

```
PASS  test_still_clip_is_still  (0.9s)
PASS  test_pan_right_is_camera_only_with_correct_sign_and_speed  (0.9s)
PASS  test_tilt_up_and_down  (1.6s)
PASS  test_zoom_in_and_out  (1.5s)
PASS  test_roll_sign  (0.8s)
PASS  test_combined_camera_move_over_still_picture_8bit  (1.1s)
PASS  test_moving_subject_static_camera_is_animated  (0.7s)
PASS  test_moving_subject_with_pan_and_with_zoom  (1.4s)
PASS  test_small_subject_is_found  (0.7s)
PASS  test_motion_that_stops_is_partly_animated_with_a_stall  (0.8s)
PASS  test_clip_that_starts_moving_late_reports_the_stall_at_the_start  (0.9s)
PASS  test_noise_and_flicker_on_a_still_picture_are_still  (0.7s)
PASS  test_noise_on_camera_move_is_camera_only  (0.7s)
PASS  test_black_clip_is_still_with_a_note  (0.0s)
PASS  test_slow_drift_below_camera_threshold_is_still  (0.7s)
PASS  test_empty_and_single_frame  (0.0s)
PASS  test_two_frames  (0.0s)
PASS  test_odd_and_tiny_sizes  (0.0s)
PASS  test_portrait_clip  (0.4s)
PASS  test_channels_1_and_4_match_3  (0.5s)
PASS  test_nan_inf_counted_and_input_untouched  (0.3s)
PASS  test_chunked_conversion_is_identical  (0.1s)
PASS  test_long_clip_bounded_and_fast  (8.8s)
PASS  test_other_frame_rates  (1.5s)
PASS  test_node_outputs_and_passthrough  (0.4s)
PASS  test_node_preview_off_and_animated_flag_false  (0.3s)
PASS  test_preview_size_range_and_no_upscale  (2.0s)
PASS  test_video_input_streams_and_matches_images  (3.3s)
PASS  test_video_trim_window_is_honoured  (0.3s)
PASS  test_cropped_video_falls_back_to_comfy_decoder  (0.2s)
PASS  test_exactly_one_input_required  (0.0s)
PASS  test_video_stream_memory_does_not_grow_with_resolution  (34.2s)
PASS  test_preview_store_evicts_oldest  (0.0s)

33 passed, 0 failed, 66s
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

  **Correction.** An earlier version of this file reported "+247 MB streamed vs +1,771 MB as IMAGE batch". That
  was **wrong**. The probe allocated 1 GB before the run (to keep import-time memory out of the peak), which
  also hid the first ~1 GB of the run itself. The Windows run (section 8) exposed it.

## 8. Memory, measured correctly (after the second Windows report)

**Windows report.** With `peak_pagefile` on Windows, the control registered (1,705 MB > 1,012 MB), but the
streamed run read 1,089 MB, over the 337 MB limit. Re-measuring on Linux with a resettable peak counter
(`/proc/self/clear_refs` → `VmHWM`), a 32-frame 2560×1440 clip:

| Run | Before the fix | After the fix |
|---|---|---|
| VIDEO, preview off / 512 px | 386 MB | 383 MB |
| VIDEO, preview 1440 px | **1,272 MB** | **392 MB** (pixel-budget chunks + in-place tint) → 289 MB (with the next two changes) |
| IMAGE batch (already in memory), preview 1440 px | 529 MB | 477 MB |

Changes:
- **Streamed preview chunks:** a pixel budget (2 M pixels, 24 MB as float) instead of 16 frames.
- **Tint and quantise in place.**
- **Pair batch 32 → 16:** −70 MB; 8 saved nothing more.
- **FFmpeg decode threads capped at 4.** "Auto" starts about one thread per core, each holding frames, so
  memory would grow with the core count on big PCs and servers. On 4 cores the decoder used 150-200 MB in every
  mode, with no speed difference.

**New memory test** (`test_video_stream_memory_does_not_grow_with_resolution`). It checks the property that
matters, not a fixed number:

| Run | Extra memory |
|---|---|
| Streamed 720p (32 frames) | **266 MB** |
| Streamed 1440p (4× the pixels) | **289 MB** (+23 MB) |
| Same 1440p clip as an IMAGE batch (control) | **2,775 MB** |

The checks are:
- the control must exceed 75% of the 1,350 MB batch, so a blind probe fails;
- the streamed growth must stay under ¼ of the full-size growth;
- the streamed run must stay under half the control.

Measurement methods:
- **Linux:** reset the high-water mark, then read it (exact).
- **Windows / macOS:** sample current committed memory every 2 ms during the run. Forcing that branch on Linux
  gave 293 / 2,775 MB, the same as the exact method.

Speed after the changes:
- 1,496 frames: 13.5 s (was 18 s).
- 4K portrait clip: 5.0 s (was 5.8 s).

Unit tests: **33/33 pass** on Linux.

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

## 9. Speed (after the third Windows report)

**Windows report.** Commit a25b1a9 on a 2-core Ryzen 3 3250U with 5.9 GB RAM:
- 32/33 tests passed.
- The memory test passed.
- The long-clip test took **123.3 s against its 120 s limit**, with the ComfyUI server running; 74 s on its
  own.
- API runs: success, `animated`; 4K clip in 41.3 s.

The 120 s limit was **not** raised. The code was made faster instead, profiled at 2 threads to match that
laptop. On 1,496 frames, 2 threads:

| Step | Time |
|---|---|
| before | 25.3 s |
| blur each frame once per clip (each frame was blurred ~4×, once per pair it belongs to) | 16.7 s |
| blur as shifted adds instead of `conv2d` with a 1×5 kernel (6.1× faster, same output to 1.8e-7) | 10.8 s |
| polish on every 2nd pixel with frame *t*'s fixed gradients (no full warp per iteration) + one tile pass instead of two | **9.2 s** |

- **Overall: 2.75×**, against a 3× target that was missed. Tried and rejected: `unfold` tile cutting (7× slower)
  and 2 polish iterations instead of 3 (−0.3 s, slightly less accurate).
- **4 threads:** the long-clip test takes 8.8 s (was 13.5 s), and the full suite 66 s (was 84 s).
- **Unit tests:** 33/33.

Judges, comparing every verdict against the previous run:
- **Real clips:** **0 verdict changes** across 230. Own motion new/old: median 1.003, 5th percentile 0.984,
  worst 0.949. Active-share change: median 0.000, largest 0.025. Analysis is 2.8× faster (2.43 → 0.86 s per
  clip).
- **Known-answer clips: 194/195.** The one change is `api_kling_o3_flf2v-1__freeze` (`partly_animated` →
  `still`).
  - Its source barely moves for the first 0.5 s, so the variant has only ~0.3 s of motion in 3 s.
  - Its deciding quarter-second step reads ≈ 0.30% against the 0.30% threshold, so active = 6/41 = 0.146,
    against a cut-off of 0.15.
  - Restoring the second tile pass did not change it.
  - It is reported as a knife-edge case. Nothing was tuned to rescue it.

## 10. Final Windows check (the user's PC, commit bfa7eb2)

Setup:
- Machine: 2-core Ryzen 3 3250U, 5.9 GB RAM, Windows 10.
- ComfyUI Desktop 0.43.1, started with `--cpu`; Python 3.13.12, torch 2.12.0+rocm7.14.0, av 19.0.2, numpy 2.5.4.

Results:
- **Unit tests with the ComfyUI server running (worst case): 33 passed, 0 failed.**
- **4K portrait API run** (`6319577-uhd_2160_3840_25fps.mp4`, 285 frames, VIDEO input, streamed): `success`,
  verdict `animated`, 24.9 s. The server log shows the prompt in 24.48 s, the node loading in 0.1 s, and no
  errors or tracebacks.
- **The same 4K run across commits:** 54.4 s (b4cd6ea) → 41.3 s (a25b1a9) → **24.9 s** (bfa7eb2).
  - Before the streamed input existed, this clip could not be analysed at all on this PC: a 28 GB IMAGE batch.

## 11. VIDEO from another node, no disk writes

Three ways of feeding a VIDEO were run through real ComfyUI with `preview_size` 1440 and `save_report` off:

| Feed | Result | Preview served from RAM |
|---|---|---|
| A: *Load Video → Motion Verdict* | `animated` | 201 KB |
| B: *Load Video → Get Video Components → Create Video (codec none) → Motion Verdict* (what a generator workflow ends with) | `animated` | 199 KB |
| C: same, Create Video with `codec` auto (encoded in memory) | `animated` | 199 KB |

- **Disk:** `find / -xdev -newer <mark>` listed **no file created or changed** during the three runs (logs and
  caches excluded).
- **Code check:** ComfyUI's `VideoFromComponents` and `VideoFromList` keep or build their data in RAM (`BytesIO`).
- **UI:** both example workflows were exported from the real frontend and run there: badge `ANIMATED`, on-node
  preview playing, no page errors.

## 12. Clean default preview, and publishing

**Clean default preview** (commit c4c8339): `preview` defaults to `video`, the clean clip, and the red overlay is
opt-in; encoding is crf 20. Checks:
- **ComfyUI:** the server lists `['video', 'video + motion overlay', 'off']` with default `video`.
- **UI:** both example workflows were re-exported from the real UI with that default and run there: badge
  `ANIMATED`, the clean preview playing (screenshot `assets/preview_clean.png`), no page errors.
- **Disk:** no file was created or changed in ComfyUI's folders or `/tmp` during those runs. Chromium's own
  profile and the logs were excluded.

**Published** (by the user's local session from commit ecae002):
- GitHub: https://github.com/VRH7733/ComfyUI-MotionVerdict (public).
- Comfy Registry: workflow run 41637314810 succeeded in 26 s, with "All validation checks passed successfully …
  Upload successful".
- Registry page: https://registry.comfy.org/nodes/comfyui-motion-verdict (id `comfyui-motion-verdict`, publisher
  `raghav`, node active; version 1.0.0 pending at the time of the report).
