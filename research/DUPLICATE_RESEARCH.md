# Duplicate-functionality research

Date: 2026-11-03. Goal: find a primary function for a new ComfyUI node that no public node already has,
because RunningHub refused the earlier nodes with:

> "This is a node with duplicate functionality, and we already have an alternative node with the same function."

Confidence tags: **[certain]** = read it in a README / listing / index; **[likely]** = strong inference;
**[guessing]** = filling a gap.

## Method (clean room)

- Sources used: GitHub READMEs, ComfyUI-Manager's `custom-node-list.json` (6,025 packages) and
  `extension-node-map.json` (5,725 repos, 45,729 node class names), both fetched 2026-11-03 from
  `raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/`, web search, aggregator listings (comfy.icu,
  comfyai.run) via search snippets, and node names / declared inputs and outputs.
- **Not read:** implementation source (.py / .js algorithm code) of any preview, compare, QC, loop, seam or
  camera node. [certain]
- Keyword sweeps were run over all 6,025 package descriptions and all 45,729 node class names (loop, seam,
  stitch, overlap, dedup, drift, continuity, last frame, flicker, PSNR/SSIM/VMAF, scene cut, camera motion,
  stabiliz*, optical flow, VBench). Three research passes then read the READMEs of every hit plus web results.
- **Blocked in this session** (could not be read): `api.comfy.org`, `registry.comfy.org`, `docs.comfy.org`,
  `runninghub.ai`, `runninghub.cn`, RunningHub's API doc host, `runcomfy.com`, `comfy.icu` (direct fetch).
  So Comfy Registry pages were checked only indirectly (via the Manager index and GitHub). [certain]

## (a) Packages that overlap with anything in scope

Feature key: P = on-node preview/player, AB = A/B compare, T = frame delta / flicker / deflicker,
Q = quality metrics, F = frozen/duplicate/black/flash frames, S = scene cut, L = loop point / loop seam,
C = clip-to-clip chaining / seam / drift, CAM = camera-motion estimate or verify, SUBJ = camera-compensated
subject motion, AV = audio-video sync, PROF = timing / VRAM profiler.
"Overlap" = overlap with the **chosen** function (Motion Verdict, see (d)).

