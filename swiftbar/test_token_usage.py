from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("token-usage.10m.py")
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("token_usage", MODULE_PATH)
assert SPEC and SPEC.loader
TOKEN_USAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOKEN_USAGE)


def metric(input_tokens: int) -> dict[str, int]:
    value = TOKEN_USAGE.metric_template()
    value["total"] = input_tokens
    value["input"] = input_tokens
    value["assistant_messages"] = 1
    return value


def snapshot(
    *,
    version: int,
    machine: str,
    generated_at: datetime,
    all_input: int,
    finite_input: int = 0,
    events: list[list[int]] | None = None,
) -> dict[str, object]:
    windows = TOKEN_USAGE.windows_template()
    windows["all"] = metric(all_input)
    for name in TOKEN_USAGE.WINDOWS:
        windows[name] = metric(finite_input)
    value: dict[str, object] = {
        "version": version,
        "source": "opencode",
        "machine": machine,
        "generated_at": generated_at.isoformat(),
        "generated_at_epoch_ms": int(generated_at.timestamp() * 1000),
        "windows": windows,
    }
    if events is not None:
        value["events"] = events
    return value


class TokenUsageTests(unittest.TestCase):
    def test_future_records_only_affect_all_time(self) -> None:
        now = datetime.now().astimezone()
        windows = TOKEN_USAGE.windows_template()

        TOKEN_USAGE.update_windows(windows, now + timedelta(hours=1), now, metric(7))

        self.assertEqual(windows["all"]["input"], 7)
        self.assertTrue(all(windows[name]["input"] == 0 for name in TOKEN_USAGE.WINDOWS))

    def test_stale_legacy_snapshot_does_not_poison_rolling_windows(self) -> None:
        now = datetime.now().astimezone()
        stale = snapshot(
            version=3,
            machine="offline",
            generated_at=now - timedelta(days=60),
            all_input=100,
            finite_input=100,
        )

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "offline.json").write_text(json.dumps(stale), encoding="utf-8")
            with patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)):
                merged = TOKEN_USAGE.merge_opencode_snapshots(None)

        self.assertEqual(merged["all"]["input"], 100)
        self.assertTrue(all(merged[name]["input"] == 0 for name in TOKEN_USAGE.WINDOWS))

    def test_v4_events_rebuild_windows_when_machine_is_offline(self) -> None:
        now = datetime.now().astimezone()
        recent_event = TOKEN_USAGE.serialize_snapshot_event(now - timedelta(days=20), metric(25))
        old_event = TOKEN_USAGE.serialize_snapshot_event(now - timedelta(days=40), metric(75))
        offline = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="offline",
            generated_at=now - timedelta(days=10),
            all_input=100,
            events=[recent_event, old_event],
        )

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "offline.json").write_text(json.dumps(offline), encoding="utf-8")
            with patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)):
                merged = TOKEN_USAGE.merge_opencode_snapshots(None)

        self.assertEqual(merged["all"]["input"], 100)
        self.assertEqual(merged["last_30d"]["input"], 25)
        self.assertEqual(merged["last_7d"]["input"], 0)

    def test_explicit_rename_migration_survives_later_history_growth(self) -> None:
        now = datetime.now().astimezone()
        older = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="old-name",
            generated_at=now - timedelta(hours=1),
            all_input=100,
            events=[],
        )
        newer = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="new-name",
            generated_at=now,
            all_input=200,
            events=[],
        )

        newer["source_id"] = "stable-lineage"
        newer["supersedes"] = ["old-name"]

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "copy-a.json").write_text(json.dumps(older), encoding="utf-8")
            Path(directory, "unrelated.json").write_text('{"windows": {}}', encoding="utf-8")
            with patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)):
                merged = TOKEN_USAGE.merge_opencode_snapshots(newer)
                self.assertTrue(TOKEN_USAGE.write_opencode_snapshot(newer))
                rebuilt = snapshot(
                    version=TOKEN_USAGE.SNAPSHOT_VERSION,
                    machine="new-name",
                    generated_at=now + timedelta(minutes=1),
                    all_input=300,
                    events=[],
                )
                rebuilt["source_id"] = "stable-lineage"
                rebuilt["supersedes"] = sorted(
                    TOKEN_USAGE.inherited_superseded_machines("stable-lineage")
                )
                merged_after_growth = TOKEN_USAGE.merge_opencode_snapshots(rebuilt)

        self.assertEqual(merged["all"]["input"], 200)
        self.assertEqual(merged_after_growth["all"]["input"], 300)

    def test_explicit_migration_does_not_claim_unrelated_equal_legacy_snapshot(self) -> None:
        now = datetime.now().astimezone()
        migrated = snapshot(
            version=3,
            machine="old-name",
            generated_at=now,
            all_input=100,
        )
        unrelated = snapshot(
            version=3,
            machine="other-machine",
            generated_at=now,
            all_input=100,
        )
        current = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="new-name",
            generated_at=now,
            all_input=100,
            events=[],
        )
        current["source_id"] = "stable-lineage"
        current["supersedes"] = ["old-name"]

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "migrated.json").write_text(json.dumps(migrated), encoding="utf-8")
            Path(directory, "unrelated.json").write_text(json.dumps(unrelated), encoding="utf-8")
            with patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)):
                merged = TOKEN_USAGE.merge_opencode_snapshots(current)

        self.assertEqual(merged["all"]["input"], 200)

    def test_stable_source_id_deduplicates_renamed_growing_database(self) -> None:
        now = datetime.now().astimezone()
        older = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="old-name",
            generated_at=now - timedelta(hours=1),
            all_input=100,
            events=[],
        )
        newer = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="new-name",
            generated_at=now,
            all_input=200,
            events=[],
        )
        older["source_id"] = "stable-lineage"
        newer["source_id"] = "stable-lineage"

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "old.json").write_text(json.dumps(older), encoding="utf-8")
            Path(directory, "new.json").write_text(json.dumps(newer), encoding="utf-8")
            with patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)):
                merged = TOKEN_USAGE.merge_opencode_snapshots(None)

        self.assertEqual(merged["all"]["input"], 200)

    def test_v4_supersedes_diverged_v3_snapshot_for_same_machine(self) -> None:
        now = datetime.now().astimezone()
        legacy = snapshot(
            version=3,
            machine="same-machine",
            generated_at=now,
            all_input=100,
        )
        current = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="same-machine",
            generated_at=now,
            all_input=200,
            events=[],
        )
        current["source_id"] = "stable-lineage"

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "legacy.json").write_text(json.dumps(legacy), encoding="utf-8")
            Path(directory, "current.json").write_text(json.dumps(current), encoding="utf-8")
            with patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)):
                merged = TOKEN_USAGE.merge_opencode_snapshots(None)

        self.assertEqual(merged["all"]["input"], 200)

    def test_distinct_source_ids_with_equal_totals_are_both_counted(self) -> None:
        now = datetime.now().astimezone()
        first = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="first",
            generated_at=now,
            all_input=100,
            events=[TOKEN_USAGE.serialize_snapshot_event(now, metric(3))],
        )
        second = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="second",
            generated_at=now,
            all_input=100,
            events=[TOKEN_USAGE.serialize_snapshot_event(now, metric(5))],
        )
        first["source_id"] = "first-lineage"
        second["source_id"] = "second-lineage"

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "first.json").write_text(json.dumps(first), encoding="utf-8")
            Path(directory, "second.json").write_text(json.dumps(second), encoding="utf-8")
            with patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)):
                merged = TOKEN_USAGE.merge_opencode_snapshots(None)

        self.assertEqual(merged["all"]["input"], 200)
        self.assertEqual(merged["last_1h"]["input"], 8)

    def test_persisted_source_id_survives_oldest_message_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory, "opencode.db")
            source_id_path = Path(directory, "source-id")
            connection = sqlite3.connect(database_path)
            connection.execute("CREATE TABLE message (id TEXT PRIMARY KEY, time_created INTEGER)")
            connection.execute("INSERT INTO message VALUES ('first', 1)")
            connection.commit()

            with (
                patch.object(TOKEN_USAGE, "OPENCODE_DB_PATH", database_path),
                patch.object(TOKEN_USAGE, "OPENCODE_SOURCE_ID_PATH", source_id_path),
            ):
                original = TOKEN_USAGE.opencode_source_id(connection)
                connection.execute("DELETE FROM message")
                connection.execute("INSERT INTO message VALUES ('replacement', 2)")
                connection.commit()
                after_prune = TOKEN_USAGE.opencode_source_id(connection)
            connection.close()

        self.assertEqual(after_prune, original)

    def test_source_id_is_not_returned_when_persistence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory, "opencode.db")
            blocked_parent = Path(directory, "blocked")
            blocked_parent.write_text("not a directory", encoding="utf-8")
            connection = sqlite3.connect(database_path)
            connection.execute("CREATE TABLE message (id TEXT PRIMARY KEY, time_created INTEGER)")
            connection.execute("INSERT INTO message VALUES ('first', 1)")
            connection.commit()

            with (
                patch.object(TOKEN_USAGE, "OPENCODE_DB_PATH", database_path),
                patch.object(
                    TOKEN_USAGE,
                    "OPENCODE_SOURCE_ID_PATH",
                    blocked_parent / "source-id",
                ),
            ):
                with self.assertRaises(OSError):
                    TOKEN_USAGE.opencode_source_id(connection)
            connection.close()

    def test_local_snapshot_groups_recent_messages_into_minute_buckets(self) -> None:
        now_ms = int(datetime.now().astimezone().timestamp() * 1000)
        minute_start = (
            now_ms // TOKEN_USAGE.SNAPSHOT_BUCKET_MS * TOKEN_USAGE.SNAPSHOT_BUCKET_MS
            - TOKEN_USAGE.SNAPSHOT_BUCKET_MS
        )

        def assistant(amount: int) -> str:
            return json.dumps(
                {"role": "assistant", "tokens": {"total": amount, "input": amount}}
            )

        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory, "opencode.db")
            source_id_path = Path(directory, "source-id")
            connection = sqlite3.connect(database_path)
            connection.execute(
                "CREATE TABLE message (id TEXT PRIMARY KEY, time_created INTEGER, data TEXT)"
            )
            connection.executemany(
                "INSERT INTO message VALUES (?, ?, ?)",
                [
                    ("one", minute_start + 1_000, assistant(1)),
                    ("two", minute_start + 2_000, assistant(2)),
                    ("user", minute_start + 3_000, json.dumps({"role": "user"})),
                ],
            )
            connection.commit()
            connection.close()

            with (
                patch.object(TOKEN_USAGE, "OPENCODE_DB_PATH", database_path),
                patch.object(TOKEN_USAGE, "OPENCODE_SOURCE_ID_PATH", source_id_path),
                patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory, "sync")),
            ):
                value = TOKEN_USAGE.build_opencode_local_snapshot()

        self.assertIsNotNone(value)
        self.assertEqual(len(value["buckets"]), 1)
        self.assertEqual(value["buckets"][0][2], 3)
        self.assertEqual(value["windows"]["all"]["input"], 3)

    def test_snapshot_writer_refuses_unreadable_oversized_output(self) -> None:
        now = datetime.now().astimezone()
        value = snapshot(
            version=TOKEN_USAGE.SNAPSHOT_VERSION,
            machine="machine",
            generated_at=now,
            all_input=1,
            events=[],
        )
        value["source_id"] = "lineage"

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(TOKEN_USAGE, "OPENCODE_SYNC_DIR", Path(directory)),
                patch.object(TOKEN_USAGE, "MAX_SNAPSHOT_BYTES", 10),
            ):
                written = TOKEN_USAGE.write_opencode_snapshot(value)

            self.assertFalse(written)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_pi_reader_skips_bad_shapes_and_keeps_usage_without_total(self) -> None:
        now = datetime.now().astimezone()
        records = [
            {"type": "session", "id": "session-1"},
            {
                "type": "message",
                "id": "valid",
                "timestamp": now.isoformat(),
                "message": {"role": "assistant", "usage": {"input": 5}},
            },
            {
                "type": "message",
                "id": "future",
                "timestamp": (now + timedelta(days=1)).isoformat(),
                "message": {"role": "assistant", "usage": {"input": 1}},
            },
            {
                "type": "message",
                "id": "bad-time",
                "timestamp": 123,
                "message": {"role": "assistant", "usage": {"input": 2}},
            },
            {"type": "message", "id": "bad-message", "message": []},
            {"type": "message", "id": "bad-usage", "message": {"role": "assistant", "usage": []}},
            [],
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "session.jsonl")
            path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
            with patch.object(TOKEN_USAGE, "PI_SESSIONS_DIR", Path(directory)):
                windows = TOKEN_USAGE.build_pi_metrics()

        self.assertEqual(windows["all"]["input"], 8)
        self.assertEqual(windows["last_1h"]["input"], 5)

    def test_local_sqlite_failure_does_not_hide_other_sources(self) -> None:
        pi = TOKEN_USAGE.windows_template()
        pi["all"] = metric(11)
        rendered: dict[str, object] = {}

        def capture_render(combined, opencode, pi_metrics, warnings=None):
            rendered.update(combined=combined, opencode=opencode, pi=pi_metrics, warnings=warnings)

        with (
            patch.object(TOKEN_USAGE, "has_any_source", return_value=True),
            patch.object(TOKEN_USAGE, "build_opencode_local_snapshot", side_effect=Exception("locked")),
            patch.object(
                TOKEN_USAGE,
                "merge_opencode_snapshots",
                return_value=TOKEN_USAGE.windows_template(),
            ),
            patch.object(TOKEN_USAGE, "build_pi_metrics", return_value=pi),
            patch.object(TOKEN_USAGE, "render", side_effect=capture_render),
            patch.object(TOKEN_USAGE, "write_opencode_snapshot"),
        ):
            result = TOKEN_USAGE.main()

        self.assertEqual(result, 0)
        self.assertEqual(rendered["combined"]["all"]["input"], 11)
        self.assertIn("local OpenCode unavailable", rendered["warnings"][0])

    def test_menu_items_are_actionable_without_visible_refresh_row(self) -> None:
        windows = TOKEN_USAGE.windows_template()
        payload = TOKEN_USAGE.build_menu_payload(windows, windows, windows)
        styled = TOKEN_USAGE.style_items(payload["items"])
        data_item = next(item for item in styled if not item.get("separator"))
        self.assertNotIn("color", data_item["attrs"])
        self.assertEqual(data_item["attrs"]["href"], TOKEN_USAGE.REFRESH_HREF)
        self.assertFalse(any(item.get("text") == "Refresh" for item in styled))

    def test_malformed_numbers_are_clamped_instead_of_crashing(self) -> None:
        target = TOKEN_USAGE.metric_template()

        TOKEN_USAGE.add_metric(
            target,
            {"input": "not-a-number", "output": -5, "cache_read": 2.5, "total": "9"},
        )

        self.assertEqual(target["total"], 9)
        self.assertEqual(target["input"], 0)
        self.assertEqual(target["output"], 0)
        self.assertEqual(target["cache_read"], 0)


if __name__ == "__main__":
    unittest.main()
