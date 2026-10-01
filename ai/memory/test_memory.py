import importlib.util
import gzip
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("memory", Path(__file__).with_name("memory.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MemoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name).resolve()
        self.cfg = {"vault": root / "vault", "state": root / "state", "backup": str(root / "backups")}
        self.cfg["vault"].mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def payload(self, text="Remember the green kitchen"):
        return {"session_id": "s/unsafe", "messages": [{"info": {"id": "u1", "role": "user"},
                "parts": [{"type": "text", "text": text}]}]}

    def test_repeat_capture_and_compaction_preserve_source(self):
        first = m.capture(self.cfg, "opencode", self.payload())
        second = m.capture(self.cfg, "opencode", self.payload())
        self.assertEqual(first["records"], second["records"])
        payload = self.payload()
        payload["messages"] = [{"info": {"id": "a1", "role": "assistant"}, "parts": [{"type": "text", "text": "Saved"}]}]
        third = m.capture(self.cfg, "opencode", payload)
        self.assertEqual(third["records"], 2)
        self.assertIn("green kitchen", (self.cfg["vault"] / third["source"]).read_text())
        self.assertEqual(first["user_hash"], third["user_hash"])

    def test_revised_message_keeps_original_but_projects_latest(self):
        first = m.capture(self.cfg, "opencode", self.payload())
        second = m.capture(self.cfg, "opencode", self.payload("Actually blue"))
        self.assertNotEqual(first["user_hash"], second["user_hash"])
        self.assertIn("green kitchen", Path(second["raw"]).read_text())
        projection = (self.cfg["vault"] / second["source"]).read_text()
        self.assertIn("Actually blue", projection)
        self.assertNotIn("green kitchen", projection)

    def test_partial_jsonl_and_tool_records(self):
        p = self.cfg["state"] / "native.jsonl"
        m.atomic(p, json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Hello"}]}}) + "\n" + '{"unfinished"')
        s = m.capture(self.cfg, "codex", {"session_id": "test", "transcript_path": str(p)})
        self.assertEqual(s["records"], 1)
        self.assertIn("Hello", (self.cfg["vault"] / s["source"]).read_text())

    def test_stale_write_and_path_escape(self):
        empty = m.digest(b"")
        m.write_note(self.cfg, {"path": "Wiki/Test.md", "expected_sha256": empty, "content": "first"})
        with self.assertRaises(ValueError):
            m.write_note(self.cfg, {"path": "Wiki/Test.md", "expected_sha256": empty, "content": "lost update"})
        for path in ("../escape.md", ".memory/private.md", "/tmp/escape.md"):
            with self.assertRaises(ValueError):
                m.vault_path(self.cfg, path)
        with self.assertRaises(ValueError):
            m.write_note(self.cfg, {"path": "Sources/a.md", "expected_sha256": empty, "content": "overwrite source"})
        with self.assertRaises(ValueError):
            m.write_note(self.cfg, {"path": "Wiki/../Sources/a.md", "expected_sha256": empty, "content": "overwrite source"})

    def test_stop_reminder_does_not_loop(self):
        p = self.cfg["state"] / "native.jsonl"
        m.atomic(p, json.dumps({"uuid": "u1", "type": "user", "message": {"role": "user", "content": "A new preference"}}) + "\n")
        event = {"session_id": "s", "transcript_path": str(p), "hook_event_name": "Stop"}
        self.assertEqual(m.hook(self.cfg, "claude", event)["decision"], "block")
        self.assertEqual(m.hook(self.cfg, "claude", event), {})

    def test_pause_and_graph_health(self):
        self.cfg["enabled"] = False
        self.assertIsNone(m.capture(self.cfg, "opencode", self.payload()))
        m.atomic(self.cfg["vault"] / "Wiki/A.md", "[[Wiki/B]] [[Missing]]")
        m.atomic(self.cfg["vault"] / "Wiki/B.md", "[[Wiki/A]]")
        result = m.doctor(self.cfg)
        self.assertEqual(len(result["broken_or_ambiguous_links"]), 1)
        self.assertEqual(result["orphans"], [])

    def test_workspace_diff_changes_do_not_grow_capture(self):
        payload = self.payload()
        payload["messages"][0]["info"]["summary"] = {"diffs": [{"patch": "large recursive patch"}]}
        tool = {"info": {"id": "a1", "role": "assistant"},
                "parts": [{"type": "tool", "state": {"output": "important evidence"}}]}
        payload["messages"].append(tool)
        first = m.capture(self.cfg, "opencode", payload)
        raw = Path(first["raw"])
        before = raw.read_bytes()
        payload["messages"][0]["info"]["summary"]["diffs"][0]["patch"] *= 100
        second = m.capture(self.cfg, "opencode", payload)
        self.assertEqual(before, raw.read_bytes())
        self.assertEqual(first["user_hash"], second["user_hash"])
        self.assertIn("important evidence", raw.read_text())
        self.assertNotIn("recursive patch", raw.read_text())
        self.assertIn("diffs", payload["messages"][0]["info"]["summary"])
        tool["parts"][0]["state"]["output"] = "revised evidence"
        m.capture(self.cfg, "opencode", payload)
        self.assertIn("important evidence", raw.read_text())
        self.assertIn("revised evidence", raw.read_text())

    def archive_config(self):
        self.cfg.update(raw_directory=str(self.cfg["state"] / "raw"),
                        raw_archive=str(self.cfg["state"] / "cloud-archive"))

    def legacy_capture(self):
        s = m.capture(self.cfg, "opencode", self.payload())
        raw = Path(s["raw"])
        row = self.payload()["messages"][0]
        row["info"]["summary"] = {"diffs": [{"patch": "recursive content" * 100}]}
        original = m.encode(row) + b"\n"
        raw.write_bytes(original)
        return s, raw, original

    def test_migrate_preserves_original_and_resumed_capture(self):
        s, old, original = self.legacy_capture()
        projection = (self.cfg["vault"] / s["source"]).read_text()
        self.archive_config()
        result = m.archive_raw(self.cfg, migrate=True)
        self.assertFalse(old.exists())
        self.assertEqual(len(result), 1)
        entry = result[0]
        archived = Path(self.cfg["raw_archive"]) / entry["archive"]
        self.assertEqual(gzip.decompress(archived.read_bytes()), original)
        normalized = m.raw_root(self.cfg) / old.name
        self.assertNotIn("recursive content", normalized.read_text())
        s2 = m.capture(self.cfg, "opencode", self.payload())
        self.assertEqual(s2["records"], 1)
        self.assertEqual(s2["user_hash"], s["user_hash"])
        self.assertIn("green kitchen", (self.cfg["vault"] / s["source"]).read_text())
        self.assertEqual(projection, (self.cfg["vault"] / s["source"]).read_text())
        restored = self.cfg["state"] / "restored.jsonl"
        m.restore_raw(self.cfg, entry["sha256"], str(restored))
        self.assertEqual(restored.read_bytes(), original)
        with self.assertRaises(FileExistsError):
            m.restore_raw(self.cfg, entry["sha256"], str(restored))
        self.assertEqual(m.archive_raw(self.cfg, migrate=True), [])
        m.archive_raw(self.cfg)
        m.archive_raw(self.cfg)
        self.assertEqual(m.verify_archives(self.cfg)["verified_archives"], 2)
        normalized.write_text("")
        with self.assertRaisesRegex(ValueError, "missing a preserved revision"):
            m.verify_archives(self.cfg)

    def test_corrupt_archive_blocks_migration_and_restore(self):
        _, raw, original = self.legacy_capture()
        self.archive_config()
        e = m.archive_file(self.cfg, raw, "legacy-original")
        archive = Path(self.cfg["raw_archive"]) / e["archive"]
        archive.write_bytes(gzip.compress(b"corrupt"))
        with self.assertRaises(ValueError):
            m.migrate_raw_file(self.cfg, raw)
        self.assertEqual(raw.read_bytes(), original)
        restored = self.cfg["state"] / "restore.jsonl"
        with self.assertRaises(ValueError):
            m.restore_raw(self.cfg, e["sha256"], str(restored))
        self.assertFalse(restored.exists())

    def test_capture_auto_migrates_legacy_without_losing_history(self):
        _, raw, original = self.legacy_capture()
        self.archive_config()
        s = m.capture(self.cfg, "opencode", self.payload("New statement"))
        self.assertFalse(raw.exists())
        self.assertIn("green kitchen", Path(s["raw"]).read_text())
        self.assertIn("New statement", Path(s["raw"]).read_text())
        self.assertEqual(s["records"], 2)
        self.assertEqual(m.archive_manifest(self.cfg)[1]["entries"][0]["sha256"], m.digest(original))

    def test_backup_excludes_git_and_includes_archive_catalog(self):
        self.archive_config()
        s = m.capture(self.cfg, "opencode", self.payload())
        m.atomic(self.cfg["vault"] / ".git/lfs/objects/large", "redundant history")
        m.atomic(self.cfg["vault"] / "Wiki/note.md", "useful knowledge")
        result = m.backup(self.cfg)
        with zipfile.ZipFile(result) as z:
            self.assertIn("Wiki/note.md", z.namelist())
            self.assertIn(s["source"], z.namelist())
            self.assertIn(".memory/archive-manifest.json", z.namelist())
            self.assertFalse(any(p.startswith(".git/") for p in z.namelist()))
            self.assertIsNone(z.testzip())
        self.assertEqual(m.verify_archives(self.cfg)["verified_archives"], 1)


if __name__ == "__main__":
    unittest.main()
