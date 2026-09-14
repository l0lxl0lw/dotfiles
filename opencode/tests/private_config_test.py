"""Private extension loading without touching user credentials or catalogs."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracking"))
import private_config
spec = importlib.util.spec_from_file_location("private_test_launch", ROOT / "runtime/launch.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class PrivateConfigTest(unittest.TestCase):
    def test_missing_optional_and_explicit_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(private_config.load({"HOME": tmp}), {})
            with self.assertRaisesRegex(RuntimeError, "does not exist"):
                private_config.load({"OPENCODE_PRIVATE_CONFIG": tmp + "/missing"})
            with patch.dict(os.environ, {"HOME": tmp}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "tracking.owner"):
                    private_config.tracking_project()

    def test_private_skill_discovery_and_project_identity_stay_out_of_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "private/skills/project-local"
            skills.mkdir(parents=True)
            (skills / "SKILL.md").write_text("---\nname: project-local\ndescription: private fixture\n---\nPRIVATE-SKILL-SENTINEL\n")
            config = root / "private/config.json"
            config.write_text(json.dumps({"version": 1, "skills_paths": ["skills"], "tracking": {"owner": "private-example", "number": 19}}))
            env = {"HOME": tmp, "OPENCODE_PRIVATE_CONFIG": str(config)}
            bundle = launch.build_bundle(ROOT, root / "state")
            actual = launch.environment(bundle, environ=env)
            cfg = json.loads(actual["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(cfg["skills"]["paths"], [str(skills.parent.resolve())])
            command = cfg["command"]["project-local"]
            self.assertIn("`project-local`", command["template"])
            self.assertIn("$ARGUMENTS", command["template"])
            self.assertNotIn("PRIVATE-SKILL-SENTINEL", actual["OPENCODE_CONFIG_CONTENT"])
            self.assertNotIn(str(skills), json.dumps(command))
            nested = launch.environment(bundle, environ=actual)
            self.assertEqual(json.loads(nested["OPENCODE_CONFIG_CONTENT"])["command"]["project-local"], command)
            self.assertEqual(launch.environment(bundle, environ=actual)["OPENCODE_CONFIG_DIR"], actual["OPENCODE_CONFIG_DIR"])
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(private_config.tracking_project(), ("private-example", 19))
            for path in bundle.rglob("*"):
                if path.is_file() and path.suffix in (".md", ".json"):
                    self.assertNotIn("PRIVATE-SKILL-SENTINEL", path.read_text())
            config.write_text(json.dumps({"version": 1, "skills_paths": []}))
            removed = launch.environment(bundle, environ=actual)
            self.assertNotIn("project-local", json.loads(removed["OPENCODE_CONFIG_CONTENT"])["command"])
            config.write_text(json.dumps({"version": 1, "skills_paths": ["skills"]}))
            (skills / "SKILL.md").write_text("---\nname: full-stack-slice\ndescription: collision\n---\n")
            with self.assertRaisesRegex(RuntimeError, "conflicts"):
                launch.environment(bundle, environ=env)

    def test_private_commands_refuse_public_inline_and_global_collisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills/local-task/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: local-task\ndescription: fixture\n---\nprivate body\n")
            config = root / "config.json"
            config.write_text(json.dumps({"version": 1, "skills_paths": ["skills"]}))
            env = {"HOME": tmp, "OPENCODE_PRIVATE_CONFIG": str(config)}
            bundle = launch.build_bundle(ROOT, root / "state")
            inline = {**env, "OPENCODE_CONFIG_CONTENT": json.dumps({"command": {"local-task": {"template": "user-owned"}}})}
            with self.assertRaisesRegex(RuntimeError, "conflicts with existing command"):
                launch.environment(bundle, environ=inline)
            global_command = root / ".config/opencode/commands/local-task.md"
            global_command.parent.mkdir(parents=True)
            global_command.write_text("user-owned command")
            with self.assertRaisesRegex(RuntimeError, "conflicts with existing command"):
                launch.environment(bundle, environ=env)
            global_command.unlink()
            # A public command without a same-named public skill must also be protected.
            skill.write_text("---\nname: track\ndescription: fixture\n---\nprivate body\n")
            with self.assertRaisesRegex(RuntimeError, "conflicts with existing command"):
                launch.environment(bundle, environ=env)
            skill.write_text("---\nname: invalid`name\ndescription: fixture\n---\n")
            with self.assertRaisesRegex(RuntimeError, "Invalid skill name"):
                launch.environment(bundle, environ=env)

    def test_invalid_schema_fails_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "private.json"
            p.write_text('{"version":1,"password":"SECRET-SENTINEL"}')
            with self.assertRaises(RuntimeError) as raised:
                private_config.load({"OPENCODE_PRIVATE_CONFIG": str(p)})
            self.assertNotIn("SECRET-SENTINEL", str(raised.exception))
