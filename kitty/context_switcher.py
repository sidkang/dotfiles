#!/usr/bin/env python3
"""Fuzzy switcher for Kitty windows/tabs using native window titles.

Launch from kitty.conf:

    map cmd+p launch --type=overlay --allow-remote-control python3 ~/.config/kitty/context_switcher.py
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

CONFIG_DIR = Path(__file__).resolve().parent

LOG_FILE = Path("/tmp/kitty-context-switcher.log")
PATH_PREFIXES = ("/opt/homebrew/bin", "/usr/local/bin", "/Applications/kitty.app/Contents/MacOS")
VIEWS = ("window", "tab")

FZF_COLORS = (
    "--color=bg:#eff1f5,bg+:#f2d5e7,fg:#4c4f69,fg+:#4c4f69,gutter:#eff1f5",
    "--color=hl:#ea76cb:bold,hl+:#8839ef:bold,prompt:#8839ef,pointer:#ea76cb,marker:#40a02b",
    "--color=spinner:#ea76cb,info:#8c8fa1,header:#6c6f85,border:#ccd0da,separator:#ccd0da",
)


@dataclass(frozen=True)
class WindowRecord:
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
    switcher_marker: str = ""

    @property
    def display_title(self) -> str:
        return self.window_title or self.tab_title


def sorted_window_records(kitty_ls: Any) -> list[WindowRecord]:
    records = []
    for os_window in kitty_ls or ():
        for tab_index, tab in enumerate(os_window.get("tabs", ()), start=1):
            for window in tab.get("windows", ()):
                is_current = bool(window.get("is_self"))
                records.append(WindowRecord(
                    os_window_id=str(os_window.get("id", "")),
                    tab_id=str(tab.get("id", "")),
                    tab_index=str(tab_index),
                    window_id=str(window.get("id", "")),
                    marker="@" if is_current else "*" if window.get("is_focused") else " ",
                    is_current=is_current,
                    is_active_in_tab=bool(window.get("is_active")) and bool(tab.get("is_focused")),
                    tab_title=str(tab.get("title", "")),
                    window_title=str(window.get("title", "")),
                    cwd=str(window.get("cwd", "")),
                    switcher_marker=str((window.get("user_vars") or {}).get("CONTEXT_SWITCHER", "")),
                ))
    records.sort(key=lambda record: (
        record.marker != "@",
        record.marker != "*",
        to_int(record.os_window_id),
        to_int(record.tab_index),
        to_int(record.window_id),
    ))
    return records


@dataclass(frozen=True)
class Choice:
    kind: str
    target_id: str
    preview_window_id: str
    text: str

    def to_fzf_line(self) -> str:
        return "\t".join((self.kind, self.target_id, self.preview_window_id, self.text))


@dataclass(frozen=True)
class Args:
    view: str = "window"
    list_only: bool = False
    fzf_input_only: bool = False
    preview_id: str = ""
    exclude_current_tab: bool = False


for path in reversed(PATH_PREFIXES):
    if path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{path}:{os.environ.get('PATH', '')}"


def command(name: str, fallback: str | None = None) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    if fallback and Path(fallback).exists():
        return fallback
    return name


KITTEN = command("kitten", "/Applications/kitty.app/Contents/MacOS/kitten")
FZF = command("fzf", "/opt/homebrew/bin/fzf")


def parse_args(argv: Sequence[str]) -> Args:
    if len(argv) >= 2 and argv[1] == "--preview":
        return Args(preview_id=argv[2] if len(argv) >= 3 else "")

    view = value_after(argv, "--view", "window")
    if view not in VIEWS:
        view = "window"
    return Args(
        view=view,
        list_only=(len(argv) >= 2 and argv[1] == "--list"),
        fzf_input_only=(len(argv) >= 2 and argv[1] == "--fzf-input"),
        exclude_current_tab=("--exclude-current-tab" in argv),
    )


def value_after(argv: Sequence[str], name: str, default: str) -> str:
    try:
        index = list(argv).index(name)
    except ValueError:
        return default
    return argv[index + 1] if index + 1 < len(argv) else default


def run(args: Sequence[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), input=input_text, text=True, capture_output=True, check=check)


def mark_switcher_window() -> None:
    subprocess.run([KITTEN, "@", "set-user-vars", f"CONTEXT_SWITCHER={os.getpid()}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def kitty_ls() -> str:
    try:
        return run([KITTEN, "@", "ls"]).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"context-switcher: failed to query kitty: {error}", file=sys.stderr)
        raise SystemExit(1)


def load_records() -> list[WindowRecord]:
    import json

    return sorted_window_records(json.loads(kitty_ls()))


def source_scope(records: Iterable[WindowRecord], source_window_id: str) -> tuple[str, str]:
    if source_window_id:
        for record in records:
            if record.window_id == source_window_id:
                return record.os_window_id, record.tab_id
    for record in records:
        if record.is_current and not record.switcher_marker:
            return record.os_window_id, record.tab_id
    return "", ""


def filtered_records(records: list[WindowRecord], *, exclude_current_tab: bool) -> list[WindowRecord]:
    source_window_id = os.environ.get("KITTY_WINDOW_ID", "")
    current_os, current_tab = source_scope(records, source_window_id)
    filtered = []
    for record in records:
        if record.switcher_marker:
            continue
        if source_window_id and record.window_id == source_window_id:
            continue
        if exclude_current_tab and (record.os_window_id, record.tab_id) == (current_os, current_tab):
            continue
        if not exclude_current_tab and record.is_current:
            continue
        filtered.append(record)
    return sorted(filtered, key=lambda record: sort_key(record, current_os, current_tab))


def sort_key(record: WindowRecord, current_os: str, current_tab: str) -> tuple[int, int, int, int]:
    scope_rank = 0 if (record.os_window_id, record.tab_id) == (current_os, current_tab) else 1 if record.os_window_id == current_os else 2
    return scope_rank, to_int(record.os_window_id), to_int(record.tab_index), to_int(record.window_id)


def to_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def choices_for_view(records: list[WindowRecord], view: str) -> list[Choice]:
    width = display_width()
    if view == "tab":
        return tab_choices(records, width)
    return window_choices(records, width)


def display_width() -> int:
    return max(80, shutil.get_terminal_size((120, 40)).columns - 8)


def fit(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def padded(text: str, width: int) -> str:
    return fit(text, width).ljust(width)


def switcher_glyph(record: WindowRecord) -> str:
    return "◆" if record.is_current else " "


def scope(record: WindowRecord) -> str:
    return f"os{record.os_window_id} t{record.tab_index} w{record.window_id}"


def window_choices(records: Iterable[WindowRecord], width: int) -> list[Choice]:
    choices = []
    for record in records:
        prefix = f"{switcher_glyph(record)} {scope(record):<13} "
        title_width = max(18, min(42, width // 3))
        detail_width = max(10, width - len(prefix) - title_width - 2)
        text = f"{prefix}{padded(record.display_title, title_width)}  {fit(record.cwd, detail_width)}"
        choices.append(Choice("window", record.window_id, record.window_id, text))
    return choices


def tab_choices(records: Iterable[WindowRecord], width: int) -> list[Choice]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for record in records:
        key = (record.os_window_id, record.tab_id)
        item = grouped.setdefault(key, {"record": record, "count": 0})
        item["count"] = int(item["count"]) + 1
        representative = item["record"]
        if not isinstance(representative, WindowRecord) or record.is_current or record.marker == "*" or record.is_active_in_tab:
            item["record"] = record

    choices = []
    for item in grouped.values():
        record = item["record"]
        if not isinstance(record, WindowRecord):
            continue
        count = int(item["count"])
        suffix = f"{count} windows" if count != 1 else "1 window"
        prefix = f"{switcher_glyph(record)} os{record.os_window_id} t{record.tab_index:<4} "
        title_width = max(18, min(42, width // 3))
        detail_width = max(10, width - len(prefix) - title_width - len(suffix) - 4)
        text = f"{prefix}{padded(record.tab_title or record.window_title, title_width)}  {suffix:<10} {fit(record.cwd, detail_width)}"
        choices.append(Choice("tab", record.tab_id, record.window_id, text))
    return choices


def choices_with_fallback(records: list[WindowRecord], preferred_view: str) -> tuple[str, list[Choice]]:
    for view in (preferred_view, *(candidate for candidate in VIEWS if candidate != preferred_view)):
        choices = choices_for_view(records, view)
        if choices:
            return view, choices
    return preferred_view, []


def visible_lines(choices: Iterable[Choice]) -> str:
    lines = [choice.text for choice in choices]
    return "\n".join(lines) + ("\n" if lines else "")


def fzf_input(choices: Iterable[Choice]) -> str:
    lines = [choice.to_fzf_line() for choice in choices]
    return "\n".join(lines) + ("\n" if lines else "")


def preview(window_id: str) -> int:
    if not window_id.isdigit():
        return 1
    try:
        return subprocess.run(
            [KITTEN, "@", "get-text", "--ansi", "--add-wrap-markers", "--add-cursor", "--match", f"id:{window_id}"],
            text=True,
            check=False,
        ).returncode
    except FileNotFoundError:
        print("context-switcher: kitten not found", file=sys.stderr)
        return 1


def select_choice(choices: list[Choice], active_view: str, preferred_view: str, *, exclude_current_tab: bool) -> tuple[str, str]:
    if not choices:
        print(f"context-switcher: no {active_view} entries found", file=sys.stderr)
        raise SystemExit(1)
    if shutil.which(FZF) is None and not Path(FZF).exists():
        print("context-switcher: fzf not found", file=sys.stderr)
        raise SystemExit(1)

    python = shutil.which(sys.executable) or sys.executable
    script = CONFIG_DIR / "context_switcher.py"
    next_view = VIEWS[(VIEWS.index(preferred_view) + 1) % len(VIEWS)]
    exclude_flag = " --exclude-current-tab" if exclude_current_tab else ""
    preview_cmd = f"{shlex.quote(python)} {shlex.quote(str(script))} --preview {{3}}"
    reload_cmd = f"{shlex.quote(python)} {shlex.quote(str(script))} --fzf-input --view {shlex.quote(active_view)}{exclude_flag}"
    tab_cmd = f"{shlex.quote(python)} {shlex.quote(str(script))} --view {shlex.quote(next_view)}{exclude_flag}"
    header = f"Enter: focus · Tab: {next_view} view\n{'─' * min(display_width(), 120)}"

    fzf = subprocess.run(
        [
            FZF,
            "--ansi",
            "--delimiter=\t",
            "--with-nth=4..",
            f"--prompt=󰄛 Kitty:{active_view} > ",
            f"--header={header}",
            "--no-separator",
            "--track",
            "--id-nth=1,2",
            *FZF_COLORS,
            "--layout=reverse",
            "--cycle",
            "--info=inline-right",
            "--preview",
            preview_cmd,
            "--preview-window=down,65%,border-top",
            "--bind",
            "change:first",
            "--bind",
            f"resize:reload({reload_cmd})",
            "--bind",
            f"tab:become({tab_cmd})",
        ],
        input=fzf_input(choices),
        text=True,
        stdout=subprocess.PIPE,
        check=False,
    )
    if fzf.returncode != 0 or not fzf.stdout.strip():
        raise SystemExit(0)
    fields = fzf.stdout.rstrip("\n").split("\t")
    if len(fields) < 2:
        raise SystemExit(0)
    return fields[0], fields[1]


def focus_target(kind: str, target_id: str) -> None:
    if not target_id.isdigit():
        print(f"context-switcher: invalid {kind} id: {target_id}", file=sys.stderr)
        return
    command_name = "focus-tab" if kind == "tab" else "focus-window"
    result = subprocess.run([KITTEN, "@", command_name, "--match", f"id:{target_id}"], check=False)
    if result.returncode != 0:
        print(f"context-switcher: focus {kind} {target_id} failed", file=sys.stderr)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if args.preview_id:
        return preview(args.preview_id)

    interactive = not args.list_only and not args.fzf_input_only
    if interactive:
        mark_switcher_window()
    records = load_records()
    records_for_view = records if args.list_only else filtered_records(records, exclude_current_tab=args.exclude_current_tab)
    view, choices = choices_with_fallback(records_for_view, args.view)

    if args.list_only:
        print(visible_lines(choices), end="")
        return 0
    if args.fzf_input_only:
        print(fzf_input(choices), end="")
        return 0

    kind, target_id = select_choice(choices, view, args.view, exclude_current_tab=args.exclude_current_tab)
    focus_target(kind, target_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as error:
        LOG_FILE.write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
        print(f"context-switcher: {error}", file=sys.stderr)
        raise SystemExit(1)