| Package | License | Overlapping features | Overlap with Motion Verdict | URL |
|---|---|---|---|---|
| ComfyUI core (Save/Preview Video, ImageCompare, ImageDeduplication, Wan camera embed) | GPL-3.0 | P, AB, F (perceptual-hash dedup) | none [certain] | https://github.com/Comfy-Org/ComfyUI |
| ComfyUI-VideoHelperSuite | GPL-3.0 | P (animated previews), pingpong/loop_count | none [certain] | https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite |
| ComfyUI-KJNodes | GPL-3.0 | P (Fast Preview, Preview Animation), C (ColorMatch, ImageBatchExtendWithOverlap, JoinWithTransition), PROF (VRAM_Debug, timer) | none [likely] | https://github.com/kijai/ComfyUI-KJNodes |
| rgthree-comfy | MIT | AB (still images) | none [certain] | https://github.com/rgthree/rgthree-comfy |
| ComfyUI-Easy-Media | GPL-3.0 | P, AB (compareVideos) | none [certain] | https://github.com/yolain/ComfyUI-Easy-Media |
| ComfyUI-BFSNodes (BFS Video Compare) | GPL-3.0 | P, AB, T (per-pixel diff, per-frame diff value), S (cut-detector curve) | none (differences are not camera-compensated) [likely] | https://github.com/alisson-anjos/ComfyUI-BFSNodes |
| **ComfyUI-CustomNodePacks (Code2Collapse), Motion Mask Tracker `MaskTrackerMEC`** | Apache-2.0 | P, AB, T, Q (PSNR/SSIM/CIEDE2000), **SUBJ: camera-compensated moving-region masks + a motion-intensity `score`** | **partial**: same core step (remove camera motion, look at what is left), but it outputs masks for masking work, and no verdict, no still/camera-only/frozen classification, no stall timeline [certain for README; outputs from listing: likely] | https://github.com/Code2Collapse/ComfyUI-CustomNodePacks |
| camera-comfyUI (Alexankharin) `MotionMaskFromDepth`, `VideoPoseEstimator` | unknown | SUBJ (dynamic-pixel mask from depth + VGGT poses), CAM (poses) | partial (mask only, needs depth + VGGT models) [likely] | https://github.com/Alexankharin/camera-comfyUI |
| **shotdrift-comfyui** | MIT | **CAM: expected camera move → `held` BOOLEAN, report, json** | partial: camera numbers only; "subject motion raises incoherence" is treated as noise; no animated/still verdict [certain] | https://github.com/Syamjith-NK/shotdrift-comfyui |
| **shotcheck** (`ShotCheckMotionVerifier`) | MIT | CAM: MATCH / MISMATCH / INCONCLUSIVE for pan, tilt, dolly, static | partial: camera only [certain] | https://github.com/soft-jelly/shotcheck |
| ComfyUI-VideoQuality-Metrics | MIT | T (warping error, flickering score), Q (PSNR, SSIM, FVD, FID, DOVER, FAST-VQA ...), motion smoothness / jerk (RAFT) | none (smoothness, not amount; not camera-compensated) [certain] | https://github.com/jajos12/ComfyUI-VideoQuality-Metrics |
| ComfyUI-VideoGate | MIT | F (black / frozen frames, ffmpeg), PASS/WARN/FAIL gate | partial at the "frozen" end only (raw frame freeze; a zoom over a still picture is not frozen) [likely] | https://github.com/madebysaira/ComfyUI-VideoGate |
| comfyui-frameaudit | MIT | T (exposure / chroma flicker), F (repeated-frame runs), S, verdict | partial at the "frozen" end only [likely] | https://github.com/Ye-Zayne/comfyui-frameaudit |
| TrentNodes | MIT | F (duplicate detection), S (Cut Detective), P | none [certain] | https://github.com/TrentHunter82/TrentNodes |
| Comfyui-SceneDetect (hndrr), Comfyui-ZNGB-SceneDetect, ComfyUI-Video-Segmentation | MIT / unknown / GPL? | S | none [certain] | https://github.com/hndrr/Comfyui-SceneDetect |
| comfyUi-deflicker | MIT | T (deflicker, step removal, debug heatmap), C (chunk-boundary jumps) | none [certain] | https://github.com/karcsiha/comfyUi-deflicker |
| ComfyUI-SuperBeasts, ComfyUI-fastblend, WAS_Extras (Exposure Stabilizer), Radiance | MIT / unknown / unknown / GPL-3.0 | T (deflicker / smoothing), P (Radiance viewer), translation-only stabilizer | none [likely] | https://github.com/FXTD-Studios/radiance |
| ComfyUI-Image-Analysis-Tools, pyiqa-toolbox, CLIPScore, Image-Evaluation, comfyui-image-metrics, Similarity-Score | various | Q (per image) | none [certain] | https://github.com/ThatGlennD/ComfyUI-Image-Analysis-Tools |
| ComfyUI-RyanOnTheInside, comfyui-optical-flow, ComfyUI-RAFT, controlnet_aux (Unimatch, MaskOptFlow), ComfyWarp | MIT / MIT / BSD-3 / Apache-2.0 / ? | optical flow fields / flow masks (camera motion **included**), "motion features" | none to partial (raw flow amount includes camera motion) [likely] | https://github.com/ryanontheinside/ComfyUI_RyanOnTheInside |
| opencv-comfyui `phaseCorrelate`, FM_nodes StabStitch, link-comfy-nodes Stabilize Frames | GPL-3.0 / MIT / unknown | translation estimate (batch 1) / stabilization | none [likely] | https://github.com/geroldmeisinger/opencv-comfyui |
| ComfyUI-vid2frames, RealtimeNodes MotionController | unknown | frame-difference motion score (not compensated) | none [certain / likely] | https://github.com/Pmobilee/ComfyUI-vid2frames |
| comfyui-seamrank | MIT | C: seam score 0-100 vs normal motion, auto-trims duplicate prefix | none [certain] | https://github.com/Ye-Zayne/comfyui-seamrank |
| ComfyUI_Eclipse, DaSiWa-Nodes, WhiteRabbit, loppiner, comfyui-loopstrip, Desert-Pixel-Nodes, comfyui-seamless-loop, LoopGif, comfyui_loops, CRT-Nodes, AtlasUtils, ea-nodes | various | L (automatic loop-point search exists in Eclipse, DaSiWa, WhiteRabbit, loppiner) | none [certain] | https://github.com/darksidewalker/ComfyUI-DaSiWa-Nodes |
| comfyui-aex-drift, H3-Project-Suite, MiniMaxH3-Context-Loop, IAMCCS-nodes, BSAI-Sol-H3, CGlide, noEmbryo, obvpm-timeline, Event-Equality-Core (Tail 5 gate), WanVideoLooper, wan_vace_auto_joiner, wanv2v-video-stitcher, VideoChunkTools, Fill-Nodes, Nukun, PainterI2V*, Stat-Imp | various | C (drift measure/correct, overlap trim, continuation, join) | none [likely] | https://github.com/EchoHeadache/comfyui-aex-drift |
| IAMCCS `WanImageMotion`, PainterI2V `motion_amplitude`, LongLook Wan Motion Scale | GPL-3.0 / MIT / ? | generation-side "add more motion" controls | none (they change generation; they do not measure) [likely] | https://github.com/IAMCCS/IAMCCS-nodes |
| Bjornulf (Audio Video Sync), Pixaroma, dagthomas H3SyncCheck | none / MIT / MIT | AV (duration matching; H3SyncCheck undocumented) | none [likely] | https://github.com/justUmen/Bjornulf_custom_nodes |
| tzwm/comfyui-profiler, Crystools, Dev-Utils, performance-report, KikoTools, many timers | various | PROF | none [certain] | https://github.com/crystian/ComfyUI-Crystools |
| **ComfyUI-RaghaPreviewVideo** (your own old repo, v2.0.0) | GPL-3.0 | P, AB, T, F, S, L (last→first), last-good-frame picker | none; it compares raw frames, no camera compensation [certain] | https://github.com/VRH7733/ComfyUI-RaghaPreviewVideo |

