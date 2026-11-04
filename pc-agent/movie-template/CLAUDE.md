# Movie project: memory for every Claude session

Claude reads this file at the start of every session. Keep it short and up to date.

## Project
- Channel / film name: (fill in)
- Formats: long-form YouTube, shorts, films.
- Story and explicit scenes are written in Grok; Grok replies land in `scripts/grok-*.md`.
  Claude does the technical work: Blender scenes, horror and gore effects, editing, renders, automation.

## Folders
- `scripts/`  scripts and Grok replies
- `assets/`   images, audio, generated clips
- `blender/`  .blend files and Blender Python scripts
- `renders/`  rendered output
- `edits/`    final cuts

## Tools on this PC
- Blender: (full path to blender.exe)
- ffmpeg: (path, or "on PATH")
- GPU: GTX 960, 4 GB VRAM, so use Eevee and keep scenes light. Heavy AI video runs on RunningHub.

## Rules
- Work only inside this folder.
- Never delete files in `renders/` or `edits/` without asking.
- At the end of each task, write a short summary: what changed, which files, what to check.

## Current status
- (Claude updates this list after each task.)
