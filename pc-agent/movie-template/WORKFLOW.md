# Movie workflow (researched 2026-11-04)

Roles: **you** = director and final yes/no. **Grok** = assistant director, movie scripts, explicit scenes.
**Claude** = YouTube scripts, Blender, edits, RunningHub runs, file management.
Confidence: [Certain] = checked, [Likely] = strong inference, [Guessing] = not verified yet.

## Key facts that shape the workflow
1. **MiniMax (Hailuo) is not for gore.** [Likely] Third-party tests report Hailuo 2.3 blocks blood/injury
   prompts, and MiniMax H3 silently removes the blood instead of refusing
   ([Atlas Cloud](https://www.atlascloud.ai/blog/guides/minimax-h3-content-restrictions),
   [Atlas Cloud, Hailuo](https://www.atlascloud.ai/blog/guides/hailuo-ai-nsfw-content-restrictions-guide)).
   Use MiniMax for clean shots (dialogue, establishing, mood); use **Wan 2.2** (open model, in ComfyUI on
   RunningHub) for blood and gore shots.
2. **Wan 2.2 FLF2V** (first + last frame → video, 720p, Apache 2.0) is the best-supported open option for
   controlled shots ([ComfyUI docs](https://docs.comfy.org/tutorials/video/wan/wan-flf.md)).
3. **RunningHub's own rules on gore are not verified.** Read https://www.runninghub.ai/protocol and test one
   mild blood shot before a full scene. [Guessing] Explicit sexual content is likely banned there; keep it in
   Grok Imagine only.
4. **Character consistency is decided before video generation:** a character bible + locked reference
   sheets; first/last frames only when they really are the first/last frame
   ([guide](https://invideo.io/faq/how-do-you-create-a-character-bible-for-ai-video-to-lock/)).
5. **Lip-sync:** InfiniteTalk (Wan 2.1 based, image + audio → talking video, no length cap)
   ([ComfyUI](https://comfy.org/workflows/video_wan2_1_infinitetalk-b95499a55c9f/)).
6. **Upscale:** SeedVR2, two passes (clean-up/1080p, then 4K only if needed). It is slow: ~312 s for a 10 s
   720p clip on an RTX 5090 ([ComfyUI docs](https://docs.comfy.org/tutorials/utility/video-upscale.md)),
   so upscale only shots in the locked cut.
7. **YouTube:** AI is allowed, but mass-produced/repetitive AI content is not monetized (July 2026 update)
   ([TechRepublic](https://techrepublic.com/article/news-youtube-ai-video-monetization-rules)).
   [Likely] Graphic gore gets age-restricted. Plan a **YouTube cut** and a **full cut**.
8. **This PC:** GTX 960 4 GB, Blender 3.6 Eevee. Blender renders key frames and layouts, not whole films.

## Stages

| # | Stage | Who / tool | Output (in D:\money) |
|---|---|---|---|
| 0 | **Bible**: characters (face, age, clothes, voice), locations, look (colours, lens), rating per scene | You + Grok, Claude writes it up | `bible/` |
| 1 | **Script → shot list** in the fixed format below | Grok (movies), Claude (YouTube) | `scripts/ep01_shots.md` |
| 2 | **Rough voices** for every line, to time the shots | RunningHub TTS | `audio/rough/` |
| 3 | **Character sheets**: 4 options each, you pick one, it is locked | Grok Imagine / RunningHub image models | `assets/characters/<name>/` |
| 4 | **Layout**: room, camera, poses, light in Blender, render first (and last) frame per shot | Claude (Blender) | `blender/`, `renders/layout/` |
| 5 | **Key frames**: restyle layout frames with the character sheets | RunningHub image edit | `assets/keyframes/S012_first.png` |
| 6 | **Animatic**: key frames + rough voices cut to time. Watch the whole film before any video credits | Claude (ffmpeg) | `edits/animatic_v1.mp4` |
| 7 | **Video drafts**, 480p/720p, max 2 takes per shot. Clean shots: MiniMax. Gore: Wan 2.2. Explicit: Grok only | RunningHub in Chrome: preview → wait 1 min for OK → else Stop | `shots/S012/take01.mp4` |
| 8 | **Final voices + lip-sync** on approved takes | RunningHub TTS + InfiniteTalk | `audio/final/`, `shots/S012/sync.mp4` |
| 9 | **Rough cut**, then lock the cut | Claude (ffmpeg) | `edits/cut_v1.mp4` |
| 10 | **Upscale only the used ranges**, 1080p (4K only if needed) | RunningHub SeedVR2 | `shots/S012/up1080.mp4` |
| 11 | **Final**: music, SFX, colour, subtitles; YouTube cut + full cut | Claude (ffmpeg / Blender VSE) | `edits/final_youtube.mp4`, `private/final_full.mp4` |

Explicit sexual shots: made in Grok, kept in `private/`, never edited by Claude. Claude leaves a
placeholder of the right length in the cut.

## Shot-list format (Grok must use this)
```
SHOT 012 | 6s | LOCATION: abandoned hospital, night | CAMERA: slow push-in, low angle
CHARACTERS: Ravi (scared), Nurse (back to camera)
ACTION: Ravi backs into the wall, blood on the floor
DIALOGUE: Ravi (male, 30s, whispering, Hindi): "..."
SOUND: dripping water, distant scream | MOOD: cold blue light
RATING: clean | gore | explicit
```
`RATING` picks the tool in stage 7: clean → MiniMax, gore → Wan 2.2, explicit → Grok.

## Credit rules
- No video credits before the animatic (stage 6) is approved.
- Drafts at 480p/720p; at most 2 takes per shot, then change the key frame, not the seed.
- Preview rule on every RunningHub run: no OK within 1 minute → Stop.
- Upscale last, only what is in the locked cut.

## Still open (answer before the first film)
1. "Dash" = character drawings / photos / reference images?
2. Language of the dialogue (Hindi, Telugu, English...)? TTS Hindi support is not verified yet.
3. One cloned voice per character, kept for all films?
4. Long form: 16:9 1080p or 4K? Shorts: 9:16? Typical lengths?
5. Music: RunningHub AI music or a royalty-free library (Content ID risk)?
6. Which RunningHub workflows do you already use (links)? They replace the guesses above.
