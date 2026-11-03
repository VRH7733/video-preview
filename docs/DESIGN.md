# Motion Verdict: design

## 1. Purpose

AI video models often return clips that *look* like video but are not animated:
- a slow zoom or pan over the start image (a "Ken Burns" move, common with image-to-video);
- an almost frozen clip;
- a clip that moves for a second and then stalls.

Frozen-frame QC compares raw frames, so a camera move over a still picture passes it: the pixels do change.

**Motion Verdict removes the camera's global motion first, then measures what still moves on its own.** It
returns:
- a verdict;
- a BOOLEAN for gating (keep or drop a seed in a batch or an AI App run);
- a subject-motion number;
- stall times;
- a timeline image and a JSON report.

All of these are ordinary node outputs, so they work in API runs with no browser. An optional in-memory preview
on the node shows what moved.

## 2. Node schema (exact ComfyUI contract)

Node id `MotionVerdict` · display name "Motion Verdict (animated / camera-only / still)" · category
`video/Motion Verdict` · `OUTPUT_NODE = True` · function `run`.

| Input | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `images` (optional) | IMAGE | | | the clip, (N, H, W, C) float. Exactly one of `images` / `video` |
| `video` (optional) | VIDEO | | | the clip as a VIDEO, streamed (see §3.0). Exactly one of `images` / `video` |
| `fps` | FLOAT | 16.0 | 1-240, step 0.01 | frame rate of `images` (Wan 16, LTX 24/25). A `video` uses `get_frame_rate()` |
| `min_speed` | FLOAT | 1.5 | 0.1-50 | % of the frame per second a pixel must move, after camera removal, to count |
| `min_area` | FLOAT | 0.3 | 0.01-50 | % of the textured picture that must move for a time step to count as moving |
| `preview` | COMBO | `video + motion overlay` | `video + motion overlay`, `video`, `off` | on-node preview |
| `preview_size` | INT | 512 | 256-1440, step 64 | longest side of the preview (never upscaled; even sizes for yuv420p) |
| `save_report` | BOOLEAN | False | | also write the JSON to `output/motion_verdict/MotionVerdict_#####_.json` |

| # | Output | Type | Content |
|---|---|---|---|
| 0 | `images` | IMAGE | the `images` input, **same object**, untouched (None when `video` was used) |
| 1 | `video` | VIDEO | the `video` input, **same object**, untouched (None when `images` was used) |
| 2 | `verdict` | STRING | `animated` \| `partly_animated` \| `camera_only` \| `still` \| `unknown` |
| 3 | `animated` | BOOLEAN | `verdict == "animated"` |
| 4 | `subject_motion` | FLOAT | mean % of textured pixels that move on their own |
| 5 | `timeline` | IMAGE | (1, 192, 768, 3) chart |
| 6 | `report` | STRING | readable report |
| 7 | `json` | STRING | all numbers + per-time-step arrays |

`run()` returns `{"ui": {"motion_verdict": [info]}, "result": (outputs 0-7)}`, where `info` =
`{verdict, headline, report, token, saved}`:
- `token` is the preview key, or null;
- `saved` is the `{filename, subfolder, type}` of the JSON file, or null.

The `ui` part is stored in ComfyUI's `/history`, so API clients can read the verdict without any extra node.

## 3. Pipeline

0. **VIDEO input** (`video_source.py`, `node.streamable`):
   - A VIDEO that exposes its file and trim window (`get_stream_source`, `get_active_trim_window`), with
     dimensions equal to the raw stream (not cropped) and no rotation, is **streamed** with PyAV.
   - Each decoded frame is scaled by FFmpeg (`reformat`, area filter) straight to the analysis size, and in a
     second pass to the preview size. 16 shrunk frames are batched into a tensor.
   - Trim is the same as ComfyUI's decoder: `start ≤ pts < start + duration`.
   - Any other VIDEO (cropped, rotated, in memory) goes through `get_components()`, then the IMAGE path below.
1. **Analysis frames** (`frames.py`, IMAGE path):
   - Rec.601 luma of the first 3 channels. C=1 or 2 uses channel 0; C=4 ignores alpha.
   - NaN/Inf are counted, then replaced (NaN→0, +Inf→1, −Inf→0) **in the analysis copy only**, and clamped
     to 0..1.
   - Area-downscaled so the long side is at most **320 px** (never upscaled).
   - Converted in chunks of at most `CHUNK_PIXELS` = 24 M full-size values, so the extra memory is bounded
     for any clip length.
2. **Pairs:** frames *t* and *t+k* with **k = round(0.25 s × fps)**, clamped to 1..N−1. That gives N−k
   overlapping pairs, processed 16 at a time.
