#!/usr/bin/env python3
"""Exercise actual OpenCode plugin events in an isolated vault, without inference."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from memory import atomic


def main():
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="life-memory-smoke-") as folder:
        tmp = Path(folder)
        cfg = tmp / "config.json"
        vault = tmp / "vault"
        vault.mkdir()
        atomic(cfg, json.dumps({"enabled": True, "vault": str(vault), "state": str(tmp / "state"),
                               "runtime": str(root / "memory.py"), "python": shutil.which("python3")}))
        # Use a free loopback port. No external listener or inference requests.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, LIFE_MEMORY_CONFIG=str(cfg), OPENCODE_DISABLE_PROJECT_CONFIG="1",
                   OPENCODE_CONFIG_CONTENT=json.dumps({"mcp": {"life-memory": {"enabled": False}}}))
        env.pop("OPENCODE_CONFIG_DIR", None)
        with (tmp / "server.log").open("w+") as log:
            p = subprocess.Popen([shutil.which("opencode"), "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                                 cwd=folder, env=env, stdout=log, stderr=log)
            base = f"http://127.0.0.1:{port}"
            sid = None
            def request(path, data=None):
                req = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.load(r)
            try:
                for _ in range(60):
                    try:
                        request("/global/health")
                        break
                    except Exception:
                        time.sleep(.5)
                session = request("/session", {"title": "Life memory isolated capture smoke"})
                sid = session["id"]
                request(f"/session/{sid}/message", {"noReply": True, "parts": [{"type": "text", "text": "Memory smoke: ceramic comet 731."}]})
                for _ in range(40):
                    notes = list((vault / "Sources/Conversations").glob("*.md"))
                    if notes and "ceramic comet 731" in notes[0].read_text():
                        print(json.dumps({"live_plugin_capture": "pass", "model_calls": 0,
                                          "source": notes[0].name}))
                        return
                    time.sleep(.5)
                log.seek(0)
                raise RuntimeError("Capture not observed. Server log: " + log.read()[-4000:])
            finally:
                if sid:
                    try:
                        urllib.request.urlopen(urllib.request.Request(base + "/session/" + sid, method="DELETE"), timeout=5).close()
                    except Exception:
                        pass
                p.terminate()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()


if __name__ == "__main__":
    main()
