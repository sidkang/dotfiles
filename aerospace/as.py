#!/usr/bin/env python3
# Startup time matters (one process per key press): keep imports minimal.

from __future__ import annotations

import fcntl
import os
import signal
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
REX_BUNDLE_ID = "com.superlogical.rex"
# Rex exposes no macOS window identity, so the hotkey window is identified by
# where it is: hidden on this workspace, or floating when shown. Other Rex
# windows must stay tiled.
REX_HOTKEY_HIDE_WORKSPACE = "T"
DEFAULT_WORKSPACE = "1"
REX_CLIENT_WAIT_SEC = 5.0
REX_WINDOW_WAIT_SEC = 3.0
HOTKEY_LOCK_WAIT_SEC = 1.0
HOTKEY_STATE_DIR = Path(os.path.expanduser("~/.local/state/aerospace"))
HOTKEY_LOCK_FILE = HOTKEY_STATE_DIR / "hotkey-lock"
FOCUS_RETRY_DELAY_SEC = 0.05
HS_CLI = os.path.expanduser("~/.local/bin/hs")
URL_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~")
REX_BIN_CANDIDATES = (
    "/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex",
    "/Applications/Rex.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex",
    os.path.expanduser(
        "~/Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex"
    ),
)
REX_APP_CANDIDATES = ("Rex Beta", "Rex")


# Summoned to `home_workspace`; `window_title` limits which windows count.
AppRule = namedtuple("AppRule", "bundle_id app_name home_workspace window_title")
APP_RULES = {
    "obsidian": AppRule("md.obsidian", "Obsidian", "Q", None),
    "wechat": AppRule("com.tencent.xinWeChat", "WeChat", "1", "WeChat"),
    "telegram": AppRule("ru.keepcoder.Telegram", "Telegram", "1", None),
    "chrome": AppRule("com.google.Chrome", "Google Chrome", "2", None),
}

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

    layout = focused_window_value("%{window-layout}")
    if layout is None:
        notify("Oops, no focused window.", ERROR)
        return
    if layout == "floating":
        hammerspoon("floatwindow", action="resize", axis=axis, size=size)
        return

    if run_cmd(("aerospace", "resize", axis, size)).returncode != 0:
        # AeroSpace words every "no tiled sibling along this axis" failure as
        # "doesn't support floating windows yet", also for tiled windows
        # (single window, accordion, native fullscreen). Say what is true.
        notify(f"Cannot resize {axis} here: layout is {layout}", INFO)


def aerospace_soft(args: Sequence[str]) -> None:
    """Run a command that routinely fails for lack of a target (swap, join-with, layout).

    Say why in plain words; the failure is not a bug, so it is only info.
    """
    result = run_cmd(("aerospace", *args))
    if result.returncode == 0:
        return

    message = (result.stderr or result.stdout).strip()
    if not message:
        # `swap` fails without a message.
        if focused_window_value("%{window-layout}") == "floating":
            message = "not supported for floating windows"
        else:
            message = "no window in that direction"
    notify(f"{' '.join(args)}: {message}", INFO)


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
        check_cmd(("aerospace", "workspace", rule.home_workspace))
        run_cmd(("open", "-a", rule.app_name))
        return

    window_id, window_workspace = windows[0]
    if (
        window_workspace == rule.home_workspace
        or window_workspace == focused_workspace()
    ):
        focus_window(window_id)
        return

    move_window_to_workspace(window_id, rule.home_workspace, focus_follows=True)


@contextmanager
def hotkey_lock():
    """Yield True when this process owns the toggle, False after waiting too long.

    A second press during a slow launch would otherwise see no hotkey window
    yet and open another one. Waiting lets a press that follows a normal
    toggle see the finished state.
    """

    def give_up(*_):
        raise TimeoutError

    HOTKEY_STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(HOTKEY_LOCK_FILE, "w") as handle:
        signal.signal(signal.SIGALRM, give_up)
        signal.setitimer(signal.ITIMER_REAL, HOTKEY_LOCK_WAIT_SEC)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
            owned = True
        except TimeoutError:
            owned = False
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        yield owned


RexWindow = namedtuple("RexWindow", "window_id workspace layout")

# The hotkey window follows the mouse pointer, not the keyboard focus.
MOUSE_WORKSPACE_QUERY = (
    'list-workspaces --monitor mouse --visible --format "#W|%{workspace}"'
)
FOCUSED_WINDOW_QUERY = 'list-windows --focused --format "#F|%{window-id}"'
# One `aerospace eval` answers every question a toggle needs. The focused
# window comes last: AeroSpace fails there on an empty workspace, and that must
# not cost the rest.
HOTKEY_STATE_SCRIPT = "; ".join(
    (
        f"list-windows --monitor all --app-bundle-id {REX_BUNDLE_ID} "
        '--format "R|%{window-id}|%{workspace}|%{window-layout}"',
        MOUSE_WORKSPACE_QUERY,
        FOCUSED_WINDOW_QUERY,
    )
)


def aerospace_eval(*commands: str) -> subprocess.CompletedProcess[str]:
    return run_cmd(("aerospace", "eval", "; ".join(commands)))


def parse_hotkey_state(
    output: str,
) -> tuple[list[RexWindow], str | None, str | None]:
    """Rex windows, the workspace under the mouse, and the focused window id."""
    windows: list[RexWindow] = []
    workspace: str | None = None
    focused: str | None = None
    for line in output.splitlines():
        if line.startswith("R|"):
            parts = line[2:].split("|")
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


