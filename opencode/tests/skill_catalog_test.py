"""Shared/project discovery, command fallbacks, and snapshot resource closure."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("catalog_launch", ROOT / "runtime/launch.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


def skill(root, name, content="fixture"):
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: Test skill\n---\n{content}\n")
    return path.resolve()


class SkillCatalogTest(unittest.TestCase):
    def test_canonical_skill_names_are_unique_and_catalog_is_complete(self):
        catalog = launch.skill_files(ROOT.parent / "ai/shared/skills")
        self.assertFalse(list((ROOT / "skills").rglob("SKILL.md")))
        self.assertIn("workflow-execute", catalog)
        self.assertIn("humanizer", catalog)
        self.assertIn("remotion-best-practices", catalog)

    def test_project_precedence_and_nested_launch_does_not_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            repo = home / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            child = repo / "src"
            child.mkdir()
            skill(home / ".config/opencode/skills", "example", "global")
            skill(repo / ".claude/skills", "example", "claude")
            skill(repo / ".agents/skills", "example", "agents")
            chosen = skill(repo / ".opencode/skills", "example", "opencode")
            local = skill(child / ".agents/skills", "nested")
            env = launch.skill_environment({"HOME": tmp}, child)
            cfg = json.loads(env["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(set(cfg["skills"]["paths"]), {str(chosen.parent), str(local.parent)})
            self.assertIn(str(chosen), cfg["command"]["skill-example"]["template"])
            self.assertEqual(launch.skill_environment(env, child), env)
            elsewhere = home / "elsewhere"
            elsewhere.mkdir()
            other = json.loads(launch.skill_environment(env, elsewhere)["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(other["skills"]["paths"], [])
            self.assertNotIn("skill-nested", other["command"])
            self.assertIn(".config/opencode/skills", other["command"]["skill-example"]["template"])

    def test_preserves_custom_commands_and_avoids_alias_collisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skill(home / ".config/opencode/skills", "plan")
            original = {"plan": {"template": "custom plan"}, "skill-plan": {"template": "custom alias"}}
            env = {"HOME": tmp, "OPENCODE_CONFIG_CONTENT": json.dumps({"command": original})}
            cfg = json.loads(launch.skill_environment(env, home)["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(cfg["command"]["plan"], original["plan"])
            self.assertEqual(cfg["command"]["skill-plan"], original["skill-plan"])
            self.assertIn("$ARGUMENTS", cfg["command"]["skill-skill-plan"]["template"])

    def test_nested_templates_are_not_skills_and_duplicates_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill(root, "one")
            skill(root / "one/templates", "template")
            self.assertEqual(list(launch.skill_files(root)), ["one"])
            skill(root / "category", "one")
            with self.assertRaisesRegex(RuntimeError, "Duplicate skill"):
                launch.skill_files(root)

    def test_shared_helpers_are_pinned_and_shared_edits_change_revision(self):
        with tempfile.TemporaryDirectory(prefix="shared resource space ") as tmp:
            source = Path(tmp) / "source/opencode"
            source.mkdir(parents=True)
            (source / "profiles.json").write_bytes((ROOT / "profiles.json").read_bytes())
            shared = source.parent / "ai/shared/skills"
            md = skill(shared / "git", "sample", "bash ~/dotfiles/ai/shared/skills/git/sample/scripts/check.sh")
            helper = md.parent / "scripts/check.sh"
            helper.parent.mkdir()
            helper.write_text("#!/bin/sh\nexit 0\n")
            state = Path(tmp) / "state"
            bundle = launch.build_bundle(source, state)
            copied = bundle / "opencode/skills/git/sample"
            self.assertEqual((copied / "scripts/check.sh").read_bytes(), helper.read_bytes())
            self.assertIn('bash "' + str(copied), (copied / "SKILL.md").read_text())
            helper.write_text("#!/bin/sh\nexit 1\n")
            self.assertNotEqual(launch.build_bundle(source, state), bundle)
            self.assertIn("exit 0", (copied / "scripts/check.sh").read_text())

    @unittest.skipUnless(os.environ.get("OPENCODE_CATALOG_SMOKE") == "1", "opt-in installed-binary discovery check")
    def test_installed_opencode_resolves_project_winner_and_commands(self):
        binary = shutil.which("opencode")
        self.assertIsNotNone(binary)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            repo = home / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            skill(home / ".config/opencode/skills", "example", "GLOBAL")
            skill(repo / ".claude/skills", "example", "CLAUDE")
            skill(repo / ".agents/skills", "example", "AGENTS")
            chosen = skill(repo / ".opencode/skills", "example", "CHOSEN")
            skill(repo / ".agents/skills", "agents-only", "AGENTS-ONLY")
            skill(repo / ".claude/skills", "claude-only", "CLAUDE-ONLY")
            env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENCODE_", "XDG_"))}
            env.update(HOME=tmp, XDG_CONFIG_HOME=str(home / ".config"), XDG_DATA_HOME=str(home / "data"),
                       XDG_CACHE_HOME=str(home / "cache"), XDG_STATE_HOME=str(home / "state"),
                       OPENCODE_DISABLE_MODELS_FETCH="1")
            env = launch.skill_environment(env, repo)
            result = subprocess.run([binary, "debug", "skill"], cwd=repo, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            catalog = {item["name"]: item for item in json.loads(result.stdout)}
            # Native duplicate discovery is concurrent. The execution overlay
            # (tested separately) makes the chosen project file authoritative.
            self.assertIn("example", catalog)
            self.assertEqual(json.loads(env["OPENCODE_SKILL_CATALOG"])["projects"]["example"], str(chosen))
            self.assertIn("agents-only", catalog)
            self.assertIn("claude-only", catalog)
            result = subprocess.run([binary, "debug", "config"], cwd=repo, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            commands = json.loads(result.stdout)["command"]
            self.assertIn(str(chosen), commands["skill-example"]["template"])
