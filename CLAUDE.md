# Motion Verdict: project memory for new Claude sessions

Read this first. It is the state of the project, so a new chat does not start from zero.

## What it is
**Motion Verdict** is a ComfyUI custom node (node id `MotionVerdict`, pack `comfyui-motion-verdict`, publisher
`raghav`, MIT licence). It tells whether an AI video is really animated or only a camera move over a still
picture.

Outputs:
- the verdict: `animated` / `partly_animated` / `camera_only` / `still` / `unknown`;
- an `animated` BOOLEAN;
- `subject_motion` (FLOAT);
- a `timeline` IMAGE;
- `report` and `json` STRINGs.

It takes an IMAGE batch or a VIDEO; a VIDEO is streamed, so 4K and long clips never sit in memory at full size.
Optional on-node preview (256-1440 px, crf 20), kept in RAM only, with **no disk or temp writes**. The default is
the clean clip; `video + motion overlay` tints in red what moves on its own.

## Where things are
- Public repo: https://github.com/VRH7733/ComfyUI-MotionVerdict. `main` = `ecae002` = Registry 1.0.0.
- Comfy Registry: https://registry.comfy.org/nodes/comfyui-motion-verdict (v1.0.0, live; the zip was verified
  identical to `ecae002`).
- Development branch: `claude/comfyui-custom-node-new-i58x6d` in `VRH7733/video-preview`. It is ahead of `main`
  with docs only; the node code is the same.
- The old repo `VRH7733/ComfyUI-RaghaPreviewVideo` (Ragha Preview Video / Inspector) must **not** be changed.

## Code map
| File | Role |
|---|---|
| `motion_verdict/analysis.py` | the clip analysis |
| `camera.py` | affine camera fit: tile phase correlation + Lucas-Kanade polish |
| `residual.py` | own motion: normal flow after camera removal |
| `frames.py`, `video_source.py` | IMAGE chunks / streamed VIDEO |
| `preview.py` | in-memory H.264 |
| `store.py` | RAM preview store |
| `node.py` | the ComfyUI node |
| `chart.py`, `report.py` | timeline image, report text / JSON |
| `__init__.py` | mappings + `/motion_verdict/preview/{token}` route |
| `web/motion_verdict.js` | on-node player, 84 lines |

## Tests (run before any change is pushed; never loosen a limit to pass)
- `python tests/test_motion_verdict.py`: 33 tests, all must pass. Also passes on the user's 2-core Windows laptop
  with ComfyUI running.
- `python tests/api_run.py [--video-only] <video>`: needs a running ComfyUI.
- `node tests/ui_run.js <video> <png>`: needs Playwright and a running ComfyUI.
- `python tests/eval_clips.py <folder>`: published results are 230 real clips → 229 animated + 1 partly; 195
  known-answer clips → 194/195.
- Full numbers and history are in `tests/RESULTS.md`. The design and thresholds, with reasons, are in
  `docs/DESIGN.md`.

## Rules the user set
- Dependencies: only torch, numpy and av. CPU-safe. No network calls. No files outside ComfyUI's folders.
- Credit kijai (KJNodes Fast Preview) for the disk-free preview idea. Never use the identifiers
  `PREVIEW_IMAGE_WITH_METADATA` or `b_preview_with_metadata`, or any KJNodes name.
- Never evade or obfuscate to get past a duplicate check. The node must be genuinely different.
- Ask before anything public: pushes to the public repo, Registry releases, posts on RunningHub or Discord.

## RunningHub status (2026-11-03)
- The old node v1.3.1 was rejected as "duplicate functionality".
- Motion Verdict was posted by the user (Discord account `gamechanger`) in #feature-requests at 7:54 PM with only
  the Registry link. The full explanation is ready in `research/runninghub_discord.md`: Part 1 English and Part 2
  Chinese, each under 2,000 characters. Reviewer `Runninghub_Charlotte` writes in Chinese.
- No reply yet. The duplicate research is in `research/DUPLICATE_RESEARCH.md`: 59 RunningHub search terms, no
  node meets all three criteria.
- The honest weak point: a *Video Stabilizer → MiniMax H3 RAFT Motion Audit* chain could approximate part of it.

## Open items
1. Wait for RunningHub's reply. If they name an "equivalent" node, check its README/panel against the 3 criteria:
   takes frames; removes camera motion; outputs how much the scene still moves.
2. Optional: 10-20 real, labelled good/dead I2V clips in `real_clips/` (gitignored) for a real-failure benchmark.
3. Optional: a Registry icon (needs a 1.0.1 release); sync `main` with the docs.

## Environment notes
- Cloud sessions cannot reach `registry.comfy.org`, `api.comfy.org` or `cdn.comfy.org`, and cannot see the
  user's PC. Verify those from a session on the PC.
- The user's PC: Windows 10, 2-core Ryzen 3 3250U, 5.9 GB RAM; ComfyUI Desktop 0.43.1 on port 8188, `--cpu`.
