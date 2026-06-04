#!/usr/bin/env python3
"""
Claude Code status line — model, tokens, DeepSeek balance, directory.

Displays a rich, color-coded status line below the Claude Code chat input.
Shows: API balance (DeepSeek) | model name | context usage % | token counts | directory.

Installation:
  1. Copy this file to ~/.claude/statusline.py
  2. Add to ~/.claude/settings.json:
     "statusLine": { "type": "command", "command": "python3 ~/.claude/statusline.py" }
  3. Or run: python3 install.py

Requirements: Python 3.8+ (stdlib only, no pip packages needed)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Configuration ────────────────────────────────────────────────────────────

CACHE_FILE = os.path.expanduser("~/.claude/.statusline_balance_cache.json")
CACHE_TTL = 300  # seconds
API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
BALANCE_URL = "https://api.deepseek.com/user/balance"

# ── ANSI colors ──────────────────────────────────────────────────────────────

R = "\033[0m"       # reset
B = "\033[1m"       # bold
D = "\033[2m"       # dim

GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
CYAN    = "\033[96m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"
GRAY    = "\033[90m"


def color_for_balance(total: float) -> str:
    if total > 10:
        return GREEN
    elif total > 5:
        return GREEN
    elif total > 1:
        return YELLOW
    else:
        return RED


def color_for_pct(pct: int) -> str:
    if pct >= 90:
        return RED
    elif pct >= 70:
        return YELLOW
    elif pct >= 50:
        return YELLOW
    else:
        return GREEN


# ── Number formatting ────────────────────────────────────────────────────────


def format_num(n: int) -> str:
    if n >= 1_000_000:
        m = n // 1_000_000
        d = (n % 1_000_000) // 100_000
        return f"{m}.{d}M"
    elif n >= 1000:
        return f"{n // 1000}K"
    return str(n)


# ── DeepSeek balance ─────────────────────────────────────────────────────────


def fetch_balance() -> dict | None:
    """Fetch DeepSeek account balance with 5-min cache."""
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
            if time.time() - cache.get("ts", 0) < CACHE_TTL:
                return cache.get("data")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    if not API_KEY:
        return None

    try:
        req = urllib.request.Request(
            BALANCE_URL,
            headers={"Accept": "application/json", "Authorization": f"Bearer {API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f).get("data")
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return None

    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"ts": time.time(), "data": raw}, f)
    except OSError:
        pass

    return raw


def format_balance(balance_data: dict | None) -> str:
    if not balance_data or not balance_data.get("is_available"):
        if balance_data and not balance_data["is_available"]:
            return f"{RED}[Balance:¥0.00 ⚠]{R}"
        return ""

    infos = balance_data.get("balance_infos", [])
    if not infos:
        return ""

    total = float(infos[0].get("total_balance", "0"))
    currency = infos[0].get("currency", "CNY")
    symbol = "¥" if currency == "CNY" else "$"
    c = color_for_balance(total)

    warning = ""
    if total <= 1.0:
        warning = f" {RED}⚠{R}"
    elif total <= 5.0:
        warning = f" {YELLOW}·{R}"

    return f"{c}{B}{symbol}{total:.2f}{R}{warning}"


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, FileNotFoundError):
        return

    parts = []

    # Balance (DeepSeek)
    balance_data = fetch_balance()
    balance_str = format_balance(balance_data)
    if balance_str:
        parts.append(balance_str)

    # Vim mode
    vim_mode = data.get("vim", {}).get("mode", "")
    if vim_mode:
        parts.append(f"{MAGENTA}[{vim_mode}]{R}")

    # Agent name
    agent_name = data.get("agent", {}).get("name", "")
    if agent_name:
        parts.append(f"{MAGENTA}[Agent:{agent_name}]{R}")

    # Model display name
    model_display = data.get("model", {}).get("display_name", "")
    model_id = data.get("model", {}).get("id", "")
    if model_display and model_display != "Unknown":
        parts.append(f"{B}{CYAN}{model_display}{R}")
    elif model_id:
        parts.append(f"{B}{CYAN}{model_id}{R}")

    # Output style
    style = data.get("output_style", {}).get("name", "")
    if style and style.lower() not in ("default", ""):
        parts.append(f"{D}({style}){R}")

    # Separator
    parts.append(f"{GRAY}|{R}")

    # Context window
    ctx = data.get("context_window", {})
    used_pct = ctx.get("used_percentage")
    total_in = ctx.get("total_input_tokens", 0)
    total_out = ctx.get("total_output_tokens", 0)
    ctx_size = ctx.get("context_window_size", 0)

    if used_pct is not None:
        pct_int = int(float(used_pct))
        pct_color = color_for_pct(pct_int)

        if pct_int >= 90:
            bar = f"{RED}[!!!]{R}"
        elif pct_int >= 70:
            bar = f"{YELLOW}[!! ]{R}"
        elif pct_int >= 50:
            bar = f"{YELLOW}[!  ]{R}"
        else:
            bar = f"{GRAY}[   ]{R}"

        token_segment = (
            f"{D}Context{R} "
            f"{pct_color}{B}{used_pct}%{R} "
            f"{bar} "
        )

        if total_in > 0 or total_out > 0:
            in_fmt = format_num(total_in)
            out_fmt = format_num(total_out)
            token_segment += (
                f"{D}In:{R}{WHITE}{in_fmt}{R} "
                f"{D}Out:{R}{WHITE}{out_fmt}{R}"
            )
            if ctx_size > 0:
                ctx_fmt = format_num(ctx_size)
                token_segment += f" {GRAY}/ {ctx_fmt}{R}"
    else:
        token_segment = f"{GRAY}No messages yet{R}"

    parts.append(token_segment)

    # Rate limits
    rate_limits = data.get("rate_limits", {})
    five_hour = rate_limits.get("five_hour", {}).get("used_percentage")
    seven_day = rate_limits.get("seven_day", {}).get("used_percentage")
    if five_hour is not None or seven_day is not None:
        parts.append(f"{GRAY}|{R}")
        if five_hour is not None:
            parts.append(f"{D}5h:{R}{five_hour:.0f}%")
        if seven_day is not None:
            parts.append(f"{D}7d:{R}{seven_day:.0f}%")

    # Working directory
    cwd = data.get("workspace", {}).get("current_dir", "")
    if cwd:
        dir_short = cwd
        if len(dir_short) > 40:
            dir_short = "..." + dir_short[-38:]
        parts.append(f"{GRAY}[{dir_short}]{R}")

    # Session name
    session_name = data.get("session_name", "")
    if session_name:
        parts.append(f"{GRAY}({session_name}){R}")

    output = " ".join(parts).strip()
    while "  " in output:
        output = output.replace("  ", " ")

    sys.stdout.write(output)


if __name__ == "__main__":
    main()
