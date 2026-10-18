"""Keep Kitty window context user vars in sync with foreground commands.

This watcher is event-driven: it updates user vars when commands start/stop or
when focus changes. The tab bar should only render these user vars; process
classification belongs here.

User-var schema:
- All values are strings; empty means unknown/cleared.
- PROGRAM is the coarse environment: local, ssh, ksh, zellij, pi, claude, codex.
- CWD is an absolute path when known; PROJECT is the nearest .jj/.git root name.
- *_UPDATED_AT is Unix epoch seconds; *_TTL is a duration in seconds.
- Empty or 0 TTL means "no expiry". Writers should set *_OWNER to their name.
- AGENT_* fields are reserved for coding-agent integrations, not shell guesses.
"""

from __future__ import annotations

import os
import shlex
from typing import Any

SSH_OPTIONS_WITH_VALUES = {
    "-b",
    "-c",
    "-D",
    "-E",
    "-F",
    "-i",
    "-J",
    "-L",
    "-l",
    "-m",
    "-O",
    "-o",
    "-p",
    "-Q",
    "-R",
    "-S",
    "-W",
    "-w",
}


def _split_cmdline(cmdline: Any) -> list[str]:
    if isinstance(cmdline, (list, tuple)):
        return [str(part) for part in cmdline]
    if not isinstance(cmdline, str) or not cmdline.strip():
        return []
    try:
        return shlex.split(cmdline)
    except ValueError:
        return cmdline.split()


def _command_name(token: str) -> str:
    return os.path.basename(token)


def _ssh_host(args: list[str]) -> str:
    skip_next = False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            continue
        if arg.startswith("-"):
            option = arg.split("=", 1)[0]
            if option in SSH_OPTIONS_WITH_VALUES:
                skip_next = "=" not in arg
            continue
        target = arg.rsplit("@", 1)[-1]
        if target.startswith("[") and "]" in target:
            return target[1 : target.index("]")]
        return target.split(":", 1)[0].split("/", 1)[0]
    return ""


def _zellij_session(args: list[str]) -> str:
    for index, arg in enumerate(args):
        if arg in {"-s", "--session"} and index + 1 < len(args):
            return args[index + 1]
    return os.environ.get("ZELLIJ_SESSION_NAME", "")


def _classify_command(cmdline: Any) -> dict[str, str] | None:
    tokens = _split_cmdline(cmdline)
    if not tokens:
        return None

    command = _command_name(tokens[0])
    args = tokens[1:]

    if command in {"ssh", "mosh"}:
        return {"PROGRAM": "ssh", "HOST": _ssh_host(args), "COMMAND": command, "SESSION": ""}

    if command == "kitten":
        if args[:1] == ["ssh"]:
            return {"PROGRAM": "ksh", "HOST": _ssh_host(args[1:]), "COMMAND": "kitten ssh", "SESSION": ""}
        return {"PROGRAM": "kitten", "HOST": "", "COMMAND": args[0] if args else "kitten", "SESSION": ""}

    if command == "kitty" and args[:2] == ["+kitten", "ssh"]:
        return {"PROGRAM": "ksh", "HOST": _ssh_host(args[2:]), "COMMAND": "kitten ssh", "SESSION": ""}

    if command == "kitty" and args[:1] == ["+kitten"]:
        return {"PROGRAM": "kitten", "HOST": "", "COMMAND": args[1] if len(args) > 1 else "kitten", "SESSION": ""}

    if command == "zellij":
        return {"PROGRAM": "zellij", "HOST": "", "SESSION": _zellij_session(args), "COMMAND": "zellij"}

    return None


def _classify_ssh_bootstrap(tokens: list[str]) -> dict[str, str] | None:
    if _command_name(tokens[0]) != "ssh":
        return None
    if "--" not in tokens:
        return None
    separator = tokens.index("--")
    args = tokens[separator + 1 :]
    if len(args) >= 3 and args[1:3] == ["exec", "sh"]:
        return {"PROGRAM": "ksh", "HOST": _ssh_host(args[:1]), "COMMAND": "kitten ssh", "SESSION": ""}
    return None


def _classify_window(window: Any) -> dict[str, str] | None:
    child = getattr(window, "child", None)
    processes = getattr(child, "foreground_processes", None) or ()

    # Prefer explicit kitten invocations when present. In a kitten ssh session,
    # kitty often exposes both the wrapper (`kitten ssh host`) and the generated
    # `/usr/bin/ssh ... -- host exec sh ...` bootstrap command.
    fallback: dict[str, str] | None = None
    for process in processes:
        cmdline = process.get("cmdline") if isinstance(process, dict) else None
        tokens = _split_cmdline(cmdline)
        if not tokens:
            continue
        classified = _classify_command(tokens)
        if classified and classified.get("COMMAND") == "kitten ssh":
            return classified
        if classified and fallback is None:
            fallback = classified
        if fallback is None:
            fallback = _classify_ssh_bootstrap(tokens)

    return fallback


def _set_user_vars(window: Any, values: dict[str, str]) -> None:
    current = getattr(window, "user_vars", {}) or {}
    for key, value in values.items():
        value = value or ""
        if current.get(key) != value:
            window.set_user_var(key, value)


def _refresh_remote_context(window: Any) -> None:
    context = _classify_window(window)
    if context:
        _set_user_vars(window, context)


def on_load(boss: Any, data: dict[str, Any]) -> None:
    all_windows = getattr(boss, "all_windows", None)
    if not callable(all_windows):
        return
    for window in all_windows():
        _refresh_remote_context(window)


def on_cmd_startstop(boss: Any, window: Any, data: dict[str, Any]) -> None:
    if data.get("is_start"):
        context = _classify_command(data.get("cmdline"))
        if context:
            _set_user_vars(window, context)
    else:
        _refresh_remote_context(window)


def on_focus_change(boss: Any, window: Any, data: dict[str, Any]) -> None:
    if data.get("focused"):
        _refresh_remote_context(window)
