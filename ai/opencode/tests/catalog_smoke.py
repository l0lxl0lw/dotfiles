#!/usr/bin/env python3
"""Check this checkout's full catalog over HTTP, without model calls or GitHub writes.

The CLI debug printer can truncate large JSON output when piped. The local API
provides a complete response and exercises the actual server configuration.
"""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
env = {k: v for k, v in os.environ.items() if not k.startswith("OPENCODE_")}
# Expose this checkout's public names through ordinary installed skill links,
# without syncing or editing the real HOME. Configured skills.paths are reserved
# for non-conflicting additional catalogs by the launcher's private integration.
scratch = tempfile.TemporaryDirectory(prefix="catalog smoke ")
config = Path(scratch.name) / "config"
skills = config / "opencode/skills"
skills.mkdir(parents=True)
for skill in (ROOT.parent / "shared/skills").rglob("SKILL.md"):
    if any((parent / "SKILL.md").exists() for parent in skill.parents if parent != skill.parent):
        continue
    (skills / skill.parent.name).symlink_to(skill.parent, target_is_directory=True)
env["XDG_CONFIG_HOME"] = str(config)
env["OPENCODE_WORKFLOW_STATE"] = str(Path(scratch.name) / "state")
env["OPENCODE_SERVER_PASSWORD"] = "local-catalog-verification"
repo = Path(scratch.name) / "project"
project_skill = repo / ".opencode/skills/catalog-collision/SKILL.md"
project_skill.parent.mkdir(parents=True)
project_skill.write_text("---\nname: catalog-collision\ndescription: Collision skill\n---\nPROJECT COLLISION CONTENT\n")
custom = {"catalog-collision": {"description": "Custom collision command", "template": "CUSTOM COLLISION $ARGUMENTS"},
          "skill-catalog-collision": {"description": "Skill fallback: catalog-collision", "template": "USER LOOKALIKE $ARGUMENTS"}}
env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"command": custom})
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
process = subprocess.Popen(
    ["python3", "-B", str(ROOT / "runtime/launch.py"), "--", "serve", "--hostname", "127.0.0.1", "--port", str(port)],
    cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
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
    for name in ("remember-life", "write-humanize", "write-better", "learn-teach-back", "use-remotion",
                 "explain-code-flow", "learn-quiz", "git-sync-orca-workspaces"):
        assert name in public, name
        assert "/ai/shared/skills/" in str(Path(public[name]["location"]).resolve()), public[name]["location"]
    request = urllib.request.Request(f"http://127.0.0.1:{port}/command")
    request.add_header("Authorization", "Basic " + token)
    with urllib.request.urlopen(request, timeout=60) as response:
        commands = {item["name"]: item for item in json.load(response)}
    assert "catalog-collision" in public
    assert Path(public["catalog-collision"]["location"]).resolve() == project_skill.resolve()
    for name, definition in custom.items():
        assert commands[name]["source"] == "command", commands[name]
        for key, value in definition.items():
            assert commands[name][key] == value, commands[name]
    assert {name for name, command in commands.items()
            if command.get("description", "").startswith("Skill fallback: ")} == {"skill-catalog-collision"}
    assert not any(name.startswith("skill-") for name in commands if name not in custom)
    assert commands["git-commit"]["source"] == "skill"
    retired = {"ticket", "research", "plan", "execute", "review", "commit"}
    # OpenCode itself supplies /review. Check removal of our stage binding,
    # without treating a native or independently configured command as ours.
    for name in retired & commands.keys():
        assert not commands[name].get("agent", "").startswith("workflow"), commands[name]
        assert "workflow-" + name not in commands[name].get("template", ""), commands[name]
    assert not any(name.startswith("workflow-") for name in public)
    request = urllib.request.Request(f"http://127.0.0.1:{port}/agent")
    request.add_header("Authorization", "Basic " + token)
    with urllib.request.urlopen(request, timeout=60) as response:
        agents = json.load(response)
    assert not any(item["name"] == "workflow" or item["name"].startswith("workflow-") for item in agents)
    for stage in ("prepare", "deliver"):
        name = "develop-" + stage
        assert name in public, name
        assert commands[name].get("source") == "skill", commands[name]
        assert not commands[name].get("subtask"), commands[name]
    for stage in ("plan", "scope-review", "execute", "review"):
        name = "develop-" + stage
        assert any(item["name"] == name and item["mode"] == "subagent" for item in agents), name
        assert name not in public and name not in commands, name
    assert {name for name in public if name.startswith("develop-")} == {"develop-prepare", "develop-deliver"}
    assert "brainstorm" not in commands
    print(f"Installed OpenCode API: {len(public)} public/builtin/private skills, {len(result) - len(public)} pinned skills; shared locations and executable command registration verified")
finally:
    process.terminate()
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
    scratch.cleanup()
