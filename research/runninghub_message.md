# Message for RunningHub #feature-requests (DRAFT: not posted)

Post only after the public repo exists and the links below work. Replace `https://github.com/VRH7733/ComfyUI-MotionVerdict` and `https://github.com/VRH7733/ComfyUI-MotionVerdict/blob/main/assets/camera_only.png (camera only) and https://github.com/VRH7733/ComfyUI-MotionVerdict/blob/main/assets/screenshot.png (animated)`.

---

## English

Hi RunningHub team,

Earlier you declined my node **Ragha Preview Video v1.3.1** with:
> "This is a node with duplicate functionality, and we already have an alternative node with the same function."

You were right. It was an on-node video preview player with A/B compare, and VideoHelperSuite, core Save Video,
Easy-Media and BFS Video Compare already do that. Its later version, **v2.0.0 (per-frame QC inspector)**, also
overlaps with existing nodes (comfyui-frameaudit, ComfyUI-VideoGate, BFS Video Compare), so I am **not**
requesting it.

I am asking about a **different function** instead: **Motion Verdict** (`MotionVerdict`), https://github.com/VRH7733/ComfyUI-MotionVerdict

**What it does:** it tells you whether an AI video is actually animated, or only a camera move over a still
picture. Image-to-video models (Wan, LTX, MiniMax, Hunyuan, Kling ...) often return a slow zoom or pan over the
start image with nothing moving. Frozen-frame checkers pass such a clip because the pixels change. Motion
Verdict:
- removes the camera's pan / tilt / zoom / roll;
- measures what still moves on its own;
- returns `animated / partly_animated / camera_only / still`, an `animated` BOOLEAN, a subject-motion FLOAT,
  stall times, a timeline IMAGE and a JSON report.

All of these are normal outputs, so it works in API and AI-App runs (e.g. drop seeds that did not animate).

**What I checked before building it:**
- ComfyUI-Manager's node list: 6,025 packs and 45,729 node names;
- GitHub and the web, by README only;
- in particular:
  - VideoHelperSuite, KJNodes, Easy-Media, BFS;
  - VideoQuality-Metrics, VideoGate, frameaudit;
  - shotdrift and shotcheck (camera-move verifiers);
  - Code2Collapse Motion Mask Tracker (a camera-compensated mask);
  - optical-flow packs;
  - loop and seam tools (SeamRank, DaSiWa, Eclipse, WhiteRabbit).

I found no node that gives this verdict. In your own node search:
- The nearest nodes are:
  - RyanOnTheInside *Motion Feature*: motion from optical flow as an effect-driving signal (its README documents no camera removal);
  - DepthAnythingV3 *Parse Camera Pose*: camera pose from a depth model.

  Neither removes the camera motion to judge whether the scene itself moves.
- WAS *Camera Motion Trajectory from Images* does the opposite: it *makes* a camera move over a still image.
- Motion Mask Tracker, shotdrift, shotcheck, VideoGate and frameaudit do not show up there.
- The closest analysis nodes are **MiniMax H3 RAFT Motion Audit** and **Motion Quality Audit**. Their panels describe
  raw flow and frame deltas with **no camera removal**, so a camera move over a still picture would count as
  motion there. On my 78 camera-only test clips the camera alone gives 0.5-2.4 px/frame of flow, and Motion
  Verdict reports ≤ 0.2 % own motion (`camera_only`).
- To be transparent: chaining **Video Stabilizer (Flow) → RAFT Motion Audit** could approximate part of this.
  But that is 2-3 nodes plus a RAFT model, gives raw pixel numbers instead of a verdict, and cannot by itself
  tell `camera_only` from `still`. Motion Verdict is one CPU-only node with a verdict, a BOOLEAN and stall
  times.

**Dependencies:** only torch, numpy and av. Runs on CPU, makes no network calls, writes nothing outside
ComfyUI's output folder (and only if `save_report` is on). MIT licence.

Screenshot: https://github.com/VRH7733/ComfyUI-MotionVerdict/blob/main/assets/camera_only.png (camera only) and https://github.com/VRH7733/ComfyUI-MotionVerdict/blob/main/assets/screenshot.png (animated)

If this still counts as duplicate functionality, could you tell me **which installed node you see as
equivalent**? And what would you need to see for a node to be accepted? Thank you!

---

## 中文

RunningHub 团队你好：

