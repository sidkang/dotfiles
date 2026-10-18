#!/opt/homebrew/bin/python3

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence
from urllib.parse import urlencode


INFO = "info"
ERROR = "error"
KITTY_BIN = "/opt/homebrew/bin/kitten"
KITTY_SOCKET = "unix:/tmp/kitten"
TAG_VAR_NAME = "tag"
DEFAULT_MATCH = "state:focused"
BASE_BACKGROUND = "#EFF1F5"


@dataclass(frozen=True)
class TagRule:
    value: str
    background: str
    active_border_color: str | None = None
    inactive_border_color: str | None = None


TAG_RULES = {
    "worker": TagRule(
        value="worker",
        background="#EEF7F5",
    ),
}


def run_cmd(
    args: Sequence[str], check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=check)


def check_cmd(args: Sequence[str]) -> str:
    return run_cmd(args, check=True).stdout.strip()


def kitty_args(*args: str) -> tuple[str, ...]:
    return (KITTY_BIN, "@", "--to", KITTY_SOCKET, *args)


def check_kitty_cmd(args: Sequence[str]) -> str:
    return check_cmd(kitty_args(*args))


def notify(message: str, level: str = INFO) -> None:
    params = urlencode({"msg": message, "level": level})
    run_cmd(("open", "-g", f"hammerspoon://notify?{params}"))


def parse_window_ids(stdout: str) -> list[str]:
    if stdout in ("", "[]"):
        return []

    try:
        os_windows = json.loads(stdout)
    except json.JSONDecodeError:
        notify("Failed to parse kitty windows", ERROR)
        return []

    window_ids = []
    for os_window in os_windows:
        if not isinstance(os_window, dict):
            continue
        for tab in os_window.get("tabs", []):
            if not isinstance(tab, dict):
                continue
            for window in tab.get("windows", []):
                if isinstance(window, dict) and "id" in window:
                    window_ids.append(str(window["id"]))

    return window_ids


def matched_window_ids(match_expr: str) -> list[str]:
    result = run_cmd(kitty_args("ls", "--match", match_expr))
    if result.returncode != 0:
        notify("Failed to query kitty windows", ERROR)
        return []
    return parse_window_ids(result.stdout.strip())


def window_vars(window_id: str) -> dict[str, str]:
    result = run_cmd(kitty_args("set-user-vars", "--match", f"id:{window_id}"))
    if result.returncode != 0:
        notify(f"Failed to read vars for kitty window {window_id}", ERROR)
        return {}

    vars_map = {}
    for line in result.stdout.splitlines():
        if not line:
            continue
        name, sep, value = line.partition("=")
        if sep:
            vars_map[name] = value

    return vars_map


def set_window_tag(window_id: str, rule: TagRule) -> None:
    check_kitty_cmd(
        ("set-user-vars", "--match", f"id:{window_id}", f"{TAG_VAR_NAME}={rule.value}")
    )

    color_args = [
        "set-colors",
        "--match",
        f"id:{window_id}",
        f"background={rule.background}",
    ]
    if rule.active_border_color:
        color_args.append(f"active_border_color={rule.active_border_color}")
    if rule.inactive_border_color:
        color_args.append(f"inactive_border_color={rule.inactive_border_color}")

    check_kitty_cmd(tuple(color_args))


def clear_window_tag(window_id: str) -> None:
    check_kitty_cmd(("set-user-vars", "--match", f"id:{window_id}", TAG_VAR_NAME))
    check_kitty_cmd(
        ("set-colors", "--match", f"id:{window_id}", f"background={BASE_BACKGROUND}")
    )


def focused_window_id() -> str | None:
    window_ids = matched_window_ids(DEFAULT_MATCH)
    if not window_ids:
        return None
    return window_ids[0]


def enable_tag(tag_name: str) -> None:
    rule = TAG_RULES.get(tag_name)
    if rule is None:
        notify(f"Unknown kitty tag: {tag_name}", ERROR)
        return

    window_id = focused_window_id()
    if window_id is None:
        notify("No focused kitty window matched", ERROR)
        return

    set_window_tag(window_id, rule)


def toggle_tag(tag_name: str) -> None:
    rule = TAG_RULES.get(tag_name)
    if rule is None:
        notify(f"Unknown kitty tag: {tag_name}", ERROR)
        return

    window_id = focused_window_id()
    if window_id is None:
        notify("No focused kitty window matched", ERROR)
        return

    if window_vars(window_id).get(TAG_VAR_NAME) == rule.value:
        clear_window_tag(window_id)
        return

    set_window_tag(window_id, rule)


def disable_all_tags(tag_name: str) -> None:
    rule = TAG_RULES.get(tag_name)
    if rule is None:
        notify(f"Unknown kitty tag: {tag_name}", ERROR)
        return

    window_ids = matched_window_ids(f"var:{TAG_VAR_NAME}={rule.value}")
    if not window_ids:
        notify(f"No kitty windows tagged as {rule.value}", ERROR)
        return

    for window_id in window_ids:
        clear_window_tag(window_id)


def main(argv: Sequence[str]) -> int:
    if len(argv) < 3:
        notify("invalid args", ERROR)
        print(":(")
        return 1

    match list(argv[1:]):
        case ["toggle", tag_name]:
            toggle_tag(tag_name)
        case ["enable", tag_name]:
            enable_tag(tag_name)
        case ["disable_all", tag_name]:
            disable_all_tags(tag_name)
        case _:
            notify("invalid args", ERROR)
            print(":(")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
