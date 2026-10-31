#!/usr/bin/env python3
# Startup time matters (one process per key press): keep imports minimal.

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import namedtuple
from collections.abc import Sequence
from pathlib import Path


INFO = "info"
ERROR = "error"
GHOST_WORKSPACE = "BIN"
KITTY_SOCKET = "unix:/tmp/kitten"
KITTY_BIN = "/opt/homebrew/bin/kitten"
KITTY_BUNDLE_ID = "net.kovidgoyal.kitty"
KITTY_HOTKEY_TITLE = "kitty-hotkey"
KITTY_HOTKEY_SESSION = "hotkey"
REX_BUNDLE_ID = "com.superlogical.rex"
REX_HOTKEY_SESSION = "hotkey"
REX_HOTKEY_TITLE_SUFFIX = " - hotkey"
REX_HOTKEY_HIDE_WORKSPACE = "T"
REX_CLIENT_WAIT_SEC = 5.0
REX_WINDOW_WAIT_SEC = 3.0
HOTKEY_STATE_DIR = Path(os.path.expanduser("~/.local/state/aerospace"))
HOTKEY_ID_FILE = HOTKEY_STATE_DIR / "hotkey-id"
HOTKEY_HIDDEN_FILE = HOTKEY_STATE_DIR / "hotkey-hidden"
HOTKEY_KEEP_FILE = HOTKEY_STATE_DIR / "hotkey-keep"
HOTKEY_WS_FILE = HOTKEY_STATE_DIR / "hotkey-ws"
FOCUS_RETRY_DELAY_SEC = 0.05
HS_CLI = os.path.expanduser("~/.local/bin/hs")
URL_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~")
REX_BIN_CANDIDATES = (
    os.path.expanduser(
        "~/Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex"
    ),
    "/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex",
    "/Applications/Rex.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex",
)
REX_APP_CANDIDATES = ("Rex Beta", "Rex")


AppRule = namedtuple(
    "AppRule",
    "bundle_id launch_args home_workspace mode window_title",
    defaults=(None, "focus_only", None),
)
KittyHotkeyRule = namedtuple("KittyHotkeyRule", "hide_workspace launch_args")


APP_RULES = {
    "obsidian": AppRule(
        bundle_id="md.obsidian",
        launch_args=("open", "-a", "Obsidian"),
        home_workspace="Q",
        mode="summon_to_home",
    ),
    "wechat": AppRule(
        bundle_id="com.tencent.xinWeChat",
        launch_args=("open", "-a", "WeChat"),
        home_workspace="1",
        mode="summon_to_home",
        window_title="WeChat",
    ),
    "telegram": AppRule(
        bundle_id="ru.keepcoder.Telegram",
        launch_args=("open", "-a", "Telegram"),
        home_workspace="1",
        mode="summon_to_home",
    ),
    "chrome": AppRule(
        bundle_id="com.google.Chrome",
        launch_args=("open", "-a", "Google Chrome"),
        home_workspace="2",
        mode="summon_to_home",
    ),
}

KITTY_HOTKEY_RULE = KittyHotkeyRule(
    hide_workspace="T",
    launch_args=(
        KITTY_BIN,
        "@",
        "--to",
        KITTY_SOCKET,
        "launch",
        "--type",
        "os-window",
        "--os-window-title",
        KITTY_HOTKEY_TITLE,
        "--add-to-session",
        KITTY_HOTKEY_SESSION,
        "--cwd=~",
    ),
)


def run_cmd(
    args: Sequence[str], check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=check)


def check_cmd(args: Sequence[str]) -> str:
    return run_cmd(args, check=True).stdout.strip()


def quote(text: str) -> str:
    return "".join(c if c in URL_SAFE else "".join(f"%{b:02X}" for b in c.encode()) for c in text)


def hammerspoon_url(route: str, **params: str) -> str:
    query = "&".join(f"{key}={quote(value)}" for key, value in params.items())
    return f"{route}?{query}"


def hammerspoon(route: str, **params: str) -> None:
    """Call a Hammerspoon URL route over IPC; fall back to `open` if Hammerspoon is not reachable."""
    url = hammerspoon_url(route, **params)
    if run_cmd((HS_CLI, "-q", "-c", f'hsurl("{url}")')).returncode != 0:
        run_cmd(("open", "-g", f"hammerspoon://{url}"))


