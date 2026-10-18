"""Shared Kitty context state model, resolver, and CLI.

Public API for other scripts:
- ``resolve_window_state(user_vars, foreground_processes, title)`` resolves one
  window's display state.
- ``iter_window_records(kitty_ls_json)`` normalizes ``kitten @ ls`` JSON into
  stable ``WindowRecord`` objects.
- ``python3 context_state.py --jsonl`` is the machine-readable CLI. Treat
  ``--list`` as human/debug output only. ``--jsonl`` omits raw user vars by
  default; use ``--jsonl-raw`` only for trusted debugging.

Schema rules:
- Every user-var value is a string; empty means unknown/cleared.
- *_UPDATED_AT is Unix epoch seconds.
- *_TTL is a duration in seconds. Empty or 0 means no expiry.
- CTX_* describes durable shell/window context.
- AGENT_STATE describes lifecycle only: idle/running/waiting/done.
- AGENT_RESULT describes task outcome/stop category: ok/error/blocked/cancelled.
- AGENT_* describes live coding-agent state and may be stale unless validated
  against foreground processes or a remote/mux boundary with a positive TTL.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = 1
FISH_TITLE_SEPARATOR = " · "
BOUNDARY_PROGRAMS = {"ssh", "ksh", "zellij"}

CONTEXT_KEYS = (
    "PROGRAM",
    "HOST",
    "CWD",
    "PROJECT",
    "SESSION",
    "COMMAND",
    "CTX_OWNER",
    "CTX_UPDATED_AT",
    "CTX_TTL",
)

AGENT_KEYS = (
    "AGENT",
    "AGENT_STATE",
    "AGENT_RESULT",
    "AGENT_MODEL",
    "AGENT_PROVIDER",
    "AGENT_SESSION",
    "AGENT_SESSION_NAME",
    "AGENT_TASK",
    "AGENT_CONTEXT",
    "AGENT_COST",
    "AGENT_UPDATED_AT",
    "AGENT_TTL",
)

AGENT_PROGRAMS = {"pi", "claude", "codex", "gemini", "opencode"}
AGENT_EXECUTABLES = AGENT_PROGRAMS | {"claude-code", "codex-cli"}

AGENT_STATES = {"idle", "running", "waiting", "done"}
AGENT_RESULTS = {"ok", "error", "blocked", "cancelled"}

AGENT_STATE_RANK = {
    "running": 40,
    "waiting": 30,
    "idle": 20,
    "done": 10,
}


@dataclass(frozen=True)
class AgentState:
    name: str
    state: str
    result: str = ""
    session: str = ""
    session_name: str = ""
    model: str = ""
    provider: str = ""
    context: str = ""
    cost: str = ""
    task: str = ""
    updated_at: int = 0
    ttl: int = 0


@dataclass(frozen=True)
class ResolvedState:
    """Resolved display state after validating user vars against runtime facts."""

    program: str
    label: str
    target: str = ""
    location: str = ""
    host: str = ""
    agent: AgentState | None = None

    @property
    def title(self) -> str:
        return f"{self.label} • {self.target}" if self.target else self.label


@dataclass(frozen=True)
class WindowRecord:
    """Stable normalized record for one Kitty window."""

    schema_version: int
    os_window_id: str
    tab_id: str
    tab_index: str
    window_id: str
    marker: str
    is_current: bool
    is_active_in_tab: bool
    tab_title: str
    window_title: str
    cwd: str
    cmdline: list[str]
    user_vars: dict[str, str]
    resolved: ResolvedState
    switcher_marker: str = ""

    @property
    def display_title(self) -> str:
        return self.window_title or self.tab_title

    @property
    def marker_glyph(self) -> str:
        if self.is_current:
            return "◆"
        if self.marker == "*":
            return "●"
        return " "

    def to_dict(self, *, include_user_vars: bool = False) -> dict[str, Any]:
        data = asdict(self)
        data["resolved"]["title"] = self.resolved.title
        if not include_user_vars:
            data.pop("user_vars", None)
        return data

    def to_tsv_row(self) -> tuple[str, ...]:
        agent = self.resolved.agent
        return (
            self.window_id,
            self.marker,
            self.os_window_id,
            self.tab_id,
            self.tab_index,
            self.resolved.title,
            self.window_title,
            self.tab_title,
            "active" if self.is_active_in_tab else "",
            " ".join(self.cmdline),
            self.switcher_marker,
            agent.name if agent else "",
            agent.state if agent else "",
            agent.result if agent else "",
            self.resolved.location,
            self.resolved.host,
            agent.model if agent else "",
            agent.context if agent else "",
            agent.cost if agent else "",
            agent.task if agent else "",
        )


# Backwards-compatible aliases for existing imports/type hints.
AgentStatus = AgentState
WindowState = ResolvedState


def now_epoch() -> str:
    return str(int(time.time()))


def context_metadata(owner: str, ttl: str = "") -> dict[str, str]:
    return {"CTX_OWNER": owner, "CTX_UPDATED_AT": now_epoch(), "CTX_TTL": ttl}


def clear_agent_values(updated_at: str | None = None) -> dict[str, str]:
    values = {key: "" for key in AGENT_KEYS}
    values["AGENT_UPDATED_AT"] = updated_at or now_epoch()
    values["AGENT_TTL"] = ""
    return values


def coerce_user_vars(raw: Any) -> dict[str, str]:
    try:
        return {str(key): str(value) for key, value in dict(raw or {}).items()}
    except (TypeError, ValueError):
        return {}


def clean_field(value: Any) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def int_user_var(user_vars: dict[str, str], key: str) -> int:
    try:
        return int(user_vars.get(key, "") or 0)
    except ValueError:
        return 0


def _process_cmdline(process: Any) -> list[str]:
    cmdline = process.get("cmdline") if isinstance(process, dict) else getattr(process, "cmdline", None)
    if isinstance(cmdline, (list, tuple)):
        return [str(part) for part in cmdline]
    if isinstance(cmdline, str):
        return cmdline.split()
    return []


def foreground_cmdline(processes: Any) -> list[str]:
    for process in reversed(list(processes or ())):
        cmdline = _process_cmdline(process)
        if cmdline:
            return cmdline
    return []


def process_command_names(processes: Any) -> set[str]:
    names: set[str] = set()
    for process in processes or ():
        cmdline = _process_cmdline(process)
        if cmdline:
            names.add(os.path.basename(cmdline[0]))
    return names


def agent_vars_are_fresh(user_vars: dict[str, str]) -> bool:
    ttl = int_user_var(user_vars, "AGENT_TTL")
    updated_at = int_user_var(user_vars, "AGENT_UPDATED_AT")
    return ttl <= 0 or updated_at <= 0 or int(time.time()) <= updated_at + ttl


def normalize_agent_status(raw_state: str, raw_result: str) -> tuple[str, str]:
    state = raw_state.strip().lower()
    result = raw_result.strip().lower()

    if state not in AGENT_STATES:
        state = "idle"
    if result not in AGENT_RESULTS:
        result = ""

    return state, result


def agent_state_from_vars(user_vars: dict[str, str]) -> AgentState | None:
    name = user_vars.get("AGENT", "").strip()
    raw_state = user_vars.get("AGENT_STATE", "").strip()
    raw_result = user_vars.get("AGENT_RESULT", "").strip()
    if not name and not raw_state and not raw_result:
        return None
    if not agent_vars_are_fresh(user_vars):
        return None
    state, result = normalize_agent_status(raw_state, raw_result)
    return AgentState(
        name=name or "agent",
        state=state,
        result=result,
        session=user_vars.get("AGENT_SESSION", "").strip(),
        session_name=user_vars.get("AGENT_SESSION_NAME", "").strip(),
        model=user_vars.get("AGENT_MODEL", "").strip(),
        provider=user_vars.get("AGENT_PROVIDER", "").strip(),
        context=user_vars.get("AGENT_CONTEXT", "").strip(),
        cost=user_vars.get("AGENT_COST", "").strip(),
        task=user_vars.get("AGENT_TASK", "").strip(),
        updated_at=int_user_var(user_vars, "AGENT_UPDATED_AT"),
        ttl=int_user_var(user_vars, "AGENT_TTL"),
    )


def agent_state_for_runtime(user_vars: dict[str, str], processes: Any) -> AgentState | None:
    """Return agent state only when user vars still match the runtime."""
    agent = agent_state_from_vars(user_vars)
    if agent is None:
        return None

    program = user_vars.get("PROGRAM", "").strip()
    if program in BOUNDARY_PROGRAMS and int_user_var(user_vars, "AGENT_TTL") > 0:
        return agent

    command_names = process_command_names(processes)
    if command_names & AGENT_EXECUTABLES:
        return agent
    if agent.name and agent.name in command_names:
        return agent
    return None


# Backwards-compatible function names.
agent_status_from_vars = agent_state_from_vars
agent_status_for_runtime = agent_state_for_runtime


def agent_state_rank(state: str) -> int:
    return AGENT_STATE_RANK.get(state, AGENT_STATE_RANK["idle"])


def project_from_path(path: str) -> str:
    path = path.strip()
    if not path:
        return ""
    if FISH_TITLE_SEPARATOR in path:
        path = path.rsplit(FISH_TITLE_SEPARATOR, 1)[-1].strip()
    path = path.removesuffix("/") if path != "/" else path
    if path in {"", "/", "~"}:
        return path or "~"
    return os.path.basename(path) or path


def project_from_title(title: str, host: str = "") -> str:
    title = title.strip()
    if not title:
        return ""
    if FISH_TITLE_SEPARATOR in title:
        return project_from_path(title.rsplit(FISH_TITLE_SEPARATOR, 1)[-1])
    if host and ":" in title:
        user_host, _, detail = title.partition(":")
        if user_host.endswith(host) or user_host.endswith(f"@{host}"):
            return project_from_path(detail)
    return ""


def context_location(user_vars: dict[str, str], title: str = "") -> str:
    host = user_vars.get("HOST", "").strip()
    return user_vars.get("PROJECT", "").strip() or project_from_path(user_vars.get("CWD", "")) or project_from_title(title, host)


def _join_parts(*parts: str) -> str:
    return " • ".join(part for part in parts if part)


def resolve_window_state(user_vars: dict[str, str], processes: Any = (), title: str = "") -> ResolvedState:
    """Resolve user vars into display state, dropping stale runtime fields."""
    user_vars = coerce_user_vars(user_vars)
    program = user_vars.get("PROGRAM", "").strip() or "local"
    command = user_vars.get("COMMAND", "").strip()
    command_names = process_command_names(processes)
    location = context_location(user_vars, title)

    agent = agent_state_for_runtime(user_vars, processes)
    if agent is not None:
        host = user_vars.get("HOST", "").strip() if program in {"ssh", "ksh"} else ""
        target = _join_parts(agent.state, location, host)
        return ResolvedState(program=program, label=agent.name, target=target, location=location, host=host, agent=agent)

    if program in AGENT_PROGRAMS:
        program = "local"

    if program == "kitten" and "kitten" not in command_names:
        program = "local"
        command = ""

    if program in {"ssh", "ksh"}:
        host = user_vars.get("HOST", "").strip()
        label = "ksh" if program == "ksh" or command == "kitten ssh" else "ssh"
        if location:
            return ResolvedState(program=program, label=location, target=_join_parts(label, host), location=location, host=host)
        return ResolvedState(program=program, label=label, target=host, host=host)

    if program == "kitten":
        return ResolvedState(program=program, label="kitten", target=command, location=location)

    if program == "zellij":
        return ResolvedState(program=program, label="zj", target=user_vars.get("SESSION", "").strip(), location=location)

    return ResolvedState(program=program, label=location or program, location=location)


def agent_context_title(user_vars: dict[str, str], program: str, processes: Any = (), title: str = "") -> str:
    state = resolve_window_state({**coerce_user_vars(user_vars), "PROGRAM": program}, processes, title)
    return state.title if state.agent is not None else ""


def iter_window_records(kitty_ls: Any) -> Iterator[WindowRecord]:
    for os_window in kitty_ls or ():
        os_id = str(os_window.get("id", ""))
        for tab_index, tab in enumerate(os_window.get("tabs", ()), start=1):
            tab_id = str(tab.get("id", ""))
            tab_title = str(tab.get("title", ""))
            tab_focused = bool(tab.get("is_focused"))
            for window in tab.get("windows", ()):  # window dicts come from kitten @ ls JSON
                user_vars = coerce_user_vars(window.get("user_vars"))
                processes = window.get("foreground_processes") or ()
                cmdline = foreground_cmdline(processes)
                window_title = str(window.get("title", ""))
                state = resolve_window_state(user_vars, processes, window_title)
                is_current = bool(window.get("is_self"))
                is_focused = bool(window.get("is_focused"))
                yield WindowRecord(
                    schema_version=SCHEMA_VERSION,
                    os_window_id=os_id,
                    tab_id=tab_id,
                    tab_index=str(tab_index),
                    window_id=str(window.get("id", "")),
                    marker="@" if is_current else "*" if is_focused else " ",
                    is_current=is_current,
                    is_active_in_tab=bool(window.get("is_active")) and tab_focused,
                    tab_title=tab_title,
                    window_title=window_title,
                    cwd=str(window.get("cwd", "")),
                    cmdline=cmdline,
                    user_vars=user_vars,
                    resolved=state,
                    switcher_marker=str(user_vars.get("CONTEXT_SWITCHER", "")),
                )


def _to_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def sorted_window_records(kitty_ls: Any) -> list[WindowRecord]:
    records = list(iter_window_records(kitty_ls))
    records.sort(key=lambda record: (record.marker != "@", record.marker != "*", _to_int(record.os_window_id), _to_int(record.tab_index), _to_int(record.window_id)))
    return records


def resolve_window_dict(window: dict[str, Any]) -> ResolvedState:
    return resolve_window_state(coerce_user_vars(window.get("user_vars")), window.get("foreground_processes") or (), window.get("title", ""))


def _iter_windows(kitty_ls: Any) -> Iterable[dict[str, Any]]:
    for os_window in kitty_ls or ():
        for tab in os_window.get("tabs", ()):
            yield from tab.get("windows", ())


def _print_tsv(kitty_ls: Any) -> None:
    for record in sorted_window_records(kitty_ls):
        print("\t".join(clean_field(value) for value in record.to_tsv_row()))


def _print_jsonl(kitty_ls: Any, *, include_user_vars: bool = False) -> None:
    for record in sorted_window_records(kitty_ls):
        print(json.dumps(record.to_dict(include_user_vars=include_user_vars), ensure_ascii=False, separators=(",", ":")))


def _print_current(kitty_ls: Any, window_id: int) -> int:
    for window in _iter_windows(kitty_ls):
        if window.get("id") != window_id:
            continue
        state = resolve_window_dict(window)
        print("resolved:")
        print(f"  title: {state.title}")
        print(f"  program: {state.program}")
        print(f"  label: {state.label}")
        if state.target:
            print(f"  target: {state.target}")
        if state.agent is not None:
            print(f"  agent: {state.agent.name}")
            print(f"  agent_state: {state.agent.state}")
            if state.agent.result:
                print(f"  agent_result: {state.agent.result}")
            if state.agent.session:
                print(f"  agent_session: {state.agent.session}")
            if state.agent.session_name:
                print(f"  agent_session_name: {state.agent.session_name}")
        return 0
    print("resolved: window not found", file=sys.stderr)
    return 1


def _main() -> int:
    kitty_ls = json.load(sys.stdin)
    if len(sys.argv) > 1 and sys.argv[1] in {"--jsonl", "--jsonl-raw"}:
        _print_jsonl(kitty_ls, include_user_vars=sys.argv[1] == "--jsonl-raw")
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        _print_tsv(kitty_ls)
        return 0

    window_id = int(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("KITTY_WINDOW_ID", "0"))
    return _print_current(kitty_ls, window_id)


if __name__ == "__main__":
    raise SystemExit(_main())
