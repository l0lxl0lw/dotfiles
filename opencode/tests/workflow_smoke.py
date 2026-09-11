#!/usr/bin/env python3
"""Explicit live-model smoke: fresh command children, native questions, nested lookup.

No GitHub writes or application edits. Uses installed OpenCode config and a temp
README fixture. Not included in unittest discovery. Run after opencode_merge_config.
"""
import concurrent.futures
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


def main():
    with tempfile.TemporaryDirectory(prefix="workflow-smoke-") as tmp:
        directory = Path(tmp)
        (directory / "README.md").write_text("Read-only workflow smoke fixture.\n")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = {**os.environ, "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1", "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1"}
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"command": {"workflow-smoke": {
            "agent": "workflow-research", "model": "openai/gpt-6-astra", "variant": "medium", "subtask": True,
            "description": "Read-only fresh-session wiring check", "template": "$ARGUMENTS"}}})

        def api(method, path, data=None, timeout=180):
            url = base + path + "?" + urllib.parse.urlencode({"directory": str(directory)})
            req = urllib.request.Request(url, method=method,
                headers={"Content-Type": "application/json"},
                data=json.dumps(data).encode() if data is not None else None)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else None

        log = (directory / "server.log").open("w")
        process = subprocess.Popen(["opencode", "serve", "--pure", "--hostname", "127.0.0.1", "--port", str(port)],
                                   cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError((directory / "server.log").read_text())
                try:
                    api("GET", "/global/health", timeout=2)
                    break
                except Exception:
                    time.sleep(.5)
            else:
                raise RuntimeError("server did not start")
            config = api("GET", "/config")
            assert config.get("subagent_depth") == 2, "set subagent_depth: 2 for nested lookup smoke"
            commands = {cmd["name"]: cmd for cmd in api("GET", "/command")}
            expected = {"ticket": "gpt-6-astra", "research": "gpt-6-astra", "plan": "gpt-6-astra",
                        "execute": "gpt-5.6-sol", "review": "gpt-6-astra", "commit": "gpt-5.6-luna-fast"}
            for name, model in expected.items():
                assert commands[name].get("subtask") is True, name
                assert commands[name]["agent"] == "workflow-" + name, name
                assert commands[name]["model"] == "openai/" + model, name
            parent = api("POST", "/session", {"title": "Workflow context-isolation smoke"})["id"]
            secret = str(uuid.uuid4())
            first_marker = str(uuid.uuid4())
            api("POST", f"/session/{parent}/message", {"agent": "workflow", "noReply": True,
                "model": {"providerID": "openai", "modelID": "gpt-5.6-luna-fast"},
                "parts": [{"type": "text", "text": "Parent-only context marker: " + secret}]})
            answered = []
            child_ids = []
            for number in (1, 2):
                before = {s["id"] for s in api("GET", f"/session/{parent}/children")}
                prompt = ("This is a read-only configuration smoke check, not a GitHub research task. "
                          "Do not access GitHub, load business workflow skills, or edit files. "
                          "Ask exactly one native question: Proceed with this read-only smoke? "
                          "Options: Proceed (Recommended), Stop. After the answer, ")
                if number == 1:
                    prompt += ("invoke codebase-locator exactly once to find only README.md in the current "
                               "directory. Do not pass any parent context. Return its path and this marker: " + first_marker)
                else:
                    prompt += "perform no other tools. Say only 'fresh stage complete'."
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(api, "POST", f"/session/{parent}/command",
                                         {"command": "workflow-smoke", "arguments": prompt, "agent": "workflow"})
                    started = time.time()
                    while not future.done():
                        assert time.time() - started < 180, "smoke timeout"
                        for request in api("GET", "/question"):
                            api("POST", f'/question/{request["id"]}/reply', {"answers": [["Proceed (Recommended)"]]})
                            answered.append(request["sessionID"])
                        permissions = api("GET", "/permission")
                        if permissions:
                            raise RuntimeError("Unexpected permission request: " + json.dumps(permissions))
                        time.sleep(.5)
                    future.result()
                children = [s for s in api("GET", f"/session/{parent}/children") if s["id"] not in before]
                assert len(children) == 1, "command must create exactly one new stage child"
                child = children[0]["id"]
                child_ids.append(child)
                messages = api("GET", f"/session/{child}/message")
                text = json.dumps(messages)
                assert secret not in text, "parent conversation leaked into stage messages"
                if number == 2:
                    assert first_marker not in text, "previous stage leaked into new stage"
                assert child in answered, "native question did not originate in stage child"
                models = {m["info"].get("modelID") for m in messages if m["info"]["role"] == "assistant"}
                assert models == {"gpt-6-astra"}, models
            assert len(set(child_ids)) == 2
            nested = api("GET", f"/session/{child_ids[0]}/children")
            assert len(nested) == 1, "stage could not invoke the bounded specialist"
            lookup = api("GET", f'/session/{nested[0]["id"]}/message')
            assert {m["info"].get("modelID") for m in lookup if m["info"]["role"] == "assistant"} == {"gpt-5.6-luna-fast"}
            parent_messages = api("GET", f"/session/{parent}/message")
            # Native subtask dispatch also inserts zero-usage synthetic assistant
            # envelopes labeled with the child model; those are not parent inference.
            parent_models = sorted({m["info"].get("modelID") for m in parent_messages
                                    if m["info"]["role"] == "assistant" and m["info"].get("tokens", {}).get("total", 0) > 0})
            assert parent_models == ["gpt-5.6-luna-fast"], parent_models
            print(json.dumps({"outcome": "pass", "parent": parent, "stage_children": child_ids,
                              "native_questions": len(answered), "lookup_children": len(nested),
                              "parent_models": parent_models, "stage_model": "gpt-6-astra",
                              "lookup_model": "gpt-5.6-luna-fast", "all_six_command_bindings": "pass",
                              "parent_and_sibling_context_isolation": "pass"}, indent=2))
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
            log.close()


if __name__ == "__main__":
    main()
