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
from granola_layers import staged_nodes


def inventory(name="meeting-inventory"):
    folder = settings()["state"] / "granola"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Inventory name must be a simple staging filename stem")
    data = json.loads((folder / (name + ".json")).read_text())
    if data.get("isError"):
        raise ValueError("Inventory response contains a tool error")
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
    atomic(folder / "inventory-scope.json", json.dumps({"staged_response": name + ".json", "returned_range": root.attrib}, indent=2))
    return folder, rows


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inventory", "fetch"])
    parser.add_argument("--refresh", action="store_true", help="Refetch notes/transcripts rather than reuse private staging")
    parser.add_argument("--inventory", default="meeting-inventory", help="Saved inventory response stem in private staging")
    args = parser.parse_args()
    folder, rows = inventory(args.inventory)
    if args.action == "inventory":
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    known = staged_nodes(folder)
    async with Client(transport(), timeout=90) as client:
        for i in range(0, len(rows), 10):
            ids = [r["id"] for r in rows[i:i+10]]
            if args.refresh or any(sid not in known for sid in ids):
                result = serialized(await client.call_tool("get_meetings", {"meeting_ids": ids}))
                if result["isError"]:
                    raise RuntimeError("Granola notes request failed")
                raw_nodes = re.findall(r"<meeting\b[^>]*>.*?</meeting>", text_content(result), re.S)
                by_id = {ET.fromstring(raw).attrib["id"]: raw for raw in raw_nodes}
                if set(by_id) != set(ids):
                    raise ValueError("Returned note identities differ from requested batch")
                for sid, raw in by_id.items():
                    # Current snapshot per ID avoids reusing the wrong positional batch
                    # after inventory grows or ordering changes. Archives stay immutable.
                    atomic(folder / "current-notes" / (sid + ".json"), json.dumps({"raw": raw, "response": result}, ensure_ascii=False, indent=2))
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
