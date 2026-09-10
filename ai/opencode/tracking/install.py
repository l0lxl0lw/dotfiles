#!/usr/bin/env python3
"""Inspect/migrate the known Agentic install and install a launchd freshness monitor."""
import argparse
import base64
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", str(HOME / ".config"))) / "opencode"
STATE = HOME / ".local/state/opencode-track"
REV = "3a3915310d3d03d4a45114b7b0c0a17c34bf0e8b"
AGENTS = ["codebase-analyzer", "codebase-locator", "codebase-pattern-finder", "thoughts-analyzer", "thoughts-locator", "web-search-researcher"]
COMMANDS = ["ticket", "research", "plan", "execute", "commit", "review"]


def candidates():
    for singular, names in [("agent", AGENTS), ("command", COMMANDS)]:
        for folder in (singular, singular + "s"):
            for name in names:
                path = CONFIG / folder / (name + ".md")
                if path.is_symlink():
                    if path.resolve() == ROOT / (singular + "s") / path.name:
                        continue
                    raise RuntimeError("Inspect foreign symlink manually: " + str(path))
                if path.exists():
                    yield path, singular


def inspect():
    for path, singular in candidates():
        raw = subprocess.check_output(["gh", "api", "repos/Cluster444/agentic/contents/" + singular + "/" + path.name + "?ref=" + REV], text=True)
        upstream = base64.b64decode(json.loads(raw)["content"]).decode()
        local = path.read_text()
        print(str(path) + " sha256=" + hashlib.sha256(path.read_bytes()).hexdigest())
        if upstream == local:
            print("  Matches upstream")
        else:
            print("".join(difflib.unified_diff(upstream.splitlines(True), local.splitlines(True), fromfile="upstream", tofile=str(path))))


def migrate():
    paths = list(candidates())
    backup = STATE / "backups" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    if paths:
        backup.mkdir(parents=True, mode=0o700)
        for path, singular in paths:
            target = backup / path.relative_to(CONFIG)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            if target.read_bytes() != path.read_bytes():
                raise RuntimeError("Backup verification failed: " + str(path))
        # All backups complete before removing any active files.
        for path, singular in paths:
            path.unlink()
        print("Originals backed up to " + str(backup))
    for folder in ("agents", "commands"):
        (CONFIG / folder).mkdir(parents=True, exist_ok=True)
        for source in (ROOT / folder).glob("*.md"):
            dest = CONFIG / folder / source.name
            if dest.is_symlink() and dest.resolve() == source:
                continue
            if dest.exists() or dest.is_symlink():
                raise RuntimeError("Preserving unrelated collision: " + str(dest))
            dest.symlink_to(source)
    print("Managed agents and commands installed")


def monitor():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    agents = HOME / "Library/LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    label = "dev.dotfiles.opencode-track"
    path = agents / (label + ".plist")
    definition = {
        "Label": label,
        "ProgramArguments": [sys.executable, str(ROOT / "tracking/track.py"), "refresh"],
        "RunAtLoad": True,
        "StartInterval": 300,
        "ProcessType": "Background",
        "WorkingDirectory": str(HOME),
        "EnvironmentVariables": {"PATH": str(Path(shutil.which("gh")).parent) + ":/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", "GIT_TERMINAL_PROMPT": "0", "GH_PROMPT_DISABLED": "1", "PYTHONUNBUFFERED": "1"},
        "StandardOutPath": str(STATE / "monitor.log"),
        "StandardErrorPath": str(STATE / "monitor-error.log"),
    }
    if path.exists() and plistlib.loads(path.read_bytes()).get("Label") != label:
        raise RuntimeError("Unexpected launchd definition: " + str(path))
    domain = "gui/" + str(os.getuid())
    subprocess.run(["launchctl", "bootout", domain + "/" + label], capture_output=True)
    path.write_bytes(plistlib.dumps(definition))
    subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
    print("Installed 5-minute monitor: " + str(path))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["inspect", "migrate", "monitor"])
    args = p.parse_args()
    globals()[args.operation]()
