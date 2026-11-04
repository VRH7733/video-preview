"""PC Agent: type a command on your phone, the PC runs it with Claude Code or Grok.

    claude: <task>       continue the Claude Code session in the work folder
    claude new: <task>   start a fresh Claude Code session
    grok: <prompt>       send to Grok in the same Grok chat (browser, your login)
    grok new: <prompt>   open a new Grok chat first
    stop                 stop the running Claude job

Every command and reply is saved in data/history.jsonl. Grok replies are also saved
as files in <workdir>/scripts/ so Claude can use them.

Run:  python agent.py              (starts the server)
      python agent.py --grok-login (opens the browser once so you can log in to Grok)
"""
import html
import json
import secrets
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
DATA = HERE / "data"
HISTORY = DATA / "history.jsonl"
GROK_PROFILE = DATA / "grok-browser-profile"

DEFAULT_CONFIG = {
    "workdir": str(Path.home() / "movie"),
    "host": "127.0.0.1",
    "port": 8765,
    "token": "",
    "claude_timeout_min": 120,
    "grok_url": "https://grok.com",
    "grok_input_selector": "textarea, div[contenteditable='true']",
    "grok_browser_channel": "chrome",
    "grok_timeout_s": 300,
}


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_config():
    DATA.mkdir(exist_ok=True)
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    if not cfg["token"]:
        cfg["token"] = secrets.token_urlsafe(16)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    Path(cfg["workdir"]).mkdir(parents=True, exist_ok=True)
    return cfg


CFG = None
JOBS = {}
JOBS_LOCK = threading.Lock()
CLAUDE_LOCK = threading.Lock()
CLAUDE_PROC = {"p": None}
GROK_QUEUE = Queue()


def save_history(job):
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(job, ensure_ascii=False) + "\n")


def new_job(kind, text):
    job = {"id": uuid.uuid4().hex[:8], "kind": kind, "text": text, "status": "queued",
           "output": "", "created": now(), "finished": None}
    with JOBS_LOCK:
        JOBS[job["id"]] = job
    return job


def finish(job, status, output):
    job["status"], job["output"], job["finished"] = status, output, now()
    save_history(job)


