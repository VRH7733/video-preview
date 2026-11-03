// Motion Verdict: shows the verdict and the in-memory preview clip on the node.
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const COLORS = {
  animated: "#3fb950",
  partly_animated: "#d29922",
  camera_only: "#f0883e",
  still: "#f85149",
  unknown: "#8b949e",
};

function buildPanel() {
  const root = document.createElement("div");
  root.style.cssText = "display:flex;flex-direction:column;gap:4px;width:100%;font:12px sans-serif;";
  const badge = document.createElement("div");
  badge.style.cssText = "padding:3px 6px;border-radius:4px;color:#fff;font-weight:bold;display:none;";
  const video = document.createElement("video");
  video.muted = true;
  video.loop = true;
  video.autoplay = true;
  video.playsInline = true;
  video.controls = true;
  video.style.cssText = "width:100%;max-height:360px;background:#000;display:none;";
  const note = document.createElement("div");
  note.style.cssText = "color:#aaa;display:none;";
  root.append(badge, video, note);
  return { root, badge, video, note };
}

async function showClip(panel, token) {
  const { video, note } = panel;
  if (panel.url) {
    URL.revokeObjectURL(panel.url);
    panel.url = null;
  }
  video.removeAttribute("src");
  video.style.display = "none";
  note.style.display = "none";
  if (!token) return;
  const res = await fetch(api.apiURL(`/motion_verdict/preview/${token}`));
  if (!res.ok) {
    note.textContent = "Preview no longer in memory. Run the node again.";
    note.style.display = "block";
    return;
  }
  panel.url = URL.createObjectURL(await res.blob());
  video.src = panel.url;
  video.style.display = "block";
}

app.registerExtension({
  name: "motion_verdict.preview",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "MotionVerdict") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated?.apply(this, arguments);
      this.mvPanel = buildPanel();
      this.addDOMWidget("motion_verdict_preview", "preview", this.mvPanel.root, { serialize: false });
      return r;
    };

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);
      const info = message?.motion_verdict?.[0];
      if (!info || !this.mvPanel) return;
      const { badge } = this.mvPanel;
      badge.textContent = `${info.verdict.toUpperCase()}: ${info.headline}`;
      badge.title = info.report;
      badge.style.background = COLORS[info.verdict] ?? COLORS.unknown;
      badge.style.display = "block";
      showClip(this.mvPanel, info.token).then(() => this.setDirtyCanvas(true, true));
    };

    const onRemoved = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function () {
      if (this.mvPanel?.url) URL.revokeObjectURL(this.mvPanel.url);
      return onRemoved?.apply(this, arguments);
    };
  },
});
