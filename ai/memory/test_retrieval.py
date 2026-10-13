import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io

import granola_layers as layers
import recall
import verify_retrieval
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
        raw = f'<meeting id="{self.sid}" title="Interview" url="https://notes.granola.ai/d/{self.sid}"><private_notes>Private heading\n\n- Detail\n  - Nested</private_notes><summary># Original heading\n\n- Nested details\n  - Zebra financing decision</summary></meeting>'
        notes = {"content": [{"type": "text", "text": raw}], "isError": False}
        transcript = {"id": self.sid, "transcript": "Speaker: Hello.\n\nSpeaker: Cobalt quotation."}
        response = {"content": [{"type": "text", "text": json.dumps(transcript)}], "isError": False}
        atomic(self.staging / "notes-0.json", json.dumps(notes))
        atomic(self.staging / f"{self.sid}-transcript.json", json.dumps(response))

    def full_fixture(self):
        self.staging = self.cfg["state"] / "granola"
        self.fixture()
        atomic(self.staging / "inventory.json", json.dumps([{"id": self.sid, "date": "Sep 29, 2026 12:00 PM PDT", "title": "Interview", "url": "https://notes.granola.ai/d/" + self.sid, "participants": "Example"}]))
        atomic(self.staging / "account.json", json.dumps({"content": [{"type": "text", "text": json.dumps({"active_workspace": {"display_name": "Test"}})}]}))
        atomic(self.staging / "synthesis.json", json.dumps({"projects": {"Example": "Example project"}, "topics": {}, "meetings": {self.sid: {"title": "Renamed interview", "kind": "test", "project": "Example", "gist": "Example gist", "organizations": [], "people": [], "topics": []}}}))
        atomic(self.cfg["vault"] / "System/Granola import.md", "# Granola import\n\n## Human note\n\nKeep this audit.")

    def run_full_publisher(self):
        import granola_publish
        with patch.object(granola_publish, "settings", return_value=self.cfg), contextlib.redirect_stdout(io.StringIO()):
            granola_publish.main()

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

    def test_altered_or_malformed_notes_projection_is_rejected_without_mutation(self):
        self.fixture()
        result = layers.publish(self.cfg, self.staging)["results"][0]
        notes = self.cfg["vault"] / result["source"] / "Notes.md"
        meeting = self.cfg["vault"] / "Meetings/Interview.md"
        registry = self.cfg["state"] / "granola/layers.json"
        original = notes.read_text()
        stable = (meeting.read_bytes(), registry.read_bytes())
        changes = {
            "source_id": original.replace(self.sid, "00000000-0000-4000-8000-000000000002", 1),
            "missing source_id": original.replace(f"source_id: {self.sid}\n", "", 1),
            "duplicated source_id": original.replace(f"source_id: {self.sid}\n", f"source_id: {self.sid}\nsource_id: {self.sid}\n", 1),
            "quoted duplicate source_id": original.replace(f"source_id: {self.sid}\n", f"source_id: 00000000-0000-4000-8000-000000000002\n'source_id': {self.sid}\n", 1),
            "merged duplicate source_id": original.replace(f"source_id: {self.sid}\n", f"defaults: &defaults {{source_id: 00000000-0000-4000-8000-000000000002}}\n<<: *defaults\nsource_id: {self.sid}\n", 1),
            "malformed source_id": original.replace(f"source_id: {self.sid}", "source_id: ["),
            "url": original.replace("https://notes.granola.ai/d/", "https://example.invalid/", 1),
            "missing url": original.replace("[Original meeting]", "[Meeting]", 1),
            "duplicated wrapper url": original.replace("## Private notes", f"[Original meeting](https://notes.granola.ai/d/{self.sid})\n\n## Private notes", 1),
            "private notes": original.replace("  - Nested", "  - Altered", 1),
            "summary": original.replace("  - Zebra financing decision", "  - Altered decision", 1),
            "source_revision": original.replace(result["revision"], "ffffffffffffffff", 1),
            "quoted duplicate source_revision": original.replace(f"source_revision: {result['revision']}\n", f"source_revision: ffffffffffffffff\n\"source_revision\": {result['revision']}\n", 1),
            "merged duplicate source_revision": original.replace(f"source_revision: {result['revision']}\n", f"defaults: &defaults {{source_revision: ffffffffffffffff}}\n<<: *defaults\nsource_revision: {result['revision']}\n", 1),
            "missing section": original.replace("## Private notes", "## Private source notes", 1),
            "duplicated section": original.replace("## Summary", "## Summary\n\nextra\n\n## Summary", 1),
        }
        for name, changed in changes.items():
            with self.subTest(name=name):
                atomic(notes, changed)
                with self.assertRaisesRegex(ValueError, "projection|source sections"):
                    layers.publish(self.cfg, self.staging)
                self.assertEqual(changed, notes.read_text())
                self.assertEqual(stable, (meeting.read_bytes(), registry.read_bytes()))
        atomic(notes, original)

    def test_notes_projection_accepts_yaml_merge_without_protected_fields(self):
        self.fixture()
        result = layers.publish(self.cfg, self.staging)["results"][0]
        notes = self.cfg["vault"] / result["source"] / "Notes.md"
        merged = notes.read_text().replace(
            f"source_id: {self.sid}\n",
            f"defaults: &defaults {{category: archive}}\n<<: *defaults\nsource_id: {self.sid}\n",
            1,
        )
        atomic(notes, merged)
        layers.publish(self.cfg, self.staging)
        self.assertEqual(merged, notes.read_text())

    def test_source_summary_may_retain_original_meeting_link(self):
        self.full_fixture()
        staged = self.staging / "notes-0.json"
        data = json.loads(staged.read_text())
        raw = data["content"][0]["text"]
        raw = raw.replace(
            "# Original heading",
            "[Original meeting](https://example.test/context)\n\n# Original heading",
        )
        data["content"][0]["text"] = raw
        atomic(staged, json.dumps(data))
        result = layers.publish(self.cfg, self.staging)["results"][0]
        notes = self.cfg["vault"] / result["source"] / "Notes.md"
        unchanged = notes.read_bytes()
        layers.publish(self.cfg, self.staging)
        self.run_full_publisher()
        self.assertEqual(unchanged, notes.read_bytes())

    def test_source_payload_may_retain_wrapper_shaped_headings(self):
        self.full_fixture()
        staged = self.staging / "notes-0.json"
        data = json.loads(staged.read_text())
        raw = data["content"][0]["text"]
        raw = raw.replace("Private heading", "Private heading\n\n## Private notes\n\nNested private heading")
        raw = raw.replace("# Original heading", "Introductory summary\n\n## Summary\n\n# Original heading")
        data["content"][0]["text"] = raw
        atomic(staged, json.dumps(data))
        result = layers.publish(self.cfg, self.staging)["results"][0]
        notes = self.cfg["vault"] / result["source"] / "Notes.md"
        unchanged = notes.read_bytes()
        layers.publish(self.cfg, self.staging)
        self.run_full_publisher()
        self.assertEqual(unchanged, notes.read_bytes())

    def test_missing_notes_recreated_only_when_raw_sources_match(self):
        self.fixture()
        result = layers.publish(self.cfg, self.staging)["results"][0]
        folder = self.cfg["vault"] / result["source"]
        notes = folder / "Notes.md"
        expected = notes.read_bytes()
        raw = folder / "original-notes.xml"
        original_raw = raw.read_bytes()
        notes.unlink()
        layers.publish(self.cfg, self.staging)
        self.assertEqual(expected, notes.read_bytes())
        self.assertEqual(original_raw, raw.read_bytes())
        notes.unlink()
        atomic(raw, original_raw + b"\nconflict")
        with self.assertRaisesRegex(ValueError, "Source revision conflict"):
            layers.publish(self.cfg, self.staging)
        self.assertFalse(notes.exists())
        self.assertEqual(original_raw + b"\nconflict", raw.read_bytes())

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
        self.full_fixture()
        self.run_full_publisher()
        result = json.loads((self.cfg["state"] / "granola/layers.json").read_text())[self.sid]
        notes = self.cfg["vault"] / result["source"] / "Notes.md"
        full_wrapper = notes.read_bytes()
        self.run_full_publisher()
        self.assertEqual([p.name for p in (self.cfg["vault"] / "Meetings").glob("*.md")], ["Interview.md"])
        self.assertIn("Keep my exact words.", (self.cfg["vault"] / "Meetings/Interview.md").read_text())
        self.assertIn("Keep this audit.", (self.cfg["vault"] / "System/Granola import.md").read_text())
        self.assertEqual(full_wrapper, notes.read_bytes())
        layers.publish(self.cfg, self.staging)
        self.assertEqual(full_wrapper, notes.read_bytes())

    def test_full_publisher_accepts_layer_wrapper_and_preflights_conflicts(self):
        self.full_fixture()
        result = layers.publish(self.cfg, self.staging)["results"][0]
        notes = self.cfg["vault"] / result["source"] / "Notes.md"
        layered_wrapper = notes.read_bytes()
        self.run_full_publisher()
        self.assertEqual(layered_wrapper, notes.read_bytes())
        atomic(notes, notes.read_text().replace("Zebra financing decision", "Corrupt source"))
        before = {str(p.relative_to(self.cfg["vault"])): p.read_bytes() for p in self.cfg["vault"].rglob("*") if p.is_file()}
        with self.assertRaisesRegex(ValueError, "Source projection conflict"):
            self.run_full_publisher()
        after = {str(p.relative_to(self.cfg["vault"])): p.read_bytes() for p in self.cfg["vault"].rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_full_publisher_recreates_only_missing_notes_projection(self):
        self.full_fixture()
        self.run_full_publisher()
        row = json.loads((self.cfg["state"] / "granola/layers.json").read_text())[self.sid]
        folder = self.cfg["vault"] / row["source"]
        notes = folder / "Notes.md"
        expected = notes.read_bytes()
        raw = {path.name: path.read_bytes() for path in folder.iterdir() if path.name.startswith("original-")}
        notes.unlink()
        self.run_full_publisher()
        self.assertEqual(expected, notes.read_bytes())
        self.assertEqual(raw, {path.name: path.read_bytes() for path in folder.iterdir() if path.name.startswith("original-")})

    def test_registered_audit_reports_notes_divergence_without_orphan_scan(self):
        self.fixture()
        result = layers.publish(self.cfg, self.staging)["results"][0]
        notes = self.cfg["vault"] / result["source"] / "Notes.md"
        atomic(notes, notes.read_text().replace("Zebra financing decision", "Corrupt source"))
        atomic(self.cfg["vault"] / "Sources/Granola/orphan/Notes.md", "not a projection")
        audit = verify_retrieval.audit(self.cfg)
        self.assertEqual(audit["complete"], 0)
        self.assertTrue(any(p["issue"] == "Notes projection differs" for p in audit["problems"]))
        self.assertFalse(any("orphan" in json.dumps(p) for p in audit["problems"]))

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
