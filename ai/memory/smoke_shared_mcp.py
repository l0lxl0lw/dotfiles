#!/usr/bin/env python3
"""Read-only live acceptance: concurrent starters and independent MCP clients."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys

from fastmcp import Client


async def client_check():
    async with Client("http://127.0.0.1:8766/mcp") as client:
        tools = await client.list_tools()
        assert any(tool.name == "read_note" for tool in tools)
        result = await client.call_tool("read_note", {
            "identifier": "System/Memory rules.md", "project": "life"})
        assert not result.is_error, result
        assert "Ownership and evidence" in str(result), result


async def main():
    launcher = str(Path(__file__).with_name("shared_mcp.py"))
    children = [subprocess.Popen([sys.executable, launcher], stdout=subprocess.PIPE) for _ in range(5)]
    for child in children:
        child.communicate(timeout=90)
        assert child.returncode == 0
    def pid():
        status = subprocess.check_output([
            "launchctl", "print", f"gui/{os.getuid()}/local.life-memory.mcp"], text=True)
        return next(line.strip() for line in status.splitlines() if line.strip().startswith("pid ="))
    original = pid()
    await asyncio.gather(*(client_check() for _ in range(5)))
    subprocess.run([sys.executable, launcher], check=True, stdout=subprocess.PIPE)
    assert pid() == original, "Reusing the endpoint restarted the server"
    await client_check()  # Other clients closing must not shut down the service.
    print("PASS: five concurrent starters and five independent MCP note readers")


if __name__ == "__main__":
    asyncio.run(main())
