import inspect
import os
import shlex
import sys
from typing import Any, NamedTuple

from kitty.boss import Boss, get_boss
from kitty.fast_data_types import Screen, add_timer
from kitty.tabs import Tab, TabManager
from kitty.tab_bar import (
    DrawData,
    ExtraData,
    TabBarData,
    as_rgb,
    wcswidth,
)

sys.path.insert(0, os.path.dirname(__file__))
from context_state import resolve_window_state  # noqa: E402

LATTE_TEXT = as_rgb(0x4C4F69)
LATTE_BASE = as_rgb(0xEFF1F5)
LATTE_MANTLE = as_rgb(0xE6E9EF)
LATTE_OVERLAY1 = as_rgb(0x8C8FA1)
LATTE_MAUVE = as_rgb(0x8839EF)
LATTE_PEACH = as_rgb(0xFE640B)
LATTE_GREEN = as_rgb(0x40A02B)
LATTE_SURFACE0 = as_rgb(0xCCD0DA)

TAB_ACTIVE_BG = as_rgb(0xEA76CB)
TAB_ACTIVE_FG = LATTE_BASE
TAB_INACTIVE_BG = as_rgb(0xDCE0E8)
TAB_INACTIVE_FG = LATTE_OVERLAY1
TAB_BAR_BG = 0
TAB_SEPARATOR = ""
LOCAL_ICON = "\uea85"
REMOTE_ICON = "\ue8b1"
HOTKEY_ICON = "\U000f1575"

