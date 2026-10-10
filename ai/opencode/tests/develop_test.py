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
STAGES = ("execute", "review")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launch = load("develop_launch", ROOT / "runtime/launch.py")
resolver = load("develop_resolver", SHARED / "develop/_lib/resolve-root.py")


class DevelopTest(unittest.TestCase):
    def test_internal_workers_resolve_methods_without_public_skill_commands(self):
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
                method = bundle / "opencode/skills/develop/_lib" / (stage + ".md")
                self.assertIn(str(method), launch.body(path))
                self.assertTrue(method.is_file())
                self.assertNotIn(name, manifest["skill_aliases"])
                self.assertFalse((ROOT / "commands" / (name + ".md")).exists())
            for stage in ("ticket", "research", "plan"):
                self.assertFalse((bundle / "opencode/agents" / ("develop-" + stage + ".md")).exists())
            self.assertEqual({name for name in manifest["skill_aliases"] if name.startswith("develop-")},
                             {"develop-prepare", "develop-deliver"})
            self.assertEqual(resolver.resolve_root(
                bundle / "opencode/skills/develop/_lib/resolve-root.py", {}), bundle / "opencode")

    def test_native_catalog_fallback_preserves_custom_commands_and_project_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skills = home / ".config/opencode/skills"
            skills.mkdir(parents=True)
            for name in ("develop-prepare", "develop-deliver"):
                (skills / name).symlink_to(SHARED / "develop" / name)
            project = home / "repo/.agents/skills/develop-prepare"
            project.mkdir(parents=True)
            (project / "SKILL.md").write_text("---\nname: develop-prepare\ndescription: Project preparation\n---\nProject method\n")
            custom = {"develop-prepare": {"template": "custom command"},
                      "skill-develop-prepare": {"template": "custom fallback"}}
            env = launch.skill_environment({"HOME": tmp, "OPENCODE_CONFIG_CONTENT":
                                            json.dumps({"command": custom})}, home / "repo")
            cfg = json.loads(env["OPENCODE_CONFIG_CONTENT"])
            for name, value in custom.items():
                self.assertEqual(cfg["command"][name], value)
            self.assertIn(str(project / "SKILL.md"), cfg["command"]["skill-skill-develop-prepare"]["template"])
            self.assertNotIn("develop-deliver", cfg["command"])
            self.assertIn("skill-develop-deliver", cfg["command"])
            self.assertNotIn("skill-develop-execute", cfg["command"])

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

    def test_prepare_delivery_resources_are_closed_over_in_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="delivery snapshot ") as tmp:
            bundle = launch.build_bundle(ROOT, Path(tmp))
            manifest = launch.validate_bundle(bundle)
            for name in ("develop-prepare", "develop-deliver"):
                skill = bundle / "config/skills" / manifest["skill_aliases"][name] / "SKILL.md"
                self.assertTrue(skill.is_file())
            self.assertTrue((bundle / "opencode/tracking/delivery.py").is_file())
            self.assertTrue((bundle / "opencode/tracking/references/delivery.md").is_file())
            prepare = (bundle / "opencode/skills/develop/develop-prepare/SKILL.md").read_text()
            self.assertIn("bug", prepare)
            self.assertIn(manifest["skill_aliases"]["develop-deliver"], prepare)
            execute = (bundle / "opencode/skills/develop/_lib/execute.md").read_text()
            self.assertIn("delivery run", execute)
            self.assertIn("three-cycle", execute)
