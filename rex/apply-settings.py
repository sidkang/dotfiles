#!/usr/bin/env python3
"""Apply Rex appearance settings from this repo to the local Rex app defaults."""

from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from pathlib import Path

DOMAIN = "com.superlogical.rex"
BUNDLE_THEME_NAME = "Catppuccin Latte"
THEME_FILE = Path(__file__).resolve().parent / "themes" / "catppuccin-latte.conf"
PREFS = Path.home() / "Library/Preferences" / f"{DOMAIN}.plist"

FONT_NAME = "Sarasa Term Slab SS17 SC Nerd Font"
FONT_SIZE = 15.0
CURSOR_STYLE = "block"
CURSOR_BLINK_MS = 400
CURSOR_SHADER = "comet"


def defaults_write(key: str, *args: str) -> None:
    subprocess.run(["defaults", "write", DOMAIN, key, *args], check=True)


def load_prefs() -> dict:
    if not PREFS.exists():
        return {}
    return plistlib.loads(PREFS.read_bytes())


def save_prefs(data: dict) -> None:
    PREFS.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))


def ensure_remote_control() -> None:
    defaults_write("rex.client.remoteControl", "-bool", "true")


def apply_font_and_cursor() -> None:
    defaults_write("Workspace.terminalFontName", "-string", FONT_NAME)
    defaults_write("Workspace.terminalFontPointSize", "-float", str(FONT_SIZE))
    defaults_write("Workspace.terminalCursorStyle", "-string", CURSOR_STYLE)
    defaults_write("Workspace.terminalCursorStyleForced", "-bool", "true")
    defaults_write("Workspace.terminalCursorBlinkUsesCustomInterval", "-bool", "true")
    defaults_write(
        "Workspace.terminalCursorBlinkIntervalMilliseconds",
        "-int",
        str(CURSOR_BLINK_MS),
    )
    defaults_write("Workspace.cursorShadersEnabled", "-bool", "true")
    defaults_write("Workspace.cursorShader", "-string", CURSOR_SHADER)
    defaults_write("Workspace.appearance", "-string", "light")


def rex_bin() -> Path:
    candidates = [
        Path.home()
        / "Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex",
        Path("/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex"),
        Path("/Applications/Rex.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit("rex binary not found")


def import_theme_if_needed(data: dict) -> str:
    themes_raw = data.get("Workspace.customThemes")
    themes: list[dict] = []
    if themes_raw:
        themes = json.loads(
            themes_raw.decode() if isinstance(themes_raw, (bytes, bytearray)) else themes_raw
        )

    for theme in themes:
        source = (theme.get("source") or {}).get("ghosttyFile") or {}
        if source.get("fileName") == THEME_FILE.name:
            theme["name"] = BUNDLE_THEME_NAME
            data["Workspace.customThemes"] = json.dumps(themes, separators=(",", ":")).encode()
            data["Workspace.lightThemeID"] = theme["id"]
            data["Workspace.appearance"] = "light"
            save_prefs(data)
            return theme["id"]

    if not THEME_FILE.is_file():
        raise SystemExit(f"missing theme file: {THEME_FILE}")

    ensure_remote_control()
    subprocess.run(
        [str(rex_bin()), "do", "client.theme.import", f"path={THEME_FILE}"],
        check=True,
    )

    data = load_prefs()
    themes_raw = data.get("Workspace.customThemes")
    if not themes_raw:
        raise SystemExit("theme import did not write Workspace.customThemes")
    themes = json.loads(
        themes_raw.decode() if isinstance(themes_raw, (bytes, bytearray)) else themes_raw
    )
    for theme in reversed(themes):
        source = (theme.get("source") or {}).get("ghosttyFile") or {}
        if source.get("fileName") == THEME_FILE.name:
            theme["name"] = BUNDLE_THEME_NAME
            # Keep a single copy of this file-based theme.
            themes = [
                t
                for t in themes
                if ((t.get("source") or {}).get("ghosttyFile") or {}).get("fileName")
                != THEME_FILE.name
            ] + [theme]
            data["Workspace.customThemes"] = json.dumps(themes, separators=(",", ":")).encode()
            data["Workspace.lightThemeID"] = theme["id"]
            data["Workspace.appearance"] = "light"
            save_prefs(data)
            return theme["id"]
    raise SystemExit("imported theme not found in preferences")


def main() -> int:
    if not THEME_FILE.is_file():
        print(f"missing {THEME_FILE}", file=sys.stderr)
        return 1

    ensure_remote_control()
    apply_font_and_cursor()
    data = load_prefs()
    theme_id = import_theme_if_needed(data)
    print(f"font={FONT_NAME} size={FONT_SIZE}")
    print(f"cursor={CURSOR_STYLE} blink_ms={CURSOR_BLINK_MS} shader={CURSOR_SHADER}")
    print(f"theme={BUNDLE_THEME_NAME} id={theme_id}")
    print("remote_control=on")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
