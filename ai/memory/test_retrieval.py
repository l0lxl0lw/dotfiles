import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io

import granola_layers as layers
import recall
from memory import atomic


class LayeredRecallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name).resolve()
        self.cfg = {"vault": root / "vault", "state": root / "state"}
        self.cfg["vault"].mkdir()
        self.sid = "00000000-0000-4000-8000-000000000001"
        self.staging = root / "staging"

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self):
        note = f"---\ntype: meeting\nsource_id: {self.sid}\n---\n# Interview\n\n## Gist\n\nOwnership and engineering judgment.\n\n## Human reflections\n\nKeep my exact words.\n"
        atomic(self.cfg["vault"] / "Meetings/Interview.md", note)
        raw = f'<meeting id="{self.sid}" title="Interview" url="https://notes.granola.ai/d/{self.sid}"><summary># Original heading\n\n- Nested details\n  - Zebra financing decision</summary></meeting>'
        notes = {"content": [{"type": "text", "text": raw}], "isError": False}
        transcript = {"id": self.sid, "transcript": "Speaker: Hello.\n\nSpeaker: Cobalt quotation."}
        response = {"content": [{"type": "text", "text": json.dumps(transcript)}], "isError": False}
        atomic(self.staging / "notes-0.json", json.dumps(notes))
        atomic(self.staging / f"{self.sid}-transcript.json", json.dumps(response))

    def test_round_trip_complete_sources_idempotent_and_human_edits(self):
        self.fixture()
        result = layers.publish(self.cfg, self.staging)
        self.assertEqual(result["local_transcripts"], 1)
        path = self.cfg["vault"] / "Meetings/Interview.md"
        first = path.read_text()
        self.assertIn("  - Zebra financing decision", first)
        self.assertIn("Keep my exact words.", first)
        layers.publish(self.cfg, self.staging)
        self.assertEqual(first, path.read_text())
        atomic(path, first.replace("Keep my exact words.", "A later personal edit."))
        layers.publish(self.cfg, self.staging)
        self.assertIn("A later personal edit.", path.read_text())
        atomic(path, path.read_text().replace("Zebra financing decision", "An edited outline"))
        with self.assertRaisesRegex(ValueError, "Human edit"):
            layers.publish(self.cfg, self.staging)

    def test_missing_wrong_and_truncated_transcripts_fail(self):
        self.fixture()
        tp = self.staging / f"{self.sid}-transcript.json"
        tp.unlink()
        with self.assertRaisesRegex(ValueError, "Missing local transcript"):
            layers.publish(self.cfg, self.staging)
        atomic(tp, json.dumps({"content": [{"type": "text", "text": '{"id":"wrong","transcript":"hello"}'}]}))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            layers.publish(self.cfg, self.staging)
        self.fixture()
        result = layers.publish(self.cfg, self.staging)
        archive = self.cfg["vault"] / result["results"][0]["source"] / "Transcript.md"
        atomic(archive, archive.read_text().replace("Speaker: Cobalt quotation.", "truncated"))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            layers.publish(self.cfg, self.staging)

    def test_source_refresh_keeps_history_and_review_flag(self):
        self.fixture()
        first = layers.publish(self.cfg, self.staging)["results"][0]
        staged = self.staging / "notes-0.json"
        data = json.loads(staged.read_text())
        data["content"][0]["text"] = data["content"][0]["text"].replace("Zebra financing decision", "Updated financing decision")
        atomic(staged, json.dumps(data))
        second = layers.publish(self.cfg, self.staging)["results"][0]
        self.assertNotEqual(first["source"], second["source"])
        self.assertTrue((self.cfg["vault"] / first["source"] / "Notes.md").exists())
        self.assertTrue(second["needs_review"])
        self.assertTrue(layers.publish(self.cfg, self.staging)["results"][0]["needs_review"])
        self.assertEqual(len(list((self.cfg["vault"] / "Meetings").glob("*.md"))), 1)

    def test_refetched_same_meeting_in_different_batch_is_not_a_conflict(self):
        self.fixture()
        first = layers.publish(self.cfg, self.staging)["results"][0]
        staged = self.staging / "notes-0.json"
        data = json.loads(staged.read_text())
        data["content"][0]["text"] = "A different response envelope\n" + data["content"][0]["text"]
        atomic(staged, json.dumps(data))
        second = layers.publish(self.cfg, self.staging)["results"][0]
        self.assertEqual(first["source"], second["source"])
        self.assertEqual(len(list((self.cfg["vault"] / first["source"]).glob("original-meeting-response-*.json"))), 2)

    def test_publisher_uses_source_identity_and_preserves_report_edits(self):
        import granola_publish
        self.staging = self.cfg["state"] / "granola"
        self.fixture()
        atomic(self.staging / "inventory.json", json.dumps([{"id":self.sid,"date":"Sep 29, 2026 12:00 PM PDT","title":"Interview","url":"https://notes.granola.ai/d/"+self.sid,"participants":"Example"}]))
        atomic(self.staging / "account.json", json.dumps({"content":[{"type":"text","text":json.dumps({"active_workspace":{"display_name":"Test"}})}]}))
        atomic(self.staging / "synthesis.json", json.dumps({"projects":{"Example":"Example project"},"topics":{},"meetings":{self.sid:{"title":"Renamed interview","kind":"test","project":"Example","gist":"Example gist","organizations":[],"people":[],"topics":[]}}}))
        atomic(self.cfg["vault"] / "System/Granola import.md", "# Granola import\n\n## Human note\n\nKeep this audit.")
        with patch.object(granola_publish, "settings", return_value=self.cfg), contextlib.redirect_stdout(io.StringIO()):
            granola_publish.main()
            granola_publish.main()
        self.assertEqual([p.name for p in (self.cfg["vault"] / "Meetings").glob("*.md")], ["Interview.md"])
        self.assertIn("Keep my exact words.", (self.cfg["vault"] / "Meetings/Interview.md").read_text())
        self.assertIn("Keep this audit.", (self.cfg["vault"] / "System/Granola import.md").read_text())

    def test_summary_default_and_explicit_evidence_depth(self):
        self.fixture()
        layers.publish(self.cfg, self.staging)
        self.assertTrue(recall.search(self.cfg, "engineering ownership")["results"])
        self.assertFalse(recall.search(self.cfg, "Zebra")["results"])
        self.assertFalse(recall.search(self.cfg, "Cobalt")["results"])
        self.assertTrue(recall.search(self.cfg, "Zebra", "outline")["results"])
        self.assertTrue(recall.search(self.cfg, "Cobalt", "transcript")["results"])
        result = recall.read(self.cfg, "Meetings/Interview")
        self.assertIn("Ownership", result["content"])
        self.assertNotIn("Zebra", result["content"])
        evidence = recall.read(self.cfg, "Meetings/Interview", layer="outline", limit=40)
        self.assertEqual(evidence["next_offset"], 40)

    def test_context_exact_identity_and_stale_index_refresh(self):
        atomic(self.cfg["vault"] / "Wiki/Project.md", "# Project\n\n## Gist\n\nNebula work.\n\n[[Meetings/Interview]]")
        self.fixture()
        ctx = recall.context(self.cfg, "Wiki/Project")
        self.assertEqual(ctx["primary"]["path"], "Wiki/Project.md")
        self.assertEqual(ctx["related"][0]["path"], "Meetings/Interview.md")
        with self.assertRaises(ValueError):
            recall.resolve(self.cfg, "not-a-note")
        with self.assertRaises(ValueError):
            recall.resolve(self.cfg, "../escape.md")
        self.assertTrue(recall.search(self.cfg, "Nebula")["results"])
        atomic(self.cfg["vault"] / "Wiki/Project.md", "# Project\n\n## Gist\n\nGalaxy work.")
        self.assertFalse(recall.search(self.cfg, "Nebula")["results"])
        self.assertTrue(recall.search(self.cfg, "Galaxy")["results"])

    def test_read_prefers_gist_and_later_outcome_over_old_next_steps(self):
        atomic(self.cfg["vault"] / "Meetings/History.md", "---\ndate: 2026-09-29\n---\n# History\n\n## Quick answers\n\nUpdated details.\n\n## Gist\n\nDeclined after screening.\n\n## Outcome\n\nRejected September 28.\n\n## Follow-ups\n\nAwait next interview round.")
        result = recall.search(self.cfg, "next interview round")["results"][0]
        self.assertIn("Rejected", result["overview"])
        self.assertTrue(result["overview"].startswith("## Gist"))
        json.dumps(recall.context(self.cfg, "Meetings/History"), default=str)


if __name__ == "__main__":
    unittest.main()
