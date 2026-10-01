"""Installer acceptance in isolated homes; no package installs or network access."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dotfiles test ")
        self.home = Path(self.tmp.name).resolve()
        self.repo = self.home / "dotfiles"
        self.repo.mkdir()
        for name in ("install", "zsh", "vim", "tmux", "emacs"):
            shutil.copytree(ROOT / name, self.repo / name)
        shutil.copy2(ROOT / "deploy.sh", self.repo / "deploy.sh")
        # Read-only fixture sources; integrations only link to them.
        (self.repo / "ai").symlink_to(ROOT / "ai", target_is_directory=True)
        (self.repo / "opencode").symlink_to(ROOT / "opencode", target_is_directory=True)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CODEX", "GROK", "XDG", "DOTFILES", "OPENCODE", "LIFE_MEMORY", "ZDOTDIR", "BACKUP"))}
        self.env.update(HOME=str(self.home), ROOT=str(self.repo), PATH=f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin", PYTHONDONTWRITEBYTECODE="1")
        self.stub("xcode-select", "exit 0")
        self.stub("uname", 'case "$1" in -s) echo Darwin;; -m) echo arm64;; esac')
        self.stub("brew", 'echo "unexpected brew call" >&2; exit 99')

    def tearDown(self):
        self.tmp.cleanup()

    def stub(self, name, body):
        target = self.bin / name
        target.write_text("#!/bin/bash\n" + body + "\n")
        target.chmod(0o755)

    def shell(self, body, answers="", expected=0):
        proc = subprocess.run(["/bin/bash", "-c", 'set -euo pipefail; source "$ROOT/install/lib.sh"; ' + body], env=self.env, input=answers, text=True, capture_output=True)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return proc

    def deploy(self, *args, answers="", expected=0):
        proc = subprocess.run(["/bin/bash", str(self.repo / "deploy.sh"), *args], env=self.env, input=answers, text=True, capture_output=True)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return proc

    def manifests(self):
        return list((self.home / ".local/state/dotfiles/backups").glob("*/manifest.tsv"))

    def test_fresh_vim_and_idempotent_rerun(self):
        self.deploy("--only", "vim", answers="y\n")
        target = self.home / ".vimrc"
        self.assertEqual(target.readlink(), self.repo / "vim/vimrc.conf")
        before = target.lstat().st_mtime_ns
        self.deploy("--only", "vim", answers="y\n")
        self.assertEqual(target.lstat().st_mtime_ns, before)
        self.assertFalse(self.manifests())

    def test_backup_skip_and_restore(self):
        target = self.home / ".vimrc"
        target.write_text("my configuration")
        self.deploy("--only", "vim", answers="y\ns\n")
        self.assertEqual(target.read_text(), "my configuration")
        self.deploy("--only", "vim", answers="y\nb\n")
        manifest = self.manifests()[0]
        slot, dst = manifest.read_text().strip().split("\t")
        self.assertEqual(dst, str(target))
        self.assertEqual((manifest.parent / slot / "original").read_text(), "my configuration")
        self.deploy("--restore", manifest.parent.name, answers="y\n")
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_text(), "my configuration")
        self.assertEqual(len(self.manifests()), 2)

    def test_foreign_and_dangling_symlinks_preserved_in_backup(self):
        for name, destination in (("live", self.home / "foreign"), ("broken", self.home / "missing")):
            if name == "live":
                destination.mkdir()
                (destination / "keep").write_text("foreign")
            target = self.home / name
            target.symlink_to(destination)
            self.shell(f'link_file "$ROOT/vim/vimrc.conf" "$HOME/{name}"', "b\n")
            self.assertEqual(target.readlink(), self.repo / "vim/vimrc.conf")
        self.assertEqual((self.home / "foreign/keep").read_text(), "foreign")
        originals = [m.parent / row.split("\t")[0] / "original" for m in self.manifests() for row in m.read_text().splitlines()]
        self.assertEqual(len(originals), 2)
        self.assertTrue(all(p.is_symlink() for p in originals))

    def test_existing_directory_backup_and_no_backup_choice(self):
        target = self.home / "directory"
        target.mkdir()
        (target / "keep").write_text("content")
        self.shell('link_file "$ROOT/vim/vimrc.conf" "$HOME/directory"', "b\n")
        self.assertTrue(target.is_symlink())
        self.assertEqual(next((self.home / ".local/state/dotfiles/backups").glob("*/item.*/original/keep")).read_text(), "content")
        other = self.home / "other"
        other.write_text("old")
        self.shell('link_file "$ROOT/vim/vimrc.conf" "$HOME/other"', "n\n")
        self.assertEqual(len(self.manifests()), 1)

    def test_eof_and_cancel_do_not_overwrite(self):
        target = self.home / ".vimrc"
        target.write_text("keep")
        self.deploy("--only", "vim", answers="y\n", expected=1)
        self.deploy("--only", "vim", answers="y\nc\n", expected=130)
        self.assertEqual(target.read_text(), "keep")

    def test_dry_run_and_doctor_do_not_write(self):
        before = sorted(str(p) for p in self.home.rglob("*"))
        self.deploy("--dry-run", "--only", "codex,opencode,vim")
        self.deploy("--doctor")
        self.assertEqual(sorted(str(p) for p in self.home.rglob("*")), before)

    def test_missing_tool_decline_and_failed_install(self):
        self.shell('ensure_tool nonexistent-cli example', "n\n", expected=2)
        self.shell('ensure_tool nonexistent-cli example', "y\n", expected=99)

    def test_missing_tool_install_and_verify(self):
        self.stub("brew", 'printf "#!/bin/bash\\nexit 0\\n" > "$HOME/bin/new-cli"; chmod +x "$HOME/bin/new-cli"')
        self.shell('ensure_tool new-cli example', "y\n")
        self.assertTrue((self.bin / "new-cli").exists())

    def test_symlink_parent_refused(self):
        (self.home / "foreign").mkdir()
        (self.home / "config").symlink_to(self.home / "foreign")
        self.shell('link_file "$ROOT/vim/vimrc.conf" "$HOME/config/test"', expected=2)
        self.assertFalse((self.home / "foreign/test").exists())

    def test_failed_clone_stops_module(self):
        self.stub("git", "exit 42")
        self.deploy("--only", "zsh", answers="y\n", expected=1)
        self.assertFalse((self.home / ".zshrc").exists())

    def test_new_module_discovered(self):
        (self.repo / "install/modules/example.sh").write_text('install_component() { say "EXAMPLE MODULE"; }\n')
        result = self.deploy("--only", "example", answers="y\n")
        self.assertIn("EXAMPLE MODULE", result.stdout)

    def test_unknown_component_rejected_before_writes(self):
        self.deploy("--only", "vim,no-such-module", expected=1)
        self.assertFalse((self.home / ".vimrc").exists())

    def test_shell_startup_without_optional_dependencies_or_network(self):
        self.stub("git", 'echo "network command attempted" >&2; exit 99')
        self.stub("curl", 'echo "network command attempted" >&2; exit 99')
        proc = subprocess.run(["/bin/zsh", "-f", "-c", 'source "$HOME/dotfiles/zsh/zshrc.conf"'], env=self.env, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / ".tmux").exists())

    def test_fresh_codex_custom_home_and_repeated_setup(self):
        self.stub("codex", "exit 0")
        self.env["CODEX_HOME"] = str(self.home / "account home")
        self.deploy("--only", "codex", answers="y\nn\n")
        cfg = self.home / "account home/config.toml"
        self.assertIn("# >>> dotfiles managed >>>", cfg.read_text())
        self.assertTrue((cfg.parent / "AGENTS.md").is_symlink())
        self.assertFalse((self.home / ".codex").exists())
        before = cfg.stat().st_mtime_ns
        self.deploy("--only", "codex", answers="y\n")
        self.assertEqual(before, cfg.stat().st_mtime_ns)

    def test_declined_ai_stays_disabled_until_successful_setup(self):
        self.stub("codex", "exit 0")
        (self.home / ".codex").mkdir()
        self.deploy("--only", "codex", answers="n\n")
        marker = self.home / ".local/state/dotfiles/disabled-sync/codex"
        self.assertTrue(marker.exists())
        proc = subprocess.run(["/bin/zsh", "-f", "-c", 'source "$HOME/dotfiles/zsh/functions.zsh"; codex_merge_config'], env=self.env, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse((self.home / ".codex/skills").exists())
        self.deploy("--only", "codex", answers="y\nn\n")
        self.assertFalse(marker.exists())
        self.assertTrue((self.home / ".codex/skills").exists())

    def test_invalid_codex_candidate_preserves_original(self):
        self.stub("codex", "exit 1")
        cfg = self.home / ".codex/config.toml"
        cfg.parent.mkdir()
        cfg.write_text('[tui]\nstatus_line = ["model-name"]\n')
        proc = self.deploy("--only", "codex", answers="y\nb\n")
        self.assertIn("action needed", proc.stdout)
        self.assertEqual(cfg.read_text(), '[tui]\nstatus_line = ["model-name"]\n')
        self.assertEqual(len(self.manifests()), 1)

    def test_ai_foreign_skill_collision_skip(self):
        self.stub("codex", "exit 0")
        dst = self.home / ".codex/AGENTS.md"
        dst.parent.mkdir()
        dst.write_text("my rules")
        proc = self.deploy("--only", "codex", answers="y\ns\nn\n")
        self.assertEqual(dst.read_text(), "my rules")
        self.assertIn("action needed", proc.stdout)

    def test_claude_initial_settings_and_existing_settings_merge(self):
        self.stub("claude", "exit 0")
        self.deploy("--only", "claude", answers="y\n")
        settings = self.home / ".claude/settings.json"
        self.assertEqual(json.loads(settings.read_text())["statusLine"]["command"], "sh ~/.claude/hooks/statusline.sh")
        settings.write_text(json.dumps({"env": {"KEEP": "value"}, "statusLine": {"command": "old"}}))
        self.deploy("--only", "claude", answers="y\nb\n")
        data = json.loads(settings.read_text())
        self.assertEqual(data["env"], {"KEEP": "value"})
        self.assertEqual(data["statusLine"]["command"], "sh ~/.claude/hooks/statusline.sh")
        self.assertEqual(len(self.manifests()), 1)

    def test_opencode_initial_config_custom_xdg_preserves_json(self):
        self.stub("opencode", "exit 0")
        self.stub("gh", "exit 0")
        self.env["XDG_CONFIG_HOME"] = str(self.home / "custom config")
        config = self.home / "custom config/opencode"
        self.deploy("--only", "opencode", answers="y\n")
        self.assertTrue((config / "tui.json").is_symlink())
        settings = config / "opencode.json"
        settings.write_text('{"model":"keep/model"}')
        self.deploy("--only", "opencode", answers="y\n")
        self.assertEqual(settings.read_text(), '{"model":"keep/model"}')
        self.assertFalse((self.home / ".config/opencode").exists())

    def test_memory_existing_vault_mismatch_fails_before_writing(self):
        cfg = self.home / ".config/life-memory/config.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"vault": str(self.home / "original")}))
        proc = self.memory_setup("--clients", "codex", "--vault", str(self.home / "other"))
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse((self.home / "other").exists())

    def memory_setup(self, *args):
        python = self.home / ".local/share/life-memory-venv/bin/python"
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_text("#!/bin/sh\nexit 0\n")
        python.chmod(0o755)
        return subprocess.run([sys.executable, str(ROOT / "ai/memory/setup.py"), *args], env=self.env, text=True, capture_output=True)

    def test_memory_only_configures_selected_client_and_paths(self):
        self.env["CODEX_HOME"] = str(self.home / "account")
        vault = self.home / "my vault"
        backup = self.home / "my backups"
        proc = self.memory_setup("--clients", "codex", "--vault", str(vault), "--backup", str(backup))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((self.home / "account/hooks.json").is_file())
        self.assertFalse((self.home / ".claude").exists())
        self.assertFalse((self.home / ".config/opencode").exists())
        cfg = json.loads((self.home / ".config/life-memory/config.json").read_text())
        self.assertEqual(cfg["vault"], str(vault))
        self.assertEqual(cfg["backup"], str(backup))

    def test_memory_jsonc_conflict_fails_before_creating_vault(self):
        config = self.home / "custom config/opencode"
        config.mkdir(parents=True)
        (config / "opencode.jsonc").write_text('{/* keep */ "model": "my/model"}')
        self.env["XDG_CONFIG_HOME"] = str(config.parent)
        proc = self.memory_setup("--clients", "opencode")
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse((self.home / "Documents/Life").exists())
        self.assertFalse((config / "opencode.json").exists())


if __name__ == "__main__":
    unittest.main()
