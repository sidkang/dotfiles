#!/opt/homebrew/bin/python3

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Sequence
from urllib.parse import urlencode


INFO = "info"
ERROR = "error"
GHOST_WORKSPACE = "BIN"
KITTY_SOCKET = "unix:/tmp/kitten"
KITTY_BIN = "/opt/homebrew/bin/kitten"
KITTY_BUNDLE_ID = "net.kovidgoyal.kitty"
KITTY_HOTKEY_TITLE = "kitty-hotkey"
KITTY_HOTKEY_SESSION = "hotkey"
FOCUS_RETRY_DELAY_SEC = 0.05


@dataclass(frozen=True)
class AppRule:
    bundle_id: str
    launch_args: tuple[str, ...]
    home_workspace: str | None = None
    mode: str = "focus_only"
    window_title: str | None = None


@dataclass(frozen=True)
class KittyHotkeyRule:
    hide_workspace: str
    launch_args: tuple[str, ...]


@dataclass(frozen=True)
class VisibleWorkspace:
    name: str
    monitor_id: str
    is_focused: bool


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


def notify(message: str, level: str = INFO) -> None:
    params = urlencode({"msg": message, "level": level})
    run_cmd(("open", "-g", f"hammerspoon://notify?{params}"))


def notify_command_error(exc: subprocess.CalledProcessError) -> None:
    output = (exc.stderr or exc.stdout or "").strip()
    command = " ".join(str(arg) for arg in exc.cmd)
    message = output or f"exit {exc.returncode}"
    notify(f"Command failed: {command}: {message}", ERROR)


def hammerspoon(route: str, **params: str) -> None:
    query = urlencode(params)
    run_cmd(("open", "-g", f"hammerspoon://{route}?{query}"))


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


def list_visible_workspaces() -> list[VisibleWorkspace]:
    rows = check_cmd(
        (
            "aerospace",
            "list-workspaces",
            "--monitor",
            "all",
            "--visible",
            "--format",
            "%{workspace}\t%{monitor-id}\t%{workspace-is-focused}",
        )
    )
    workspaces = []
    for line in rows.splitlines():
        if not line:
            continue
        name, monitor_id, is_focused = line.split("\t")
        workspaces.append(
            VisibleWorkspace(
                name=name,
                monitor_id=monitor_id,
                is_focused=is_focused == "true",
            )
        )
    return workspaces


def list_window_ids(*args: str) -> list[str]:
    output = check_cmd(("aerospace", "list-windows", *args, "--format", "%{window-id}"))
    return [line for line in output.splitlines() if line]


def list_windows(*args: str) -> list[tuple[str, ...]]:
    output = check_cmd(
        (
            "aerospace",
            "list-windows",
            *args,
            "--format",
            "%{window-id}\t%{workspace}\t%{app-bundle-id}",
        )
    )
    return [tuple(line.split("\t")) for line in output.splitlines() if line]


def focus_window(window_id: str) -> None:
    check_cmd(("aerospace", "focus", "--window-id", window_id))


def focus_workspace(workspace: str) -> None:
    check_cmd(("aerospace", "workspace", workspace))


def focus_monitor(monitor_id: str) -> None:
    check_cmd(("aerospace", "focus-monitor", monitor_id))


def summon_workspace(workspace: str) -> None:
    check_cmd(("aerospace", "summon-workspace", workspace))


def focus_window_robustly(window_id: str) -> None:
    for _ in range(2):
        focus_window(window_id)
        time.sleep(FOCUS_RETRY_DELAY_SEC)
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

    move_window_to_workspace(window_id, current_workspace)
    # kitty may reactivate a different OS window after the cross-monitor move.
    focus_window_robustly(window_id)


def cycle_win(direction: str) -> None:
    window_ids = list_window_ids("--workspace", "focused")
    if not window_ids:
        notify("No window in workspace.", ERROR)
        return

    try:
        focus_window(next_id(window_ids, focused_window_id(), direction))
    except ValueError:
        notify("Invalid direction", ERROR)


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


def swap_workspace() -> None:
    visible_workspaces = list_visible_workspaces()
    if len(visible_workspaces) != 2:
        notify("swap_workspace requires exactly 2 visible workspaces", ERROR)
        return

    focused = next((ws for ws in visible_workspaces if ws.is_focused), None)
    if focused is None:
        notify("Failed to find focused workspace", ERROR)
        return

    other = next(
        (ws for ws in visible_workspaces if ws.monitor_id != focused.monitor_id), None
    )
    if other is None:
        notify("Failed to find the other monitor workspace", ERROR)
        return

    # In AeroSpace, summoning the focused workspace onto the other monitor already
    # displaces that monitor's visible workspace. So the swap is effectively done
    # by a single summon. Re-focus the original workspace name afterwards so the
    # same workspace remains focused after the swap.
    try:
        focus_monitor(other.monitor_id)
        summon_workspace(focused.name)
        focus_workspace(focused.name)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        notify(f"swap_workspace failed: {message}", ERROR)
        return

    visible_after = list_visible_workspaces()
    focused_after = next((ws for ws in visible_after if ws.name == focused.name), None)
    other_after = next((ws for ws in visible_after if ws.name == other.name), None)
    if focused_after is None or other_after is None:
        notify("swap_workspace failed to keep both workspaces visible", ERROR)
        return

    if (
        focused_after.monitor_id != other.monitor_id
        or other_after.monitor_id != focused.monitor_id
    ):
        notify("swap_workspace finished with unexpected workspace placement", ERROR)


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
        case ["window", "cycle", direction]:
            cycle_win(direction)
        case ["window", "cycle-app", direction]:
            cycle_app_win(direction)
        case ["window", "smart-move", axis, size, direction]:
            smart_move(axis, size, direction)
        case ["window", "smart-resize", axis, size]:
            smart_resize(axis, size)
        case ["window", "move-ghost"]:
            move_ghost_win()
        case ["workspace", "swap-visible"]:
            swap_workspace()
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