3. **Camera motion** (`camera.py`, all batched over pairs):
   1. Whole-frame phase correlation with a Hann window gives the coarse shift.
   2. 64 px tiles at half-tile spacing (45 tiles at 320×180). The second frame is warped by the current
      estimate, then each tile is phase-correlated, with parabolic sub-pixel peaks; peak height = confidence.
   3. A robust affine fit of `x_b = x + t + M x` to the tile shifts: Tukey IRLS, 5 iterations,
      c = 4.685 × (1.4826·MAD + 0.1 px). Tiles on a moving subject get weight 0.
   4. Steps 2-3 run twice.
   5. A robust Gauss-Newton (Lucas-Kanade) polish of the 6 affine parameters on all pixels, 3 iterations,
      same Tukey weights.
   6. Readable terms:
      - pan / tilt: −t_x / w and t_y / h, in % per second (content moving left = the camera pans right);
      - zoom: ½·log det(I+M), in % per second;
      - roll: atan2(m21 − m12, 2 + m11 + m22), in degrees per second, sign flipped to the camera's view;
      - camera speed: the largest corner displacement, in % of the long side per second.
4. **Own motion** (`residual.py`):
   1. Warp frame *t+k* onto frame *t* with the camera transform.
   2. Binomial blur (σ≈1 px).
   3. Remove the global gain and offset, so exposure flicker is not read as motion.
   4. Normal-flow magnitude: |ΔI|·|∇I| / (|∇I|² + λ²).
   5. Pixels count only if they are inside the warp, ≥2 px from the border and textured (|∇I| ≥ GRAD_MIN).
   6. A pixel moves "on its own" if its normal flow is ≥ `min_speed`, converted to px per pair.
   7. A 3×3 majority filter (≥5 of 9 neighbours) removes speckle.
   8. Per pair: moving share = moving pixels ÷ textured pixels.
5. **Verdict** (`analysis.py`):
   - A time step is *active* if moving share ≥ `min_area` and it has ≥ 2% textured pixels.
   - `active_ratio` = share of active steps.
   - The verdict is the first rule that matches:
     1. active_ratio ≥ **0.5** → `animated`
     2. active_ratio ≥ **0.15** → `partly_animated`
     3. median camera speed ≥ **1.5%/s** → `camera_only`
     4. otherwise → `still`
   - All steps flat (black, empty) → `still` with a note. N < 2 → `unknown`.
   - **Stalls** are reported for `animated` and `partly_animated`: runs of inactive steps covering
     ≥ **1.0 s**, as frame ranges [t₀, t₁ + k].

## 4. Thresholds and why

| Constant | Value | Why |
|---|---|---|
| analysis long side | 320 px | Phase correlation and normal flow are accurate to well under 1 px here, so 1/320 of the frame is still measurable. Cost is ~1.5 s per 3 s clip on 4 CPU cores. |
| step | 0.25 s | Slow motion adds up over k frames while per-frame noise does not. A shorter step needs a lower px threshold, which is closer to the codec-noise floor. |
| `min_speed` | 1.5 %/s | Measured on synthetic clips (`calib` in tests): Gaussian noise σ = 0.04 and 8×8 block artefacts gave residual "motion" above 1.0 %/s but **none above 1.5 %/s**. 1.5 %/s is ~19 px/s on a 1280 px frame: slow, but visible. |
| `min_area` | 0.3 % | A 36×64 px subject (1% of a 640×360 frame) moving 1-2 px/frame registers 0.30-0.61 %. The worst of 78 camera-only clips built from real AI frames registers 0.20 %. The weakest of 230 real AI clips averages 0.14 % but moves 0.3 %+ during its active part (`partly_animated`). |
| camera threshold | 1.5 %/s at the fastest corner | Below this, a drift reads as "static" to a viewer; above it, a pan or zoom is visible. A 0.5 %/s synthetic drift is classed as `still` (test). |
| animated / partly | 0.5 / 0.15 of time | "Animated" = it moves most of the time. "Partly" = it clearly moves, but for less than half of the clip (e.g. 1 s of motion, then 2 s frozen = 0.31). |
| stall | 1.0 s | Shorter pauses are normal (a held pose); 1 s of nothing is noticeable. |
| `PEAK_MIN` | 0.08 | Phase-correlation peaks of pure noise are ~0.02-0.05. |
| `GRAD_MIN`, `λ` | 0.01, 0.02 | Set by the real-content sweep (`tests/RESULTS.md` §3). Below the gradient floor, codec shimmer divided by a tiny gradient looks like large motion. At 0.004 / 0.01 the worst camera-only clip showed 0.44 % own motion and 2 of 78 were misjudged; at 0.01 / 0.02 it is 0.20 % and all 195 known-answer clips are right. Larger values started to lose real subtle motion (4-5 errors). |
| low texture | 2 % of pixels | Below that, nothing can be measured (black or flat frames). |

All thresholds are tuned on synthetic clips and on clips derived from real AI video thumbnails (§7). They are
**not calibrated on full-resolution user generations**: see Known limits.

## 5. Edge cases