def notify(message: str, level: str = INFO) -> None:
    hammerspoon("notify", msg=message, level=level)


def notify_command_error(exc: subprocess.CalledProcessError) -> None:
    output = (exc.stderr or exc.stdout or "").strip()
    command = " ".join(str(arg) for arg in exc.cmd)
    message = output or f"exit {exc.returncode}"
    notify(f"Command failed: {command}: {message}", ERROR)


def focused_window_id() -> str | None:
    result = run_cmd(
        ("aerospace", "list-windows", "--focused", "--format", "%{window-id}")
    )
    if result.returncode != 0:
        return None

    window_id = result.stdout.strip()
    return window_id or None


def focused_window_value(field: str) -> str | None:
    result = run_cmd(("aerospace", "list-windows", "--focused", "--format", field))
    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    return value or None


def focused_workspace() -> str:
    return check_cmd(
        ("aerospace", "list-workspaces", "--monitor", "focused", "--visible")
    )


def list_window_ids(*args: str) -> list[str]:
    output = check_cmd(("aerospace", "list-windows", *args, "--format", "%{window-id}"))
    return [line for line in output.splitlines() if line]


def focus_window(window_id: str) -> None:
    check_cmd(("aerospace", "focus", "--window-id", window_id))


def focus_window_robustly(window_id: str) -> None:
    # Happy path: focus once and return immediately. Sleep only on retry.
    focus_window(window_id)
    if focused_window_id() == window_id:
        return

    for _ in range(2):
        time.sleep(FOCUS_RETRY_DELAY_SEC)
        focus_window(window_id)
        if focused_window_id() == window_id:
            return

    notify(f"Failed to focus window {window_id}", ERROR)


def move_window_to_workspace(
    window_id: str, workspace: str, focus_follows: bool = False
) -> None:
    args = ["aerospace", "move-node-to-workspace"]
    if focus_follows:
        args.append("--focus-follows-window")
    args.extend(("--window-id", window_id, workspace))
    check_cmd(tuple(args))


def smart_move(axis: str, size: str, direction: str) -> None:
    if axis not in {"h", "v"}:
        notify(f"Invalid move axis: {axis}", ERROR)
        return
    if direction not in {"left", "right", "up", "down"}:
        notify(f"Invalid move direction: {direction}", ERROR)
        return

    if focused_window_value("%{window-layout}") == "floating":
        hammerspoon("floatwindow", action="move", axis=axis, size=size)
        return

    check_cmd(
        (
            "aerospace",
            "move",
            "--boundaries",
            "all-monitors-outer-frame",
            "--boundaries-action",
            "stop",
            direction,
        )
    )


def smart_resize(axis: str, size: str) -> None:
    if axis not in {"width", "height"}:
        notify(f"Invalid resize axis: {axis}", ERROR)
        return

    if focused_window_value("%{window-layout}") == "floating":
        hammerspoon("floatwindow", action="resize", axis=axis, size=size)
        return

    check_cmd(("aerospace", "resize", axis, size))


def launch_app(rule: AppRule) -> None:
    run_cmd(rule.launch_args)


def launch_kitty_hotkey() -> None:
    result = run_cmd(KITTY_HOTKEY_RULE.launch_args)
    if result.returncode != 0:
        notify("Failed to launch kitty hotkey", ERROR)


def next_id(ids: Sequence[str], current_id: str | None, direction: str) -> str:
    if current_id not in ids:
        return ids[0]

    current_index = ids.index(current_id)
    if direction == "next":
        return ids[(current_index + 1) % len(ids)]
    if direction == "prev":
        return ids[(current_index - 1) % len(ids)]

    raise ValueError(f"invalid direction: {direction}")