## (b) Gap list

1. **No node gives a verdict on whether a clip actually animates.** Nothing outputs "animated" vs
   "camera move over a still picture" vs "still". [likely]
2. **No camera-compensated subject-motion number for QC.** MaskTrackerMEC's intensity score is the closest,
   but it is built for masking, and its README gives no formula. [likely]
3. **Frozen-frame detectors miss "camera-only" clips.** VideoGate, frameaudit and the old Ragha v2 compare
   raw frames, so a slow zoom or pan over a still image passes as moving. [likely: follows from what their
   READMEs say they compare]
4. **No timeline of when the scene stops moving.** Nothing reports that "the subject moves for 1.5 s and
   then stalls". [likely]
5. No VBench-style dynamic-degree node. [likely]
6. Other gaps found but not chosen:
   - audio-video **offset** measurement [likely]
   - VMAF, blockiness [likely]
   - interpolation-cadence detection [likely]
   - a joint A-tail × B-head cut search [likely]

## (c) Three candidate primary functions

Scores are 0-3 per criterion: 3 = strong, 0 = fails.

| Candidate | No public equivalent | Useful for Wan / LTX / MiniMax / Hunyuan users | Works in API mode | Known-answer testable | CPU-friendly | Verdict |
|---|---|---|---|---|---|---|
| **C1. Camera-move verifier**: did the clip pan / tilt / zoom / stay locked off as prompted? PASS/FAIL | **0**: shotdrift and shotcheck already do this. **FULL overlap** [certain] | 3 | 3 | 3 | 3 | reject |
| **C2. Seam finder**: best loop point inside a clip, or the best cut between clip A's tail and clip B's head, with duplicate-frame removal | **0-1**: loop search is done by Eclipse, DaSiWa, WhiteRabbit and loppiner (**full**). Chain duplicate trim and jump-vs-normal-motion are done by SeamRank (**full/partial**). Only "both cut points free" is new [certain] | 3 | 3 | 3 | 3 | reject |
| **C3. Motion Verdict**: remove the camera's global motion, measure what still moves. Verdict animated / camera_only / still, subject-motion score, stall timeline | **2**: core step partly shared with MaskTrackerMEC (mask + intensity) and MotionMaskFromDepth (mask). Nobody gives the verdict, the score as QC, or the stall timeline. **PARTIAL overlap** [likely] | 3: "my I2V output barely moves / is just a zoom on the picture" is a common failure, and seed batches can be auto-filtered with a BOOLEAN [likely] | 3: STRING, BOOLEAN, FLOAT and IMAGE outputs, no player needed | 3: synthetic still + known zoom/pan, moving patch on a static or panning background, noise, flicker | 3: prototype runs 241 frames at 320 px in ~5 s on 4 CPU cores [certain, measured] | **pick** |

