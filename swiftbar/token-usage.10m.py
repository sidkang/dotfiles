#!/opt/homebrew/bin/python3.14
# <xbar.title>OpenCode + Pi Token Usage</xbar.title>
# <xbar.version>v0.5</xbar.version>
# <xbar.author>Sid</xbar.author>
# <xbar.desc>Show combined token usage from OpenCode and Pi.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>


from __future__ import annotations

import hashlib
import json
import os
import platform
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable
from urllib.parse import quote

from swiftbar_menu import render_swiftbar_menu

OPENCODE_DB_PATH = Path(os.environ.get("OPENCODE_DB_PATH", "~/.local/share/opencode/opencode.db")).expanduser()
OPENCODE_SOURCE_ID_PATH = Path(
    os.environ.get("OPENCODE_USAGE_SOURCE_ID_PATH", f"{OPENCODE_DB_PATH}.usage-source-id")
).expanduser()
OPENCODE_SYNC_DIR = Path(os.environ.get("OPENCODE_USAGE_SYNC_DIR", "~/config/statics/opencode")).expanduser()
PI_SESSIONS_DIR = Path(
    os.environ.get(
        "PI_USAGE_SESSIONS_DIR",
        str(Path(os.environ.get("PI_CODING_AGENT_DIR", "~/.config/pi/agent")) / "sessions"),
    )
).expanduser()

WINDOWS = {
    "last_1h": timedelta(hours=1),
    "last_24h": timedelta(hours=24),
    "last_7d": timedelta(days=7),
    "last_30d": timedelta(days=30),
}
MAX_WINDOW = max(WINDOWS.values())
LEGACY_SNAPSHOT_MAX_AGE = timedelta(minutes=30)
SNAPSHOT_VERSION = 4
MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024
MAX_PI_RECORD_BYTES = 16 * 1024 * 1024
MAX_METRIC_VALUE = 10**15
SNAPSHOT_BUCKET_MS = 60_000
METRIC_KEYS = (
    "total",
    "input",
    "output",
    "cache_read",
    "cache_write",
    "assistant_messages",
)
WINDOW_NAMES = (*WINDOWS.keys(), "all")
WINDOW_LABELS = {
    "last_1h": "1h",
    "last_24h": "24h",
    "last_7d": "7d",
    "last_30d": "30d",
    "all": "All",
}

PLUGIN_ID = quote(Path(__file__).name)
REFRESH_HREF = f"swiftbar://refreshplugin?plugin={PLUGIN_ID}"


def metric_template() -> dict[str, int]:
    return dict.fromkeys(METRIC_KEYS, 0)


def windows_template() -> dict[str, dict[str, int]]:
    return {name: metric_template() for name in WINDOW_NAMES}


def nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, float) and not value.is_integer():
        return 0
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0
    return parsed if 0 <= parsed <= MAX_METRIC_VALUE else 0


def normalized_metric(source: Any) -> dict[str, int]:
    if not isinstance(source, dict):
        return metric_template()
    return {key: nonnegative_int(source.get(key)) for key in METRIC_KEYS}


def add_metric(target: dict[str, int], source: Any) -> None:
    metric = normalized_metric(source)
    for key in METRIC_KEYS:
        target[key] += metric[key]


def has_token_usage(metric: dict[str, int]) -> bool:
    return any(metric[key] > 0 for key in METRIC_KEYS if key != "assistant_messages")


def update_windows(
    windows: dict[str, dict[str, int]],
    timestamp: datetime,
    now: datetime,
    metric: dict[str, int],
) -> None:
    add_metric(windows["all"], metric)
    if timestamp > now:
        return
    for name, delta in WINDOWS.items():
        if timestamp >= now - delta:
            add_metric(windows[name], metric)


def extract_opencode_metric(tokens: Any) -> dict[str, int]:
    if not isinstance(tokens, dict):
        return metric_template()
    cache = tokens.get("cache")
    if not isinstance(cache, dict):
        cache = {}
    return {
        "total": nonnegative_int(tokens.get("total")),
        "input": nonnegative_int(tokens.get("input")),
        "output": nonnegative_int(tokens.get("output")),
        "cache_read": nonnegative_int(cache.get("read")),
        "cache_write": nonnegative_int(cache.get("write")),
        "assistant_messages": 1,
    }


