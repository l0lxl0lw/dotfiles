"""Portable settings tests use isolated source, config and state directories."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("opencode_settings", ROOT / "settings/manage.py")
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="settings space ")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "dotfiles/ai/opencode"
        (self.root / "settings").mkdir(parents=True)
        self.write_source({"websearch": False, "instructions": ["{config_dir}/browser-preferences.md"]})
        (self.root / "cli.json").write_text('{"theme":{"name":"portable"}}\n')
        (self.root / "settings/browser-preferences.md").write_text("Use Google via Orca.\n")
        self.settings = manage.Settings(self.root, base / "config space/opencode", base / "state")

    def write_source(self, data):
        (self.root / "settings/opencode.json").write_text(manage.encode(data))

    def write_local(self, data, name="opencode.json"):
        self.settings.config.mkdir(parents=True, exist_ok=True)
        (self.settings.config / name).write_text(manage.encode(data))

    def local(self, name="opencode.json"):
        return manage.object_file(self.settings.config / name)

    def apply(self, **kwargs):
        return self.settings.apply(yes=True, **kwargs)

    def test_fresh_apply_writable_portable_and_idempotent(self):
        self.assertEqual(self.apply(), 0)
        path = self.settings.config / "opencode.json"
        self.assertFalse(path.is_symlink())
        self.assertEqual(self.local()["instructions"], [str(self.settings.config / "browser-preferences.md")])
        stamp = path.stat().st_mtime_ns
        state_stamp = (self.settings.state / "applied.json").stat().st_mtime_ns
        self.assertEqual(self.apply(), 0)
        self.assertEqual(path.stat().st_mtime_ns, stamp)
        self.assertEqual((self.settings.state / "applied.json").stat().st_mtime_ns, state_stamp)

    def test_status_does_not_create_directories(self):
        self.settings.plan()
        self.assertFalse(self.settings.state.exists())
        self.assertFalse(self.settings.config.exists())

    def test_sync_does_not_initialize_absent_app(self):
        self.assertEqual(self.settings.apply(sync=True), 0)
        self.assertFalse(self.settings.state.exists())
        self.assertFalse(self.settings.config.exists())

    def test_preserves_integrations_and_local_array_entries(self):
        private = {"mcp": {"private": {"url": "http://localhost", "headers": {"Authorization": "secret-fixture"}}},
                   "instructions": ["/private/notes.md"]}
        self.write_local(private)
        self.assertEqual(self.apply(), 0)
        self.assertEqual(self.local()["mcp"], private["mcp"])
        self.assertIn("/private/notes.md", self.local()["instructions"])
        state = (self.settings.state / "applied.json").read_text()
        self.assertNotIn("secret-fixture", state)

    def test_local_changes_stay_local_until_explicit_import(self):
        self.apply()
        self.write_local({**self.local(), "websearch": {"provider": "random"}})
        source = (self.root / "settings/opencode.json").read_text()
        self.assertEqual(self.settings.apply(sync=True), 0)
        self.assertEqual(self.local()["websearch"], {"provider": "random"})
        self.assertEqual((self.root / "settings/opencode.json").read_text(), source)
        self.assertEqual(self.apply(), 2)
        with self.settings.lock():
            self.assertEqual(self.settings.import_keys("opencode.json", ["/websearch"], yes=True), 0)
        self.assertEqual(self.apply(), 0)
        self.assertFalse(self.settings.plan()[2])

    def test_repo_update_and_owned_removal_preserve_foreign_entries(self):
        self.apply()
        self.write_local({**self.local(), "instructions": [*self.local()["instructions"], "/private/extra.md"], "model": "local/model"})
        self.write_source({"websearch": True})
        self.assertEqual(self.apply(), 0)
        self.assertEqual(self.local(), {"websearch": True, "instructions": ["/private/extra.md"], "model": "local/model"})

    def test_conflict_requires_explicit_force_and_is_backed_up(self):
        self.apply()
        self.write_local({**self.local(), "websearch": True})
        before = (self.settings.config / "opencode.json").read_text()
        self.assertEqual(self.apply(), 2)
        self.assertEqual(self.apply(force=True), 0)
        self.assertFalse(self.local()["websearch"])
        backups = list((self.settings.state / "backups").glob("opencode.json.*"))
        self.assertTrue(any(p.read_text() == before for p in backups))
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in backups))

    def test_owned_cli_symlink_migration_never_writes_source(self):
        self.settings.config.mkdir(parents=True)
        target = self.settings.config / "cli.json"
        target.symlink_to(self.root / "cli.json")
        before = (self.root / "cli.json").read_text()
        self.assertEqual(self.apply(), 2)
        self.assertEqual(self.apply(force=True), 0)
        self.assertFalse(target.is_symlink())
        self.assertEqual((self.root / "cli.json").read_text(), before)

    def test_foreign_symlink_and_jsonc_are_never_overwritten(self):
        self.settings.config.mkdir(parents=True)
        foreign = Path(self.tmp.name) / "foreign.json"
        foreign.write_text("{}")
        (self.settings.config / "opencode.json").symlink_to(foreign)
        self.assertEqual(self.apply(force=True), 2)
        self.assertEqual(foreign.read_text(), "{}")
        (self.settings.config / "opencode.jsonc").write_text('{/* keep */ "model":"private"}')
        with self.assertRaisesRegex(ValueError, "JSONC"):
            self.settings.plan()

    def test_sensitive_and_machine_specific_imports_rejected(self):
        for at, value in [(('providers',), {}), (('model',), '/Users/person/model'),
                          (('websearch',), {'apiKey': 'fixture'}), (('websearch', 'apiKey'), 'fixture'),
                          (('warming',), {'prompt': 'private conversation'})]:
            with self.subTest(at=at), self.assertRaises(ValueError):
                manage.Settings.portable(at, value)

    def test_selected_import_only_and_cancellation(self):
        self.apply()
        self.write_local({**self.local(), "model": "provider/new", "mcp": {"secret": {"apiKey": "fixture"}}})
        source = self.root / "settings/opencode.json"
        before = source.read_text()
        with patch('builtins.input', return_value='n'):
            self.assertEqual(self.settings.import_keys("opencode.json", ["/model"]), 2)
        self.assertEqual(source.read_text(), before)
        self.assertEqual(self.settings.import_keys("opencode.json", ["/model"], yes=True), 0)
        self.assertEqual(manage.object_file(source)["model"], "provider/new")
        self.assertNotIn("mcp", manage.object_file(source))

    def test_local_removed_owned_array_entry_is_drift(self):
        self.apply()
        self.write_local({**self.local(), "instructions": []})
        self.settings.apply(sync=True)
        self.assertEqual(self.local()["instructions"], [])
        self.assertTrue(self.settings.plan()[2])

    def test_external_write_during_confirmation_aborts(self):
        self.apply()
        self.write_source({"websearch": True})
        def edit(_):
            self.write_local({"model": "external/edit"})
            return 'y'
        with patch('builtins.input', side_effect=edit), self.assertRaisesRegex(ValueError, "changed during apply"):
            self.settings.apply()
        self.assertEqual(self.local(), {"model": "external/edit"})

    def test_scalar_object_transitions_and_nested_removals(self):
        self.apply()
        self.write_source({"websearch": {"provider": "random"}})
        self.assertEqual(self.apply(), 0)
        self.assertEqual(self.local()["websearch"], {"provider": "random"})
        self.write_source({"websearch": False})
        self.assertEqual(self.apply(), 0)
        self.assertFalse(self.local()["websearch"])
        self.assertFalse(self.settings.plan()[2])

    def test_parent_replacement_does_not_discard_unowned_nested_values(self):
        self.write_source({"watcher": {"ignore": ["dist"]}})
        self.apply()
        self.write_local({**self.local(), "watcher": {"ignore": ["dist"], "local": "keep"}})
        self.write_source({"watcher": False})
        self.assertEqual(self.apply(), 2)
        self.assertEqual(self.local()["watcher"]["local"], "keep")
        self.settings.apply(sync=True)
        self.assertEqual(self.local()["watcher"], {"ignore": ["dist"], "local": "keep"})

    def test_ordered_arrays_are_not_union_merged(self):
        original = [{"action": "shell", "effect": "deny"}]
        replacement = [{"action": "shell", "effect": "allow"}]
        self.write_source({"permissions": original})
        self.apply()
        self.write_source({"permissions": replacement})
        self.assertEqual(self.apply(), 0)
        self.assertEqual(self.local()["permissions"], replacement)

    def test_tracked_list_order_changes_are_propagated(self):
        self.write_source({"instructions": ["first.md", "second.md"]})
        self.write_local({"instructions": ["foreign.md"]})
        self.apply()
        self.write_source({"instructions": ["second.md", "first.md"]})
        self.apply()
        self.assertEqual(self.local()["instructions"], ["foreign.md", "second.md", "first.md"])

    def test_status_lists_untracked_preferences_without_values(self):
        self.write_local({"model": "sensitive-fixture", "mcp": {"private": {"key": "secret"}}})
        self.assertEqual(self.settings.local_only(), ["local-only opencode.json/model (not tracked; import explicitly)"])
        self.assertFalse(self.settings.state.exists())

    def test_optional_local_plugin_is_enabled_after_installation(self):
        (self.root / "cli.json").write_text(manage.encode({"plugins": ["file://{config_dir}/plugins/status.js"]}))
        self.write_local({"plugins": ["foreign-plugin"]}, "cli.json")
        self.apply()
        self.assertEqual(self.local("cli.json")["plugins"], ["foreign-plugin"])
        plugin = self.settings.config / "plugins/status.js"
        plugin.parent.mkdir()
        plugin.write_text("export default {}")
        self.apply()
        self.assertEqual(self.local("cli.json")["plugins"], ["foreign-plugin", plugin.as_uri()])

    def test_legacy_instruction_path_normalization_is_idempotent(self):
        # Home-relative spelling refers to the same installed instruction file.
        with patch.object(manage.Path, "home", return_value=self.settings.config.parent):
            self.write_local({"instructions": ["~/opencode/browser-preferences.md"]})
            with patch.dict('os.environ', {'HOME': str(self.settings.config.parent)}):
                self.apply()
                self.assertEqual(self.local()["instructions"], [str(self.settings.config / "browser-preferences.md")])
                self.assertFalse(self.settings.plan()[2])


if __name__ == "__main__":
    unittest.main()
