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
        for name in ("install", "zsh", "vim", "tmux", "emacs", "agents"):
            shutil.copytree(ROOT / name, self.repo / name)
        shutil.copy2(ROOT / "deploy.sh", self.repo / "deploy.sh")
        # Read-only fixture sources; integrations only link to them.
        (self.repo / "ai").symlink_to(ROOT / "ai", target_is_directory=True)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CODEX", "GROK", "XDG", "DOTFILES", "OPENCODE", "LIFE_MEMORY", "ZDOTDIR", "BACKUP"))}
        self.env.update(HOME=str(self.home), ROOT=str(self.repo), PATH=f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin", PYTHONDONTWRITEBYTECODE="1")
        # Never let a test reach the real Orca app through its bundle path.
        self.env["ORCA_CLI_COMMAND"] = str(self.home / "no-orca")
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

    def make_hub(self, name, skill="hub-skill", agent="hub-agent", persona="Persona."):
        """A hub under $HOME/<name> with one skill, one rendered agent and a persona, listed in the hubs file."""
        hub = self.home / name
        (hub / "skills" / skill).mkdir(parents=True)
        (hub / "skills" / skill / "SKILL.md").write_text(f"---\nname: {skill}\ndescription: {skill}\n---\n")
        (hub / "agents/src").mkdir(parents=True)
        (hub / "agents/src" / f"{agent}.md").write_text(f"---\nname: {agent}\ndescription: {agent}\ntier: fast\naccess: research\n---\n\nBody.\n")
        (hub / "tiers.json").write_text('{"codex": {"fast": {"model": "gpt-6-luna"}}}')
        (hub / "persona").mkdir()
        (hub / "persona/global.md").write_text(persona + "\n")
        subprocess.run([sys.executable, "-B", str(self.repo / "agents/render.py"), "--hub", str(hub)], check=True, capture_output=True)
        hubs = self.home / ".config/dotfiles/hubs"
        hubs.parent.mkdir(parents=True, exist_ok=True)
        with hubs.open("a") as f:
            f.write(str(hub) + "\n")
        return hub

    def orca_stub(self, log):
        self.env["ORCA_CLI_COMMAND"] = str(self.bin / "orca")
        self.stub("orca", f'printf \'%s\\n\' "$*" >> "{log}"; case "$1 $2 $3" in "agent hooks status") echo "claude: installed"; echo "codex: installed"; echo "opencode: installed";; esac; exit 0')

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
        self.deploy("--dry-run", "--only", "codex,vim")
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
        self.assertFalse((cfg.parent / "AGENTS.md").exists(), "no hub, so no generated AGENTS.md")
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
        # No hubs file: nothing is linked, but the tool-specific extras still run.
        self.assertIn("# >>> dotfiles managed >>>", (self.home / ".codex/config.toml").read_text())

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

    def test_hub_skills_agents_and_persona_linked_and_pruned(self):
        hub = self.make_hub("zubot", skill="hub-skill", agent="hub-agent", persona="Be warm.")
        (self.home / ".codex").mkdir()
        (self.home / ".claude/skills").mkdir(parents=True)
        stale = self.home / ".claude/skills/deleted-skill"
        stale.symlink_to(self.home / "dotfiles-private/.claude/skills/deleted-skill")

        sync = 'source "$HOME/dotfiles/zsh/functions.zsh"; claude_merge_config && codex_merge_config'
        for _ in range(2):
            proc = subprocess.run(["/bin/zsh", "-f", "-c", sync], env=self.env, text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        self.assertEqual(os.readlink(self.home / ".claude/skills/hub-skill"), str(hub / "skills/hub-skill"))
        self.assertEqual(os.readlink(self.home / ".codex/skills/hub-skill"), str(hub / "skills/hub-skill"))
        self.assertEqual(os.readlink(self.home / ".claude/agents/hub-agent.md"), str(hub / ".claude/agents/hub-agent.md"))
        self.assertTrue((self.home / ".codex/agents/hub-agent.toml").is_file())
        self.assertIn("## zubot\n\nBe warm.", (self.home / ".claude/CLAUDE.md").read_text())
        self.assertIn("Be warm.", (self.home / ".codex/AGENTS.md").read_text())
        self.assertFalse(stale.is_symlink())
        self.assertEqual(proc.stdout, "", "second sync should converge silently")

        (self.home / ".config/dotfiles/hubs").write_text("")
        proc = subprocess.run(["/bin/zsh", "-f", "-c", sync], env=self.env, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((self.home / ".claude/skills/hub-skill").is_symlink())
        self.assertFalse((self.home / ".codex/agents/hub-agent.toml").exists())
        self.assertNotIn("Be warm.", (self.home / ".claude/CLAUDE.md").read_text())

    def test_hubs_module_runs_hubs_sync_and_orca(self):
        hub = self.make_hub("zubot")
        log = self.home / "orca.log"
        self.orca_stub(log)
        (self.home / ".claude").mkdir()
        (self.home / ".codex").mkdir()
        proc = self.deploy("--only", "hubs", answers="y\n")
        self.assertEqual(os.readlink(self.home / ".claude/skills/hub-skill"), str(hub / "skills/hub-skill"))
        self.assertTrue((self.home / ".codex/agents/hub-agent.toml").is_file())
        calls = log.read_text().splitlines()
        self.assertIn("skills install --all", calls)
        self.assertIn("agent hooks on", calls)
        self.assertIn("hubs: completed", proc.stdout)

    def test_hubs_module_without_orca_is_quiet(self):
        self.make_hub("zubot")
        (self.home / ".claude").mkdir()
        proc = self.deploy("--only", "hubs", answers="y\n")
        self.assertNotIn("orca", proc.stdout.lower())
        self.assertIn("hubs: completed", proc.stdout)

    def test_hubs_module_reports_orca_failure_without_aborting(self):
        self.make_hub("zubot")
        self.stub("orca", 'echo "boom" >&2; exit 1')
        self.env["ORCA_CLI_COMMAND"] = str(self.bin / "orca")
        (self.home / ".claude").mkdir()
        proc = self.deploy("--only", "hubs", answers="y\n")
        self.assertIn("hubs: completed", proc.stdout)
        self.assertIn("orca", proc.stdout.lower())

    def test_opencode_module_offers_brew_and_syncs(self):
        self.make_hub("zubot")
        self.stub("brew", 'echo "brew $*"; if [[ "$1" == install ]]; then printf "exit 0" > "$HOME/bin/opencode"; chmod +x "$HOME/bin/opencode"; fi')
        proc = self.deploy("--only", "opencode", answers="y\ny\n")
        self.assertIn("brew install --formula opencode", proc.stdout)
        self.assertTrue((self.home / ".config/opencode/skills/hub-skill").is_symlink())
        self.assertTrue((self.home / ".config/opencode/agents/hub-agent.md").is_file())
        self.assertIn("Persona.", (self.home / ".config/opencode/AGENTS.md").read_text())

    def test_doctor_lists_each_hub_state_and_render_drift(self):
        hub = self.make_hub("zubot")
        with (self.home / ".config/dotfiles/hubs").open("a") as f:
            f.write(str(self.home / "absent") + "\n")
        (hub / "agents/src/hub-agent.md").write_text("---\nname: hub-agent\ndescription: changed\ntier: fast\naccess: research\n---\n\nBody.\n")
        log = self.home / "orca.log"
        self.orca_stub(log)
        proc = self.deploy("--doctor")
        self.assertIn(f"{self.home / 'absent'}: missing", proc.stdout)
        self.assertIn(f"{hub}: render drift", proc.stdout)
        self.assertNotIn(f"{hub}: ok", proc.stdout)
        self.assertIn("opencode: installed", proc.stdout)

    def test_doctor_reports_no_drift_when_rendered(self):
        hub = self.make_hub("zubot")
        proc = self.deploy("--doctor")
        self.assertNotIn("render drift", proc.stdout)
        self.assertIn(f"{hub}: ok", proc.stdout)

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

    def test_claude_hooks_for_missing_scripts_removed(self):
        self.stub("claude", "exit 0")
        self.deploy("--only", "claude", answers="y\n")
        settings = self.home / ".claude/settings.json"
        dead = {"type": "command", "command": "sh ~/.claude/hooks/retired.sh"}
        live = {"type": "command", "command": "sh ~/.claude/hooks/statusline.sh"}
        foreign = {"type": "command", "command": "node /opt/other/hook.js"}
        data = json.loads(settings.read_text())
        data["hooks"] = {
            "UserPromptSubmit": [{"hooks": [dead]}, {"hooks": [foreign, dead]}],
            "PreToolUse": [{"matcher": "Bash", "hooks": [live]}],
            "Stop": [{"hooks": [dead]}],
        }
        settings.write_text(json.dumps(data))

        # The launch-time sync only reports; the installer asks first.
        sync = 'source "$HOME/dotfiles/zsh/functions.zsh"; claude_merge_config'
        proc = subprocess.run(["/bin/zsh", "-f", "-c", sync], env=self.env, text=True, capture_output=True)
        self.assertIn("removed hooks for missing retired.sh", proc.stderr)
        self.assertEqual(json.loads(settings.read_text()), data)

        self.deploy("--only", "claude", answers="y\nb\n")
        self.assertEqual(json.loads(settings.read_text())["hooks"], {
            "UserPromptSubmit": [{"hooks": [foreign]}],
            "PreToolUse": [{"matcher": "Bash", "hooks": [live]}],
        })
        self.assertEqual(len(self.manifests()), 1)
        proc = subprocess.run(["/bin/zsh", "-f", "-c", sync], env=self.env, text=True, capture_output=True)
        self.assertEqual(proc.stdout + proc.stderr, "", "second sync should converge silently")


if __name__ == "__main__":
    unittest.main()
