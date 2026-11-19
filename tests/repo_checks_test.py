"""Declared review skills: frontmatter parsing, org scoping and path gating."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "ai/shared/skills/git/_lib/repo-checks.sh"
SCRIPT = ROOT / "ai/shared/skills/git/git-pr/scripts/repo-check.sh"


def skill(path: Path, name: str, frontmatter: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(f"---\nname: {name}\n{frontmatter}---\n\n# {name}\n")


class RepoChecksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="repo-checks-test-")
        self.home = Path(self.tmp.name).resolve()
        self.repo = self.home / "repo"
        self.repo.mkdir()
        self.global_skills = self.home / ".claude/skills"
        self.git("init", "-q")
        self.git("remote", "add", "origin", "git@github.com:example-org/thing.git")
        self.env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_HOME",)}
        self.env.update(HOME=str(self.home), PATH="/usr/bin:/bin:/usr/sbin:/sbin")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def bash(self, body, cwd=None):
        proc = subprocess.run(["/bin/bash", "-c", body], cwd=cwd or self.repo, env=self.env, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def review(self):
        return self.bash(f'bash "{SCRIPT}" review')

    def test_parser_emits_flow_and_block_forms(self):
        skill(self.repo / ".claude/skills/decl", "decl",
              "review:\n  skills: [one, 'two']\n  when-paths:\n    - server/\n    - \"openapi/\"\n  orgs: [example-org, other]\n")
        out = self.bash(f'source "{LIB}"; _repo_check_parse .claude/skills/decl/SKILL.md')
        self.assertEqual(out.splitlines(), [
            "NAME\tdecl", "REVIEW_SKILL\tone", "REVIEW_SKILL\ttwo",
            "REVIEW_WHENPATH\tserver/", "REVIEW_WHENPATH\topenapi/",
            "REVIEW_ORG\texample-org", "REVIEW_ORG\tother",
        ])

    def test_review_block_does_not_leak_into_pre_pr(self):
        skill(self.repo / ".claude/skills/both", "both",
              "pre-pr:\n  command: ./audit.sh\n  when-paths: [a/]\nreview:\n  skills: [x]\n  when-paths: [b/]\n")
        out = self.bash(f'source "{LIB}"; _repo_check_parse .claude/skills/both/SKILL.md')
        self.assertIn("PREPR_WHENPATH\ta/", out)
        self.assertIn("REVIEW_WHENPATH\tb/", out)
        self.assertNotIn("PREPR_WHENPATH\tb/", out)
        self.assertNotIn("REVIEW_WHENPATH\ta/", out)

    def test_origin_owner_for_ssh_and_https(self):
        out = self.bash(f'source "{LIB}"; repo_check_origin_owner')
        self.assertEqual(out.strip(), "example-org")
        self.git("remote", "set-url", "origin", "https://github.com/Other-Org/thing")
        out = self.bash(f'source "{LIB}"; repo_check_origin_owner')
        self.assertEqual(out.strip(), "Other-Org")

    def test_global_declaration_scoped_by_org_and_merged_with_repo(self):
        skill(self.global_skills / "org-decl", "org-decl",
              "review:\n  orgs: [example-org]\n  skills: [runtime-evidence, api-contract-review]\n")
        skill(self.global_skills / "elsewhere", "elsewhere",
              "review:\n  orgs: [someone-else]\n  skills: [never-listed]\n")
        skill(self.global_skills / "unscoped", "unscoped",
              "review:\n  skills: [never-listed-either]\n")
        skill(self.global_skills / "runtime-evidence", "runtime-evidence", "")
        skill(self.repo / ".claude/skills/local-decl", "local-decl",
              "review:\n  skills: [local-gate, runtime-evidence]\n")
        skill(self.repo / ".claude/skills/local-gate", "local-gate", "")
        out = self.review()
        self.assertIn("local-gate  [REQUIRED", out)
        self.assertIn(f"read:     {self.repo}/.claude/skills/local-gate/SKILL.md", out)
        self.assertIn("runtime-evidence  [REQUIRED", out)
        self.assertEqual(out.count("runtime-evidence  ["), 1, "first declaration wins, no duplicate")
        self.assertIn("declared by local-decl (repo)", out.split("runtime-evidence  [")[1].splitlines()[0])
        self.assertIn("api-contract-review  [MISSING", out)
        self.assertIn("declared by org-decl (global), org example-org", out)
        self.assertNotIn("never-listed", out)

    def test_when_paths_gate_against_changed_files(self):
        skill(self.global_skills / "org-decl", "org-decl",
              "review:\n  orgs: [example-org]\n  skills: [ui-gate]\n  when-paths: [web/]\n")
        skill(self.global_skills / "ui-gate", "ui-gate", "")
        (self.repo / "docs").mkdir(); (self.repo / "docs/readme.md").write_text("x")
        out = self.review()
        self.assertIn("ui-gate  [skipped — diff touches none of: web/", out)
        (self.repo / "web").mkdir(); (self.repo / "web/app.ts").write_text("x")
        out = self.review()
        self.assertIn("ui-gate  [REQUIRED — diff touches web/app.ts", out)
        self.assertIn("matched:  web/", out)

    def test_nothing_declared(self):
        out = self.review()
        self.assertIn("(no review: block applies", out)
        self.assertIn("owner 'example-org'", out)

    def test_no_origin_skips_global_declarations(self):
        self.git("remote", "remove", "origin")
        skill(self.global_skills / "org-decl", "org-decl", "review:\n  orgs: [example-org]\n  skills: [g]\n")
        out = self.review()
        self.assertNotIn("g  [", out)
        self.assertIn("owner 'none'", out)


if __name__ == "__main__":
    unittest.main()