## (d) Recommendation

**Build C3, "Motion Verdict", narrowed to what nobody else does:**
- the verdict (`animated` / `camera_only` / `still`) and an `animated` BOOLEAN for gating;
- a camera-compensated subject-motion score (FLOAT) with camera numbers kept as context only;
- a per-time-step timeline (IMAGE chart + JSON) showing when the subject moves and when it stalls.

**Not built, on purpose:**
- a camera-compensated MASK output, which is MaskTrackerMEC's job;
- expected-camera-move PASS/FAIL, which is shotdrift's and shotcheck's job.

The moving-region overlay appears only in the optional preview.

Why C3:
- It is the only candidate where research found no node with the same function. [likely]
- It catches a real class of bad I2V output that existing frozen-frame QC cannot catch by design. [likely]

## (e) DECISION: **PROCEED-NARROWED** [likely]

Reasons:
- C1 overlaps fully. [certain]
- C2 overlaps fully or partly. [certain]
- C3 overlaps only partly, and the overlapping part is removed from the node's outputs. [likely]

Remaining risks:
1. RunningHub's duplicate test is not public. They may weigh the shared camera-compensation step differently
   from us. [certain that this is unknown]
2. Packages outside the Manager index and outside web search could not be checked. [certain]

## Name collision check

| Name | Manager node names (45,729) | Manager package titles/ids (6,025) | GitHub repo search | ComfyUI core (`research/installed_nodes.txt`) |
|---|---|---|---|---|
| `MotionVerdict` (node id) | 0 | 0 | 0 repos named so; 0 code hits with `NODE_CLASS_MAPPINGS` | 0 |
| `comfyui-motion-verdict` (pack id) | n/a | 0 | 0 | n/a |

The Comfy Registry API (`api.comfy.org`) was blocked here, so the registry id must be re-checked at publish
time. `comfy node publish` refuses a taken id anyway. [certain]

## RunningHub: what is and is not documented

What is documented:
- A REST API: `/task/openapi/create`, `/task/openapi/ai-app/run`, `/openapi/v2/query`.
- Outputs come back as file URLs with a `fileType`.
- RunningHub's own client code (`HM-RunningHub/ComfyUI_RH_APICall`, `RH_CLI`) handles `txt` / `text`
  results. [certain about the client code]

What is NOT documented:
- admission criteria for custom nodes;
- the channel for requesting a node (no official Discord / #feature-requests link was found);
- a list of supported nodes;
- the "duplicate functionality" policy and how it is detected (the exact rejection text is not on any public
  page found);
- which output node types produce API results. Whether a display-only STRING becomes a result is unknown, so
  the node can also save its report as a `.json` file inside ComfyUI's output folder. [certain that these
  were not found]

Users cannot install nodes on RunningHub; the platform preinstalls them. This comes from third-party articles,
e.g. https://zhuanlan.zhihu.com/p/715385255. [likely]

The detection method was not guessed.
