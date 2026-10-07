"""Development adapters, native commands and physical/pinned helper resolution."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / "shared/skills"
STAGES = ("ticket", "research", "plan", "execute", "review")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launch = load("develop_launch", ROOT / "runtime/launch.py")
resolver = load("develop_resolver", SHARED / "develop/_lib/resolve-root.py")


class DevelopTest(unittest.TestCase):
    def test_worker_skill_aliases_and_agent_names_are_distinct(self):
        with tempfile.TemporaryDirectory(prefix="develop snapshot space ") as tmp:
            bundle = launch.build_bundle(ROOT, Path(tmp))
            manifest = launch.validate_bundle(bundle)
            for stage in STAGES:
                name = "develop-" + stage
                path = bundle / "opencode/agents" / (name + ".md")
                definition = launch.definition(path)
                self.assertEqual(definition["mode"], "subagent")
                self.assertNotIn("model", definition)
                self.assertNotIn("variant", definition)
                self.assertIn("`" + manifest["skill_aliases"][name] + "`", launch.body(path))
                self.assertFalse((ROOT / "commands" / (name + ".md")).exists())
            feature = (bundle / "opencode/skills/develop/develop-feature/SKILL.md").read_text()
            self.assertIn("subagent named develop-ticket", feature)
            self.assertNotIn("subagent named wf-", feature)
            self.assertEqual(resolver.resolve_root(
                bundle / "opencode/skills/develop/_lib/resolve-root.py", {}), bundle / "opencode")

    def test_native_catalog_fallback_preserves_custom_commands_and_project_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skills = home / ".config/opencode/skills"
            skills.mkdir(parents=True)
            for name in ("develop-feature", *("develop-" + stage for stage in STAGES)):
                (skills / name).symlink_to(SHARED / "develop" / name)
            project = home / "repo/.agents/skills/develop-plan"
            project.mkdir(parents=True)
            (project / "SKILL.md").write_text("---\nname: develop-plan\ndescription: Project plan\n---\nProject method\n")
            custom = {"develop-plan": {"template": "custom command"},
                      "skill-develop-plan": {"template": "custom fallback"}}
            env = launch.skill_environment({"HOME": tmp, "OPENCODE_CONFIG_CONTENT":
                                            json.dumps({"command": custom})}, home / "repo")
            cfg = json.loads(env["OPENCODE_CONFIG_CONTENT"])
            for name, value in custom.items():
                self.assertEqual(cfg["command"][name], value)
            self.assertIn(str(project / "SKILL.md"), cfg["command"]["skill-skill-develop-plan"]["template"])
            self.assertNotIn("develop-execute", cfg["command"])
            self.assertIn("skill-develop-execute", cfg["command"])

    def test_resolver_live_relocated_symlink_and_explicit_root(self):
        self.assertEqual(resolver.resolve_root(environ={}), ROOT)
        with tempfile.TemporaryDirectory(prefix="develop live space ") as tmp:
            base = Path(tmp)
            for layout in ("opencode", "ai/opencode"):
                repo = base / layout.replace("/", "-")
                integration = repo / layout
                for relative in ("tracking/handoff.py", "tracking/verify.py", "tracking/WORKFLOW.md",
                                 "schemas/plan.example.json"):
                    path = integration / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
                library = repo / "ai/shared/skills/develop/_lib"
                library.mkdir(parents=True)
                script = library / "resolve-root.py"
                shutil.copy2(SHARED / "develop/_lib/resolve-root.py", script)
                link = repo / "installed-library"
                link.symlink_to(library)
                env = {k: v for k, v in os.environ.items() if k != "OPENCODE_WORKFLOW_ROOT"}
                result = subprocess.run(["python3", "-B", str(link / script.name)], env=env,
                                        capture_output=True, text=True, check=True)
                self.assertEqual(Path(result.stdout.strip()), integration.resolve())
                self.assertEqual(resolver.resolve_root(script, {"OPENCODE_WORKFLOW_ROOT": str(ROOT)}), ROOT)
                with self.assertRaisesRegex(RuntimeError, "Invalid inherited"):
                    resolver.resolve_root(script, {"OPENCODE_WORKFLOW_ROOT": str(base / "absent")})
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                resolver.resolve_root(base / "missing/script.py", {})

    def test_library_changes_change_revision_without_mutating_old_workers(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source/opencode"
            source.mkdir(parents=True)
            shared = source.parent / "shared/skills/develop"
            shutil.copytree(SHARED / "develop", shared)
            first = launch.build_bundle(source, base / "state")
            library = shared / "_lib/workflow.md"
            old = library.read_text()
            library.write_text(old + "\nNew resource revision\n")
            second = launch.build_bundle(source, base / "state")
            self.assertNotEqual(first, second)
            self.assertNotIn("New resource revision", (first / "opencode/skills/develop/_lib/workflow.md").read_text())
            launch.validate_bundle(first)