def extract_pi_metric(usage: Any) -> dict[str, int]:
    if not isinstance(usage, dict):
        return metric_template()
    return {
        "total": nonnegative_int(usage.get("totalTokens")),
        "input": nonnegative_int(usage.get("input")),
        "output": nonnegative_int(usage.get("output")),
        "cache_read": nonnegative_int(usage.get("cacheRead")),
        "cache_write": nonnegative_int(usage.get("cacheWrite")),
        "assistant_messages": 1,
    }


def format_tokens(value: int) -> str:
    value = int(value or 0)
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def visible_tokens(metric: dict[str, int]) -> int:
    return int(metric.get("input", 0) or 0) + int(metric.get("output", 0) or 0)


def local_tzinfo() -> Any:
    return datetime.now().astimezone().tzinfo


def valid_source_id(value: Any) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        return None
    if not all(char.isalnum() or char in {"-", "_"} for char in value):
        return None
    return value


def machine_name() -> str:
    raw = os.environ.get("OPENCODE_USAGE_MACHINE") or platform.node() or "unknown-machine"
    allowed = {"-", "_", "."}
    cleaned = "".join(char for char in raw if char.isalnum() or char in allowed).strip("._-")
    return cleaned or "unknown-machine"


def parse_timestamp(value: Any, tzinfo: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(tzinfo)
    except (ValueError, OverflowError, OSError):
        return None


def parse_epoch_ms(value: Any, tzinfo: Any) -> datetime | None:
    if isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=tzinfo)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def serialize_snapshot_event(timestamp: datetime, metric: dict[str, int]) -> list[int]:
    normalized = normalized_metric(metric)
    return [
        int(timestamp.timestamp() * 1000),
        *(normalized[key] for key in METRIC_KEYS),
    ]


def parse_snapshot_event(value: Any, tzinfo: Any) -> tuple[datetime, dict[str, int]] | None:
    if not isinstance(value, list) or len(value) != len(METRIC_KEYS) + 1:
        return None
    timestamp = parse_epoch_ms(value[0], tzinfo)
    if timestamp is None:
        return None
    metric = {key: nonnegative_int(raw) for key, raw in zip(METRIC_KEYS, value[1:])}
    if not has_token_usage(metric):
        return None
    return timestamp, metric


def iter_opencode_messages(connection: sqlite3.Connection) -> Iterable[tuple[int, str]]:
    cursor = connection.execute("SELECT time_created, data FROM message")
    yield from cursor


