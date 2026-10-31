#!/usr/bin/env python3
# Startup time matters (one process per key press): keep imports minimal.

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from collections import namedtuple
from collections.abc import Sequence
from contextlib import contextmanager
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
REX_HOTKEY_SESSION = "arc"
# Rex titles read "<block title> - <session label>".
REX_HOTKEY_TITLE_SUFFIX = f" - {REX_HOTKEY_SESSION}"
REX_HOTKEY_HIDE_WORKSPACE = "T"
DEFAULT_WORKSPACE = "1"
REX_CLIENT_WAIT_SEC = 5.0
REX_WINDOW_WAIT_SEC = 3.0
HOTKEY_STATE_DIR = Path(os.path.expanduser("~/.local/state/aerospace"))
HOTKEY_ID_FILE = HOTKEY_STATE_DIR / "hotkey-id"
HOTKEY_HIDDEN_FILE = HOTKEY_STATE_DIR / "hotkey-hidden"
HOTKEY_KEEP_FILE = HOTKEY_STATE_DIR / "hotkey-keep"
HOTKEY_WS_FILE = HOTKEY_STATE_DIR / "hotkey-ws"
HOTKEY_LOCK_FILE = HOTKEY_STATE_DIR / "hotkey-lock"
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
    # The workspace-change hook reads this file; skip the write when unchanged.
    if hotkey_cached_id() == window_id:
        return
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


def set_hotkey_keep(enabled: bool) -> None:
    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    if enabled:
        HOTKEY_KEEP_FILE.touch()
    else:
        try:
            HOTKEY_KEEP_FILE.unlink()
        except OSError:
            pass


