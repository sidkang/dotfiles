from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

SWIFTBAR_ATTR_KEYS = (
    "alternate",
    "ansi",
    "badge",
    "bash",
    "checked",
    "color",
    "dropdown",
    "emojize",
    "font",
    "href",
    "image",
    "key",
    "length",
    "md",
    "refresh",
    "sfcolor",
    "sfcolor2",
    "sfconfig",
    "sfimage",
    "sfsize",
    "shortcut",
    "size",
    "stdin",
    "symbolize",
    "templateImage",
    "terminal",
    "tooltip",
    "trim",
    "webview",
    "webviewh",
    "webvieww",
)

RESERVED_ITEM_KEYS = {"attrs", "children", "hidden", "separator", "text"}


def parse_swiftbar_pyobj(raw: str) -> dict[str, Any]:
    payload = ast.literal_eval(raw)
    if not isinstance(payload, dict):
        raise ValueError("Top-level payload must be a Python dict")

    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("'items' must be a list")

    return payload


def load_swiftbar_pyobj(path: str | Path) -> dict[str, Any]:
    return parse_swiftbar_pyobj(Path(path).read_text(encoding="utf-8"))


def _escape_text(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def _format_attr_value(value: Any) -> str:
    if isinstance(value, str):
        cleaned = value.replace("\n", " ")
        if not cleaned:
            return '""'
        if any(char.isspace() for char in cleaned) or '"' in cleaned:
            return json.dumps(cleaned, ensure_ascii=False)
        return cleaned.replace("|", "\\|")
    return str(value)


def _normalize_attrs(item: dict[str, Any]) -> dict[str, Any]:
    attrs = dict(item.get("attrs") or {})

    for key in SWIFTBAR_ATTR_KEYS:
        if key in item and key not in attrs:
            attrs[key] = item[key]

    for key, value in item.items():
        if key.startswith("param") and key not in RESERVED_ITEM_KEYS and key not in attrs:
            attrs[key] = value

    return attrs


def _format_attrs(attrs: dict[str, Any]) -> str:
    if not attrs:
        return ""

    parts: list[str] = []
    for key, value in attrs.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_attr_value(value)}")

    return f" | {' '.join(parts)}" if parts else ""


def _render_items(items: list[dict[str, Any]], depth: int = 0) -> list[str]:
    lines: list[str] = []

    for item in items:
        if item.get("hidden"):
            continue

        if item.get("separator"):
            lines.append("---")
            continue

        text = _escape_text(item.get("text", ""))
        attrs = _format_attrs(_normalize_attrs(item))
        prefix = "--" * depth
        lines.append(f"{prefix}{text}{attrs}")

        children = item.get("children") or []
        if children:
            if not isinstance(children, list):
                raise ValueError("'children' must be a list")
            lines.extend(_render_items(children, depth + 1))

    return lines


def render_swiftbar_menu(payload: dict[str, Any]) -> str:
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("'items' must be a list")

    lines = [_escape_text(payload.get("title", "")), "---", *_render_items(items)]
    return "\n".join(lines)


def render_swiftbar_pyobj(raw: str) -> str:
    return render_swiftbar_menu(parse_swiftbar_pyobj(raw))