之前你们拒绝了我的节点 **Ragha Preview Video v1.3.1**，理由是：
> "This is a node with duplicate functionality, and we already have an alternative node with the same function."
>（这是一个功能重复的节点，我们已经有功能相同的替代节点。）

你们说得对。它是一个带 A/B 对比的节点内视频预览播放器，VideoHelperSuite、官方 Save Video、Easy-Media 和
BFS Video Compare 已经有这些功能。它的后续版本 **v2.0.0（逐帧质检）** 也与现有节点重叠（comfyui-frameaudit、
ComfyUI-VideoGate、BFS Video Compare），所以我**不**申请它。

这次申请的是一个**不同的功能**：**Motion Verdict**（`MotionVerdict`），https://github.com/VRH7733/ComfyUI-MotionVerdict

**它做什么：** 判断一段 AI 视频是真的在动，还是只是对一张静止画面做镜头运动。图生视频模型（Wan、LTX、MiniMax、
Hunyuan、Kling 等）经常只输出对首帧图片的缓慢推拉或平移，画面里没有任何东西在动。冻结帧检测会把这种片段判为正常，
因为像素在变化。Motion Verdict：
- 先去掉镜头的平移、俯仰、缩放和旋转；
- 再测量画面中自己在动的部分；
- 输出 `animated / partly_animated / camera_only / still`、一个 `animated` 布尔值、主体运动数值、停滞时间段、
  时间线图片和 JSON 报告。

这些都是普通输出，在 API 和 AI 应用模式下都能用（例如自动丢弃没有动起来的种子）。

**开发前查过的内容：**
- ComfyUI-Manager 节点列表：6025 个插件包、45729 个节点名；
- GitHub 和网络（只看 README）；
- 重点包括：
  - VideoHelperSuite、KJNodes、Easy-Media、BFS；
  - VideoQuality-Metrics、VideoGate、frameaudit；
  - shotdrift 和 shotcheck（镜头运动校验）；
  - Code2Collapse Motion Mask Tracker（补偿镜头运动的遮罩）；
  - 光流类插件；
  - 循环和接缝类工具（SeamRank、DaSiWa、Eclipse、WhiteRabbit）。

没有找到给出这种判定的节点。在你们的节点搜索里：
- 最接近的是：
  - RyanOnTheInside 的 *Motion Feature*：基于光流的运动量，用来驱动特效（其 README 没有提到去除镜头运动）；
  - DepthAnythingV3 的 *Parse Camera Pose*：由深度模型得到的相机位姿。

  它们都没有先去掉镜头运动，再判断画面本身是否在动。
- WAS 的 *Camera Motion Trajectory from Images* 正好相反：它是对静止图片*生成*镜头运动。
- 搜索 Motion Mask Tracker、shotdrift、shotcheck、VideoGate、frameaudit 都没有结果。
- 最接近的分析节点是 **MiniMax H3 RAFT Motion Audit** 和 **Motion Quality Audit**。它们的面板说明里只有原始光流和帧差，
  **没有提到去除镜头运动**，所以对静止画面做的镜头运动在那里会被算作"在动"。在我的 78 段纯镜头运动测试片段上，仅镜头本身就产生
  0.5-2.4 像素/帧的光流，而 Motion Verdict 报告的自身运动 ≤ 0.2%（判为 `camera_only`）。
- 坦白说：把 **Video Stabilizer (Flow) → RAFT Motion Audit** 串起来，可以近似实现其中一部分。但那需要 2-3 个节点加一个
  RAFT 模型，输出的是原始像素数值而不是判定，而且单靠它分不出 `camera_only` 和 `still`。Motion Verdict 是一个只用 CPU
  的节点，直接给出判定、布尔值和停滞时间段。

**依赖：** 只需要 torch、numpy、av。可在 CPU 上运行，不联网；只有打开 `save_report` 时才会写文件，而且只写到
ComfyUI 的 output 目录。MIT 许可证。

截图：https://github.com/VRH7733/ComfyUI-MotionVerdict/blob/main/assets/camera_only.png (camera only) and https://github.com/VRH7733/ComfyUI-MotionVerdict/blob/main/assets/screenshot.png (animated)

如果你们仍然认为功能重复，能否告诉我**你们认为哪个已安装的节点与它等效**？另外，一个节点需要满足哪些条件才会被接受？
谢谢！