def toggle_app(app_name: str) -> None:
    rule = APP_RULES.get(app_name)
    if rule is None:
        notify(f"Unknown app: {app_name}", ERROR)
        return

    rows = check_cmd(
        (
            "aerospace",
            "list-windows",
            "--monitor",
            "all",
            "--app-bundle-id",
            rule.bundle_id,
            "--format",
            "%{window-id}\t%{workspace}\t%{window-title}",
        )
    )
    windows: list[tuple[str, str]] = []
    for line in rows.splitlines():
        if not line:
            continue
        parts = line.split("\t", 2)
        if len(parts) < 2:
            continue
        window_id, workspace = parts[:2]
        title = parts[2] if len(parts) == 3 else ""
        if rule.window_title is not None and title != rule.window_title:
            continue
        windows.append((window_id, workspace))

    if not windows:
        if rule.home_workspace:
            check_cmd(("aerospace", "workspace", rule.home_workspace))
        launch_app(rule)
        return

    window_id, window_workspace = windows[0]

    if rule.mode == "summon_to_home":
        if not rule.home_workspace:
            notify(f"Missing home workspace for {app_name}", ERROR)
            return

        current_workspace = focused_workspace()
        if (
            current_workspace == window_workspace
            or window_workspace == rule.home_workspace
        ):
            focus_window(window_id)
            return

        move_window_to_workspace(window_id, rule.home_workspace, focus_follows=True)
        return

    focus_window(window_id)


def find_kitty_hotkey_window() -> tuple[str, str] | None:
    rows = check_cmd(
        (
            "aerospace",
            "list-windows",
            "--all",
            "--format",
            "%{window-id}\t%{workspace}\t%{app-bundle-id}\t%{window-title}",
        )
    )
    matches = []
    for line in rows.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        # some windows may have empty title (or missing fields); make parsing robust
        while len(parts) < 4:
            parts.append("")
        window_id, workspace, bundle_id, title = parts[:4]
        if bundle_id == KITTY_BUNDLE_ID and title == KITTY_HOTKEY_TITLE:
            matches.append((window_id, workspace))

    if not matches:
        return None
    if len(matches) > 1:
        notify("Multiple kitty hotkey windows found", ERROR)

    return matches[0]


def toggle_kitty_hotkey() -> None:
    hotkey_window = find_kitty_hotkey_window()
    if hotkey_window is None:
        launch_kitty_hotkey()
        return

    window_id, window_workspace = hotkey_window
    current_window_id = focused_window_id()
    if current_window_id is not None and current_window_id == window_id:
        move_window_to_workspace(window_id, KITTY_HOTKEY_RULE.hide_workspace)
        return

    current_workspace = focused_workspace()
    if current_workspace == window_workspace:
        focus_window_robustly(window_id)
        return

    # One aerospace call; fall back only if Kitty steals focus after the move.
    move_window_to_workspace(window_id, current_workspace, focus_follows=True)
    if focused_window_id() != window_id:
        focus_window_robustly(window_id)


def hotkey_cached_id() -> str | None:
    try:
        value = HOTKEY_ID_FILE.read_text().strip()
    except OSError:
        return None
    return value or None


def remember_hotkey_window(window_id: str) -> None:
    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    HOTKEY_ID_FILE.write_text(window_id)


def clear_hotkey_cache() -> None:
    for path in (HOTKEY_ID_FILE, HOTKEY_HIDDEN_FILE):
        try:
            path.unlink()
        except OSError:
            pass


def mark_hotkey_hidden(hidden: bool) -> None:
    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    if hidden:
        HOTKEY_HIDDEN_FILE.touch()
    else:
        try:
            HOTKEY_HIDDEN_FILE.unlink()
        except OSError:
            pass


def hotkey_keep_enabled() -> bool:
    return HOTKEY_KEEP_FILE.exists()


def set_hotkey_keep(enabled: bool) -> None:
    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    if enabled:
        HOTKEY_KEEP_FILE.touch()
    else:
        try:
            HOTKEY_KEEP_FILE.unlink()
        except OSError:
            pass


