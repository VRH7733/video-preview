"""Integration test through a running ComfyUI's HTTP API (no browser).

    python tests/api_run.py [http://127.0.0.1:8188] <video in ComfyUI/input> [<video> ...]

For each video it queues  Load Video -> Get Video Components -> Motion Verdict -> Preview Any (report)
+ Save Image (timeline), with save_report on, waits for the result and prints what came back through
/history: the node's own ui payload, the Preview Any text and the saved files. Exit code 1 on any error.
Uses only the Python standard library.
"""

import json
import sys
import time
import urllib.request
import uuid


def call(base, path, data=None):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def workflow(video):
    return {
        "1": {"class_type": "LoadVideo", "inputs": {"file": video}},
        "2": {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}},
        "3": {"class_type": "MotionVerdict", "inputs": {
            "images": ["2", 0], "fps": ["2", 2], "min_speed": 1.5, "min_area": 0.3,
            "preview": "video + motion overlay", "save_report": True}},
        "4": {"class_type": "PreviewAny", "inputs": {"source": ["3", 5]}},
        "5": {"class_type": "SaveImage", "inputs": {"images": ["3", 4], "filename_prefix": "motion_verdict/timeline"}},
    }


def main():
    args = sys.argv[1:]
    base = args.pop(0) if args and args[0].startswith("http") else "http://127.0.0.1:8188"
    ok = True
    for video in args:
        pid = call(base, "/prompt", {"prompt": workflow(video), "client_id": str(uuid.uuid4())})["prompt_id"]
        t0 = time.time()
        while True:
            hist = call(base, f"/history/{pid}")
            if pid in hist and hist[pid].get("status", {}).get("completed") is not None:
                break
            if time.time() - t0 > 300:
                raise TimeoutError(video)
            time.sleep(0.5)
        h = hist[pid]
        status = h["status"]["status_str"]
        outs = h["outputs"]
        mv = outs.get("3", {}).get("motion_verdict", [{}])[0]
        text = outs.get("4", {}).get("text", [""])[0]
        saved = outs.get("5", {}).get("images", [])
        print(f"== {video}: status={status} in {time.time() - t0:.1f}s")
        print(f"   node ui: verdict={mv.get('verdict')} token={'yes' if mv.get('token') else 'no'} saved={mv.get('saved')}")
        print(f"   Preview Any text, first line: {text.splitlines()[0] if text else None}")
        print(f"   Save Image: {[s['filename'] for s in saved]}")
        ok &= status == "success" and bool(mv.get("verdict")) and text.startswith("Motion Verdict:") and bool(saved)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
