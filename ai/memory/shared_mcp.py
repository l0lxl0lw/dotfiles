#!/usr/bin/env python3
"""On-demand, launchd-owned Life MCP service. Only stdlib is loaded by clients."""
import fcntl
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

LABEL = "local.life-memory.mcp"
URL = "http://127.0.0.1:8766/mcp"


def ready():
    """Verify MCP identity, not merely an open TCP port; release probe sessions."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-03-26", "capabilities": {},
        "clientInfo": {"name": "life-memory-startup", "version": "1"}}}).encode()
    request = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            session = response.headers.get("mcp-session-id")
            raw = response.read().decode()
        if raw.startswith("event:") or raw.startswith("data:"):
            raw = next(line[6:] for line in raw.splitlines() if line.startswith("data: "))
        result = json.loads(raw).get("result", {})
        if session:
            delete = urllib.request.Request(URL, method="DELETE", headers={"mcp-session-id": session})
            with urllib.request.urlopen(delete, timeout=2):
                pass
        if result.get("serverInfo", {}).get("name") != "Basic Memory":
            raise RuntimeError(f"Unexpected MCP service at {URL}")
        return True
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Unexpected HTTP service at {URL}: {error.code}") from error
    except (urllib.error.URLError, TimeoutError):
        return False


def ensure():
    config = Path(os.environ.get("LIFE_MEMORY_CONFIG", "~/.config/life-memory/config.json")).expanduser()
    cfg = json.loads(config.read_text())
    state = Path(cfg["state"]).expanduser()
    state.mkdir(parents=True, exist_ok=True)
    # Serialize the check/register/start sequence across simultaneous OpenCode clients.
    with (state / "shared-mcp.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if ready():
            return
        plist = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
        plist.parent.mkdir(parents=True, exist_ok=True)
        definition = {
            "Label": LABEL,
            "ProgramArguments": [cfg["basic_memory"], "mcp", "--project", "life",
                "--transport", "streamable-http", "--host", "127.0.0.1", "--port", "8766", "--path", "/mcp"],
            "EnvironmentVariables": {"BASIC_MEMORY_FORCE_LOCAL": "true", "BASIC_MEMORY_NO_PROMOS": "1"},
            "RunAtLoad": False,
            "StandardOutPath": str(state / "shared-mcp.log"),
            "StandardErrorPath": str(state / "shared-mcp-errors.log"),
        }
        domain = f"gui/{os.getuid()}"
        service = f"{domain}/{LABEL}"
        registered = subprocess.run(["launchctl", "print", service], capture_output=True).returncode == 0
        if not registered:
            plist.write_bytes(plistlib.dumps(definition))
            subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=True, capture_output=True)
        # No -k: never terminate/restart an already-running service.
        subprocess.run(["launchctl", "kickstart", service], check=True, capture_output=True)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if ready():
                return
            time.sleep(0.25)
        raise RuntimeError(f"Life MCP did not become ready; see {state / 'shared-mcp-errors.log'}")


if __name__ == "__main__":
    try:
        ensure()
        print(URL)
    except Exception as error:
        print(f"Life memory startup failed: {error}", file=sys.stderr)
        sys.exit(1)