def focused_workspace_quick() -> str | None:
    """The focused workspace in one cheap call.

    Returns None when the workspace has no window, where AeroSpace exits
    non-zero with "No window is focused".
    """
    result = run_cmd(
        (
            "aerospace",
            "eval",
            'list-windows --focused --format "#W|%{workspace}"',
        )
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("#W|"):
            return line[3:].strip() or None
    return None


def hotkey_shown_workspace() -> str | None:
    try:
        return HOTKEY_WS_FILE.read_text().strip() or None
    except OSError:
        return None


def remember_shown_workspace(workspace: str) -> None:
    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    HOTKEY_WS_FILE.write_text(workspace)


def hide_hotkey(window_id: str) -> bool:
    result = run_cmd(
        (
            "aerospace",
            "eval",
            f"move-node-to-workspace --window-id {window_id} {REX_HOTKEY_HIDE_WORKSPACE}",
        )
    )
    if result.returncode != 0:
        return False
    mark_hotkey_hidden(True)
    return True


def show_hotkey(window_id: str, target_workspace: str | None) -> bool:
    """Summon the hotkey window, float it, and centre it. False means it is gone."""
    if target_workspace is None:
        target_workspace = focused_workspace()

    result = run_cmd(
        (
            "aerospace",
            "eval",
            f"move-node-to-workspace --focus-follows-window --window-id {window_id} {target_workspace}; "
            f"focus --window-id {window_id}; "
            # Target the window explicitly: floating whatever happens to be
            # focused would catch the previously active window instead.
            f"layout --window-id {window_id} floating",
        )
    )
    if result.returncode != 0:
        # A non-zero status here means the window id no longer exists.
        # "already belongs to workspace" is only a warning, not an error.
        return False

    mark_hotkey_hidden(False)
    remember_shown_workspace(target_workspace)
    return True


def rex_bin() -> str:
    for path in REX_BIN_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError("rex binary not found")


def rex_run(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run_cmd((rex_bin(), *args), check=check)


def rex_json(*args: str):
    result = rex_run(*args, "--json", check=True)
    text = result.stdout.strip()
    if not text or text == "null":
        return None
    return json.loads(text)


def list_rex_os_windows() -> list[tuple[str, str, str, bool]]:
    return rex_hotkey_snapshot()[0]


# One `aerospace eval` process answers every question the toggle needs.
# Titles come from `--json` because resolving `%{window-title}` inside a larger
# format string costs several extra milliseconds per call (it is an AX read)
# and spikes under load; the JSON path stays flat. The remaining fields are
# cheap and stay in `--format`.
HOTKEY_STATE_SCRIPT = (
    'list-windows --all --json; '
    'list-windows --all --format "W|%{window-id}|%{workspace}|%{app-bundle-id}|%{workspace-is-focused}"; '
    'list-windows --focused --format "#F|%{window-id}"; '
    'list-workspaces --monitor focused --visible --format "#W|%{workspace}"'
)


def rex_hotkey_snapshot() -> tuple[
    list[tuple[str, str, str, bool]], str | None, str | None
]:
    """Rex windows, the focused window id, and the focused workspace in one call."""
    output = check_cmd(("aerospace", "eval", HOTKEY_STATE_SCRIPT))

    titles: dict[str, str] = {}
    placement: dict[str, tuple[str, str, bool]] = {}
    focused_window: str | None = None
    focused_workspace: str | None = None
    json_lines: list[str] = []
    reading_json = True

    for line in output.splitlines():
        if reading_json:
            if line.startswith("W|"):
                reading_json = False
            else:
                json_lines.append(line)
                continue
        if not line:
            continue
        if line.startswith("#F|"):
            focused_window = line[3:] or None
        elif line.startswith("#W|"):
            focused_workspace = line[3:] or None
        elif line.startswith("W|"):
            parts = line[2:].split("|")
            while len(parts) < 4:
                parts.append("")
            window_id, workspace, bundle_id, workspace_focused = parts[:4]
            placement[window_id] = (
                workspace,
                bundle_id,
                workspace_focused == "true",
            )

    if json_lines:
        for item in json.loads("\n".join(json_lines) or "[]"):
            window_id = item.get("window-id")
            if window_id is not None:
                titles[str(window_id)] = item.get("window-title") or ""

    windows: list[tuple[str, str, str, bool]] = []
    for window_id, (workspace, bundle_id, workspace_focused) in placement.items():
        if bundle_id == REX_BUNDLE_ID:
            windows.append(
                (window_id, workspace, titles.get(window_id, ""), workspace_focused)
            )
    return windows, focused_window, focused_workspace


def find_rex_hotkey_window() -> tuple[str, str] | None:
    windows, _focused_window, _focused_workspace = rex_hotkey_snapshot()
    matches = [
        (window_id, workspace)
        for window_id, workspace, title, _focused in windows
        if title.endswith(REX_HOTKEY_TITLE_SUFFIX)
    ]
    if not matches:
        return None
    if len(matches) > 1:
        notify("Multiple Rex hotkey windows found", ERROR)
    return matches[0]


def connected_rex_app_client_id() -> str | None:
    payload = rex_json("client", "ls")
    if not isinstance(payload, dict):
        return None
    for client in payload.get("clients", []):
        info = client.get("info") or {}
        if (
            client.get("connection_state") == "connected"
            and info.get("kind") == "app"
        ):
            return client.get("client_id")
    return None


def ensure_rex_app_client() -> str:
    client_id = connected_rex_app_client_id()
    if client_id is not None:
        return client_id

    for app_name in REX_APP_CANDIDATES:
        app_path = f"/Applications/{app_name}.app"
        if os.path.isdir(app_path):
            run_cmd(("open", "-a", app_name))
            break
    else:
        notify("Rex app not found", ERROR)
        raise FileNotFoundError("Rex app not found")

    deadline = time.time() + REX_CLIENT_WAIT_SEC
    while time.time() < deadline:
        client_id = connected_rex_app_client_id()
        if client_id is not None:
            return client_id
        time.sleep(0.1)

    notify("Rex app client did not connect", ERROR)
    raise TimeoutError("Rex app client did not connect")


def list_rex_session_labels() -> set[str]:
    payload = rex_json("ls")
    if not isinstance(payload, dict):
        return set()
    labels = set()
    for session in payload.get("sessions", []):
        label = session.get("label")
        if label:
            labels.add(label)
    return labels


def ensure_rex_hotkey_session() -> str:
    payload = rex_json("ls")
    if isinstance(payload, dict):
        for session in payload.get("sessions", []):
            if session.get("label") == REX_HOTKEY_SESSION:
                session_id = session.get("session_id")
                if session_id:
                    return session_id

    created = rex_json("new", REX_HOTKEY_SESSION)
    if not isinstance(created, dict) or not created.get("session_id"):
        notify("Failed to create Rex hotkey session", ERROR)
        raise RuntimeError("Failed to create Rex hotkey session")
    return created["session_id"]


def wait_for_new_rex_window(before_ids: set[str]) -> str | None:
    deadline = time.time() + REX_WINDOW_WAIT_SEC
    while time.time() < deadline:
        after = {window_id for window_id, _ws, _title, _foc in list_rex_os_windows()}
        created = after - before_ids
        if len(created) == 1:
            return next(iter(created))
        if len(created) > 1:
            notify("Multiple new Rex windows appeared", ERROR)
            return None
        time.sleep(0.05)
    return None


def launch_rex_hotkey() -> None:
    session_id = ensure_rex_hotkey_session()
    client_id = ensure_rex_app_client()
    windows = list_rex_os_windows()
    before_ids = {window_id for window_id, _ws, _title, _foc in windows}
    before_labels = list_rex_session_labels()

    existing = [
        (window_id, workspace)
        for window_id, workspace, title, _foc in windows
        if title.endswith(REX_HOTKEY_TITLE_SUFFIX)
    ]
    if existing:
        current_workspace = next(
            (workspace for _id, workspace, _title, foc in windows if foc),
            focused_workspace(),
        )
        move_window_to_workspace(
            existing[0][0], current_workspace, focus_follows=True
        )
        return

    result = rex_run("-C", client_id, "do", "client.window.new")
    if result.returncode != 0:
        notify("Failed to open Rex window", ERROR)
        return

    window_id = wait_for_new_rex_window(before_ids)
    if window_id is None:
        # Reuse an existing Rex window if the app refused a second OS window.
        windows = list_rex_os_windows()
        if not windows:
            notify("Rex hotkey window did not appear", ERROR)
            return
        window_id = windows[0][0]

    focus_window_robustly(window_id)
    select = rex_run(
        "-C",
        client_id,
        "do",
        "session.select",
        f"session_id={session_id}",
    )
    if select.returncode != 0:
        notify("Failed to show Rex hotkey session", ERROR)
        return

    # client.window.new may create a throwaway session; drop orphans we just added.
    for label in sorted(list_rex_session_labels() - before_labels):
        if label != REX_HOTKEY_SESSION:
            rex_run("session", "kill", label)

    hotkey_window = find_rex_hotkey_window()
    if hotkey_window is None:
        notify("Rex hotkey window title did not update", ERROR)
        return
    focus_window_robustly(hotkey_window[0])


def toggle_rex_hotkey() -> None:
    """Show the hotkey window, or hide it when it is already on screen."""
    cached_id = hotkey_cached_id()

    if cached_id is not None:
        current_ws = focused_workspace_quick() or focused_workspace()
        visible = not HOTKEY_HIDDEN_FILE.exists()

        # Visible on the workspace the user is looking at: hide it,
        # whether or not it currently holds keyboard focus.
        if visible and current_ws is not None and hotkey_shown_workspace() == current_ws:
            if hide_hotkey(cached_id):
                return

        if show_hotkey(cached_id, current_ws):
            return

        # The cached window is gone; fall back to a full scan.
        clear_hotkey_cache()

    toggle_rex_hotkey_slow()


def toggle_rex_hotkey_slow() -> None:
    windows, _focused_window, focused_workspace_name = rex_hotkey_snapshot()
    matches = [
        (window_id, workspace)
        for window_id, workspace, title, _foc in windows
        if title.endswith(REX_HOTKEY_TITLE_SUFFIX)
    ]
    if not matches:
        launch_rex_hotkey()
        return
    if len(matches) > 1:
        notify("Multiple Rex hotkey windows found", ERROR)

    window_id, window_workspace = matches[0]
    remember_hotkey_window(window_id)

    target = focused_workspace_name or focused_workspace_quick() or focused_workspace()
    if show_hotkey(window_id, target):
        return
    notify(f"Failed to show Rex hotkey window {window_id}", ERROR)


def cycle_app_win(direction: str) -> None:
    bundle_id = focused_window_value("%{app-bundle-id}")
    if bundle_id is None:
        notify("Oops, no focused window.", ERROR)
        return

    window_ids = list_window_ids("--monitor", "all", "--app-bundle-id", bundle_id)

    if not window_ids:
        notify("Oops, no focused window.", ERROR)
        return
    if len(window_ids) == 1:
        notify("There is only 1 window for this app.", ERROR)
        return

    try:
        focus_window(next_id(window_ids, focused_window_id(), direction))
    except ValueError:
        notify("Invalid direction", ERROR)


def move_ghost_win() -> None:
    rows = check_cmd(
        (
            "aerospace",
            "list-windows",
            "--all",
            "--format",
            "%{window-id}\t%{window-title}",
        )
    )
    ghost_ids = []
    for line in rows.splitlines():
        if not line:
            continue
        window_id, _, title = line.partition("\t")
        if not title.strip():
            ghost_ids.append(window_id)

    for window_id in ghost_ids:
        move_window_to_workspace(window_id, GHOST_WORKSPACE)


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        notify("invalid args", ERROR)
        print(":(")
        return 1

    match list(argv[1:]):
        case ["app", "toggle", app_name]:
            toggle_app(app_name)
        case ["kitty", "toggle-hotkey"]:
            toggle_kitty_hotkey()
        case ["rex", "toggle-hotkey"]:
            toggle_rex_hotkey()
        case ["rex", "hotkey-keep", state]:
            set_hotkey_keep(state == "on")
            notify(f"Rex hotkey workspace follow: {state}")
        case ["window", "cycle-app", direction]:
            cycle_app_win(direction)
        case ["window", "smart-move", axis, size, direction]:
            smart_move(axis, size, direction)
        case ["window", "smart-resize", axis, size]:
            smart_resize(axis, size)
        case ["window", "move-ghost"]:
            move_ghost_win()
        case _:
            notify("invalid args", ERROR)
            print(":(")
            return 1

    return 0


def run(argv: Sequence[str]) -> int:
    try:
        return main(argv)
    except subprocess.CalledProcessError as exc:
        notify_command_error(exc)
        return exc.returncode or 1
    except Exception as exc:
        notify(f"as.py failed: {exc}", ERROR)
        return 1


if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