# ---------------------------------------------------------------- Claude Code
def _run_claude_once(text, fresh):
    exe = shutil.which("claude")
    if not exe:
        return 127, "The 'claude' command was not found. Install Claude Code and log in first."
    cmd = [exe, "-p", "--output-format", "text"]
    if not fresh:
        cmd.insert(1, "--continue")
    p = subprocess.Popen(cmd, cwd=CFG["workdir"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    CLAUDE_PROC["p"] = p
    try:
        out, _ = p.communicate(text, timeout=CFG["claude_timeout_min"] * 60)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
        return 124, (out or "") + "\n[stopped: time limit reached]"
    finally:
        CLAUDE_PROC["p"] = None
    return p.returncode, out


def run_claude(job, fresh):
    with CLAUDE_LOCK:
        job["status"] = "running"
        code, out = _run_claude_once(job["text"], fresh)
        if code != 0 and not fresh and "no conversation" in (out or "").lower():
            code, out = _run_claude_once(job["text"], True)
        finish(job, "done" if code == 0 else f"error ({code})", out.strip())


def stop_claude():
    p = CLAUDE_PROC["p"]
    if p and p.poll() is None:
        p.kill()
        return "Stopped the running Claude job."
    return "No Claude job is running."


# ---------------------------------------------------------------- Grok (browser)
def _open_grok_browser(pw):
    kwargs = {"headless": False}
    if CFG.get("grok_browser_channel"):
        kwargs["channel"] = CFG["grok_browser_channel"]
    return pw.chromium.launch_persistent_context(str(GROK_PROFILE), **kwargs)


def _ask_grok(page, text, fresh):
    if fresh or not page.url.startswith(CFG["grok_url"]):
        page.goto(CFG["grok_url"])
    box = page.locator(CFG["grok_input_selector"]).first
    box.wait_for(timeout=30000)
    before = page.inner_text("body")
    box.click()
    box.fill(text)
    page.keyboard.press("Enter")
    deadline = time.time() + CFG["grok_timeout_s"]
    last, stable_since = before, time.time()
    while time.time() < deadline:
        time.sleep(2)
        cur = page.inner_text("body")
        if cur != last:
            last, stable_since = cur, time.time()
        elif last != before and time.time() - stable_since > 8:
            break
    else:
        raise TimeoutError("Grok did not finish in time.")
    key = text.strip()[:200]
    idx = last.rfind(key)
    return (last[idx + len(key):] if idx >= 0 else last[len(before):]).strip()


def grok_worker():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        while True:
            job, _ = GROK_QUEUE.get()
            finish(job, "error", "Playwright is missing: run  pip install playwright")
    with sync_playwright() as pw:
        ctx, page = None, None
        while True:
            job, fresh = GROK_QUEUE.get()
            job["status"] = "running"
            try:
                if ctx is None:
                    ctx = _open_grok_browser(pw)
                    page = ctx.pages[0] if ctx.pages else ctx.new_page()
                reply = _ask_grok(page, job["text"], fresh)
                out_dir = Path(CFG["workdir"]) / "scripts"
                out_dir.mkdir(parents=True, exist_ok=True)
                f = out_dir / f"grok-{datetime.now():%Y%m%d-%H%M%S}.md"
                f.write_text(f"# Prompt\n\n{job['text']}\n\n# Grok\n\n{reply}\n", encoding="utf-8")
                finish(job, "done", f"[saved: {f}]\n\n{reply}")
            except Exception as e:  # keep the worker alive whatever the page does
                finish(job, "error", f"{type(e).__name__}: {e}")
                try:
                    if ctx is not None:
                        ctx.close()
                except Exception:
                    pass
                ctx = page = None


def grok_login():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = _open_grok_browser(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(CFG["grok_url"])
        input("Log in to Grok in the browser window, then press Enter here... ")
        ctx.close()
    print("Saved. The agent will reuse this login.")


# ---------------------------------------------------------------- commands
HELP = ("claude: <task> | claude new: <task> | grok: <prompt> | grok new: <prompt> | stop")


def handle(text):
    t = text.strip()
    low = t.lower()
    for prefix, kind, fresh in (("claude new:", "claude", True), ("claude:", "claude", False),
                                ("grok new:", "grok", True), ("grok:", "grok", False)):
        if low.startswith(prefix):
            body = t[len(prefix):].strip()
            if not body:
                break
            job = new_job(kind, body)
            if kind == "claude":
                threading.Thread(target=run_claude, args=(job, fresh), daemon=True).start()
            else:
                GROK_QUEUE.put((job, fresh))
            return job
    job = new_job("system", t)
    finish(job, "done", stop_claude() if low == "stop" else "Commands: " + HELP)
    return job


# ---------------------------------------------------------------- phone web page
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PC Agent</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;padding:12px;background:#111;color:#eee}
textarea{width:100%;box-sizing:border-box;height:90px;font-size:16px;background:#222;color:#eee;border:1px solid #444;border-radius:8px;padding:8px}
button{font-size:16px;padding:10px 16px;margin:6px 6px 0 0;border:0;border-radius:8px;background:#3b82f6;color:#fff}
.job{border:1px solid #333;border-radius:8px;padding:8px;margin-top:10px}
.meta{font-size:12px;color:#999}pre{white-space:pre-wrap;word-break:break-word;margin:6px 0 0}
</style></head><body>
<textarea id="t" placeholder="claude: edit ep01 ...   |   grok: write scene 5 ..."></textarea>
<button onclick="pre('claude: ')">claude:</button><button onclick="pre('grok: ')">grok:</button>
<button onclick="send()">Send</button><button onclick="document.getElementById('t').value='stop';send()" style="background:#b91c1c">Stop</button>
<div id="jobs"></div>
<script>
const tok=new URLSearchParams(location.search).get('t')||'';
function pre(p){const t=document.getElementById('t');if(!t.value.startsWith(p))t.value=p+t.value;t.focus()}
async function send(){const t=document.getElementById('t');if(!t.value.trim())return;
 await fetch('/send?t='+encodeURIComponent(tok),{method:'POST',body:t.value});t.value='';load()}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function load(){const r=await fetch('/jobs?t='+encodeURIComponent(tok));if(!r.ok)return;
 const j=await r.json();document.getElementById('jobs').innerHTML=j.map(x=>
 `<div class="job"><div class="meta">${x.kind} · ${x.status} · ${x.created}</div><b>${esc(x.text)}</b><pre>${esc(x.output||'')}</pre></div>`).join('')}
load();setInterval(load,3000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _ok_token(self):
        q = parse_qs(urlparse(self.path).query)
        return secrets.compare_digest(q.get("t", [""])[0], CFG["token"])

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._ok_token():
            return self._send(403, "Wrong or missing token.")
        path = urlparse(self.path).path
        if path == "/":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if path == "/jobs":
            with JOBS_LOCK:
                jobs = sorted(JOBS.values(), key=lambda j: j["created"], reverse=True)[:30]
            return self._send(200, json.dumps(jobs, ensure_ascii=False), "application/json")
        self._send(404, "Not found")

    def do_POST(self):
        if not self._ok_token():
            return self._send(403, "Wrong or missing token.")
        if urlparse(self.path).path != "/send":
            return self._send(404, "Not found")
        n = int(self.headers.get("Content-Length") or 0)
        if n > 200_000:
            return self._send(413, "Too long.")
        job = handle(self.rfile.read(n).decode("utf-8", errors="replace"))
        self._send(200, json.dumps(job, ensure_ascii=False), "application/json")

    def log_message(self, *args):
        pass


def main():
    global CFG
    CFG = load_config()
    if "--grok-login" in sys.argv:
        return grok_login()
    threading.Thread(target=grok_worker, daemon=True).start()
    srv = ThreadingHTTPServer((CFG["host"], CFG["port"]), Handler)
    print(f"PC Agent running. Work folder: {CFG['workdir']}")
    print(f"On this PC:  http://localhost:{CFG['port']}/?t={CFG['token']}")
    print("On the phone: your Tailscale address (see README) + /?t=" + html.escape(CFG["token"]))
    srv.serve_forever()


if __name__ == "__main__":
    main()