RIGHT_MARGIN = 0
ACTIVE_TITLE_MAX = 48
HOTKEY_SESSION = "hotkey"
FISH_TITLE_SEPARATOR = " · "
PI_WORKING_FRAMES = frozenset("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
BRAILLE_START = 0x2800
BRAILLE_ALIAS_START = 0xF800
# Pi emits frames every 80ms; redraw at 8 FPS to limit full tab-bar rendering cost.
BACKGROUND_SPINNER_REDRAW_DELAY = 0.125

_pending_spinner_tab_ids: set[int] = set()
_pending_spinner_redraw_timer: int | None = None
_tabs_with_working_pi: set[int] = set()


class RemoteTitle(NamedTuple):
    host: str
    project: str
    user: str = ""


def draw_title(data):
    title = data.get("title", "").strip()
    parts = [_context_title() or (_compact_title(title) if title else "")]

    layout = data.get("layout_name", "")
    num_windows = data.get("num_windows", 0)
    if layout and not (layout == "splits" and num_windows <= 1):
        parts.append(layout)

    compact_title = _truncate_title(" • ".join(part for part in parts if part))
    return f"{compact_title} " if compact_title else ""


def _is_called_from_tab_bar_mouse() -> bool:
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    while caller is not None:
        if (
            caller.f_code.co_name == "handle_tab_bar_mouse"
            and caller.f_globals.get("__name__") == "kitty.tabs"
        ):
            return True
        caller = caller.f_back
    return False


def _is_blank_tab_bar_double_click_new_tab() -> bool:
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    while caller is not None:
        if (
            caller.f_code.co_name == "handle_tab_bar_mouse"
            and caller.f_globals.get("__name__") == "kitty.tabs"
        ):
            return "tab" in caller.f_locals and caller.f_locals["tab"] is None
        caller = caller.f_back
    return False


def _disable_tab_bar_mouse_side_effects() -> None:
    """Disable tab-bar double-click rename and blank-area double-click new-tab."""
    current_set_tab_title = Boss.set_tab_title
    if not getattr(current_set_tab_title, "_dotfile_no_tab_double_click_rename", False):
        original_set_tab_title = current_set_tab_title

        def set_tab_title_without_tab_double_click(self, *args, **kwargs):
            if _is_called_from_tab_bar_mouse():
                return None
            return original_set_tab_title(self, *args, **kwargs)

        set_tab_title_without_tab_double_click._dotfile_no_tab_double_click_rename = True
        Boss.set_tab_title = set_tab_title_without_tab_double_click

    current_new_tab = TabManager.new_tab
    if not getattr(current_new_tab, "_dotfile_no_blank_double_click_new_tab", False):
        original_new_tab = current_new_tab

        def new_tab_without_blank_double_click(self, *args, **kwargs):
            if _is_blank_tab_bar_double_click_new_tab():
                return None
            return original_new_tab(self, *args, **kwargs)

        new_tab_without_blank_double_click._dotfile_no_blank_double_click_new_tab = True
        TabManager.new_tab = new_tab_without_blank_double_click


def _is_pi_title(title: str) -> bool:
    return title.startswith("π - ") or title[1:].startswith(" π - ")


def _flush_pending_spinner_tab_bar_redraw(_timer_id: int | None) -> None:
    global _pending_spinner_redraw_timer
    _pending_spinner_redraw_timer = None

    pending_tab_ids = _pending_spinner_tab_ids.copy()
    _pending_spinner_tab_ids.clear()
    dirtied_os_window_ids: set[int] = set()
    for tab_id in pending_tab_ids:
        tab = get_boss().tab_for_id(tab_id)
        if tab is not None and tab.os_window_id not in dirtied_os_window_ids:
            tab.mark_tab_bar_dirty()
            dirtied_os_window_ids.add(tab.os_window_id)


def _request_spinner_tab_bar_redraw(tab_id: int) -> None:
    global _pending_spinner_redraw_timer
    _pending_spinner_tab_ids.add(tab_id)
    if _pending_spinner_redraw_timer is None:
        _pending_spinner_redraw_timer = add_timer(
            _flush_pending_spinner_tab_bar_redraw,
            BACKGROUND_SPINNER_REDRAW_DELAY,
            False,
        )


def _invalidate_tab_bar_for_background_title_changes() -> None:
    """Coalesce background Pi title changes into at most one redraw every 125ms."""
    current_title_changed = Tab.title_changed
    if getattr(current_title_changed, "_dotfile_background_title_invalidation_version", 0) == 2:
        return

    original_title_changed = getattr(current_title_changed, "_dotfile_original_title_changed", None)
    if original_title_changed is None and getattr(current_title_changed, "_dotfile_background_title_invalidates_tab_bar", False):
        original_title_changed = inspect.getclosurevars(current_title_changed).nonlocals.get("original_title_changed")
    if not callable(original_title_changed):
        original_title_changed = current_title_changed

    def title_changed_and_invalidate_tab_bar(self, window):
        original_title_changed(self, window)
        if window is not self.active_window and (_is_pi_title(window.title) or self.id in _tabs_with_working_pi):
            _request_spinner_tab_bar_redraw(self.id)

    title_changed_and_invalidate_tab_bar._dotfile_background_title_invalidation_version = 2
    title_changed_and_invalidate_tab_bar._dotfile_original_title_changed = original_title_changed
    Tab.title_changed = title_changed_and_invalidate_tab_bar


def _active_title() -> str:
    tm = get_boss().active_tab_manager
    if tm is None or tm.active_tab is None:
        return ""
    return tm.active_tab.effective_title or ""


def _split_remote_target(target: str) -> tuple[str, str]:
    target = target.removeprefix("ssh://")
    user = ""
    if "@" in target:
        user, target = target.rsplit("@", 1)
    if target.startswith("[") and "]" in target:
        host = target[1 : target.index("]")]
    else:
        host = target.split(":", 1)[0]
    return user, host


def _project_from_path(path: str) -> str:
    path = path.strip()
    if not path:
        return ""
    if FISH_TITLE_SEPARATOR in path:
        path = path.rsplit(FISH_TITLE_SEPARATOR, 1)[-1].strip()
    path = path.removesuffix("/") if path != "/" else path
    if path in {"", "/", "~"}:
        return path or "~"
    return os.path.basename(path) or path


def _remote_target_from_command(command: str) -> tuple[str, str]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    if not tokens:
        return "", ""
    if tokens[:2] == ["kitten", "ssh"]:
        args = tokens[2:]
    elif tokens[:2] == ["kitty", "+kitten"] and len(tokens) > 2 and tokens[2] == "ssh":
        args = tokens[3:]
    elif tokens[0] in {"ssh", "mosh"}:
        args = tokens[1:]
    else:
        return "", ""

    user = ""
    options_with_values = {"-b", "-c", "-D", "-E", "-F", "-i", "-J", "-L", "-m", "-O", "-o", "-p", "-Q", "-R", "-S", "-W", "-w"}
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            index += 1
            break
        if arg == "-l" and index + 1 < len(args):
            user = args[index + 1]
            index += 2
            continue
        if arg.startswith("-"):
            index += 2 if arg in options_with_values else 1
            continue
        target_user, host = _split_remote_target(arg)
        return target_user or user, host

    return _split_remote_target(args[index]) if index < len(args) else ("", "")


def _parse_remote_title(title: str) -> RemoteTitle | None:
    command, separator, detail = title.partition(FISH_TITLE_SEPARATOR)
    user, host = _remote_target_from_command(command.strip())
    if host:
        return RemoteTitle(host, _project_from_path(detail) if separator else "", user)

    if "@" in title and ":" in title:
        user_host, _, remote_detail = title.partition(":")
        user, host = _split_remote_target(user_host.strip())
        if host:
            return RemoteTitle(host, _project_from_path(remote_detail), user)

    return None


def _left_status(title: str) -> tuple[str, int]:
    if _parse_remote_title(title) is not None:
        return REMOTE_ICON, LATTE_MAUVE
    return LOCAL_ICON, LATTE_GREEN


def _window_user_vars(window: Any) -> dict[str, str]:
    user_vars = window.get("user_vars") if isinstance(window, dict) else getattr(window, "user_vars", None)
    try:
        return dict(user_vars or {})
    except (TypeError, ValueError):
        return {}


def _active_window() -> Any:
    return getattr(get_boss(), "active_window", None)


def _window_foreground_processes(window: Any) -> Any:
    if isinstance(window, dict):
        return window.get("foreground_processes") or ()
    child = getattr(window, "child", None)
    return getattr(child, "foreground_processes", None) or ()


def _tab_bg(is_active: bool) -> int:
    return TAB_ACTIVE_BG if is_active else TAB_INACTIVE_BG


def _tab_fg(is_active: bool) -> int:
    return TAB_ACTIVE_FG if is_active else TAB_INACTIVE_FG


# Kitty context user-var schema is defined and interpreted in context_state.py.


def _context_title() -> str:
    window = _active_window()
    user_vars = _window_user_vars(window)
    if not user_vars.get("PROGRAM", "").strip() and not user_vars.get("AGENT", "").strip():
        return ""
    return resolve_window_state(user_vars, _window_foreground_processes(window), _active_title().strip()).title


def _local_path_from_title(title: str) -> str:
    _, separator, path = title.rpartition(FISH_TITLE_SEPARATOR)
    return (path if separator else title).strip()


def _repo_project_from_path(path: str) -> str:
    if not path.startswith(("/", "~")):
        return ""

    current = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(current):
        return ""
    if os.path.isfile(current):
        current = os.path.dirname(current)

    while True:
        if os.path.exists(os.path.join(current, ".jj")) or os.path.exists(os.path.join(current, ".git")):
            return os.path.basename(os.path.normpath(current)) or current
        parent = os.path.dirname(current)
        if parent == current:
            return ""
        current = parent


def _local_title(title: str) -> str:
    path = _local_path_from_title(title)
    return _repo_project_from_path(path) or path


def _compact_title(title: str) -> str:
    parsed = _parse_remote_title(title)
    if parsed is None:
        return _local_title(title)

    parts = [parsed.project] if parsed.project else []
    parts.append(f"ssh {parsed.host}")
    if parsed.user == "root":
        parts.append("root!")
    return " • ".join(parts)


def _truncate_title(title: str) -> str:
    if wcswidth(title) <= ACTIVE_TITLE_MAX:
        return title

    truncated = ""
    for char in title:
        if wcswidth(truncated + char) > ACTIVE_TITLE_MAX - 1:
            break
        truncated += char
    return truncated + "…"


def _fit_text(text: str, available: int) -> str:
    if available <= 0:
        return ""
    if wcswidth(text) <= available:
        return text
    if available == 1:
        return "…"

    truncated = ""
    for char in text:
        if wcswidth(truncated + char) > available - 1:
            break
        truncated += char
    return truncated + "…"


def _draw_left_icon(screen: Screen, tab: TabBarData, index: int) -> int:
    if index != 1:
        return 0

    fg, bg = screen.cursor.fg, screen.cursor.bg
    title = _active_title().strip()
    is_hotkey = tab.session_name == HOTKEY_SESSION or tab.active_session_name == HOTKEY_SESSION
    label, color = (HOTKEY_ICON, LATTE_PEACH) if is_hotkey else _left_status(title)
    bold = screen.cursor.bold
    italic = screen.cursor.italic

    screen.cursor.bg = color
    screen.cursor.fg = LATTE_MANTLE
    screen.cursor.bold = False
    screen.cursor.italic = False
    right_padding = "  " if is_hotkey else " "
    screen.draw(f" {label}{right_padding}")

    screen.cursor.fg = color
    screen.cursor.bg = _tab_bg(tab.is_active)
    screen.draw(TAB_SEPARATOR)

    screen.cursor.fg, screen.cursor.bg = fg, bg
    screen.cursor.bold = bold
    screen.cursor.italic = italic
    return screen.cursor.x


def _pi_working_frames(tab_id: int) -> str:
    """Return one leading spinner frame for every working Pi window in a tab."""
    tab = get_boss().tab_for_id(tab_id)
    if tab is None:
        return ""

    frames: list[str] = []
    for window in tab:
        title = getattr(window, "title", "") or ""
        if not title or not title[1:].startswith(" π - "):
            continue
        if title[0] in PI_WORKING_FRAMES:
            frames.append(chr(BRAILLE_ALIAS_START + ord(title[0]) - BRAILLE_START))

    if frames:
        _tabs_with_working_pi.add(tab_id)
    else:
        _tabs_with_working_pi.discard(tab_id)
    return " ".join(frames)


def _draw_tab_number(screen: Screen, tab: TabBarData, index: int) -> int:
    bold = screen.cursor.bold
    italic = screen.cursor.italic
    screen.cursor.fg = _tab_fg(tab.is_active)
    screen.cursor.bg = _tab_bg(tab.is_active)
    screen.cursor.bold = tab.is_active
    screen.cursor.italic = False
    screen.draw(f" {index}")

    frames = _pi_working_frames(tab.tab_id)
    if frames:
        screen.cursor.fg = LATTE_TEXT if tab.is_active else LATTE_MAUVE
        screen.cursor.bold = True
        screen.draw(f" {frames}")

    screen.cursor.bold = bold
    screen.cursor.italic = italic
    return screen.cursor.x


def _draw_tab_separator(screen: Screen, current_tab: TabBarData, next_tab: TabBarData | None) -> int:
    fg, bg = screen.cursor.fg, screen.cursor.bg
    bold = screen.cursor.bold
    italic = screen.cursor.italic
    screen.cursor.fg = _tab_bg(current_tab.is_active)
    screen.cursor.bg = _tab_bg(next_tab.is_active) if next_tab is not None else TAB_BAR_BG
    screen.cursor.bold = False
    screen.cursor.italic = False
    screen.draw(TAB_SEPARATOR)
    screen.cursor.fg, screen.cursor.bg = fg, bg
    screen.cursor.bold = bold
    screen.cursor.italic = italic
    return screen.cursor.x


def _draw_tab_index(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_title_length: int,
    index: int,
    is_last: bool,
    extra_data: ExtraData,
) -> int:
    if draw_data.leading_spaces:
        screen.draw(" " * draw_data.leading_spaces)

    _draw_left_icon(screen, tab, index)
    _draw_tab_number(screen, tab, index)
    screen.draw(" ")
    _draw_tab_separator(screen, tab, extra_data.next_tab)
    screen.cursor.bg = TAB_BAR_BG
    return screen.cursor.x


def _draw_right_status(screen: Screen, is_last: bool) -> int:
    if not is_last:
        return 0

    title = _context_title()
    if not title:
        title = _compact_title(_active_title().strip())
    if not title:
        return screen.cursor.x

    available = screen.columns - screen.cursor.x - RIGHT_MARGIN
    if available <= 0:
        return screen.cursor.x

    text = _fit_text(f" {title} ", available)
    screen.draw(" " * max(0, available - wcswidth(text)))
    screen.cursor.bg = 0
    screen.cursor.fg = LATTE_TEXT
    screen.cursor.bold = False
    screen.cursor.italic = False
    screen.draw(text)
    return screen.cursor.x


def draw_tab(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_title_length: int,
    index: int,
    is_last: bool,
    extra_data: ExtraData,
) -> int:
    _disable_tab_bar_mouse_side_effects()
    _invalidate_tab_bar_for_background_title_changes()
    tab_end = _draw_tab_index(draw_data, screen, tab, before, max_title_length, index, is_last, extra_data)
    _draw_right_status(screen, is_last)
    return tab_end
