# Open-source tools per stage (researched 2026-11-04)

How to read this: **Pick** = use first. **Backup** = if the pick fails or is missing on RunningHub.
"Public" = what users and community threads prefer. Most sources are blogs, vendor pages and Reddit,
not neutral benchmarks, so every pick still needs one test on our own shots.
Confidence: [Certain] checked, [Likely] strong inference, [Guessing] not verified.

**Licence rule:** monetized YouTube is commercial use. Prefer Apache 2.0 / MIT. Avoid non-commercial
models (marked NC) for anything that goes on the channel.

**Where it runs:** RH = RunningHub (search the name in RunningHub's workflow search). PC = runs on our
GTX 960 / 16 GB PC.

| Stage | Pick | Backup | Why (public view) | Where |
|---|---|---|---|---|
| Character sheets, key frames (image edit) | **Qwen-Image-Edit-2511** | FLUX.2 Klein; FLUX.1 Kontext dev (NC licence, test only) | Community favourite for keeping the same face across edits; Kontext holds identity but follows prompts poorly | RH |
| Video, image → video, first/last frame | **Wan 2.2** (I2V, FLF2V) | LTX-2.3; HunyuanVideo 1.5 | Wan: best faces and motion, Apache 2.0, biggest ComfyUI ecosystem. LTX: native audio, up to ~30 s, faster | RH |
| Blender mannequin → real-looking actor | **Wan 2.2 Animate** (Move / Mix mode) | Wan 2.2 VACE (pose / depth control) | Takes motion from a video and puts a new character into it. Lets Blender do the acting and AI do the look | RH |
| Clean (non-gore) shots | MiniMax Hailuo / H3 (closed) | Wan 2.2 | [Likely] blocks or strips blood, so clean shots only | RH |
| Voice, English, with emotion | **IndexTTS2** (emotion sliders: afraid, angry, sad...) | Chatterbox (MIT); VibeVoice (long, up to 4 speakers, EN/ZH only) | Top pick in 2026 guides for cloning plus emotion control, good for horror. [Guessing] Check its licence for commercial use | RH |
| Voice, Hindi / Indian languages | **IndicF5** (AI4Bharat, 11 Indian languages, cloning) | vibevoice-hindi-7b (community); Dhee-Indic-F5 is NC, avoid | Main open Indian-language voice cloner; needs a reference clip and its exact transcript | RH (if present) or a cloud GPU |
| Lip-sync, static camera | **InfiniteTalk** (image or video + audio) | LatentSync (re-sync an existing clip) | Reddit 2026: best lip accuracy. Slow (~600-800 s per run) and static camera only | RH |
| Lip-sync, moving camera | **LTX-2.3** | Wan 2.2 S2V (weaker reports) | Users report better lip-sync with camera movement | RH |
| Music (score, songs) | **ACE-Step 1.5 / XL** (MIT) | YuE2; DiffRhythm 2 | Leads open music models; LoRA from a few songs. Very seed-sensitive, so make several takes | RH |
| Sound effects from the video | **HunyuanVideo-Foley** (48 kHz) | MMAudio; ThinkSound | Best scores on its own benchmark; a RunningHub workflow exists for adding sound to silent Wan clips | RH |
| Upscale | **SeedVR2**, 2 passes (1080p, then 4K only if needed) | Real-ESRGAN via Video2X | Strongest quality; slow (~312 s per 10 s clip on an RTX 5090), so only the locked cut | RH (Video2X on PC) |
| Frame interpolation (smoother motion) | **RIFE** | GIMM-VFI | Standard, fast, good quality | PC or RH |
| Subtitles, Hindi | **IndicConformer 600M** (runs on CPU) | IndicWhisper; Whisper-Hindi2Hinglish (Hinglish output) | ~12% WER on the Vistaar benchmark (uploader's figure) | PC |
| Subtitles, English | **Whisper large-v3-turbo** (faster-whisper) | Whisper medium | The standard | PC |
| Vocal / music separation, denoise | **BS-RoFormer / Mel-RoFormer** in UVR | HTDemucs FT | Top of the MVSEP leaderboard | PC (UVR desktop app) |
| Edit, assemble | ffmpeg + Blender VSE | DaVinci Resolve free (manual polish) | Fully scriptable by Claude | PC |
| Story, explicit scenes | Grok (closed) | n/a | Your choice | Grok app |

## The Blender plan with Wan 2.2 Animate
1. Claude blocks the scene in Blender: room, camera, MPFB mannequins doing the action.
2. Render the shot as a cheap 480p video (Eevee, no detail needed).
3. Wan 2.2 Animate takes that motion and puts the locked character sheet into it.
4. Gore shots: the same, with Wan (not MiniMax).
This keeps camera and acting under our control and moves the realism to RunningHub.

## To check on RunningHub (search each name, send Claude the best workflow links)
Qwen-Image-Edit-2511, Wan 2.2 FLF2V, Wan 2.2 Animate, Wan 2.2 VACE, LTX-2.3, IndexTTS2, IndicF5,
InfiniteTalk, ACE-Step 1.5, HunyuanVideo-Foley, SeedVR2.
Known: a HunyuanVideo-Foley + Wan workflow exists (runninghub.ai/post/1963220499021139969).

## Sources
- TTS: https://www.siliconflow.com/articles/en/best-open-source-models-for-voice-cloning ,
  https://findskill.ai/blog/best-open-source-tts-2026/ , https://github.com/phpcws/ComfyUI-IndexTTS2
- Hindi TTS: https://github.com/samnaveenkumaroff/Indic-F5 , https://huggingface.co/tarun7r/vibevoice-hindi-7b ,
  https://huggingface.co/dheeyantra/dhee-indic-f5
- VibeVoice: https://arxiv.org/html/2508.19205v1 , https://www.runcomfy.com/comfyui-nodes/VibeVoice-ComfyUI
- Music: https://ace-step.github.io/ace-step-v1.5.github.io , https://www.creativeainews.com/articles/best-open-source-ai-music-models-2026/
- Foley: https://github.com/Tencent-Hunyuan/HunyuanVideo-Foley , https://www.runninghub.ai/post/1963220499021139969
- Lip-sync: https://www.pixazo.ai/blog/best-open-source-lip-sync-models ,
  https://reddit.sentinel-team.org/posts/1s1j5mn/snapshots/2026-03-27T22%3A16%3A10.082755Z
- Image edit: https://www.pulse.bot/ai/news/5-open-source-image-editing-ai-models-5038104a-00a7-45ce-aba0-d4516da9dc3b/ ,
  https://reddit.sentinel-team.org/posts/1tdi287/snapshots/2026-05-15T21%3A30%3A42.175693Z
- Video: https://magichour.ai/blog/ltx-2-3-vs-wan-2-2 , https://www.thundercompute.com/blog/best-open-source-ai-video-generation-models ,
  https://docs.comfy.org/tutorials/video/wan/wan-flf.md
- Wan Animate / VACE: https://comfyui-wiki.com/en/tutorial/advanced/video/wan2.2/wan2-2-animate ,
  https://www.runcomfy.com/comfyui-workflows/wan-2-2-vace-in-comfyui-pose-driven-motion-video-workflow
- Upscale: https://docs.comfy.org/tutorials/utility/video-upscale.md
- Interpolation: https://ai-tools-compared.pages.dev/ai-tools-for-video-frame-interpolation
- Subtitles: https://huggingface.co/Abhay-Verma031/indic-conformer-600m , https://oriserve.com/blog/oriserve-open-sources-india-focused-ai-speech-model-fine-tuned-on-whisper
- Separation: https://huggingface.co/spaces/JacobLinCool/vocal-separation/blob/main/README.md ,
  https://lyruno-website.pages.dev/blog/remove-vocals/ai-vocal-separation-guide-latest
