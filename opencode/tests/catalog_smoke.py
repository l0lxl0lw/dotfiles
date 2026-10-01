#!/usr/bin/env python3
"""Check the installed full catalog over HTTP, without model calls or GitHub writes.

The CLI debug printer can truncate large JSON output when piped. The local API
provides a complete response and exercises the actual server configuration.
"""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
env = {k: v for k, v in os.environ.items() if not k.startswith("OPENCODE_")}
env["OPENCODE_SERVER_PASSWORD"] = "local-catalog-verification"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
process = subprocess.Popen(
    ["python3", "-B", str(ROOT / "runtime/launch.py"), "--", "serve", "--hostname", "127.0.0.1", "--port", str(port)],
    cwd=ROOT.parent, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
)
try:
    result = None
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError("OpenCode server exited: " + process.stderr.read())
        request = urllib.request.Request(f"http://127.0.0.1:{port}/skill")
        token = base64.b64encode(b"opencode:local-catalog-verification").decode()
        request.add_header("Authorization", "Basic " + token)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                result = json.load(response)
            break
        except OSError:
            time.sleep(0.5)
    if result is None:
        raise RuntimeError("OpenCode catalog API did not become ready")
    public = {item["name"]: item for item in result if not item["name"].startswith("wf-")}
    for name in ("life-memory", "humanizer", "workflow-execute", "forced-feynman", "remotion-best-practices"):
        assert name in public, name
        assert "/ai/shared/skills/" in str(Path(public[name]["location"]).resolve()), public[name]["location"]
    request = urllib.request.Request(f"http://127.0.0.1:{port}/command")
    request.add_header("Authorization", "Basic " + token)
    with urllib.request.urlopen(request, timeout=60) as response:
        commands = {item["name"]: item for item in json.load(response)}
    for name, info in public.items():
        if info["location"] == "<built-in>":
            continue
        assert any(command.get("description") == "Skill fallback: " + name for command in commands.values()), name
    assert commands["execute"]["agent"] == "workflow-execute"
    print(f"Installed OpenCode API: {len(public)} public/builtin/private skills, {len(result) - len(public)} pinned skills; shared locations and executable command registration verified")
finally:
    process.terminate()
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
