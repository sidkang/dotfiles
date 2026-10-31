#!/usr/bin/env python3
"""Apply Rex appearance settings from this repo to the local Rex app defaults.

Source of truth: glacier's preferred Workspace / rex.* settings.
Machine-local layout (window frames, sidebar width) is left alone.
"""

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
FONT_SIZE = 14.5
CURSOR_STYLE = "block"
CURSOR_BLINK_MS = 400
CURSOR_SHADER = "comet"
DARK_THEME_ID = "merino-dark"


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


def apply_workspace_settings() -> None:
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
    defaults_write("Workspace.darkThemeID", "-string", DARK_THEME_ID)
    defaults_write("Workspace.interfaceStyle", "-string", "system")
    defaults_write("Workspace.tabStyle", "-string", "vertical")
    defaults_write("Workspace.tabIconTintMode", "-string", "off")
    defaults_write("Workspace.tabIconColorMode", "-string", "always")
    defaults_write("Workspace.paneDensity", "-string", "compact")
    defaults_write("Workspace.inactivePaneFadeMode", "-string", "none")
    defaults_write("Workspace.usesPaneGlass", "-bool", "true")
    defaults_write("Workspace.usesStandardInactiveWindowPaneStyles", "-bool", "false")
    defaults_write("Workspace.showsActivePaneBorder", "-bool", "false")
    defaults_write("Workspace.showsPaneHeaders", "-bool", "false")
    defaults_write("Workspace.tintsPanesWithProgramBackground", "-bool", "true")
    defaults_write("Workspace.terminalAllowsLigatures", "-bool", "true")
    defaults_write("Workspace.terminalFontSmoothing", "-bool", "false")
    defaults_write("Workspace.terminalUsesDisplayP3", "-bool", "true")
    defaults_write("Workspace.appIcon", "-string", "light")
    defaults_write("Workspace.appIconVisibility", "-string", "menuBarOnly")
    defaults_write("Workspace.animationStyle", "-string", "natural")
    defaults_write("Workspace.allowsTerminalNotifications", "-bool", "true")
    defaults_write("Workspace.notificationPosition", "-string", "bottom-right")
    defaults_write("Workspace.sidebarPosition", "-string", "left")
    defaults_write("rex.server.automatic-restart-enabled", "-bool", "true")
    defaults_write("rex.agents.names-sessions", "-bool", "false")


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


def local_hostname() -> str:
    for args in (["scutil", "--get", "LocalHostName"], ["hostname", "-s"]):
        try:
            out = subprocess.run(args, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError):
            continue
        name = out.stdout.strip()
        if name:
            return name
    return ""


def local_app_client(rex: Path) -> str:
    """Pick this machine's Rex app client so theme import is unambiguous."""
    out = subprocess.run(
        [str(rex), "client", "ls", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    clients = json.loads(out.stdout).get("clients") or []
    apps = []
    for client in clients:
        info = client.get("info") or {}
        principal = client.get("principal") or {}
        if info.get("kind") != "app":
            continue
        if principal.get("transport") != "unix":
            continue
        label = info.get("label") or client.get("client_id")
        if label:
            apps.append(label)
    if not apps:
        raise SystemExit("no local Rex app client connected; open Rex first")
    host = local_hostname().casefold()
    for label in apps:
        if label.casefold() == host:
            return label
    if len(apps) == 1:
        return apps[0]
    raise SystemExit(f"ambiguous local Rex app clients: {', '.join(apps)}")


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
    rex = rex_bin()
    client = local_app_client(rex)
    subprocess.run(
        [
            str(rex),
            "-C",
            client,
            "do",
            "client.theme.import",
            f"path={THEME_FILE}",
        ],
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
    apply_workspace_settings()
    data = load_prefs()
    theme_id = import_theme_if_needed(data)
    print(f"font={FONT_NAME} size={FONT_SIZE}")
    print(f"cursor={CURSOR_STYLE} blink_ms={CURSOR_BLINK_MS} shader={CURSOR_SHADER}")
    print(f"theme={BUNDLE_THEME_NAME} id={theme_id}")
    print("tabs=vertical pane_glass=on inactive_fade=none")
    print("remote_control=on automatic_restart=on")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
