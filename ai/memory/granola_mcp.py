#!/usr/bin/env python3
"""Read-only Granola MCP bridge using the user's existing OpenCode OAuth grant.

Credentials stay in OpenCode's private store and are never printed or copied.
Run `opencode mcp auth granola` again if the access token expires.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import time
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from memory import atomic, settings

URL = "https://mcp.granola.ai/mcp"
READ_TOOLS = {"get_account_info", "list_meetings", "get_meetings", "get_meeting_transcript", "list_meeting_folders"}


def transport():
    data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    auth = json.loads((data_home / "opencode/mcp-auth.json").read_text())["granola"]
    if auth.get("serverUrl") != URL:
        raise SystemExit("Granola grant URL does not match the official server")
    tokens = auth["tokens"]
    if tokens.get("expiresAt", float("inf")) <= time.time():
        raise SystemExit("Granola token expired. Run: opencode mcp auth granola")
    return StreamableHttpTransport(URL, headers={"Authorization": "Bearer " + tokens["accessToken"]})


def serialized(response):
    return {"content": [c.model_dump(mode="json") for c in response.content],
            "structuredContent": response.structured_content, "isError": response.is_error}


def text_content(response):
    return "\n\n".join(c["text"] for c in response["content"] if c["type"] == "text")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=["tools", *sorted(READ_TOOLS)])
    parser.add_argument("--args", default="{}", help="JSON tool arguments, following the discovered schema")
    parser.add_argument("--save", help="Simple output name in private state/granola; omit to print the response")
    args = parser.parse_args()
    async with Client(transport(), timeout=90) as client:
        if args.tool == "tools":
            result = [{"name": t.name, "inputSchema": t.input_schema} for t in await client.list_tools()]
        else:
            response = await client.call_tool(args.tool, json.loads(args.args))
            result = serialized(response)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.save:
        if not args.save.replace("-", "").replace("_", "").isalnum():
            raise SystemExit("Save name must contain only letters, digits, hyphens and underscores")
        p = settings()["state"] / "granola" / (args.save + ".json")
        atomic(p, text)
        if args.tool != "tools":
            atomic(p.with_suffix(".md"), text_content(result))
        print(json.dumps({"saved": str(p), "bytes": len(text.encode())}))
    else:
        print(text)


if __name__ == "__main__":
    asyncio.run(main())
