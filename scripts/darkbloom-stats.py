#!/usr/bin/env -S uv run --no-project --no-python-downloads python
"""Archive and analyze local Darkbloom usage and model load history."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import plistlib
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_USAGE_FILE = Path("~/.darkbloom/usage-history.json").expanduser()
DEFAULT_LOADS_FILE = Path("~/.config/darkbloom/autopilot-load-history.json").expanduser()
DEFAULT_STATE_DIR = Path(
    os.environ.get("DARKBLOOM_STATS_DIR", "~/.local/state/darkbloom-stats")
).expanduser()

LAUNCH_AGENT_LABEL = "local.darkbloom-stats-sync"
LAUNCH_AGENT_PLIST = Path(f"~/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist").expanduser()
DEFAULT_SYNC_INTERVAL = 1800
USAGE_RING_BUFFER_CAPACITY = 4096
OFFICIAL_PRICING_URL = "https://api.darkbloom.dev/v1/pricing"

# Official rates from https://api.darkbloom.dev/v1/pricing (USD per 1M tokens).
DEFAULT_PRICING: dict[str, Any] = {
    "default_cached_input_ratio": 0.50,
    "models": {
        "EigenLabs/Qwen3.8-27B-4bit-mtp": {
            "input_per_1m": 0.0350,
            "cached_input_per_1m": 0.0175,
            "output_per_1m": 1.5000,
        },
        "qwen3.5-35b-a3b": {
            "input_per_1m": 0.0650,
            "cached_input_per_1m": 0.0325,
            "output_per_1m": 0.7500,
        },
        "qwen3.6-35b-a3b-vl-mtp-mxfp8": {
            "input_per_1m": 0.0500,
            "cached_input_per_1m": 0.0250,
            "output_per_1m": 0.7000,
        },
        "ternary-bonsai-2-27b": {
            "input_per_1m": 0.0750,
            "cached_input_per_1m": 0.0375,
            "output_per_1m": 0.5000,
        },
        "qwen3.8-flash-next": {
            "input_per_1m": 0.1300,
            "cached_input_per_1m": 0.0650,
            "output_per_1m": 0.4000,
        },
        "qwen3-vl-30b-a3b-instruct": {
            "input_per_1m": 0.0900,
            "cached_input_per_1m": 0.0450,
            "output_per_1m": 0.4000,
        },
        "RecursiveSI/flint-int4": {
            "input_per_1m": 0.0500,
            "cached_input_per_1m": 0.0250,
            "output_per_1m": 0.4000,
        },
        "nvidia-nemotron-3.5-super": {
            "input_per_1m": 0.0600,
            "cached_input_per_1m": 0.0100,
            "output_per_1m": 0.3500,
        },
        "mimo-v2.6-flash-mopd": {
            "input_per_1m": 0.1000,
            "cached_input_per_1m": 0.0028,
            "output_per_1m": 0.2800,
        },
        "gemma-4-26b": {
            "input_per_1m": 0.0500,
            "cached_input_per_1m": 0.0125,
            "output_per_1m": 0.1900,
        },
        "gemma-4-26b-qat-4bit": {
            "input_per_1m": 0.0500,
            "cached_input_per_1m": 0.0125,
            "output_per_1m": 0.1900,
        },
        "gemma-4-26b-8bit": {
            "input_per_1m": 0.0500,
            "cached_input_per_1m": 0.0125,
            "output_per_1m": 0.1900,
        },
        "glm-5.3-flash": {
            "input_per_1m": 0.0650,
            "cached_input_per_1m": 0.0120,
            "output_per_1m": 0.1800,
        },
        "Qwen3.5-9B": {
            "input_per_1m": 0.0800,
            "cached_input_per_1m": 0.0400,
            "output_per_1m": 0.1300,
        },
        "EigenLabs/Ternary-Bonsai-2-9B-MLX-2bit": {
            "input_per_1m": 0.0800,
            "cached_input_per_1m": 0.0400,
            "output_per_1m": 0.1300,
        },
        "thinkingmachines/Inkling-2-Mini": {
            "input_per_1m": 0.02625,
            "cached_input_per_1m": 0.013125,
            "output_per_1m": 0.1050,
        },
        "nvidia-nemotron-3.5-lightning": {
            "input_per_1m": 0.0200,
            "cached_input_per_1m": 0.0100,
            "output_per_1m": 0.0960,
        },
        "gpt-oss-20b": {
            "input_per_1m": 0.0153,
            "cached_input_per_1m": 0.00765,
            "output_per_1m": 0.0765,
        },
    },
}


def resolve_db_path(db_arg: str | None) -> Path:
    if db_arg:
        return Path(db_arg).expanduser()
    return DEFAULT_STATE_DIR / "archive.sqlite3"


def resolve_prices_path(prices_arg: str | None, db_path: Path) -> Path:
    if prices_arg:
        return Path(prices_arg).expanduser()
    return db_path.parent / "prices.json"


def load_pricing(prices_path: Path, write_default: bool = True) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    merged_models = {k: dict(v) for k, v in DEFAULT_PRICING["models"].items()}
    ratio = float(DEFAULT_PRICING["default_cached_input_ratio"])

    if not prices_path.exists():
        if write_default:
            try:
                prices_path.parent.mkdir(parents=True, exist_ok=True)
                prices_path.write_text(
                    json.dumps(DEFAULT_PRICING, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                warnings.append(f"could not write default prices to {prices_path}: {exc}")
        return {"default_cached_input_ratio": ratio, "models": merged_models}, warnings

    raw, err = load_json_file(prices_path)
    if err:
        warnings.append(err)
        return {"default_cached_input_ratio": ratio, "models": merged_models}, warnings
    if not isinstance(raw, dict):
        warnings.append(f"unexpected pricing format in {prices_path}: expected object")
        return {"default_cached_input_ratio": ratio, "models": merged_models}, warnings

    if raw.get("default_cached_input_ratio") is not None:
        try:
            ratio = float(raw["default_cached_input_ratio"])
        except (TypeError, ValueError):
            warnings.append(f"invalid default_cached_input_ratio in {prices_path}")

    raw_models = raw.get("models")
    if isinstance(raw_models, dict):
        for model_id, entry in raw_models.items():
            if not isinstance(entry, dict):
                continue
            cur = dict(merged_models.get(model_id, {}))
            for key in ("input_per_1m", "cached_input_per_1m", "output_per_1m"):
                if key in entry:
                    val = entry[key]
                    cur[key] = None if val is None else float(val)
            merged_models[model_id] = cur

    return {"default_cached_input_ratio": ratio, "models": merged_models}, warnings


def resolve_model_rate(model_id: str, pricing: dict[str, Any]) -> dict[str, Any] | None:
    entry = pricing["models"].get(model_id)
    if not entry or entry.get("input_per_1m") is None or entry.get("output_per_1m") is None:
        return None
    inp = float(entry["input_per_1m"])
    out = float(entry["output_per_1m"])
    cached_raw = entry.get("cached_input_per_1m")
    if cached_raw is None:
        cached = inp * float(pricing["default_cached_input_ratio"])
        cached_exact = False
    else:
        cached = float(cached_raw)
        cached_exact = True
    return {
        "input_per_1m": inp,
        "cached_input_per_1m": cached,
        "output_per_1m": out,
        "cached_exact": cached_exact,
    }


def calc_revenue_usd(
    model_id: str,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    pricing: dict[str, Any],
) -> dict[str, Any]:
    rate = resolve_model_rate(model_id, pricing)
    uncached = max(input_tokens - cached_input_tokens, 0)
    if rate is None:
        return {
            "priced": False,
            "uncached_input_tokens": uncached,
            "input_usd": 0.0,
            "cached_usd": 0.0,
            "output_usd": 0.0,
            "total_usd": 0.0,
            "rate": None,
        }
    input_usd = uncached * rate["input_per_1m"] / 1_000_000.0
    cached_usd = cached_input_tokens * rate["cached_input_per_1m"] / 1_000_000.0
    output_usd = output_tokens * rate["output_per_1m"] / 1_000_000.0
    return {
        "priced": True,
        "uncached_input_tokens": uncached,
        "input_usd": input_usd,
        "cached_usd": cached_usd,
        "output_usd": output_usd,
        "total_usd": input_usd + cached_usd + output_usd,
        "rate": rate,
    }


@contextmanager
def connect_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                completed_at REAL NOT NULL,
                session_started_at REAL,
                input_tokens INTEGER NOT NULL,
                cached_input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                reasoning_tokens INTEGER NOT NULL,
                exact INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_requests_completed_at
                ON requests(completed_at);
            CREATE INDEX IF NOT EXISTS idx_requests_model_completed_at
                ON requests(model, completed_at);

            CREATE TABLE IF NOT EXISTS model_loads (
                model_id TEXT NOT NULL,
                measured_at_ms INTEGER NOT NULL,
                load_ms INTEGER NOT NULL,
                weight_hash TEXT,
                PRIMARY KEY (model_id, measured_at_ms)
            );

            CREATE TABLE IF NOT EXISTS sync_runs (
                synced_at REAL NOT NULL,
                usage_source_count INTEGER NOT NULL,
                usage_inserted INTEGER NOT NULL,
                loads_inserted INTEGER NOT NULL,
                gap_detected INTEGER NOT NULL DEFAULT 0,
                gap_from REAL,
                gap_to REAL
            );
            """
        )
        with conn:
            yield conn
    finally:
        conn.close()


