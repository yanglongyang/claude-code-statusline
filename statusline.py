#!/usr/bin/env python3
"""Status line command for Claude Code - model, tokens, balance, directory (with colors)."""
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE_FILE = os.path.expanduser("~/.claude/.deepseek_balance_cache.json")
DAILY_FILE = os.path.expanduser("~/.claude/.statusline_daily_cache.json")
CACHE_TTL = 300
API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
BALANCE_URL = "https://api.deepseek.com/user/balance"

# DeepSeek pricing (¥ per 1M tokens). Override via env vars.
INPUT_PRICE = float(os.environ.get("DEEPSEEK_INPUT_PRICE",  "1.0"))
OUTPUT_PRICE = float(os.environ.get("DEEPSEEK_OUTPUT_PRICE", "2.0"))

# ── ANSI color helpers ─────────────────────────────────────────────────────

R = "\033[0m"       # reset
B = "\033[1m"       # bold
D = "\033[2m"       # dim

# 8-bit bright colors (works on most terminals)
GREEN = "\033[92m"   # bright green
YELLOW = "\033[93m"  # bright yellow
RED = "\033[91m"     # bright red
CYAN = "\033[96m"    # bright cyan
BLUE = "\033[94m"    # bright blue
MAGENTA = "\033[95m" # bright magenta
WHITE = "\033[97m"   # bright white
GRAY = "\033[90m"    # bright black = gray

# 256-color variants (fallback)
GREEN256 = "\033[38;5;46m"
YELLOW256 = "\033[38;5;226m"
ORANGE256 = "\033[38;5;214m"
RED256 = "\033[38;5;196m"
GRAY256 = "\033[38;5;243m"


def color_for_balance(total: float) -> str:
    if total > 10:
        return GREEN
    elif total > 5:
        return GREEN  # still healthy
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


# ── number formatting ──────────────────────────────────────────────────────


def format_num(n: int) -> str:
    if n >= 1_000_000:
        m = n // 1_000_000
        d = (n % 1_000_000) // 100_000
        return f"{m}.{d}M"
    elif n >= 1000:
        return f"{n // 1000}K"
    return str(n)


# ── balance ────────────────────────────────────────────────────────────────


def fetch_balance() -> dict | None:
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


# ── Daily token tracking ─────────────────────────────────────────────────────


def track_daily(total_in: int, total_out: int) -> tuple[int, float]:
    """Track cumulative token usage for today across sessions.

    Returns (today_total_tokens, today_cost_rmb).
    """
    today = time.strftime("%Y-%m-%d")
    try:
        with open(DAILY_FILE) as f:
            cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}

    if cache.get("date") != today:
        cache = {"date": today, "daily_total": 0, "session_peak": 0}

    session_total = total_in + total_out
    session_peak = cache.get("session_peak", 0)

    if session_total > session_peak:
        cache["daily_total"] += session_total - session_peak
        cache["session_peak"] = session_total

    try:
        os.makedirs(os.path.dirname(DAILY_FILE), exist_ok=True)
        with open(DAILY_FILE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass

    daily_total = cache.get("daily_total", 0)
    cost = (total_in / 1_000_000) * INPUT_PRICE + (total_out / 1_000_000) * OUTPUT_PRICE
    return daily_total, cost


# ── main ───────────────────────────────────────────────────────────────────


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, FileNotFoundError):
        return

    parts = []

    # ── Balance ──
    balance_data = fetch_balance()
    balance_str = format_balance(balance_data)
    if balance_str:
        parts.append(balance_str)

    # ── Vim mode ──
    vim_mode = data.get("vim", {}).get("mode", "")
    if vim_mode:
        parts.append(f"{MAGENTA}[{vim_mode}]{R}")

    # ── Agent ──
    agent_name = data.get("agent", {}).get("name", "")
    if agent_name:
        parts.append(f"{MAGENTA}[Agent:{agent_name}]{R}")

    # ── Model ──
    model_display = data.get("model", {}).get("display_name", "")
    model_id = data.get("model", {}).get("id", "")
    if model_display and model_display != "Unknown":
        parts.append(f"{B}{CYAN}{model_display}{R}")
    elif model_id:
        parts.append(f"{B}{CYAN}{model_id}{R}")

    # ── Output style ──
    style = data.get("output_style", {}).get("name", "")
    if style and style.lower() not in ("default", ""):
        if parts:
            parts[-1] = parts[-1].replace(R, f" {D}({style}){R}")
        else:
            parts.append(f"{D}({style}){R}")

    # ── Separator ──
    parts.append(f"{GRAY}|{R}")

    # ── Context window tokens ──
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

            daily_total, _ = track_daily(total_in, total_out)
            if daily_total > 0:
                daily_fmt = format_num(daily_total)
                token_segment += f" {GRAY}| Today:{R}{WHITE}{daily_fmt}{R}"
    else:
        token_segment = f"{GRAY}No messages yet{R}"

    parts.append(token_segment)

    # ── Rate limits ──
    rate_limits = data.get("rate_limits", {})
    five_hour = rate_limits.get("five_hour", {}).get("used_percentage")
    seven_day = rate_limits.get("seven_day", {}).get("used_percentage")
    if five_hour is not None or seven_day is not None:
        parts.append(f"{GRAY}|{R}")
        if five_hour is not None:
            parts.append(f"{D}5h:{R}{five_hour:.0f}%")
        if seven_day is not None:
            parts.append(f"{D}7d:{R}{seven_day:.0f}%")

    # ── Directory ──
    cwd = data.get("workspace", {}).get("current_dir", "")
    if cwd:
        dir_short = cwd
        if len(dir_short) > 40:
            dir_short = "..." + dir_short[-38:]
        parts.append(f"{GRAY}[{dir_short}]{R}")

    # ── Session name ──
    session_name = data.get("session_name", "")
    if session_name:
        parts.append(f"{GRAY}({session_name}){R}")

    output = " ".join(parts).strip()
    while "  " in output:
        output = output.replace("  ", " ")

    sys.stdout.write(output)


if __name__ == "__main__":
    main()
