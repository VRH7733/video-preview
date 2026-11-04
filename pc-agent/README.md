# PC Agent

Type a command on your phone; the PC runs it with Claude Code or Grok and shows the reply.
It has no AI model of its own: 0 VRAM, about 50 MB RAM. Not part of Motion Verdict; do not ship it in a release.

## Commands
- `claude: <task>`: continue the Claude Code session in the work folder
- `claude new: <task>`: start a fresh Claude Code session
- `grok: <prompt>` / `grok new: <prompt>`: ask Grok in the browser with your own login; the reply is saved to `<workdir>/scripts/`
- `stop`: stop the running Claude job

History is saved in `data/history.jsonl`.

## Setup on the Windows PC
1. Install Python 3.12, Git for Windows, Google Chrome, Tailscale (PC and phone, same account).
2. Install Claude Code and log in once: `irm https://claude.ai/install.ps1 | iex`, then `claude`.
3. `pip install playwright`
4. Copy `movie-template/` to your work folder (default `%USERPROFILE%\movie`), including `.claude/settings.json`.
5. `python agent.py --grok-login`: log in to Grok in the window that opens, then press Enter.
6. `start.bat` (or `python agent.py`). It prints the link with your secret token.
7. Make it reachable from the phone only through Tailscale: `tailscale serve --bg 8765`.
   On the phone open `https://<pc-name>.<tailnet>.ts.net/?t=<token>` and add it to the home screen.

`config.json` (created on first run) holds the work folder, port, token and Grok page selectors.
Keep the token secret. The server listens on 127.0.0.1 only.

## Status
- Server, token check, Claude job flow and history: tested with a stand-in `claude` command.
- Grok browser part: not tested yet. The page selectors may need one adjustment on the real grok.com.
