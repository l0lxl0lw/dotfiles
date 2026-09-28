import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
