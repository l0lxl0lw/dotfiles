#!/usr/bin/env python3
"""Install the launchd branch-freshness monitor."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
STATE = HOME / ".local/state/opencode-track"


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
    p.add_argument("operation", choices=["monitor"])
    args = p.parse_args()
    monitor()