def find_hotkey_window(windows: Sequence[RexWindow]) -> RexWindow | None:
    """The hidden window, else a floating one, else the only Rex window."""
    hidden = [w for w in windows if w.workspace == REX_HOTKEY_HIDE_WORKSPACE]
    if hidden:
        return hidden[0]
    floating = [w for w in windows if w.layout == "floating"]
    if floating:
        return floating[0]
    # A lone window is adopted rather than opening a second one.
    if len(windows) == 1:
        return windows[0]
    return None


def stash_hotkey_size(window_id: str) -> None:
    """Have Hammerspoon remember the window's size before it leaves its screen."""
    hammerspoon("floatwindow", action="stash", window=window_id)


def hide_hotkey(window_id: str) -> bool:
    """Park the window on the hiding workspace; the user stays where they are."""
    stash_hotkey_size(window_id)
    result = aerospace_eval(
        f"move-node-to-workspace --window-id {window_id} {REX_HOTKEY_HIDE_WORKSPACE}"
    )
    return result.returncode == 0


def show_hotkey(window: RexWindow, workspace: str, center: bool = False) -> bool:
    """Summon the window to `workspace`, float it and make sure it has focus.

    Crossing workspaces centers the window at its remembered share of the
    new screen; `center` forces centering.
    False means the window is gone.
    """
    window_id = window.window_id
    # Showing it on the hiding workspace would leave the user looking at
    # nothing and make the next toggle appear to do nothing.
    target = DEFAULT_WORKSPACE if workspace == REX_HOTKEY_HIDE_WORKSPACE else workspace
    if window.workspace != target:
        center = True
        # A tiled window's frame is its tile, not a size worth keeping.
        if window.layout == "floating":
            stash_hotkey_size(window_id)
    # `&&`, not `;`: eval reports only the last command's status, so with `;`
    # a vanished window id would go unnoticed.
    result = run_cmd(
        (
            "aerospace",
            "eval",
            " && ".join(
                (
                    f"move-node-to-workspace --focus-follows-window --window-id {window_id} {target}",
                    f"focus --window-id {window_id}",
                    # Target the window explicitly: floating whatever happens to be
                    # focused would catch the previously active window instead.
                    f"layout --window-id {window_id} floating",
                    FOCUSED_WINDOW_QUERY,
                )
            ),
        )
    )
    if result.returncode != 0:
        # The window id no longer exists. "already belongs to workspace" and
        # "already floating" are warnings with status 0.
        return False
    if parse_hotkey_state(result.stdout)[2] != window_id:
        focus_window_robustly(window_id)
    if center:
        hammerspoon("floatwindow", action="move", target="center", window=window_id)
    return True


def rex_bin() -> str:
    for path in REX_BIN_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError("rex binary not found")


def rex_run(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run_cmd((rex_bin(), *args), check=check)


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


def rex_local_client() -> str:
    """This Mac's Rex app client, addressed by its label (the local host name).

    Rex apps on other Macs also connect to this server, over TCP. Driving one
    of them would open windows on that machine.
    """
    return check_cmd(("scutil", "--get", "LocalHostName"))


def ensure_rex_app(client: str) -> None:
    if rex_run("-C", client, "actions").returncode == 0:
        return

    for app_name in REX_APP_CANDIDATES:
        if os.path.isdir(f"/Applications/{app_name}.app"):
            run_cmd(("open", "-a", app_name))
            break
    else:
        raise FileNotFoundError("Rex app not found")

    deadline = time.time() + REX_CLIENT_WAIT_SEC
    while time.time() < deadline:
        time.sleep(0.1)
        if rex_run("-C", client, "actions").returncode == 0:
            return
    raise TimeoutError("Rex app client did not connect")


def launch_rex_hotkey(workspace: str) -> None:
    client = rex_local_client()
    ensure_rex_app(client)
    # Read the windows only now: starting the app may have restored some.
    before_ids = {w.window_id for w in hotkey_state()[0]}

    if rex_run("-C", client, "do", "client.window.new").returncode != 0:
        notify("Failed to open Rex window", ERROR)
        return

    window = wait_for_new_rex_window(before_ids)
    if window is None:
        notify("Rex hotkey window did not appear", ERROR)
        return
    # A fresh window is tiled: floating it marks it as the hotkey window.
    if not show_hotkey(window, workspace, center=True):
        notify("Failed to show Rex hotkey window", ERROR)


def toggle_rex_hotkey() -> None:
    """Hide the hotkey window when it is on screen and focused, else summon it."""
    with hotkey_lock() as owned:
        if not owned:
            notify("Rex hotkey is still busy", ERROR)
            return

        windows, mouse_workspace, focused_id = hotkey_state()
        # A focused floating Rex window under the mouse is the one on screen:
        # hide it. Visible but unfocused (covered, or focus is elsewhere), or
        # on another monitor than the mouse, means the user wants it here and
        # in front, not gone.
        focused = next((w for w in windows if w.window_id == focused_id), None)
        if (
            focused is not None
            and focused.layout == "floating"
            and focused.workspace == mouse_workspace != REX_HOTKEY_HIDE_WORKSPACE
        ):
            hotkey, ok, action = focused, hide_hotkey(focused.window_id), "hide"
        else:
            hotkey = find_hotkey_window(windows)
            if hotkey is None:
                launch_rex_hotkey(mouse_workspace)
                return
            ok = show_hotkey(hotkey, mouse_workspace)
            action = "show"
        if not ok:
            notify(f"Failed to {action} Rex hotkey window {hotkey.window_id}", ERROR)


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
        notify("There is only 1 window for this app.", INFO)
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
        case ["aerospace", *args] if args:
            aerospace_soft(args)
        case ["rex", "toggle-hotkey"]:
            toggle_rex_hotkey()
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
