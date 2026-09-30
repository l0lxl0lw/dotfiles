#!/usr/bin/env python3
"""Publish reviewed private Granola synthesis and preserved MCP sources into Life.

Meeting-specific judgments are supplied in private staging/synthesis.json, not embedded
in tracked code. Reruns preserve existing human-edited meeting/canonical notes.
"""
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from granola_mcp import text_content
from memory import atomic, digest, encode, locked, now, settings, write_note
from granola_layers import staged_nodes, publish as publish_layers, source_id, managed, frontmatter


def decode_json_response(data):
    text = text_content(data)
    return json.loads(text[text.index("{"):])


def parse_meetings(text):
    matches = re.findall(r"<meeting\b[^>]*>.*?</meeting>", text, re.S)
    result = {}
    for raw in matches:
        node = ET.fromstring(raw)
        result[node.attrib["id"]] = (node, raw)
    return result


def save_new(cfg, rel, content):
    p = cfg["vault"] / rel
    if p.exists():
        return False
    write_note(cfg, {"path": rel, "content": content, "expected_sha256": digest(b"")})
    return True


def append_links(cfg, rel, description, links):
    p = cfg["vault"] / rel
    original = p.read_bytes() if p.exists() else b""
    content = original.decode() if original else "# " + p.stem + "\n\n" + description + "\n\n## Meetings and related notes\n"
    if not original and rel.startswith("Wiki/"):
        kind = {"Projects": "project", "People": "person", "Organizations": "organization", "Concepts": "concept", "Maps": "map"}.get(p.parent.name, "note")
        content = frontmatter("# " + p.stem + "\n\n## Gist\n\n" + description + "\n\n## Meetings and related notes\n", {
            "title": p.stem, "type": kind, "retrieval_layer": "navigation" if kind == "map" else "canonical"})
    missing = [link for link in links if f"[[{link}]]" not in content]
    if not missing and p.exists():
        return
    content += "\n" + "\n".join("- [[" + link + "]]" for link in missing) + "\n"
    write_note(cfg, {"path": rel, "content": content, "expected_sha256": digest(original)})


