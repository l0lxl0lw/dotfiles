#!/usr/bin/env python3
"""Opt-in live-model wiring and authorization smoke; no GitHub or application writes.

Uses configured model/provider access, an isolated fixture and test-only permission
overrides. Proves real Task children, pinned skill loading, questions and no-input
stops. This is not an end-to-end issue/implementation acceptance test.
"""
import base64
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("ticket", "research", "plan", "execute", "review")


def main():
    spec = importlib.util.spec_from_file_location("develop_smoke_launch", ROOT / "runtime/launch.py")
    launch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch)
    with tempfile.TemporaryDirectory(prefix="develop smoke ") as tmp:
        base_dir = Path(tmp).resolve()
        fixture = base_dir / "fixture"
        fixture.mkdir()
        sentinel = fixture / "README.md"
        sentinel.write_text("Read-only development smoke fixture.\n")
        bundle = launch.build_bundle(ROOT, base_dir / "state")
        aliases = launch.validate_bundle(bundle)["skill_aliases"]
        inherited = {k: v for k, v in os.environ.items() if k not in
                     ("OPENCODE_CONFIG_DIR", "OPENCODE_WORKFLOW_ROOT", "OPENCODE_WORKFLOW_REVISION")}
        env = launch.environment(bundle, environ=inherited, directory=fixture)
        config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        # No filesystem writes or shell/network operations are needed for probes.
        permissions = {"edit": "deny", "bash": "deny", "read": "allow", "skill": "allow", "question": "allow",
                       "webfetch": "deny", "websearch": "deny", "life-memory*": "deny", "granola*": "deny",
                       "external_directory": {"*": "deny", str(bundle) + "/**": "allow"}}
        config["permission"] = permissions
        agents = config.setdefault("agent", {})
        agents["develop-smoke-parent"] = {
            "mode": "primary", "description": "Read-only development integration probe",
            "permission": {**permissions, "task": {"*": "deny", **{"develop-" + s: "allow" for s in STAGES}}},
            "prompt": "Perform only the requested read-only integration probe. Never send parent history to a child.",
        }
        for stage in STAGES:
            agents.setdefault("develop-" + stage, {})["permission"] = {**permissions, "task": "deny"}
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
        env["OPENCODE_ENABLE_QUESTION_TOOL"] = "1"
        env["OPENCODE_SERVER_PASSWORD"] = uuid.uuid4().hex
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"

        def api(method, path, data=None, timeout=240):
            request = urllib.request.Request(
                base + path + "?" + urllib.parse.urlencode({"directory": str(fixture)}),
                method=method, data=json.dumps(data).encode() if data is not None else None,
                headers={"Content-Type": "application/json", "Authorization": "Basic " +
                         base64.b64encode(("opencode:" + env["OPENCODE_SERVER_PASSWORD"]).encode()).decode()})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else None

        def run_message(session, prompt):
            answered = set()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(api, "POST", f"/session/{session}/message", {
                    "agent": "develop-smoke-parent", "parts": [{"type": "text", "text": prompt}]})
                deadline = time.monotonic() + 240
                while not future.done():
                    if time.monotonic() > deadline:
                        raise RuntimeError("Live probe timed out")
                    for question in api("GET", "/question", timeout=5):
                        api("POST", f'/question/{question["id"]}/reply', {"answers": [["Stop"]]}, timeout=5)
                        answered.add(question["sessionID"])
                    if api("GET", "/permission", timeout=5):
                        raise RuntimeError("Unexpected permission request in read-only probe")
                    time.sleep(0.3)
                result = future.result()
                if result.get("info", {}).get("error"):
                    raise RuntimeError("Model request failed: " + json.dumps(result["info"]["error"]))
            return answered

        log_path = base_dir / "server.log"
        with log_path.open("w") as log:
            process = subprocess.Popen(["opencode", "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                                       cwd=fixture, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                for _ in range(120):
                    if process.poll() is not None:
                        raise RuntimeError(log_path.read_text())
                    try:
                        api("GET", "/global/health", timeout=2)
                        break
                    except OSError:
                        time.sleep(0.5)
                else:
                    raise RuntimeError("OpenCode server did not start")
                catalog = {item["name"]: item for item in api("GET", "/agent")}
                assert all("develop-" + stage in catalog for stage in STAGES)
                parent = api("POST", "/session", {"title": "Development wiring smoke"})["id"]
                secret = uuid.uuid4().hex
                api("POST", f"/session/{parent}/message", {"agent": "develop-smoke-parent", "noReply": True,
                    "parts": [{"type": "text", "text": "Parent-only marker, never pass to workers: " + secret}]})
                children = []
                previous_marker = uuid.uuid4().hex
                for number in (1, 2):
                    before = {child["id"] for child in api("GET", f"/session/{parent}/children")}
                    probe = ("Read-only harness probe, not a business planning request. Load your assigned stage skill, "
                             "then ask one native question 'Continue probe?' with options Stop and Continue. "
                             "After the reply return only 'probe complete'. Do not call other tools, read GitHub, "
                             "publish anything or change files.")
                    if number == 1:
                        probe += " Child-only marker: " + previous_marker
                    answered = run_message(parent, "Invoke Task exactly once with subagent_type develop-plan, "
                        "a NEW session (no task_id), and ONLY this prompt: " + probe +
                        "\nAfter the worker returns, report its result and stop. Do not invoke another stage.")
                    new = [child for child in api("GET", f"/session/{parent}/children") if child["id"] not in before]
                    assert len(new) == 1, "Expected exactly one fresh Task worker"
                    child = new[0]["id"]
                    messages = api("GET", f"/session/{child}/message")
                    serialized = json.dumps(messages)
                    assert secret not in serialized, "Parent marker leaked into child"
                    if number == 2:
                        assert previous_marker not in serialized, "Prior worker marker leaked"
                    if child not in answered:
                        details = {"experimental": api("GET", "/config").get("experimental"),
                                   "session_permissions": api("GET", f"/session/{child}").get("permission"),
                                   "question_permissions": [rule for rule in catalog["develop-plan"].get("permission", [])
                                                            if rule["permission"] in ("*", "question")]}
                        raise AssertionError("Worker did not ask a native question: " + json.dumps(details))
                    skill_calls = [part for message in messages for part in message.get("parts", [])
                                   if part.get("type") == "tool" and part.get("tool") == "skill"]
                    assert any(part.get("state", {}).get("input", {}).get("name") == aliases["develop-plan"]
                               and part["state"]["status"] == "completed" for part in skill_calls), "Pinned method not loaded"
                    children.append(child)
                # Exercise the actual dispatcher method with absent authorization/artifacts.
                for request in ("I want to develop a feature; I have supplied no issue or plan. Ask what is needed and stop.",
                                "Run execute, but I have supplied no exact plan and no implementation authorization. Stop for clarification."):
                    session = api("POST", "/session", {"title": "Development missing-input stop"})["id"]
                    await_questions = run_message(session, "Load the skill " + aliases["develop-feature"] +
                                                  " and follow it. Its physical shared library is " +
                                                  str(bundle / "opencode/skills/develop/_lib/workflow.md") + ". " + request)
                    messages = api("GET", f"/session/{session}/message")
                    parts = [part for message in messages if message["info"]["role"] == "assistant"
                             for part in message.get("parts", [])]
                    assert any(part.get("type") == "tool" and part.get("tool") == "skill"
                               and part.get("state", {}).get("input", {}).get("name") == aliases["develop-feature"]
                               and part["state"]["status"] == "completed" for part in parts)
                    assert all(part["tool"] in ("skill", "read", "question") for part in parts if part["type"] == "tool"), \
                        "Missing-input probe performed an action instead of stopping"
                    assert session in await_questions or any(part["type"] == "text" and part.get("text", "").strip()
                                                             for part in parts), "No missing-input handoff"
                    assert not api("GET", f"/session/{session}/children"), "Dispatched without required inputs"
                assert sentinel.read_text() == "Read-only development smoke fixture.\n"
                print(json.dumps({"outcome": "pass", "fresh_workers": children,
                                  "pinned_skill_and_native_questions": "pass",
                                  "parent_and_sibling_isolation": "pass", "missing_input_stops": "pass",
                                  "scope": "Read-only wiring probes; not full implementation acceptance"}))
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()


if __name__ == "__main__":
    main()
