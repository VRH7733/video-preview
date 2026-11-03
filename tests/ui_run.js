// Drive the real ComfyUI frontend in headless Chromium (Playwright for Node).
//
//   node tests/ui_run.js <video in ComfyUI/input> <screenshot.png> [<exported_workflow.json>] [--url URL]
//
// Builds Load Video -> Get Video Components -> Motion Verdict -> Preview Any in the page, exports the workflow
// the way the UI saves it, queues it, waits for the verdict badge and the on-node preview video, takes a
// screenshot and prints every console error / page error. Exit code 1 if the badge or the video does not appear.
const fs = require("fs");
const { chromium } = require("playwright");

const args = process.argv.slice(2);
const urlAt = args.indexOf("--url");
const url = urlAt >= 0 ? args.splice(urlAt, 2)[1] : "http://127.0.0.1:8188";
const [video, shot, wfPath] = args;
const BADGE = /^(ANIMATED|PARTLY_ANIMATED|CAMERA_ONLY|STILL|UNKNOWN):/;

(async () => {
  const errors = [];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
  page.on("pageerror", (e) => errors.push(`pageerror: ${e}`));
  page.on("response", (r) => r.status() >= 400 && errors.push(`http ${r.status()}: ${r.url()}`));
  page.on("requestfailed", (r) => errors.push(`failed: ${r.url()} (${r.failure()?.errorText})`));
  await page.goto(url);
  await page.waitForFunction(() => (window.app ?? window.comfyAPI?.app?.app)?.graph, null, { timeout: 120000 });
  await page.waitForTimeout(3000);
  for (let i = 0; i < 3; i++) await page.keyboard.press("Escape"); // close the first-run templates dialog
  const wf = await page.evaluate((file) => {
    const app = window.app ?? window.comfyAPI.app.app;
    app.graph.clear();
    const add = (type, x, y) => { const n = LiteGraph.createNode(type); n.pos = [x, y]; app.graph.add(n); return n; };
    const load = add("LoadVideo", 20, 60);
    const parts = add("GetVideoComponents", 20, 520);
    const mv = add("MotionVerdict", 400, 60);
    const show = add("PreviewAny", 880, 60);
    load.widgets.find((w) => w.name === "file").value = file;
    load.connect(0, parts, 0);
    parts.connect(0, mv, 0);
    parts.connect(2, mv, mv.inputs.findIndex((i) => i.name === "fps"));
    mv.connect(5, show, 0);
    mv.setSize([440, 660]);
    show.setSize([520, 300]);
    app.graph.setDirtyCanvas(true, true);
    return JSON.stringify(app.graph.serialize(), null, 1);
  }, video);
  if (wfPath) fs.writeFileSync(wfPath, wf + "\n");
  await page.evaluate(() => (window.app ?? window.comfyAPI.app.app).queuePrompt(0, 1));
  let ok = true;
  try {
    await page.waitForFunction((src) => [...document.querySelectorAll("div")].some((d) => new RegExp(src).test(d.textContent) && d.offsetParent),
      BADGE.source, { timeout: 300000 });
    await page.waitForFunction(() => [...document.querySelectorAll("video")].some((v) => v.readyState >= 2 && v.src.startsWith("blob:")),
      null, { timeout: 60000 });
  } catch (e) {
    errors.push(`timeout: ${e.message.split("\n")[0]}`);
    ok = false;
  }
  await page.waitForTimeout(1500);
  for (let i = 0; i < 3; i++) await page.keyboard.press("Escape");
  await page.evaluate(() => { const app = window.app ?? window.comfyAPI.app.app; app.canvas.ds.offset = [10, -20]; app.canvas.ds.scale = 1; app.graph.setDirtyCanvas(true, true); });
  await page.waitForTimeout(800);
  await page.screenshot({ path: shot });
  const state = await page.evaluate((src) => {
    const b = [...document.querySelectorAll("div")].find((d) => new RegExp(src).test(d.textContent));
    const v = [...document.querySelectorAll("video")].find((x) => x.src.startsWith("blob:"));
    return { badge: b?.textContent ?? null, video: v ? { w: v.videoWidth, h: v.videoHeight, dur: v.duration } : null };
  }, BADGE.source);
  await browser.close();
  console.log(JSON.stringify(state));
  console.log(`${errors.length} console/page errors`);
  errors.forEach((e) => console.log("  " + e));
  process.exit(ok && state.badge && state.video ? 0 : 1);
})();