def main():
    cfg = settings()
    staging = cfg["state"] / "granola"
    inventory = json.loads((staging / "inventory.json").read_text())
    synthesis = json.loads((staging / "synthesis.json").read_text())
    account = decode_json_response(json.loads((staging / "account.json").read_text()))
    staged = staged_nodes(staging)
    nodes = {sid: (node, raw) for sid, (node, raw, _) in staged.items() if sid in {m['id'] for m in inventory}}
    ids = {m["id"] for m in inventory}
    if ids != set(nodes) or ids != set(synthesis["meetings"]):
        raise ValueError("Inventory, retrieved notes and reviewed synthesis IDs must match exactly")
    for item in synthesis["meetings"].values():
        for name in [item["title"], item["project"], *item["organizations"], *item["people"], *item["topics"]]:
            if not name or any(c in name for c in '/\\[]#|\n') or name in (".", ".."):
                raise ValueError("Unsafe note title in reviewed synthesis")
    published = []
    with locked(cfg):
        existing = {}
        for path in (cfg["vault"] / "Meetings").glob("*.md"):
            sid = source_id(path.read_text())
            if sid:
                if sid in existing:
                    raise ValueError(f"Duplicate meeting source ID: {sid}")
                existing[sid] = str(path.relative_to(cfg["vault"]))[:-3]
        for m in inventory:
            sid = m["id"]
            entry = synthesis["meetings"][sid]
            node, raw = nodes[sid]
            transcript_path = staging / (sid + "-transcript.json")
            transcript_response = json.loads(transcript_path.read_text()) if transcript_path.exists() else None
            transcript = decode_json_response(transcript_response) if transcript_response and not transcript_response.get("isError") else None
            has_transcript = bool(transcript and transcript.get("transcript"))
            revision = digest(encode({"notes": raw, "transcript": transcript_response}))[:16]
            source = f"Sources/Granola/{sid}/{revision}"
            source_path = cfg["vault"] / source
            date = datetime.strptime(m["date"][:12].strip(), "%b %d, %Y").date().isoformat()
            meeting = existing.get(sid, f"Meetings/{date} — {entry['title']} — {sid[:8]}")
            summary = html.unescape(node.findtext("summary") or "").strip()
            private_notes = html.unescape(node.findtext("private_notes") or "").strip()
            if not (source_path / "Notes.md").exists():
                atomic(source_path / "original-notes.xml", raw)
                atomic(source_path / "metadata.json", json.dumps({**m, "retrieved_at": now(), "workspace": account["active_workspace"], "revision": revision}, indent=2))
                notes = f"# Granola notes — {m['title']}\n\nDate: {m['date']}\n\n[Original meeting]({m['url']})\n\n"
                notes += "Preserved Granola output. Summaries may contain transcription or attribution errors.\n\n"
                notes += "## Known participants\n\n" + m["participants"] + "\n\n"
                notes += "## Private notes\n\n" + (private_notes or "No private notes returned.") + "\n\n"
                notes += "## Summary\n\n" + (summary or "No summary returned.") + f"\n\n## Related synthesis\n\n[[{meeting}]]\n"
                atomic(source_path / "Notes.md", frontmatter(notes, {"title": f"{date} — {entry['title']} — original Granola outline", "type": "source", "retrieval_layer": "source", "source_id": sid}))
                if transcript_response:
                    atomic(source_path / "original-transcript-response.json", json.dumps(transcript_response, ensure_ascii=False, indent=2))
                if has_transcript:
                    # Preserve supplied labels. A microphone label doesn't establish a person's identity.
                    context = transcript.get("recording_context", {})
                    text = f"# Granola transcript — {m['title']}\n\n[Original meeting]({m['url']})\n\n"
                    text += "Source-provided speaker labels are retained; microphone/system labels may contain multiple people. No timestamps were supplied by this response.\n\n"
                    text += "## Recording context\n\n```json\n" + json.dumps(context, ensure_ascii=False, indent=2) + "\n```\n\n## Transcript\n\n"
                    for i, paragraph in enumerate(transcript["transcript"].split("\n\n"), 1):
                        text += paragraph + f"\n\n^utterance-{i:05d}\n\n"
                    atomic(source_path / "Transcript.md", frontmatter(text + f"## Related synthesis\n\n[[{meeting}]]\n", {"title": f"{date} — {entry['title']} — full transcript", "type": "source", "retrieval_layer": "transcript", "source_id": sid}))
            relations = [f"- part_of [[Wiki/Projects/{entry['project']}]]"]
            relations += [f"- involves [[Wiki/Organizations/{name}]]" for name in entry["organizations"]]
            relations += [f"- mentions [[Wiki/People/{name}]]" for name in entry["people"]]
            relations += [f"- relates_to [[Wiki/Concepts/{name}]]" for name in entry["topics"]]
            relations += [f"- supported_by [[{source}/Notes]]"]
            if has_transcript:
                relations += [f"- supported_by [[{source}/Transcript]]"]
            steps = re.search(r"^# (?:Next Steps|Logistics and Next Steps)\s*\n(.*?)(?=^# |\Z)", summary, re.M | re.S)
            next_steps = steps[1].strip() if steps else "No standalone next-steps section was returned. Review the source discussion for open work."
            content = f"---\ntype: meeting\nkind: {entry['kind']}\ndate: {date}\nsource_system: granola\nsource_id: {sid}\n---\n# {entry['title']}\n\n"
            content += f"## Gist\n\n{entry['gist']}\n\n## Source and date\n\n{m['date']} — [Open in Granola]({m['url']})\n\n"
            content += f"Summary synthesized from [[{source}/Notes#Summary]]. Full transcript " + (f"available at [[{source}/Transcript]]." if has_transcript else "was not returned.") + "\n\n"
            content += "## Follow-ups recorded at the meeting\n\nHistorical commitments or expectations, not verified current tasks. Completion and subsequent outcomes are unknown unless another source establishes them.\n\n" + next_steps + "\n\n"
            content += "## Human reflections\n\n## Relations\n\n" + "\n".join(relations) + "\n"
            created = save_new(cfg, meeting + ".md", content)
            if not created:
                append_links(cfg, meeting + ".md", "", [source + "/Notes"] + ([source + "/Transcript"] if has_transcript else []))
            published.append({"id": sid, "meeting": meeting, "source": source, "transcript": has_transcript, "kind": entry["kind"], "created": created})
        for category, field in (("Projects", "project"), ("Organizations", "organizations"), ("People", "people"), ("Concepts", "topics")):
            groups = {}
            for p in published:
                entry = synthesis["meetings"][p["id"]]
                names = [entry[field]] if field == "project" else entry[field]
                for name in names:
                    groups.setdefault(name, []).append(p["meeting"])
            for name, links in groups.items():
                description = synthesis.get("projects" if field == "project" else "topics", {}).get(name)
                if not description:
                    description = "Appears in the dated Granola sources below. Relationships and claims should be checked against the linked meeting context; mention does not by itself prove attendance or employment."
                append_links(cfg, f"Wiki/{category}/{name}.md", description, links)
        append_links(cfg, "Wiki/Maps/Meetings.md", "Meetings imported from Granola, grouped by context through the linked project notes. Original source revisions and transcripts are preserved.",
                     [p["meeting"] for p in published] + ["Wiki/Projects/" + name for name in synthesis["projects"]])
        append_links(cfg, "Wiki/Maps/Projects.md", "", ["Wiki/Projects/" + name for name in synthesis["projects"]])
        append_links(cfg, "Home.md", "", ["Wiki/Maps/Meetings", "System/Granola import"])
        scope_path = staging / "inventory-scope.json"
        scope = json.loads(scope_path.read_text()) if scope_path.exists() else {"scope": "Selected staged inventory; original request bounds not recorded"}
        receipt = {"imported_at": now(), "workspace": account["active_workspace"], "meetings": published, "scope": scope}
        atomic(staging / "import-receipt.json", json.dumps(receipt, ensure_ascii=False, indent=2))
        report = f"# Granola import\n\nImported: {now()}\n\nWorkspace: {account['active_workspace']['display_name']}\n\n"
        report += f"{len(published)} meetings; {sum(p['transcript'] for p in published)} nonempty transcripts.\n\n"
        report += "Scope: selected staged inventory, not proof of all historical meetings or other workspaces.\n\n```json\n" + json.dumps(scope, indent=2) + "\n```\n\n"
        report += "Notes and available transcripts were retrieved via the official Granola MCP server. Source revisions are content-addressed. Existing human-edited notes are preserved on rerun. Summaries derive from Granola's meeting summaries; transcripts are available for detailed verification, not exhaustively fact-checked.\n\n"
        report += "The connection is installed in OpenCode. Restart OpenCode to expose Granola tools directly in a normal session. No periodic Granola polling job has been enabled.\n\n## Meetings\n\n"
        report += "\n".join(f"- [[{p['meeting']}]] — {p['kind']}; transcript {'available' if p['transcript'] else 'missing'}" for p in published) + "\n"
        path = cfg["vault"] / "System/Granola import.md"
        original = path.read_bytes() if path.exists() else b""
        state = staging / "report-hashes.json"
        hashes = json.loads(state.read_text()) if state.exists() else {}
        report = report.replace("# Granola import", "## Latest importer receipt", 1)
        content = managed(original.decode() or "# Granola import\n", "import-report", report, hashes)
        write_note(cfg, {"path": "System/Granola import.md", "content": content, "expected_sha256": digest(original)})
        atomic(state, json.dumps(hashes))
    layers = publish_layers(cfg, staging)
    print(json.dumps({"meetings": len(published), "transcripts": sum(p["transcript"] for p in published), "new_meetings": sum(p["created"] for p in published), "layered_meetings": layers["meetings"]}))


if __name__ == "__main__":
    main()