def opencode_source_id(connection: sqlite3.Connection) -> str:
    try:
        existing = valid_source_id(OPENCODE_SOURCE_ID_PATH.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError):
        existing = None
    if existing:
        return existing

    row = connection.execute(
        "SELECT id FROM message ORDER BY time_created, id LIMIT 1"
    ).fetchone()
    lineage = str(row[0]) if row else f"empty:{OPENCODE_DB_PATH.resolve()}"
    source_id = hashlib.sha256(f"opencode:{lineage}".encode()).hexdigest()[:24]

    temporary_path: Path | None = None
    try:
        OPENCODE_SOURCE_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=OPENCODE_SOURCE_ID_PATH.parent,
            prefix=f".{OPENCODE_SOURCE_ID_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(f"{source_id}\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, OPENCODE_SOURCE_ID_PATH)
        temporary_path = None
    except OSError as exc:
        raise OSError(f"could not persist OpenCode source ID at {OPENCODE_SOURCE_ID_PATH}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass

    return source_id


def build_opencode_local_snapshot() -> dict[str, Any] | None:
    if not OPENCODE_DB_PATH.is_file():
        return None

    tzinfo = local_tzinfo()
    now = datetime.now(tzinfo)
    windows = windows_template()
    buckets: dict[int, dict[str, int]] = {}
    database_uri = f"{OPENCODE_DB_PATH.resolve().as_uri()}?mode=ro"

    with sqlite3.connect(database_uri, uri=True, timeout=2) as connection:
        source_id = opencode_source_id(connection)
        for time_created_ms, raw_data in iter_opencode_messages(connection):
            try:
                message = json.loads(raw_data)
            except (ValueError, TypeError, UnicodeError, RecursionError):
                continue

            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue

            metric = extract_opencode_metric(message.get("tokens"))
            if not has_token_usage(metric):
                continue

            timestamp = parse_epoch_ms(time_created_ms, tzinfo)
            if timestamp is None:
                add_metric(windows["all"], metric)
                continue

            update_windows(windows, timestamp, now, metric)
            if now - MAX_WINDOW <= timestamp <= now:
                bucket_epoch_ms = int(timestamp.timestamp() * 1000) // SNAPSHOT_BUCKET_MS * SNAPSHOT_BUCKET_MS
                bucket = buckets.setdefault(bucket_epoch_ms, metric_template())
                add_metric(bucket, metric)

    serialized_buckets = [
        [epoch_ms, *(buckets[epoch_ms][key] for key in METRIC_KEYS)]
        for epoch_ms in sorted(buckets)
    ]

    return {
        "version": SNAPSHOT_VERSION,
        "source": "opencode",
        "source_id": source_id,
        "machine": machine_name(),
        "generated_at": now.isoformat(),
        "generated_at_epoch_ms": int(now.timestamp() * 1000),
        "windows": windows,
        "buckets": serialized_buckets,
        "supersedes": sorted(
            inherited_superseded_machines(source_id) | configured_superseded_machines()
        ),
    }


def read_snapshot(path: Path) -> dict[str, Any] | None:
    try:
        if path.stat().st_size > MAX_SNAPSHOT_BYTES:
            return None
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        return snapshot if isinstance(snapshot, dict) else None
    except (OSError, UnicodeError, ValueError, RecursionError):
        return None


def snapshot_supersedes(snapshot: dict[str, Any]) -> set[str]:
    values = snapshot.get("supersedes")
    if not isinstance(values, list):
        return set()
    return {
        value
        for value in values
        if isinstance(value, str) and 0 < len(value) <= 255
    }


def inherited_superseded_machines(source_id: str) -> set[str]:
    inherited: set[str] = set()
    if not OPENCODE_SYNC_DIR.exists():
        return inherited
    for path in OPENCODE_SYNC_DIR.glob("*.json"):
        snapshot = read_snapshot(path)
        if snapshot and snapshot_source_id(snapshot) == source_id:
            inherited.update(snapshot_supersedes(snapshot))
    return inherited


# Explicitly associate pre-v4 hostname snapshots after a machine rename.
def configured_superseded_machines() -> set[str]:
    return {
        machine.strip()
        for machine in os.environ.get("OPENCODE_USAGE_SUPERSEDES", "").split(",")
        if machine.strip()
    }


def snapshot_generated_at(snapshot: dict[str, Any], tzinfo: Any) -> datetime | None:
    timestamp = parse_epoch_ms(snapshot.get("generated_at_epoch_ms"), tzinfo)
    return timestamp or parse_timestamp(snapshot.get("generated_at"), tzinfo)


def supported_snapshot(snapshot: dict[str, Any]) -> bool:
    return (
        snapshot.get("version") in {3, SNAPSHOT_VERSION}
        and snapshot.get("source") == "opencode"
        and isinstance(snapshot.get("machine"), str)
        and bool(snapshot["machine"])
        and isinstance(snapshot.get("windows"), dict)
    )


def snapshot_source_id(snapshot: dict[str, Any]) -> str | None:
    return valid_source_id(snapshot.get("source_id"))


def snapshot_identity(snapshot: dict[str, Any]) -> str:
    source_id = snapshot_source_id(snapshot)
    if source_id:
        return f"source:{source_id}"
    return f"machine:{snapshot['machine']}"


def prefer_snapshot(
    current: tuple[bool, dict[str, Any]],
    candidate: tuple[bool, dict[str, Any]],
    tzinfo: Any,
) -> tuple[bool, dict[str, Any]]:
    current_is_local, current_snapshot = current
    candidate_is_local, candidate_snapshot = candidate
    if current_is_local != candidate_is_local:
        return current if current_is_local else candidate

    current_time = snapshot_generated_at(current_snapshot, tzinfo)
    candidate_time = snapshot_generated_at(candidate_snapshot, tzinfo)
    if candidate_time and (current_time is None or candidate_time > current_time):
        return candidate
    return current


def add_superseded_machine(snapshot: dict[str, Any], machine: str) -> None:
    superseded = snapshot_supersedes(snapshot)
    superseded.add(machine)
    snapshot["supersedes"] = sorted(superseded)


def collect_opencode_snapshots(
    local_snapshot: dict[str, Any] | None,
    tzinfo: Any,
) -> list[dict[str, Any]]:
    candidates: list[tuple[bool, dict[str, Any]]] = []
    if local_snapshot and supported_snapshot(local_snapshot):
        candidates.append((True, local_snapshot))

    if OPENCODE_SYNC_DIR.exists():
        for path in sorted(OPENCODE_SYNC_DIR.glob("*.json")):
            snapshot = read_snapshot(path)
            if snapshot and supported_snapshot(snapshot):
                candidates.append((False, snapshot))

    snapshots_by_identity: dict[str, tuple[bool, dict[str, Any]]] = {}
    for candidate in candidates:
        identity = snapshot_identity(candidate[1])
        current = snapshots_by_identity.get(identity)
        snapshots_by_identity[identity] = (
            candidate if current is None else prefer_snapshot(current, candidate, tzinfo)
        )

    selected = list(snapshots_by_identity.values())
    lineage_snapshots = [candidate for candidate in selected if snapshot_source_id(candidate[1])]
    legacy_snapshots = [candidate for candidate in selected if not snapshot_source_id(candidate[1])]
    superseded_machines = {
        machine
        for _, snapshot in lineage_snapshots
        for machine in snapshot_supersedes(snapshot)
    }
    retained_legacy: list[tuple[bool, dict[str, Any]]] = []

    for legacy in legacy_snapshots:
        legacy_snapshot = legacy[1]
        legacy_machine = legacy_snapshot["machine"]
        if legacy_machine in superseded_machines:
            continue

        matches = [
            candidate
            for candidate in lineage_snapshots
            if candidate[1]["machine"] == legacy_machine
        ]
        if not matches:
            retained_legacy.append(legacy)
            continue

        claimant = matches[0]
        for candidate in matches[1:]:
            claimant = prefer_snapshot(claimant, candidate, tzinfo)
        add_superseded_machine(claimant[1], legacy_machine)
        superseded_machines.add(legacy_machine)

    return [snapshot for _, snapshot in lineage_snapshots + retained_legacy]


def merge_opencode_snapshots(
    local_snapshot: dict[str, Any] | None,
) -> dict[str, dict[str, int]]:
    tzinfo = local_tzinfo()
    now = datetime.now(tzinfo)
    merged = windows_template()

    for snapshot in collect_opencode_snapshots(local_snapshot, tzinfo):
        snapshot_windows = snapshot["windows"]
        add_metric(merged["all"], snapshot_windows.get("all"))

        if snapshot.get("version") == SNAPSHOT_VERSION:
            buckets = snapshot.get("buckets", snapshot.get("events"))
            if not isinstance(buckets, list):
                continue
            for raw_bucket in buckets:
                parsed = parse_snapshot_event(raw_bucket, tzinfo)
                if parsed is None:
                    continue
                timestamp, metric = parsed
                if timestamp > now or timestamp < now - MAX_WINDOW:
                    continue
                for name, delta in WINDOWS.items():
                    if timestamp >= now - delta:
                        add_metric(merged[name], metric)
            continue

        generated_at = snapshot_generated_at(snapshot, tzinfo)
        if generated_at is None or not timedelta(0) <= now - generated_at <= LEGACY_SNAPSHOT_MAX_AGE:
            continue
        for name in WINDOWS:
            add_metric(merged[name], snapshot_windows.get(name))

    return merged


def write_opencode_snapshot(snapshot: dict[str, Any] | None) -> bool:
    if not snapshot:
        return True

    try:
        serialized = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n"
    except (TypeError, ValueError, RecursionError):
        return False
    if len(serialized.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        return False

    temporary_path: Path | None = None
    try:
        OPENCODE_SYNC_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_name = snapshot_source_id(snapshot) or snapshot["machine"]
        path = OPENCODE_SYNC_DIR / f"{snapshot_name}.json"
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=OPENCODE_SYNC_DIR,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
        temporary_path = None
        return True
    except (OSError, TypeError, ValueError):
        return False
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def iter_pi_session_records(path: Path):
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            first_line = handle.readline(MAX_PI_RECORD_BYTES + 1)
            if not first_line or len(first_line) > MAX_PI_RECORD_BYTES:
                return

            try:
                header = json.loads(first_line)
            except (ValueError, RecursionError):
                return

            if not isinstance(header, dict) or header.get("type") != "session":
                return

            session_id = str(header.get("id") or path)
            line_number = 1
            while True:
                raw_line = handle.readline(MAX_PI_RECORD_BYTES + 1)
                if not raw_line:
                    break
                line_number += 1
                if len(raw_line) > MAX_PI_RECORD_BYTES:
                    while raw_line and not raw_line.endswith("\n"):
                        raw_line = handle.readline(MAX_PI_RECORD_BYTES + 1)
                    continue
                try:
                    record = json.loads(raw_line)
                except (ValueError, RecursionError):
                    continue
                if isinstance(record, dict):
                    yield session_id, line_number, record
    except OSError:
        return


def build_pi_metrics() -> dict[str, dict[str, int]]:
    tzinfo = local_tzinfo()
    now = datetime.now(tzinfo)
    windows = windows_template()
    seen_records: set[tuple[str, str]] = set()

    if not PI_SESSIONS_DIR.is_dir():
        return windows

    for path in sorted(PI_SESSIONS_DIR.rglob("*.jsonl")):
        for session_id, line_number, record in iter_pi_session_records(path):
            if record.get("type") != "message":
                continue

            message = record.get("message")
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue

            metric = extract_pi_metric(message.get("usage"))
            if not has_token_usage(metric):
                continue

            record_id = str(record.get("id") or f"line-{line_number}")
            dedupe_key = (session_id, record_id)
            if dedupe_key in seen_records:
                continue
            seen_records.add(dedupe_key)

            timestamp = parse_timestamp(record.get("timestamp"), tzinfo)
            if timestamp is None:
                add_metric(windows["all"], metric)
                continue

            update_windows(windows, timestamp, now, metric)

    return windows


def combine_sources(
    opencode: dict[str, dict[str, int]],
    pi: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    combined = windows_template()
    for name in WINDOW_NAMES:
        add_metric(combined[name], opencode.get(name, {}))
        add_metric(combined[name], pi.get(name, {}))
    return combined


def format_share(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value == 0:
        return "0%"
    if value >= 10:
        return f"{value:.0f}%"
    return f"{value:.1f}%"


def format_cache_multiple(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}X"


def calc_share_percent(metric: dict[str, int], combined_metric: dict[str, int]) -> float | None:
    combined_visible = visible_tokens(combined_metric)
    if combined_visible <= 0:
        return None
    return visible_tokens(metric) / combined_visible * 100


def calc_cache_multiple(metric: dict[str, int]) -> float | None:
    input_tokens = int(metric.get("input", 0) or 0)
    if input_tokens <= 0:
        return None
    return int(metric.get("cache_read", 0) or 0) / input_tokens


LABEL_WIDTH = 10
VALUE_WIDTH = 8
SHARE_WIDTH = 5
CACHE_WIDTH = 5


def build_column_widths(
    combined: dict[str, dict[str, int]],
    opencode: dict[str, dict[str, int]],
    pi: dict[str, dict[str, int]],
) -> dict[str, int]:
    label_width = max(
        LABEL_WIDTH,
        *(len(WINDOW_LABELS[name]) for name in WINDOW_NAMES),
        len("Pi"),
        len("OpenCode"),
    )

    value_width = VALUE_WIDTH
    share_width = SHARE_WIDTH
    cache_width = CACHE_WIDTH

    for name in WINDOW_NAMES:
        combined_metric = combined[name]
        opencode_metric = opencode[name]
        pi_metric = pi[name]

        value_width = max(
            value_width,
            len(format_tokens(visible_tokens(combined_metric))),
            len(format_tokens(visible_tokens(opencode_metric))),
            len(format_tokens(visible_tokens(pi_metric))),
        )
        share_width = max(
            share_width,
            len(format_share(calc_share_percent(opencode_metric, combined_metric))),
            len(format_share(calc_share_percent(pi_metric, combined_metric))),
        )
        cache_width = max(
            cache_width,
            len(format_tokens(combined_metric["cache_read"])),
            len(format_cache_multiple(calc_cache_multiple(opencode_metric))),
            len(format_cache_multiple(calc_cache_multiple(pi_metric))),
        )

    return {
        "label": label_width,
        "value": value_width,
        "share": share_width,
        "cache": cache_width,
    }


def format_window_line(
    name: str,
    combined_metric: dict[str, int],
    widths: dict[str, int],
) -> str:
    return (
        f"{WINDOW_LABELS[name]:<{widths['label']}}"
        f"{format_tokens(visible_tokens(combined_metric)):>{widths['value']}}"
        f"   {'':>{widths['share']}}"
        f"   Cache {format_tokens(combined_metric['cache_read']):>{widths['cache']}}"
    )


def format_source_line(
    label: str,
    metric: dict[str, int],
    combined_metric: dict[str, int],
    widths: dict[str, int],
) -> str:
    return (
        f"{label:<{widths['label']}}"
        f"{format_tokens(visible_tokens(metric)):>{widths['value']}}"
        f"   {format_share(calc_share_percent(metric, combined_metric)):>{widths['share']}}"
        f"   Cache {format_cache_multiple(calc_cache_multiple(metric)):>{widths['cache']}}"
    )


def build_window_items(
    name: str,
    combined_metric: dict[str, int],
    opencode_metric: dict[str, int],
    pi_metric: dict[str, int],
    widths: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        {"text": format_window_line(name, combined_metric, widths)},
        {"text": format_source_line("Pi", pi_metric, combined_metric, widths)},
        {"text": format_source_line("OpenCode", opencode_metric, combined_metric, widths)},
    ]


def build_menu_payload(
    combined: dict[str, dict[str, int]],
    opencode: dict[str, dict[str, int]],
    pi: dict[str, dict[str, int]],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    widths = build_column_widths(combined, opencode, pi)
    items: list[dict[str, Any]] = []
    for index, name in enumerate(("last_1h", "last_24h", "last_7d", "last_30d", "all")):
        if index:
            items.append({"separator": True})
        items.extend(build_window_items(name, combined[name], opencode[name], pi[name], widths))

    for warning in warnings or []:
        items.extend(({"separator": True}, {"text": f"Warning: {warning}"}))
    return {
        "title": (
            f"{format_tokens(visible_tokens(combined['last_1h']))}"
            f" · {format_tokens(visible_tokens(combined['last_24h']))}"
            f"{' ⚠' if warnings else ''}"
        ),
        "items": items,
    }


def style_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    styled: list[dict[str, Any]] = []
    for item in items:
        cloned = dict(item)
        if not cloned.get("separator"):
            attrs = dict(cloned.get("attrs") or {})
            attrs.setdefault("font", "Menlo")
            # SwiftBar renders items without an action as disabled gray text.
            # Keep the refresh href on each row so the menu remains enabled and readable.
            attrs.setdefault("href", REFRESH_HREF)
            cloned["attrs"] = attrs
        children = cloned.get("children")
        if isinstance(children, list):
            cloned["children"] = style_items(children)
        styled.append(cloned)
    return styled


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    styled_payload = dict(payload)
    styled_payload["items"] = style_items(list(payload.get("items") or []))
    print(render_swiftbar_menu(styled_payload))


def render(
    combined: dict[str, dict[str, int]],
    opencode: dict[str, dict[str, int]],
    pi: dict[str, dict[str, int]],
    warnings: list[str] | None = None,
) -> None:
    emit(build_menu_payload(combined, opencode, pi, warnings))


def render_error(message: str) -> None:
    emit(
        {
            "title": "OpenCode + Pi Error",
            "items": [
                {"text": "Plugin failed"},
                {"text": message},
            ],
        }
    )


def has_any_source() -> bool:
    if OPENCODE_DB_PATH.exists():
        return True
    if OPENCODE_SYNC_DIR.exists() and next(OPENCODE_SYNC_DIR.glob("*.json"), None):
        return True
    if PI_SESSIONS_DIR.exists():
        return True
    return False


def main() -> int:
    if not has_any_source():
        render_error(
            "No data source found:"
            f" OpenCode DB={OPENCODE_DB_PATH};"
            f" OpenCode Sync={OPENCODE_SYNC_DIR};"
            f" Pi Sessions={PI_SESSIONS_DIR}"
        )
        return 1

    warnings: list[str] = []
    opencode_local_snapshot: dict[str, Any] | None = None

    try:
        opencode_local_snapshot = build_opencode_local_snapshot()
    except Exception as exc:  # Keep synced and Pi data available.
        warnings.append(f"local OpenCode unavailable: {exc}")

    try:
        opencode = merge_opencode_snapshots(opencode_local_snapshot)
    except Exception as exc:  # Keep Pi data available.
        warnings.append(f"synced OpenCode unavailable: {exc}")
        opencode = windows_template()

    try:
        pi = build_pi_metrics()
    except Exception as exc:  # Keep OpenCode data available.
        warnings.append(f"Pi unavailable: {exc}")
        pi = windows_template()

    if opencode_local_snapshot and not write_opencode_snapshot(opencode_local_snapshot):
        warnings.append("could not publish local OpenCode snapshot")

    combined = combine_sources(opencode, pi)
    render(combined, opencode, pi, warnings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
