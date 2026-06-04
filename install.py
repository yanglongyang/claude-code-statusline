#!/usr/bin/env python3
"""
Installer for Claude Code status line.

Usage:
  python3 install.py          # install to ~/.claude/settings.json
  python3 install.py --local  # install to ~/.claude/settings.local.json
  python3 install.py --uninstall  # remove statusLine from settings

Copies statusline.py to ~/.claude/ and adds the statusLine hook to settings.
"""

import json
import os
import shutil
import sys

SCRIPT_NAME = "statusline.py"
SETTINGS_KEY = "statusLine"
HOOK_CONFIG = {"type": "command", "command": f"python3 ~/.claude/{SCRIPT_NAME}"}


def settings_path(local: bool = False) -> str:
    filename = "settings.local.json" if local else "settings.json"
    return os.path.expanduser(f"~/.claude/{filename}")


def read_settings(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_settings(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def install(local: bool = False) -> None:
    # Copy the script
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), SCRIPT_NAME)
    dst = os.path.expanduser(f"~/.claude/{SCRIPT_NAME}")
    shutil.copy2(src, dst)
    print(f"  Copied {os.path.basename(src)} -> {dst}")

    # Update settings
    sp = settings_path(local)
    settings = read_settings(sp)

    if settings.get(SETTINGS_KEY) == HOOK_CONFIG:
        print(f"  Already configured in {sp}")
        return

    settings[SETTINGS_KEY] = HOOK_CONFIG
    write_settings(sp, settings)
    print(f"  Added statusLine hook to {sp}")


def uninstall(local: bool = False) -> None:
    sp = settings_path(local)
    settings = read_settings(sp)

    if SETTINGS_KEY not in settings:
        print(f"  No statusLine hook found in {sp}")
        return

    del settings[SETTINGS_KEY]
    write_settings(sp, settings)
    print(f"  Removed statusLine from {sp}")

    # Optionally remove the script
    script = os.path.expanduser(f"~/.claude/{SCRIPT_NAME}")
    if os.path.exists(script):
        os.remove(script)
        print(f"  Removed {script}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    local = "--local" in sys.argv
    uninstall_flag = "--uninstall" in sys.argv

    if uninstall_flag:
        print("Uninstalling Claude Code status line...")
        uninstall(local)
        print("Done.")
    else:
        print("Installing Claude Code status line...")
        install(local)
        print("Done. Restart Claude Code to see the status line.")


if __name__ == "__main__":
    main()
