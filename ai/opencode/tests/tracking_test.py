"""Real local Git histories; GitHub mutations intercepted. No network or user refs."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("track", Path(__file__).resolve().parents[1] / "tracking/track.py")
track = importlib.util.module_from_spec(spec)
spec.loader.exec_module(track)
ISSUE = "https://github.com/opencfo-ai/backend/issues/123"


class TrackingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {
            "GIT_AUTHOR_NAME": "Tracking Test", "GIT_COMMITTER_NAME": "Tracking Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.state = patch.object(track, "STATE", self.root / "state")
        self.state.start()
        self.addCleanup(self.state.stop)
        self.origin = self.root / "origin.git"
        self.repo = self.root / "repo"
        self.work = self.root / "parallel work"
        self.cmd("git", "init", "--bare", str(self.origin))
        self.cmd("git", "init", "-b", "main", str(self.repo))
        (self.repo / "shared.txt").write_text("base\n")
        self.g(self.repo, "add", "shared.txt")
        self.g(self.repo, "commit", "-m", "initial")
        self.g(self.repo, "remote", "add", "origin", str(self.origin))
        self.g(self.repo, "push", "-u", "origin", "main")
        self.g(self.repo, "worktree", "add", "-b", "feature", str(self.work))
        self.record = dict(path=str(self.work), common=str(self.repo / ".git"), branch="feature", target="main", state="Up to date", observed=None)
        self.mutations = []
        self.notes = []
        for name, replacement in [
            ("set_field", lambda *args: self.mutations.append(args)),
            ("note", lambda *args: self.notes.append(args)),
            ("gh", lambda *args: {"state": "OPEN"}),
        ]:
            p = patch.object(track, name, replacement)
            p.start()
            self.addCleanup(p.stop)
        self.save()

    def cmd(self, *args, cwd=None):
        return subprocess.check_output(args, cwd=cwd, stderr=subprocess.STDOUT, text=True).strip()

    def g(self, path, *args):
        return self.cmd("git", *args, cwd=path)

    def save(self):
        with track.registry() as data:
            data[ISSUE] = self.record.copy()

    def load(self):
        with track.registry() as data:
            return data[ISSUE].copy()

    def advance(self):
        (self.repo / "shared.txt").write_text("main change\n")
        self.g(self.repo, "commit", "-am", "advance main")
        self.g(self.repo, "push", "origin", "main")

    def test_parallel_branch_detected_without_worktree_mutation(self):
        head = self.g(self.work, "rev-parse", "HEAD")
        (self.work / "dirty.txt").write_text("user work\n")
        self.advance()
        track.refresh()
        self.assertEqual(self.load()["state"], "Needs sync")
        self.assertEqual(self.g(self.work, "rev-parse", "HEAD"), head)
        self.assertEqual((self.work / "dirty.txt").read_text(), "user work\n")
        self.assertEqual(len(self.notes), 1)
        track.refresh()
        self.assertEqual(len(self.notes), 1)

    def test_explicit_merge_requires_verification(self):
        self.advance()
        track.sync_state(ISSUE, "Syncing")
        self.g(self.work, "fetch", "origin")
        self.g(self.work, "merge", "origin/main")
        track.refresh()
        self.assertEqual(self.load()["state"], "Verifying")
        with self.assertRaises(RuntimeError):
            track.sync_state(ISSUE, "Up to date")
        evidence = self.root / "checks.md"
        evidence.write_text("git diff --check: passed; shared.txt verified\n")
        track.sync_state(ISSUE, "Up to date", str(evidence))
        self.assertEqual(self.load()["state"], "Up to date")

    def conflict(self, operation):
        (self.work / "shared.txt").write_text("feature change\n")
        self.g(self.work, "commit", "-am", "feature")
        self.advance()
        self.g(self.work, "fetch", "origin")
        track.sync_state(ISSUE, "Syncing")
        with self.assertRaises(subprocess.CalledProcessError):
            self.g(self.work, operation, "origin/main")
        track.refresh()
        self.assertEqual(self.load()["state"], "Conflicts")

    def test_merge_conflict_and_resolution(self):
        self.conflict("merge")
        (self.work / "shared.txt").write_text("main change\nfeature change\n")
        self.g(self.work, "add", "shared.txt")
        self.g(self.work, "commit", "-m", "resolve")
        track.refresh()
        self.assertEqual(self.load()["state"], "Verifying")

    def test_detached_rebase_conflict_is_detected(self):
        self.conflict("rebase")
        self.g(self.work, "rebase", "--abort")
        track.refresh()
        self.assertEqual(self.load()["state"], "Verifying")

    def test_renamed_worktree_is_recovered(self):
        moved = self.root / "renamed work"
        self.g(self.repo, "worktree", "move", str(self.work), str(moved))
        track.refresh()
        self.assertEqual(Path(self.load()["path"]).resolve(), moved.resolve())
        self.assertEqual(self.load()["state"], "Up to date")

    def test_renamed_branch_is_not_silently_reassigned(self):
        self.g(self.work, "branch", "-m", "different")
        with self.assertRaises(RuntimeError):
            track.refresh()
        self.assertEqual(self.load()["state"], "Unchecked")
        self.assertEqual(self.load()["branch"], "feature")

    def test_offline_preserves_verification_then_recovers(self):
        self.record["state"] = "Verifying"
        self.save()
        with patch.object(track, "inspect", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                track.refresh()
        self.assertEqual(self.load()["state"], "Verifying")
        self.assertEqual(self.load()["error"], "offline")
        track.refresh()
        self.assertIsNone(self.load()["error"])
        self.assertEqual(self.load()["state"], "Verifying")

    def test_main_moves_before_verification(self):
        self.record["state"] = "Verifying"
        self.save()
        self.advance()
        evidence = self.root / "checks.md"
        evidence.write_text("checks passed against previous main\n")
        with self.assertRaises(RuntimeError):
            track.sync_state(ISSUE, "Up to date", str(evidence))
        self.assertEqual(self.load()["state"], "Verifying")

    def test_failed_github_write_retries(self):
        self.advance()
        with patch.object(track, "set_field", side_effect=RuntimeError("GitHub offline")):
            with self.assertRaises(RuntimeError):
                track.refresh()
        self.assertNotEqual(self.load()["state"], "Needs sync")
        track.refresh()
        self.assertEqual(self.load()["state"], "Needs sync")

    def test_closed_issue_does_not_imply_done(self):
        with patch.object(track, "gh", return_value={"state": "CLOSED"}):
            track.refresh()
        self.assertFalse(self.mutations)


class CommentTest(unittest.TestCase):
    def test_comment_retry_checks_all_pages(self):
        with patch.object(track, "gh", return_value=[[{"body": "first"}], [{"body": "<!-- opencode-track:key -->"}]]) as api:
            with patch.object(track, "run") as write:
                track.note(ISSUE, "Research", "body", "key")
                write.assert_not_called()
                self.assertIn("--paginate", api.call_args.args)


if __name__ == "__main__":
    unittest.main()