@contextmanager
def hotkey_lock():
    """Yield True when this process owns the toggle, False when another does.

    A second press during a slow launch would otherwise see no hotkey window
    yet and open another one (plus another throwaway session).
    """
    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(HOTKEY_LOCK_FILE, "w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def resolve_show_workspace(candidate: str | None) -> str:
    """Pick a workspace that is not the hiding one.

    Showing the window on the holding workspace leaves the user looking at
    nothing and makes the next toggle appear to do nothing.
    """
    for value in (candidate, hotkey_shown_workspace()):
        if value and value != REX_HOTKEY_HIDE_WORKSPACE:
            return value
    return DEFAULT_WORKSPACE


def hotkey_shown_workspace() -> str | None:
    try:
        return HOTKEY_WS_FILE.read_text().strip() or None
    except OSError:
        return None


def remember_shown_workspace(workspace: str) -> None:
    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    HOTKEY_WS_FILE.write_text(workspace)


RexWindow = namedtuple("RexWindow", "window_id workspace title")

FOCUSED_WORKSPACE_QUERY = (
    'list-workspaces --monitor focused --visible --format "#W|%{workspace}"'
)
FOCUSED_WINDOW_QUERY = 'list-windows --focused --format "#F|%{window-id}"'
# One `aerospace eval` answers every question a toggle needs. Titles are read
# only for Rex windows (each is an AX call). The focused window comes last:
# AeroSpace fails there on an empty workspace, and that must not cost the rest.
HOTKEY_STATE_SCRIPT = "; ".join(
    (
        f"list-windows --monitor all --app-bundle-id {REX_BUNDLE_ID} "
        '--format "R|%{window-id}|%{workspace}|%{window-title}"',
        FOCUSED_WORKSPACE_QUERY,
        FOCUSED_WINDOW_QUERY,
    )
)


def aerospace_eval(*commands: str) -> subprocess.CompletedProcess[str]:
    return run_cmd(("aerospace", "eval", "; ".join(commands)))


def parse_hotkey_state(
    output: str,
) -> tuple[list[RexWindow], str | None, str | None]:
    """Rex windows, the focused workspace, and the focused window id."""
    windows: list[RexWindow] = []
    workspace: str | None = None
    focused: str | None = None
    for line in output.splitlines():
        if line.startswith("R|"):
            # The title is last because it may contain "|".
            parts = line[2:].split("|", 2)
            if len(parts) == 3:
                windows.append(RexWindow(*parts))
        elif line.startswith("#W|"):
            workspace = line[3:] or None
        elif line.startswith("#F|"):
            focused = line[3:] or None
    return windows, workspace, focused


def hotkey_state() -> tuple[list[RexWindow], str, str | None]:
    result = run_cmd(("aerospace", "eval", HOTKEY_STATE_SCRIPT))
    windows, workspace, focused = parse_hotkey_state(result.stdout)
    if workspace is None:
        raise RuntimeError(result.stderr.strip() or "AeroSpace returned no workspace")
    return windows, workspace, focused


def find_hotkey_window(windows: Sequence[RexWindow]) -> tuple[RexWindow | None, bool]:
    """The hotkey window, and whether it lost its session.

    Killing the session leaves its macOS window behind, showing whichever
    session the app fell back to. Reusing that window (found by its recorded
    id) keeps stray windows from piling up next to the user's real one.
    """
    cached = hotkey_cached_id()
    matches = [w for w in windows if w.title.endswith(REX_HOTKEY_TITLE_SUFFIX)]
    if matches:
        if len(matches) > 1:
            notify("Multiple Rex hotkey windows found", ERROR)
        return next((w for w in matches if w.window_id == cached), matches[0]), False
    return next((w for w in windows if w.window_id == cached), None), True


def hide_hotkey(window_id: str) -> bool:
    result = aerospace_eval(
        f"move-node-to-workspace --window-id {window_id} {REX_HOTKEY_HIDE_WORKSPACE}",
        FOCUSED_WORKSPACE_QUERY,
    )
    if result.returncode != 0:
        return False
    remember_hotkey_window(window_id)
    mark_hotkey_hidden(True)

    # The window is parked; make sure the user is not parked with it.
    if parse_hotkey_state(result.stdout)[1] == REX_HOTKEY_HIDE_WORKSPACE:
        fallback = resolve_show_workspace(None)
        check_cmd(("aerospace", "workspace", fallback))
        remember_shown_workspace(fallback)
    return True


def show_hotkey(window_id: str, workspace: str | None) -> tuple[bool, str | None]:
    """Summon the window and float it; also report which window ended up focused.

    False means the window is gone.
    """
    target = resolve_show_workspace(workspace)
    result = aerospace_eval(
        f"move-node-to-workspace --focus-follows-window --window-id {window_id} {target}",
        f"focus --window-id {window_id}",
        # Target the window explicitly: floating whatever happens to be
        # focused would catch the previously active window instead.
        f"layout --window-id {window_id} floating",
        FOCUSED_WINDOW_QUERY,
    )
    if result.returncode != 0:
        # A non-zero status here means the window id no longer exists.
        # "already belongs to workspace" is only a warning, not an error.
        return False, None

    remember_hotkey_window(window_id)
    mark_hotkey_hidden(False)
    remember_shown_workspace(target)
    return True, parse_hotkey_state(result.stdout)[2]


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


def connected_rex_app_client_id() -> str | None:
    """This Mac's Rex app client.

    Rex apps on other Macs also connect to this server, over TCP. Driving one
    of them opens windows and throwaway sessions on that machine, where the
    orphan cleanup cannot reach. Only the local app connects over a unix socket.
    """
    payload = rex_json("client", "ls")
    if not isinstance(payload, dict):
        return None
    for client in payload.get("clients", []):
        info = client.get("info") or {}
        principal = client.get("principal") or {}
        if (
            client.get("connection_state") == "connected"
            and info.get("kind") == "app"
            and principal.get("transport") == "unix"
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


def rex_session_ids() -> dict[str, str]:
    payload = rex_json("ls")
    if not isinstance(payload, dict):
        return {}
    return {
        session["label"]: session.get("session_id", "")
        for session in payload.get("sessions", [])
        if session.get("label")
    }


def ensure_rex_hotkey_session() -> tuple[str, set[str]]:
    """The hotkey session id, creating it if needed, and all session labels."""
    sessions = rex_session_ids()
    labels = set(sessions)
    session_id = sessions.get(REX_HOTKEY_SESSION)
    if session_id:
        return session_id, labels

    created = rex_json("new", REX_HOTKEY_SESSION)
    if not isinstance(created, dict) or not created.get("session_id"):
        notify("Failed to create Rex hotkey session", ERROR)
        raise RuntimeError("Failed to create Rex hotkey session")
    labels.add(REX_HOTKEY_SESSION)
    return created["session_id"], labels


def select_hotkey_session(
    window_id: str, focused_id: str | None, session_id: str, client_id: str
) -> bool:
    """Show the hotkey session in its window; the app acts on its active window."""
    if focused_id != window_id:
        focus_window_robustly(window_id)
    select = rex_run(
        "-C", client_id, "do", "session.select", f"session_id={session_id}"
    )
    return select.returncode == 0


def wait_for_new_rex_window(before_ids: set[str]) -> RexWindow | None:
    deadline = time.time() + REX_WINDOW_WAIT_SEC
    while time.time() < deadline:
        created = [w for w in hotkey_state()[0] if w.window_id not in before_ids]
        if len(created) == 1:
            return created[0]
        if len(created) > 1:
            notify("Multiple new Rex windows appeared", ERROR)
            return None
        time.sleep(0.05)
    return None


def launch_rex_hotkey() -> None:
    session_id, before_labels = ensure_rex_hotkey_session()
    client_id = ensure_rex_app_client()
    # Read the windows only now: starting the app may have restored some.
    windows, current_workspace, focused_id = hotkey_state()

    existing, lost_session = find_hotkey_window(windows)
    if existing is not None:
        ok, focused_id = show_hotkey(existing.window_id, current_workspace)
        if ok and lost_session:
            ok = select_hotkey_session(
                existing.window_id, focused_id, session_id, client_id
            )
        if not ok:
            notify("Failed to show Rex hotkey session", ERROR)
        return

    result = rex_run("-C", client_id, "do", "client.window.new")
    if result.returncode != 0:
        notify("Failed to open Rex window", ERROR)
        return

    try:
        window = wait_for_new_rex_window({w.window_id for w in windows})
        if window is None:
            # Never fall back to another Rex window: that is the user's own.
            notify("Rex hotkey window did not appear", ERROR)
            return
        # A fresh window is tiled and shows a throwaway session: float it,
        # then give it the hotkey session.
        ok, focused_id = show_hotkey(window.window_id, window.workspace)
        if not ok or not select_hotkey_session(
            window.window_id, focused_id, session_id, client_id
        ):
            notify("Failed to show Rex hotkey session", ERROR)
    finally:
        # client.window.new may create a throwaway session; drop what it added.
        for label in sorted(set(rex_session_ids()) - before_labels):
            if label != REX_HOTKEY_SESSION:
                rex_run("session", "kill", label)


def toggle_rex_hotkey() -> None:
    """Show the hotkey window, or hide it when it is already on screen."""
    with hotkey_lock() as owned:
        if not owned:
            return

        windows, current_workspace, focused_id = hotkey_state()
        hotkey, lost_session = find_hotkey_window(windows)
        if hotkey is None:
            clear_hotkey_cache()
            launch_rex_hotkey()
            return

        # Where the window actually is decides the action, not recorded state.
        if (
            not lost_session
            and hotkey.workspace == current_workspace
            and current_workspace != REX_HOTKEY_HIDE_WORKSPACE
        ):
            if not hide_hotkey(hotkey.window_id):
                clear_hotkey_cache()
                notify(f"Failed to hide Rex hotkey window {hotkey.window_id}", ERROR)
            return

        ok, focused_id = show_hotkey(hotkey.window_id, current_workspace)
        if not ok:
            clear_hotkey_cache()
            notify(f"Failed to show Rex hotkey window {hotkey.window_id}", ERROR)
            return
        if lost_session:
            session_id, _labels = ensure_rex_hotkey_session()
            client_id = ensure_rex_app_client()
            if not select_hotkey_session(
                hotkey.window_id, focused_id, session_id, client_id
            ):
                notify("Failed to restore Rex hotkey session", ERROR)


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
