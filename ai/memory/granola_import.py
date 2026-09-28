#!/usr/bin/env python3
"""Fetch selected Granola inventory records into private staging for evidence review."""
import argparse
import asyncio
import json
import re
import xml.etree.ElementTree as ET
from fastmcp import Client
from granola_mcp import transport, serialized, text_content
from memory import atomic, settings


def inventory():
    folder = settings()["state"] / "granola"
    data = json.loads((folder / "meeting-inventory.json").read_text())
    text = text_content(data)
    atomic(folder / "meeting-inventory.md", text)
    match = re.search(r"<meetings_data\b.*?</meetings_data>", text, re.S)
    if not match:
        raise ValueError("Unexpected meeting inventory format")
    root = ET.fromstring(match[0])
    rows = [{**m.attrib, "participants": (m.findtext("known_participants") or "").strip()} for m in root.findall("meeting")]
    if int(root.attrib["count"]) != len(rows):
        raise ValueError("Inventory count mismatch; check server truncation")
    atomic(folder / "inventory.json", json.dumps(rows, indent=2, ensure_ascii=False))
    return folder, rows


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inventory", "fetch"])
    parser.add_argument("--refresh", action="store_true", help="Refetch notes/transcripts rather than reuse private staging")
    args = parser.parse_args()
    folder, rows = inventory()
    if args.action == "inventory":
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    async with Client(transport(), timeout=90) as client:
        for i in range(0, len(rows), 10):
            ids = [r["id"] for r in rows[i:i+10]]
            dest = folder / f"notes-{i // 10}.json"
            if args.refresh or not dest.exists():
                result = serialized(await client.call_tool("get_meetings", {"meeting_ids": ids}))
                if result["isError"]:
                    raise RuntimeError("Granola notes request failed")
                atomic(dest, json.dumps(result, indent=2, ensure_ascii=False))
            result = json.loads(dest.read_text())
            atomic(dest.with_suffix(".md"), text_content(result))
        for r in rows:
            dest = folder / (r["id"] + "-transcript.json")
            if dest.exists() and not args.refresh:
                continue
            try:
                result = serialized(await client.call_tool("get_meeting_transcript", {"meeting_id": r["id"]}))
                atomic(dest, json.dumps(result, indent=2, ensure_ascii=False))
                atomic(dest.with_suffix(".md"), text_content(result))
                print(json.dumps({"id": r["id"], "transcript": "error" if result["isError"] else "retrieved"}))
            except Exception as error:
                # A plan limit or unavailable transcript must remain visibly missing.
                atomic(folder / (r["id"] + "-transcript-error.txt"), str(error))
                print(json.dumps({"id": r["id"], "transcript": "unavailable"}))
            await asyncio.sleep(.8)


if __name__ == "__main__":
    asyncio.run(main())