| Case | Behaviour |
|---|---|
| empty batch (N = 0) | `unknown`, note "The image batch is empty.", empty timeline, no preview |
| N = 1 | `unknown`, note "Need at least 2 frames" |
| N = 2 | k = 1, one pair, normal verdict |
| odd sizes (37×53) | fine: tiles are placed with `linspace`; the preview crops to even size |
| tiny (9×11, 3×5, 180×1) | camera estimate skipped when tiles cannot fit (note), residual skipped below 7 px; a verdict is still returned |
| C = 1 / C = 4 | luma of channel 0 / RGB (alpha ignored); same verdict as RGB (test) |
| NaN / Inf | counted (reported in the JSON and the notes), replaced only in the analysis copy; the passthrough is the same untouched tensor (test) |
| black / flat clip | `still`, note |
| 4K / long files | use the `video` input (streamed); the `images` path needs the full batch to exist upstream |
| cropped / rotated VIDEO | falls back to ComfyUI's `get_components()` (exact same frames, but full size in memory) |
| both or neither of `images` / `video` | `ValueError` with a clear message |
| very long clips | chunked conversion; memory is the 320 px analysis copy (N × 320 × 180 × 4 B ≈ 230 KB per frame) plus 32-pair work buffers; 1,500 frames in the test |
| portrait | long side → 320 (180×320) |
| fps 8 / 24 / 30 | k adapts; numbers are per second (test) |

## 6. Memory plan

- **VIDEO input:** full-size frames exist only inside FFmpeg, one at a time, plus its decoder threads.
  FFmpeg decoding is capped at 4 threads; shrunk frames are turned into tensors 2 M pixels at a time. Measured
  (32 frames, whole node run, 1440 px preview): 720p +266 MB, 1440p +289 MB. The same 1440p clip as an IMAGE batch
  adds +2,775 MB.
  4K portrait (75 frames) in ComfyUI: server peak ≤ 0.6 GB above idle, against 7.1 GB for the IMAGE batch.
- **IMAGE input:** the batch already exists (made by ComfyUI). It is never copied as a whole: at most
  `CHUNK_PIXELS` values are converted at a time.
- The analysis copy is N × h × w float32, at most 320 px on the long side. Example: 241 frames of 1080p use
  56 MB, against 6 GB for the IMAGE batch itself.
- Pair processing holds 16 pairs at a time: warped frames, tiles, FFTs, the Gauss-Newton Jacobian
  (16 × 6 × 57,600 floats = 22 MB).
- Moving-pixel masks (bool, analysis size) are kept only when the overlay preview is on.
- The preview is encoded while streaming: one chunk of frames is downscaled to ≤ `preview_size` (256-1440 px)
  and encoded, then dropped. Measured on 81 frames of 1080p: 0.40 MB at 1440 px; the node adds 3.3 s over the
  512 px setting. The finished MP4 lives in an in-memory store: 16 clips / 256 MB, least recently used out first.
- Nothing is written to disk unless `save_report` is on, and then only into ComfyUI's output folder.

## 7. Calibration data (what was actually measured)

The sources are real AI-generated clips. ComfyUI's own template packages (`comfyui_workflow_templates_media_*`)
include animated WebP thumbnails of example outputs from Wan 2.x, LTX-2, Hunyuan, MiniMax/Hailuo, Kling,
Seedance, Vidu, PixVerse, Veo, Luma, Runway and others. They are 300-512 px squares at 15-30 fps.
`tests/eval_clips.py` runs the node on a folder, and `tests/derive_clips.py` builds known-answer variants
from those clips. All variants are re-encoded with H.264, so codec noise is present:

- frame 0 held (expected `still`);
- a zoom-in + pan over frame 0 (expected `camera_only`);
- a pan + roll over frame 0 (expected `camera_only`);
- 0.8 s of the real clip, then frozen (expected `partly_animated`);
- the clip itself (expected `animated`).

Results are in `tests/RESULTS.md`: 195/195 known-answer clips correct; 229/230 real clips `animated`.

## 8. Known limits

1. **Parallax counts as own motion.** A real 3D camera move (dolly, orbit) over a static scene leaves motion
   that no single 2-D affine explains, so it reads as `animated`. This is by design: only a flat 2-D move
   over a still picture is `camera_only`.
2. **A subject that fills most of the frame** can be taken as "the camera" by the robust fit. The verdict is
   still `animated`, because the background then moves on its own, but the camera numbers describe the
   subject.
3. **Boiling textures and shimmering detail** (AI artefacts, heavy grain with σ ≳ 0.06, strong
   compression) can read as own motion. Raise `min_speed` for such footage.
4. **Very slow motion** under `min_speed` (e.g. 1.25 %/s) is not counted, by definition.
5. Normal flow sees motion across edges only. Motion along an edge, or of a texture-less object, is
   under-counted.
6. Fine periodic patterns (grids, fabric) under rotation + re-encoding produce some false motion. The worst
   case in calibration was 0.20 % against the 0.3 % threshold, so the margin is about 1.5×.
7. Camera numbers describe the 2-D image motion. Pan vs truck and zoom vs dolly cannot be told apart.
8. Thresholds were not calibrated on full-resolution user generations. The calibration clips are small
   template thumbnails.
