# Claude Code Statusline

Real-time status line for Claude Code, showing model info, token usage, DeepSeek balance, and working directory below the chat input.

![screenshot](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)

## Features

- **DeepSeek balance** — live API balance with color-coded warnings (green > ¥10, yellow > ¥1, red < ¥1)
- **Model name** — current model display name (cyan, bold)
- **Context usage** — percentage bar with visual indicators (`[!!!]` at 90%, `[!! ]` at 70%, `[! ]` at 50%)
- **Token counts** — input/output tokens with K/M formatting
- **Rate limits** — 5-hour and 7-day rate limit percentages (Anthropic API only)
- **Working directory** — current path (truncated to 40 chars)
- **Vim mode / Agent / Session** — additional indicators when active

## Quick Start

### One-command install

```bash
python3 install.py
```

This copies `statusline.py` to `~/.claude/` and configures the hook in `~/.claude/settings.json`. Restart Claude Code to apply.

### Install to local settings

```bash
python3 install.py --local
```

Uses `settings.local.json` instead (not committed to dotfiles repos).

### Uninstall

```bash
python3 install.py --uninstall
```

## Manual Setup

1. Copy `statusline.py` to `~/.claude/statusline.py`:
   ```bash
   cp statusline.py ~/.claude/statusline.py
   ```

2. Add to `~/.claude/settings.json`:
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "python3 ~/.claude/statusline.py"
     }
   }
   ```

3. Restart Claude Code.

## Requirements

- Python 3.8+ (stdlib only, no pip packages needed)
- `ANTHROPIC_AUTH_TOKEN` environment variable set (for DeepSeek balance display)

## How It Works

Claude Code passes a JSON object to the status line command via stdin with fields like:

```json
{
  "model": { "display_name": "DeepSeek V4 Pro", "id": "deepseek-v4-pro" },
  "context_window": {
    "used_percentage": "45.2",
    "total_input_tokens": 124000,
    "total_output_tokens": 8500,
    "context_window_size": 262144
  },
  "workspace": { "current_dir": "/c/Users/yly12/Projects" },
  "vim": { "mode": "" },
  "agent": { "name": "" },
  "session_name": "main"
}
```

The script outputs a single line of ANSI-colored text, displayed below the chat input.

## Customization

Edit `~/.claude/statusline.py` to change:
- Balance API endpoint (if not using DeepSeek)
- Color scheme
- Display fields
- Cache TTL (default: 5 minutes)

## License

MIT