def load_json_file(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, f"missing: {path}"
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"unreadable {path}: {exc}"


def sync_data(
    db_path: Path,
    usage_file: Path = DEFAULT_USAGE_FILE,
    loads_file: Path = DEFAULT_LOADS_FILE,
    now: float | None = None,
) -> dict[str, Any]:
    synced_at = time.time() if now is None else now
    warnings: list[str] = []

    usage_raw, usage_err = load_json_file(usage_file)
    if usage_err:
        warnings.append(usage_err)
    elif not isinstance(usage_raw, list):
        warnings.append(f"unexpected usage format in {usage_file}: expected list")
        usage_raw = None

    loads_raw, loads_err = load_json_file(loads_file)
    if loads_err:
        warnings.append(loads_err)
    elif not isinstance(loads_raw, dict) or not isinstance(loads_raw.get("loads"), list):
        warnings.append(f"unexpected loads format in {loads_file}: expected object with 'loads' list")
        loads_raw = None

    usage_rows: list[dict[str, Any]] = usage_raw or []
    load_rows: list[dict[str, Any]] = loads_raw["loads"] if loads_raw else []

    with connect_db(db_path) as conn:
        prev_max_row = conn.execute("SELECT MAX(completed_at) AS max_ts FROM requests").fetchone()
        prev_max = prev_max_row["max_ts"] if prev_max_row else None

        valid_usage: list[tuple[Any, ...]] = []
        src_completed: list[float] = []
        for item in usage_rows:
            if not isinstance(item, dict):
                continue
            req_id = item.get("id")
            model = item.get("model")
            completed_at = item.get("completedAt")
            if not req_id or not model or completed_at is None:
                continue
            completed_f = float(completed_at)
            src_completed.append(completed_f)
            session_started = item.get("sessionStartedAt")
            valid_usage.append(
                (
                    str(req_id),
                    str(model),
                    completed_f,
                    float(session_started) if session_started is not None else None,
                    int(item.get("inputTokens") or 0),
                    int(item.get("cachedInputTokens") or 0),
                    int(item.get("outputTokens") or 0),
                    int(item.get("reasoningTokens") or 0),
                    1 if item.get("exact", True) else 0,
                )
            )

        gap_detected = False
        gap_from: float | None = None
        gap_to: float | None = None
        if prev_max is not None and len(src_completed) >= USAGE_RING_BUFFER_CAPACITY:
            src_min = min(src_completed)
            if src_min > prev_max:
                gap_detected = True
                gap_from = float(prev_max)
                gap_to = float(src_min)

        before_changes = conn.total_changes
        conn.executemany(
            """
            INSERT OR IGNORE INTO requests (
                id, model, completed_at, session_started_at,
                input_tokens, cached_input_tokens, output_tokens, reasoning_tokens, exact
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            valid_usage,
        )
        usage_inserted = conn.total_changes - before_changes

        valid_loads: list[tuple[Any, ...]] = []
        for item in load_rows:
            if not isinstance(item, dict):
                continue
            model_id = item.get("model_id")
            measured_at_ms = item.get("measured_at_ms")
            load_ms = item.get("load_ms")
            if not model_id or measured_at_ms is None or load_ms is None:
                continue
            valid_loads.append(
                (
                    str(model_id),
                    int(measured_at_ms),
                    int(load_ms),
                    str(item["weight_hash"]) if item.get("weight_hash") is not None else None,
                )
            )

        before_loads = conn.total_changes
        conn.executemany(
            """
            INSERT OR IGNORE INTO model_loads (
                model_id, measured_at_ms, load_ms, weight_hash
            ) VALUES (?, ?, ?, ?)
            """,
            valid_loads,
        )
        loads_inserted = conn.total_changes - before_loads

        conn.execute(
            """
            INSERT INTO sync_runs (
                synced_at, usage_source_count, usage_inserted, loads_inserted,
                gap_detected, gap_from, gap_to
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                synced_at,
                len(valid_usage),
                usage_inserted,
                loads_inserted,
                1 if gap_detected else 0,
                gap_from,
                gap_to,
            ),
        )

        totals = conn.execute(
            "SELECT COUNT(*) AS n, MIN(completed_at) AS min_ts, MAX(completed_at) AS max_ts FROM requests"
        ).fetchone()
        total_loads = conn.execute("SELECT COUNT(*) AS n FROM model_loads").fetchone()["n"]

    return {
        "db_path": str(db_path),
        "synced_at": synced_at,
        "usage_source_count": len(valid_usage),
        "usage_inserted": usage_inserted,
        "loads_source_count": len(valid_loads),
        "loads_inserted": loads_inserted,
        "gap_detected": gap_detected,
        "gap_from": gap_from,
        "gap_to": gap_to,
        "total_requests": totals["n"],
        "archive_from": totals["min_ts"],
        "archive_to": totals["max_ts"],
        "total_loads": total_loads,
        "warnings": warnings,
    }


def parse_window_seconds(spec: str) -> float | None:
    text = spec.strip().lower()
    if text == "all":
        return None
    units = {"m": 60, "h": 3600, "d": 86400}
    if len(text) < 2 or text[-1] not in units or not text[:-1].isdigit():
        raise ValueError(f"invalid window '{spec}'; use e.g. 30m, 1h, 6h, 24h, 7d, or all")
    value = int(text[:-1])
    if value <= 0:
        raise ValueError(f"window must be positive: '{spec}'")
    return float(value * units[text[-1]])


def build_report(
    db_path: Path,
    window: str = "24h",
    by_day: bool = False,
    now: float | None = None,
    prices_path: Path | None = None,
) -> dict[str, Any]:
    window_secs = parse_window_seconds(window)
    now_ts = time.time() if now is None else now
    cutoff = None if window_secs is None else (now_ts - window_secs)
    effective_prices_path = resolve_prices_path(str(prices_path) if prices_path else None, db_path)
    pricing, price_warnings = load_pricing(effective_prices_path)

    with connect_db(db_path) as conn:
        archive = conn.execute(
            "SELECT COUNT(*) AS n, MIN(completed_at) AS min_ts, MAX(completed_at) AS max_ts FROM requests"
        ).fetchone()

        if cutoff is None:
            model_rows = conn.execute(
                """
                SELECT
                    model,
                    COUNT(*) AS reqs,
                    SUM(input_tokens) AS input_tokens,
                    SUM(cached_input_tokens) AS cached_input_tokens,
                    SUM(output_tokens) AS output_tokens,
                    SUM(reasoning_tokens) AS reasoning_tokens,
                    MIN(completed_at) AS first_at,
                    MAX(completed_at) AS last_at
                FROM requests
                GROUP BY model
                ORDER BY reqs DESC, output_tokens DESC, model ASC
                """
            ).fetchall()
            gap_rows = conn.execute(
                "SELECT gap_from, gap_to FROM sync_runs WHERE gap_detected = 1 ORDER BY synced_at ASC"
            ).fetchall()
        else:
            model_rows = conn.execute(
                """
                SELECT
                    model,
                    COUNT(*) AS reqs,
                    SUM(input_tokens) AS input_tokens,
                    SUM(cached_input_tokens) AS cached_input_tokens,
                    SUM(output_tokens) AS output_tokens,
                    SUM(reasoning_tokens) AS reasoning_tokens,
                    MIN(completed_at) AS first_at,
                    MAX(completed_at) AS last_at
                FROM requests
                WHERE completed_at >= ?
                GROUP BY model
                ORDER BY reqs DESC, output_tokens DESC, model ASC
                """,
                (cutoff,),
            ).fetchall()
            gap_rows = conn.execute(
                """
                SELECT gap_from, gap_to FROM sync_runs
                WHERE gap_detected = 1 AND gap_to >= ?
                ORDER BY synced_at ASC
                """,
                (cutoff,),
            ).fetchall()

        load_rows = conn.execute(
            """
            SELECT
                model_id,
                COUNT(*) AS load_count,
                AVG(load_ms) AS avg_load_ms,
                MAX(measured_at_ms) AS last_measured_at_ms
            FROM model_loads
            GROUP BY model_id
            ORDER BY last_measured_at_ms DESC, model_id ASC
            """
        ).fetchall()

        latest_loads: dict[str, dict[str, Any]] = {}
        for row in load_rows:
            latest = conn.execute(
                """
                SELECT load_ms, weight_hash FROM model_loads
                WHERE model_id = ? AND measured_at_ms = ?
                """,
                (row["model_id"], row["last_measured_at_ms"]),
            ).fetchone()
            latest_loads[row["model_id"]] = {
                "model": row["model_id"],
                "load_count": row["load_count"],
                "last_load_ms": latest["load_ms"] if latest else None,
                "avg_load_ms": round(row["avg_load_ms"], 1),
                "last_measured_at": row["last_measured_at_ms"] / 1000.0,
            }

        daily: list[dict[str, Any]] = []
        if by_day:
            if cutoff is None:
                raw_reqs = conn.execute(
                    "SELECT model, completed_at, input_tokens, cached_input_tokens, output_tokens, reasoning_tokens FROM requests"
                ).fetchall()
            else:
                raw_reqs = conn.execute(
                    """
                    SELECT model, completed_at, input_tokens, cached_input_tokens, output_tokens, reasoning_tokens
                    FROM requests WHERE completed_at >= ?
                    """,
                    (cutoff,),
                ).fetchall()
            buckets: dict[tuple[str, str], dict[str, Any]] = {}
            for r in raw_reqs:
                day = datetime.fromtimestamp(r["completed_at"]).strftime("%Y-%m-%d")
                key = (day, r["model"])
                b = buckets.setdefault(
                    key,
                    {
                        "day": day,
                        "model": r["model"],
                        "requests": 0,
                        "input_tokens": 0,
                        "cached_input_tokens": 0,
                        "output_tokens": 0,
                        "reasoning_tokens": 0,
                    },
                )
                b["requests"] += 1
                b["input_tokens"] += r["input_tokens"]
                b["cached_input_tokens"] += r["cached_input_tokens"]
                b["output_tokens"] += r["output_tokens"]
                b["reasoning_tokens"] += r["reasoning_tokens"]
            for b in sorted(buckets.values(), key=lambda x: (x["day"], -x["requests"], x["model"])):
                rev = calc_revenue_usd(
                    b["model"],
                    b["input_tokens"],
                    b["cached_input_tokens"],
                    b["output_tokens"],
                    pricing,
                )
                b["uncached_input_tokens"] = rev["uncached_input_tokens"]
                b["cache_hit_pct"] = (
                    round(b["cached_input_tokens"] / b["input_tokens"] * 100.0, 1)
                    if b["input_tokens"]
                    else 0.0
                )
                b["input_usd"] = round(rev["input_usd"], 6)
                b["cached_usd"] = round(rev["cached_usd"], 6)
                b["output_usd"] = round(rev["output_usd"], 6)
                b["total_usd"] = round(rev["total_usd"], 6)
                b["priced"] = rev["priced"]
                daily.append(b)

    total_reqs = sum(r["reqs"] for r in model_rows)
    total_input = sum(r["input_tokens"] or 0 for r in model_rows)
    total_cached = sum(r["cached_input_tokens"] or 0 for r in model_rows)
    total_output = sum(r["output_tokens"] or 0 for r in model_rows)
    total_reasoning = sum(r["reasoning_tokens"] or 0 for r in model_rows)

    models_out: list[dict[str, Any]] = []
    tot_in_usd = 0.0
    tot_cache_usd = 0.0
    tot_out_usd = 0.0
    unpriced_models: list[str] = []

    for r in model_rows:
        reqs = r["reqs"]
        inp = r["input_tokens"] or 0
        cached = r["cached_input_tokens"] or 0
        out = r["output_tokens"] or 0
        reasoning = r["reasoning_tokens"] or 0
        span_sec = (r["last_at"] - r["first_at"]) if reqs >= 2 else 0.0
        span_min = span_sec / 60.0 if span_sec >= 1.0 else None
        span_hr = span_sec / 3600.0 if span_sec >= 60.0 else None
        load_info = latest_loads.get(r["model"])
        rev = calc_revenue_usd(r["model"], inp, cached, out, pricing)
        if rev["priced"]:
            tot_in_usd += rev["input_usd"]
            tot_cache_usd += rev["cached_usd"]
            tot_out_usd += rev["output_usd"]
        else:
            unpriced_models.append(r["model"])

        models_out.append(
            {
                "model": r["model"],
                "requests": reqs,
                "share_pct": round(reqs / total_reqs * 100.0, 1) if total_reqs else 0.0,
                "req_per_min": round(reqs / span_min, 2) if span_min else None,
                "output_tokens": out,
                "output_per_min": round(out / span_min, 1) if span_min else None,
                "input_tokens": inp,
                "uncached_input_tokens": rev["uncached_input_tokens"],
                "cached_input_tokens": cached,
                "cache_hit_pct": round(cached / inp * 100.0, 1) if inp else 0.0,
                "reasoning_tokens": reasoning,
                "first_at": r["first_at"],
                "last_at": r["last_at"],
                "active_span_minutes": round(span_sec / 60.0, 1),
                "last_load_ms": load_info["last_load_ms"] if load_info else None,
                "priced": rev["priced"],
                "unit_prices": rev["rate"],
                "input_usd": round(rev["input_usd"], 6),
                "cached_usd": round(rev["cached_usd"], 6),
                "output_usd": round(rev["output_usd"], 6),
                "total_usd": round(rev["total_usd"], 6),
                "usd_per_hour": round(rev["total_usd"] / span_hr, 4) if (rev["priced"] and span_hr) else None,
            }
        )

    models_out.sort(key=lambda m: (-m["total_usd"], -m["requests"], m["model"]))
    tot_usd = tot_in_usd + tot_cache_usd + tot_out_usd
    win_first = min((m["first_at"] for m in models_out), default=None)
    win_last = max((m["last_at"] for m in models_out), default=None)
    win_span_hr = (
        (win_last - win_first) / 3600.0
        if (win_first is not None and win_last is not None and (win_last - win_first) >= 60.0)
        else None
    )

    return {
        "db_path": str(db_path),
        "prices_path": str(effective_prices_path),
        "price_warnings": price_warnings,
        "unpriced_models": unpriced_models,
        "generated_at": now_ts,
        "window": window,
        "window_start": cutoff,
        "archive": {
            "total_requests": archive["n"],
            "from": archive["min_ts"],
            "to": archive["max_ts"],
        },
        "totals": {
            "requests": total_reqs,
            "input_tokens": total_input,
            "uncached_input_tokens": max(total_input - total_cached, 0),
            "cached_input_tokens": total_cached,
            "cache_hit_pct": round(total_cached / total_input * 100.0, 1) if total_input else 0.0,
            "output_tokens": total_output,
            "reasoning_tokens": total_reasoning,
            "input_usd": round(tot_in_usd, 6),
            "cached_usd": round(tot_cache_usd, 6),
            "output_usd": round(tot_out_usd, 6),
            "total_usd": round(tot_usd, 6),
            "usd_per_hour": round(tot_usd / win_span_hr, 4) if win_span_hr else None,
        },
        "models": models_out,
        "loads": list(latest_loads.values()),
        "gaps": [{"from": g["gap_from"], "to": g["gap_to"]} for g in gap_rows],
        "daily": daily,
    }


def fmt_count(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 10_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,}"


def fmt_usd(v: float | None, priced: bool = True) -> str:
    if not priced or v is None:
        return "-"
    if v >= 10.0:
        return f"${v:.2f}"
    if v >= 0.1:
        return f"${v:.3f}"
    return f"${v:.4f}"


def fmt_ts(ts: float | None) -> str:
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def fmt_ms(ms: float | int | None) -> str:
    if ms is None:
        return "-"
    return f"{ms / 1000.0:.1f}s"


def render_table(headers: list[str], rows: list[list[str]], right_align: set[int]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            parts.append(cell.rjust(widths[i]) if i in right_align else cell.ljust(widths[i]))
        return "  ".join(parts).rstrip()

    lines = [fmt_row(headers), "  ".join("-" * w for w in widths)]
    lines.extend(fmt_row(r) for r in rows)
    return "\n".join(lines)


def format_report(report: dict[str, Any], sync_result: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    arc = report["archive"]
    tot = report["totals"]

    lines.append(f"Darkbloom Usage Report (window: {report['window']})")
    lines.append(
        f"Archive: {arc['total_requests']:,} requests ({fmt_ts(arc['from'])} -> {fmt_ts(arc['to'])})  [{report['db_path']}]"
    )
    lines.append(f"Prices:  {report['prices_path']}")
    if sync_result is not None:
        lines.append(
            f"Sync: +{sync_result['usage_inserted']} reqs, +{sync_result['loads_inserted']} loads "
            f"(source: {sync_result['usage_source_count']} reqs, {sync_result['loads_source_count']} loads)"
        )
        for w in sync_result["warnings"]:
            lines.append(f"Warning: {w}")
    for w in report.get("price_warnings", []):
        lines.append(f"Warning: {w}")
    if report.get("unpriced_models"):
        lines.append(f"Warning: missing unit prices for {', '.join(report['unpriced_models'])}")

    if report["gaps"]:
        lines.append(
            f"Warning: {len(report['gaps'])} ring-buffer gap(s) detected in window (latest: "
            f"{fmt_ts(report['gaps'][-1]['from'])} -> {fmt_ts(report['gaps'][-1]['to'])}); "
            "shorten sync interval if needed."
        )

    lines.append(
        f"Window totals: {tot['requests']:,} reqs | in {fmt_count(tot['uncached_input_tokens'])} + "
        f"cache {fmt_count(tot['cached_input_tokens'])} ({tot['cache_hit_pct']:.1f}%) | "
        f"out {fmt_count(tot['output_tokens'])} (reason {fmt_count(tot['reasoning_tokens'])})"
    )
    rate_suffix = f" (~${tot['usd_per_hour']:.3f}/h)" if tot["usd_per_hour"] is not None else ""
    lines.append(
        f"Est inference: {fmt_usd(tot['total_usd'])}{rate_suffix} "
        f"[in {fmt_usd(tot['input_usd'])} + cache {fmt_usd(tot['cached_usd'])} + out {fmt_usd(tot['output_usd'])}; excl. base rewards]"
    )
    lines.append("")

    if report["models"]:
        headers = [
            "Model",
            "Reqs",
            "In Tok",
            "Cache%",
            "Out Tok",
            "In$",
            "Cache$",
            "Out$",
            "Est$",
            "$/h*",
            "Load",
        ]
        table_rows = []
        for m in report["models"]:
            priced = m["priced"]
            rate_str = f"${m['usd_per_hour']:.3f}" if m["usd_per_hour"] is not None else "-"
            table_rows.append(
                [
                    m["model"],
                    f"{m['requests']:,}",
                    fmt_count(m["uncached_input_tokens"]),
                    f"{m['cache_hit_pct']:.1f}%",
                    fmt_count(m["output_tokens"]),
                    fmt_usd(m["input_usd"], priced),
                    fmt_usd(m["cached_usd"], priced),
                    fmt_usd(m["output_usd"], priced),
                    fmt_usd(m["total_usd"], priced),
                    rate_str,
                    fmt_ms(m["last_load_ms"]),
                ]
            )
        lines.append(render_table(headers, table_rows, {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}))
        lines.append(
            "* In Tok = uncached input tokens; $/h* is measured over each model's active span in the window; Est$ excludes base rewards."
        )
    else:
        lines.append("No requests recorded in this window.")

    if report["daily"]:
        lines.append("")
        lines.append("By day:")
        day_headers = ["Day", "Model", "Reqs", "In Tok", "Cache%", "Out Tok", "In$", "Cache$", "Out$", "Est$"]
        day_rows = [
            [
                d["day"],
                d["model"],
                f"{d['requests']:,}",
                fmt_count(d["uncached_input_tokens"]),
                f"{d['cache_hit_pct']:.1f}%",
                fmt_count(d["output_tokens"]),
                fmt_usd(d["input_usd"], d["priced"]),
                fmt_usd(d["cached_usd"], d["priced"]),
                fmt_usd(d["output_usd"], d["priced"]),
                fmt_usd(d["total_usd"], d["priced"]),
            ]
            for d in report["daily"]
        ]
        lines.append(render_table(day_headers, day_rows, {2, 3, 4, 5, 6, 7, 8, 9}))

    if report["loads"]:
        lines.append("")
        lines.append("Model load history (autopilot-load-history):")
        load_headers = ["Model", "Loads", "Last Load", "Avg Load", "Last Measured"]
        load_rows = [
            [
                l["model"],
                str(l["load_count"]),
                fmt_ms(l["last_load_ms"]),
                fmt_ms(l["avg_load_ms"]),
                fmt_ts(l["last_measured_at"]),
            ]
            for l in report["loads"]
        ]
        lines.append(render_table(load_headers, load_rows, {1, 2, 3}))

    return "\n".join(lines)


def refresh_official_pricing(prices_path: Path, url: str = OFFICIAL_PRICING_URL) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("prices"), list):
        raise ValueError(f"unexpected response from {url}")

    models: dict[str, dict[str, float]] = {}
    for item in raw["prices"]:
        if not isinstance(item, dict) or not item.get("model"):
            continue
        models[str(item["model"])] = {
            "input_per_1m": float(item["input_price"]) / 1_000_000.0,
            "cached_input_per_1m": float(item["cache_read_price"]) / 1_000_000.0,
            "output_per_1m": float(item["output_price"]) / 1_000_000.0,
        }
    fb_in = float(raw.get("fallback_input_price") or 50000)
    fb_cache = float(raw.get("fallback_cache_read_price") or 25000)
    ratio = round(fb_cache / fb_in, 4) if fb_in else 0.50
    pricing = {
        "source": url,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "default_cached_input_ratio": ratio,
        "models": dict(sorted(models.items())),
    }
    prices_path.parent.mkdir(parents=True, exist_ok=True)
    prices_path.write_text(json.dumps(pricing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pricing


def format_prices_table(prices_path: Path, pricing: dict[str, Any]) -> str:
    headers = ["Model", "Input/1M", "Cached/1M", "Cache%", "Output/1M"]
    rows: list[list[str]] = []
    for model_id in sorted(pricing["models"].keys()):
        rate = resolve_model_rate(model_id, pricing)
        if not rate:
            continue
        pct = (rate["cached_input_per_1m"] / rate["input_per_1m"] * 100.0) if rate["input_per_1m"] else 0.0
        rows.append(
            [
                model_id,
                f"${rate['input_per_1m']:.4f}",
                f"${rate['cached_input_per_1m']:.4f}",
                f"{pct:.1f}%",
                f"${rate['output_per_1m']:.4f}",
            ]
        )
    lines = [
        f"Unit Prices ({prices_path})",
        "",
        render_table(headers, rows, {1, 2, 3, 4}),
    ]
    return "\n".join(lines)


def build_launch_agent_plist(
    script_path: Path,
    db_path: Path,
    usage_file: Path,
    loads_file: Path,
    interval: int,
) -> bytes:
    uv_bin = shutil.which("uv") or "/opt/homebrew/bin/uv"
    log_path = db_path.parent / "sync.log"
    payload = {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [
            uv_bin,
            "run",
            "--no-project",
            "--no-python-downloads",
            "python",
            str(script_path.resolve()),
            "--db",
            str(db_path.resolve()),
            "--usage-file",
            str(usage_file.resolve()),
            "--loads-file",
            str(loads_file.resolve()),
            "sync",
        ],
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        },
        "StartInterval": interval,
        "RunAtLoad": True,
        "StandardOutPath": str(log_path),
        "StandardErrorPath": str(log_path),
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)


def cmd_schedule(args: argparse.Namespace, db_path: Path, usage_file: Path, loads_file: Path) -> int:
    action = args.schedule_action or "status"
    script_path = Path(__file__).resolve()
    uid = os.getuid()
    domain = f"gui/{uid}"
    service = f"{domain}/{LAUNCH_AGENT_LABEL}"

    if action == "print":
        data = build_launch_agent_plist(script_path, db_path, usage_file, loads_file, args.interval)
        sys.stdout.write(data.decode("utf-8"))
        return 0

    if action == "status":
        installed = LAUNCH_AGENT_PLIST.exists()
        loaded = (
            subprocess.run(
                ["/bin/launchctl", "print", service],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
        print(f"LaunchAgent: {LAUNCH_AGENT_LABEL}")
        print(f"  plist: {LAUNCH_AGENT_PLIST} ({'installed' if installed else 'not installed'})")
        print(f"  state: {'loaded' if loaded else 'not loaded'}")
        print(f"  db:    {db_path}")
        if db_path.exists():
            with connect_db(db_path) as conn:
                last = conn.execute(
                    "SELECT synced_at, usage_inserted, loads_inserted FROM sync_runs ORDER BY synced_at DESC LIMIT 1"
                ).fetchone()
            if last:
                print(
                    f"  last sync: {fmt_ts(last['synced_at'])} "
                    f"(+{last['usage_inserted']} reqs, +{last['loads_inserted']} loads)"
                )
        return 0

    if action == "install":
        if args.interval < 60:
            print("error: --interval must be at least 60 seconds", file=sys.stderr)
            return 2
        db_path.parent.mkdir(parents=True, exist_ok=True)
        LAUNCH_AGENT_PLIST.parent.mkdir(parents=True, exist_ok=True)
        data = build_launch_agent_plist(script_path, db_path, usage_file, loads_file, args.interval)
        LAUNCH_AGENT_PLIST.write_bytes(data)
        subprocess.run(["/usr/bin/plutil", "-lint", str(LAUNCH_AGENT_PLIST)], check=True)
        subprocess.run(
            ["/bin/launchctl", "bootout", service],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(["/bin/launchctl", "bootstrap", domain, str(LAUNCH_AGENT_PLIST)], check=True)
        print(f"Installed and loaded {LAUNCH_AGENT_PLIST} (interval: {args.interval}s).")
        return 0

    if action == "uninstall":
        subprocess.run(
            ["/bin/launchctl", "bootout", service],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if LAUNCH_AGENT_PLIST.exists():
            LAUNCH_AGENT_PLIST.unlink()
        print(f"Uninstalled {LAUNCH_AGENT_PLIST}.")
        return 0

    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Archive and summarize Darkbloom usage-history and model load history.",
    )
    parser.add_argument("--db", help=f"SQLite archive path (default: {DEFAULT_STATE_DIR / 'archive.sqlite3'})")
    parser.add_argument("--prices-file", help=f"Unit price JSON path (default: {DEFAULT_STATE_DIR / 'prices.json'})")
    parser.add_argument("--usage-file", default=str(DEFAULT_USAGE_FILE), help="Path to usage-history.json")
    parser.add_argument("--loads-file", default=str(DEFAULT_LOADS_FILE), help="Path to autopilot-load-history.json")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("sync", help="Incrementally import new records into the local SQLite archive")

    rep = sub.add_parser("report", help="Print model usage, revenue breakdown, and load summary (default command)")
    rep.add_argument("--window", default="24h", help="Lookback window: 30m, 1h, 6h, 24h, 7d, all (default: 24h)")
    rep.add_argument("--by-day", action="store_true", help="Include per-day breakdown")
    rep.add_argument("--no-sync", action="store_true", help="Read existing archive without syncing first")
    rep.add_argument("--json", action="store_true", help="Emit JSON instead of formatted tables")

    pr = sub.add_parser("prices", help="Show active unit prices (or --refresh from official Darkbloom API)")
    pr.add_argument("--refresh", action="store_true", help=f"Fetch latest public rates from {OFFICIAL_PRICING_URL}")
    pr.add_argument("--json", action="store_true", help="Emit pricing JSON")

    sched = sub.add_parser("schedule", help="Manage user-level LaunchAgent for periodic sync (no sudo)")
    sched.add_argument(
        "schedule_action",
        nargs="?",
        choices=["status", "print", "install", "uninstall"],
        default="status",
    )
    sched.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_SYNC_INTERVAL,
        help=f"Sync interval in seconds (default: {DEFAULT_SYNC_INTERVAL})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path = resolve_db_path(args.db)
    prices_path = resolve_prices_path(args.prices_file, db_path)
    usage_file = Path(args.usage_file).expanduser()
    loads_file = Path(args.loads_file).expanduser()

    cmd = args.command or "report"

    if cmd == "sync":
        res = sync_data(db_path, usage_file, loads_file)
        print(
            f"[{fmt_ts(res['synced_at'])}] +{res['usage_inserted']} reqs, +{res['loads_inserted']} loads "
            f"(total: {res['total_requests']:,} reqs, {res['total_loads']} loads)"
        )
        if res["gap_detected"]:
            print(
                f"Warning: ring-buffer gap detected ({fmt_ts(res['gap_from'])} -> {fmt_ts(res['gap_to'])})",
                file=sys.stderr,
            )
        for w in res["warnings"]:
            print(f"Warning: {w}", file=sys.stderr)
        return 0

    if cmd == "prices":
        if getattr(args, "refresh", False):
            try:
                pricing = refresh_official_pricing(prices_path)
            except (urllib.error.URLError, ValueError, OSError) as exc:
                print(f"error: failed to refresh pricing: {exc}", file=sys.stderr)
                return 1
            warnings: list[str] = []
        else:
            pricing, warnings = load_pricing(prices_path)
        for w in warnings:
            print(f"Warning: {w}", file=sys.stderr)
        if getattr(args, "json", False):
            print(json.dumps(pricing, indent=2, ensure_ascii=False))
        else:
            print(format_prices_table(prices_path, pricing))
        return 0

    if cmd == "report":
        no_sync = getattr(args, "no_sync", False)
        window = getattr(args, "window", "24h")
        by_day = getattr(args, "by_day", False)
        as_json = getattr(args, "json", False)

        sync_res = None if no_sync else sync_data(db_path, usage_file, loads_file)
        try:
            report = build_report(db_path, window=window, by_day=by_day, prices_path=prices_path)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if as_json:
            payload = {"report": report, "sync": sync_res}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(format_report(report, sync_res))
        return 0

    if cmd == "schedule":
        return cmd_schedule(args, db_path, usage_file, loads_file)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
