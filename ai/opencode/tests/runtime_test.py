"""Snapshot behavior without paid models or changing real HOME."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_launch", ROOT / "runtime/launch.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class RuntimeTest(unittest.TestCase):
    def test_snapshot_isolated_from_live_edits_and_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="workflow snapshot space ") as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "tracking").mkdir()
            target = source / "tracking/procedure.md"
            target.write_text("Run python3 ~/dotfiles/ai/opencode/tracking/handoff.py packet\n")
            bundle = launch.build_bundle(source, Path(tmp) / "state")
            content = (bundle / "opencode/tracking/procedure.md").read_text()
            self.assertIn('python3 "' + str(bundle), content)
            self.assertNotIn("~/dotfiles", content)
            self.assertEqual(launch.build_bundle(source, Path(tmp) / "state"), bundle)
            target.write_text("new live procedure\n")
            self.assertEqual((bundle / "opencode/tracking/procedure.md").read_text(), content)
            self.assertNotEqual(launch.build_bundle(source, Path(tmp) / "state"), bundle)
            (bundle / "opencode/tracking/procedure.md").write_text("tampered")
            with self.assertRaisesRegex(RuntimeError, "changed"):
                launch.validate_bundle(bundle)

    def test_snapshot_preserves_user_configuration_and_nested_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = launch.build_bundle(ROOT, Path(tmp))
            env = {"HOME": "/real/home", "GH_TOKEN": "private-fixture-token", "OPENCODE_CONFIG_CONTENT": json.dumps({"model": "local/keep", "agent": {"custom": {"description": "keep"}}})}
            actual = launch.environment(bundle, environ=env)
            cfg = json.loads(actual["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(actual["HOME"], env["HOME"])
            self.assertEqual(actual["GH_TOKEN"], env["GH_TOKEN"])
            self.assertEqual(cfg["agent"], {"custom": {"description": "keep"}})
            self.assertEqual(cfg["model"], "local/keep")
            self.assertFalse({"ticket", "research", "plan", "execute", "review", "commit"} & cfg["command"].keys())
            self.assertTrue({"sync", "track", "orca-coordinate", "orca-handoff"} <= cfg["command"].keys())
            self.assertEqual(launch.environment(bundle, environ=actual), actual)
            self.assertNotIn("private-fixture-token", (bundle / "manifest.json").read_text())
            with self.assertRaisesRegex(RuntimeError, "does not exist"):
                launch.environment(bundle, environ={"OPENCODE_CONFIG_DIR": "/unrelated/custom"})

    def test_orca_hooks_and_custom_agents_are_preserved_without_home_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = launch.build_bundle(ROOT, Path(tmp) / "state")
            custom = Path(tmp) / "orca config"
            (custom / "plugins").mkdir(parents=True)
            (custom / "plugins/hook.js").write_text("export default async()=>({})")
            (custom / "agents").mkdir()
            (custom / "agents/vendor.md").write_text("vendor agent")
            env = launch.environment(bundle, environ={"HOME": "/real/home", "OPENCODE_CONFIG_DIR": str(custom)})
            bridge = Path(env["OPENCODE_CONFIG_DIR"])
            self.assertEqual((bridge / "plugins/hook.js").resolve(), (custom / "plugins/hook.js").resolve())
            self.assertEqual((bridge / "agents/vendor.md").resolve(), (custom / "agents/vendor.md").resolve())
            self.assertEqual(launch.environment(bundle, environ=env)["OPENCODE_CONFIG_DIR"], str(bridge))
            self.assertEqual(env["HOME"], "/real/home")
            (custom / "agents/codebase-analyzer.md").write_text("conflicting custom worker")
            with self.assertRaisesRegex(RuntimeError, "conflicts"):
                launch.environment(bundle, environ={"OPENCODE_CONFIG_DIR": str(custom)})

    def test_retained_commands_resolve_their_agents(self):
        commands = list((ROOT / "commands").glob("*.md"))
        self.assertTrue(commands)
        for path in commands:
            agent = launch.definition(path).get("agent", "build")
            self.assertTrue(agent in {"build", "plan"} or (ROOT / "agents" / (agent + ".md")).is_file(), path)
