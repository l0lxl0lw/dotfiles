"""Shared/project discovery, command fallbacks, and snapshot resource closure."""
import importlib.util
import json
import os
import re
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
        catalog = launch.skill_files(ROOT.parent / "shared/skills")
        self.assertFalse(list((ROOT / "skills").rglob("SKILL.md")))
        self.assertEqual(len(catalog), 38)
        self.assertIn("develop-brainstorm", catalog)
        self.assertIn("write-better", catalog)
        removed = {"business", "codebase", "impeccable", "mattpocock", "omc", "utilities", "workflow"}
        shared = ROOT.parent / "shared/skills"
        self.assertFalse(any(path.relative_to(shared).parts[0] in removed for path in catalog.values()))
        self.assertEqual({path.relative_to(shared).parts[0] for path in catalog.values()},
                         {"develop", "write", "learn", "explain", "git", "use", "remember", "respond", "orca"})
        for name, path in catalog.items():
            self.assertEqual(name, path.parent.name)
            self.assertTrue(name.startswith(path.relative_to(shared).parts[0] + "-"), name)
        for stage in ("ticket", "research", "plan", "execute", "review", "commit"):
            self.assertNotIn("workflow-" + stage, catalog)
            self.assertFalse((ROOT / "commands" / (stage + ".md")).exists())
            self.assertFalse((ROOT / "agents" / ("workflow-" + stage + ".md")).exists())
        self.assertIn("write-humanize", catalog)
        self.assertIn("use-remotion", catalog)

    def test_shared_skill_resources_resolve_from_live_and_pinned_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = launch.build_bundle(ROOT, Path(tmp))
            for shared in (ROOT.parent / "shared/skills", bundle / "opencode/skills"):
                catalog = launch.skill_files(shared)
                for path in catalog.values():
                    text = path.read_text()
                    resources = re.findall(r"`((?:\.\./)+[^`]+\.md)`", text)
                    resources += re.findall(r"\]\(((?:\./)?(?:rules|references|templates|scripts)/[^)#]+)\)", text)
                    for relative in resources:
                        self.assertTrue((path.parent / relative).is_file(), (path, relative))
                handoff = next(path.parent for path in catalog.values() if path.parent.name == "orca-handoff")
                self.assertTrue((handoff / "scripts/handoff.py").is_file())
                self.assertTrue((handoff / "README.md").is_file())
                self.assertTrue((shared / "git/git-sync-orca-workspaces/scripts/survey.sh").stat().st_mode & 0o111)
            manifest = json.loads((bundle / "manifest.json").read_text())
            pinned_name = manifest["skill_aliases"]["orca-handoff"]
            command = (bundle / "opencode/commands/orca-handoff.md").read_text()
            self.assertIn("`" + pinned_name + "`", command)

    def test_brainstorm_alias_resolves_live_and_pinned_skill_with_attribution(self):
        command = ROOT / "commands/brainstorm.md"
        live = launch.skill_files(ROOT.parent / "shared/skills")
        live_name, = re.findall(r"`([^`]+)`", launch.body(command))
        self.assertIn(live_name, live)
        self.assertIn("$ARGUMENTS", launch.body(command))
        self.assertNotIn("model", launch.definition(command))
        with tempfile.TemporaryDirectory() as tmp:
            bundle = launch.build_bundle(ROOT, Path(tmp) / "state")
            env = launch.environment(bundle, {"HOME": tmp}, Path(tmp))
            alias = json.loads(env["OPENCODE_CONFIG_CONTENT"])["command"]["brainstorm"]
            pinned_name, = re.findall(r"`([^`]+)`", alias["template"])
            manifest = launch.validate_bundle(bundle)
            self.assertEqual(pinned_name, manifest["skill_aliases"][live_name])
            self.assertNotEqual(pinned_name, live_name)
            self.assertIn("$ARGUMENTS", alias["template"])
            pinned = launch.skill_files(bundle / "config/skills")[pinned_name]
            # Handoff references must stay in the same resource revision as brainstorm.
            for next_skill in ("develop-ticket", "develop-feature"):
                self.assertIn("`" + next_skill + "`", live[live_name].read_text())
                target = manifest["skill_aliases"][next_skill]
                self.assertIn("`" + target + "`", pinned.read_text())
                self.assertIn(target, launch.skill_files(bundle / "config/skills"))
            for resource in ("sources.md", "LICENSE.superpowers"):
                self.assertEqual((pinned.parent / resource).read_bytes(),
                                 (live[live_name].parent / resource).read_bytes())

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
            source = Path(tmp) / "source/ai/opencode"
            source.mkdir(parents=True)
            shared = source.parent / "shared/skills"
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
