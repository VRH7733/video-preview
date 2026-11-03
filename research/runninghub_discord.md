# RunningHub #feature-requests: Discord-length versions (each part < 2,000 characters)

Post part 1 (English), then part 2 (中文) as a second message. Long version: runninghub_message.md.

## Part 1: English

Hi RunningHub team! You declined my **Ragha Preview Video v1.3.1** with: *"This is a node with duplicate functionality, and we already have an alternative node with the same function."* You were right: VHS, Save Video, Easy-Media and BFS already do preview/compare. My later v2.0.0 (frame QC) also overlaps (frameaudit, VideoGate, BFS), so I'm **not** requesting it.

I'm asking about a **different function**: **Motion Verdict** (`MotionVerdict`).

**What it does:** it tells you if an AI video is really animated, or **only a camera move over a still picture**. I2V models (Wan, LTX, MiniMax, Kling...) often return a slow zoom or pan over the start image with nothing moving. Frozen-frame checks miss that, because the pixels change. Motion Verdict removes the camera's pan/tilt/zoom/roll, measures what still moves, and outputs:
- `animated / partly_animated / camera_only / still`;
- an `animated` BOOLEAN (drop dead seeds in AI-App runs);
- a subject-motion FLOAT, stall times, a timeline IMAGE and a JSON report.

It also has an in-memory video preview (no disk/temp files).

**Checked first:** 59 search terms in *your* node search. No node does this.
- Closest: MiniMax H3 RAFT Motion Audit / Motion Quality Audit (raw flow / frame deltas; no camera removal in their panels) and RyanOnTheInside Motion Feature.
- To be fair: Video Stabilizer → RAFT Audit could approximate part of it, but that is 2-3 nodes plus a RAFT model, gives raw px numbers, and cannot tell camera_only from still.

**Deps:** torch, numpy, av only. CPU OK, no network, MIT.
Repo: https://github.com/VRH7733/ComfyUI-MotionVerdict
Registry: https://registry.comfy.org/nodes/comfyui-motion-verdict

If this still counts as a duplicate, **which installed node do you see as equivalent**, and what would you need to accept a node? Thanks!

## Part 2: 中文

RunningHub 团队你好！你们之前拒绝了我的 **Ragha Preview Video v1.3.1**，理由是"功能重复，已有相同功能的替代节点"。你们说得对：VHS、Save Video、Easy-Media、BFS 已有预览/对比功能。后来的 v2.0.0（逐帧质检）也与 frameaudit、VideoGate、BFS 重叠，所以我**不**申请它。

这次申请的是**不同的功能**：**Motion Verdict**（`MotionVerdict`）。

**作用：**判断 AI 视频是真的在动，还是**只是对静止画面做镜头运动**。图生视频模型（Wan、LTX、MiniMax、Kling 等）经常只对首帧做缓慢推拉或平移，画面里没有东西在动。冻结帧检测会漏掉这种情况，因为像素在变。Motion Verdict 先去掉镜头的平移/俯仰/缩放/旋转，再测量画面里自己在动的部分，输出：
- `animated / partly_animated / camera_only / still`；
- `animated` 布尔值（AI 应用里可自动丢弃没动起来的种子）；
- 主体运动数值、停滞时间段、时间线图片和 JSON 报告。

另有纯内存视频预览（不写磁盘/临时文件）。

**事先检查：**在你们的节点搜索里查了 59 个关键词，没有节点做这件事。
- 最接近：MiniMax H3 RAFT Motion Audit / Motion Quality Audit（原始光流/帧差，面板里没有去除镜头运动），以及 RyanOnTheInside Motion Feature。
- 坦白说：Video Stabilizer → RAFT Audit 能近似一部分，但需要 2-3 个节点加 RAFT 模型，只给像素数值，也分不出 camera_only 和 still。

**依赖：**仅 torch、numpy、av。支持 CPU，不联网，MIT 许可。
仓库：https://github.com/VRH7733/ComfyUI-MotionVerdict
Registry：https://registry.comfy.org/nodes/comfyui-motion-verdict

如果仍算功能重复，能否告诉我**你们认为哪个已安装节点与它等效**？接受一个节点需要满足什么条件？谢谢！
