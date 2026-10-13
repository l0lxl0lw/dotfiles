#!/usr/bin/env python3
"""Materialize staged Granola evidence and layer existing meeting notes, entirely locally.

Network fetches are a separate, explicit operation. Source revisions are immutable;
managed sections refuse to replace edits made since the last publication.
"""
import argparse
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from uuid import UUID

from memory import atomic, digest, encode, locked, now, settings, write_note

OUTLINE_START = "<!-- life-memory:outline:start -->"
OUTLINE_END = "<!-- life-memory:outline:end -->"
EVIDENCE_START = "<!-- life-memory:evidence:start -->"
EVIDENCE_END = "<!-- life-memory:evidence:end -->"


def response_text(data):
    if data.get("isError"):
        raise ValueError("Granola response contains a tool error")
    return "\n\n".join(c["text"] for c in data.get("content", []) if c.get("type") == "text")


def transcript_data(data, sid):
    text = response_text(data)
    result = json.loads(text[text.index("{"):])
    if result.get("id") != sid:
        raise ValueError("Transcript identity mismatch")
    if not isinstance(result.get("transcript"), str) or not result["transcript"].strip():
        raise ValueError("No nonempty transcript returned")
    return result


def staged_nodes(staging):
    nodes = {}
    current = {p.stem: json.loads(p.read_text()) for p in (staging / "current-notes").glob("*.json")}
    for path in sorted(staging.glob("notes-*.json")):
        response = json.loads(path.read_text())
        for raw in re.findall(r"<meeting\b[^>]*>.*?</meeting>", response_text(response), re.S):
            node = ET.fromstring(raw)
            sid = str(UUID(node.attrib["id"]))
            if sid in current:
                continue
            if sid in nodes and nodes[sid][1] != raw:
                raise ValueError(f"Conflicting staged notes for {sid}; select one revision first")
            nodes[sid] = (node, raw, response)
    for sid, data in current.items():
        node = ET.fromstring(data["raw"])
        if str(UUID(node.attrib["id"])) != sid:
            raise ValueError("Current notes identity mismatch")
        response_text(data["response"])
        nodes[sid] = (node, data["raw"], data["response"])
    return nodes


def frontmatter(text, updates):
    """Merge selected scalar/list YAML fields without rewriting unrelated frontmatter."""
    import yaml
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    meta = yaml.safe_load(match[1]) or {} if match else {}
    meta.update(updates)
    body = text[match.end():] if match else text
    return "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n" + body


def source_id(text):
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    import yaml
    return (yaml.safe_load(match[1]) or {}).get("source_id")


def notes_projection(text, expected_private, expected_summary):
    """Parse the source-bearing fields shared by both supported Notes wrappers."""
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise ValueError("Notes projection has missing or malformed frontmatter")
    import yaml
    try:
        document = yaml.compose(match[1], Loader=yaml.SafeLoader)
        meta = yaml.safe_load(match[1]) or {}
    except yaml.YAMLError as exc:
        raise ValueError("Notes projection has missing or malformed frontmatter") from exc
    if not isinstance(document, yaml.nodes.MappingNode) or not isinstance(meta, dict):
        raise ValueError("Notes projection has missing or malformed frontmatter")

    def occurrences_in_mapping(mapping, field, active=None):
        active = set() if active is None else active
        if id(mapping) in active:
            raise ValueError("Notes projection has missing or malformed frontmatter")
        active.add(id(mapping))
        occurrences = 0
        for key, value in mapping.value:
            if isinstance(key, yaml.nodes.ScalarNode) and key.value == field:
                occurrences += 1
            if isinstance(key, yaml.nodes.ScalarNode) and key.tag == "tag:yaml.org,2002:merge":
                merged = value.value if isinstance(value, yaml.nodes.SequenceNode) else [value]
                if not all(isinstance(node, yaml.nodes.MappingNode) for node in merged):
                    raise ValueError("Notes projection has missing or malformed frontmatter")
                occurrences += sum(occurrences_in_mapping(node, field, active) for node in merged)
        active.remove(id(mapping))
        return occurrences

    for field, required in (("source_id", True), ("source_revision", False)):
        occurrences = occurrences_in_mapping(document, field)
        if (required and occurrences != 1) or (not required and occurrences > 1):
            raise ValueError(f"Notes projection has missing or duplicated {field}")
        if occurrences and (not isinstance(meta.get(field), str) or not meta[field].strip()):
            raise ValueError(f"Notes projection has malformed {field}")
    body = text[match.end():]
    private_marker = "## Private notes\n\n"
    summary_marker = "\n\n## Summary\n\n"
    related_marker = "\n\n## Related synthesis\n\n"
    private = expected_private or "No private notes returned."
    summary = expected_summary
    source_sections = private_marker + private + summary_marker + summary + related_marker
    if body.count(source_sections) != 1:
        raise ValueError("Notes projection has missing, malformed, or duplicated source sections")
    before, after = body.split(source_sections, 1)
    wrapper_heading = re.compile(r"^## (?:Private notes|Summary|Related synthesis)\s*$", re.M)
    if wrapper_heading.search(before) or wrapper_heading.search(after):
        raise ValueError("Notes projection has missing, malformed, or duplicated source sections")
    link_pattern = r"^\[Original meeting\]\(([^\n]+)\)\s*$"
    links = re.findall(link_pattern, before, re.M) + re.findall(link_pattern, after, re.M)
    if len(links) != 1:
        raise ValueError("Notes projection has missing or duplicated original meeting URL")
    return {
        "source_id": meta["source_id"],
        "source_revision": meta.get("source_revision"),
        "url": links[0],
        "private_notes": private,
        "summary": summary,
    }


def validate_notes_projection(path, sid, url, private, summary, revision):
    if not path.exists():
        return
    try:
        observed = notes_projection(path.read_text(), private, summary)
    except ValueError as exc:
        raise ValueError(f"Source projection conflict at {path}: {exc}") from exc
    expected = {
        "source_id": sid,
        "url": url,
        "private_notes": private or "No private notes returned.",
        "summary": summary,
    }
    for field, value in expected.items():
        if observed[field] != value:
            raise ValueError(f"Source projection conflict at {path}: {field} differs")
    if observed["source_revision"] is not None and observed["source_revision"] != revision:
        raise ValueError(f"Source projection conflict at {path}: source_revision differs")


def managed(text, name, value, hashes):
    start, end = f"<!-- life-memory:{name}:start -->", f"<!-- life-memory:{name}:end -->"
    pattern = re.escape(start) + r".*?" + re.escape(end)
    matches = list(re.finditer(pattern, text, re.S))
    if text.count(start) != len(matches) or text.count(end) != len(matches) or len(matches) > 1:
        raise ValueError(f"Malformed {name} markers; reconcile manually")
    block = start + "\n" + value.rstrip() + "\n" + end
    if matches:
        old = matches[0][0]
        if old != block and digest(old.encode()) != hashes.get(name):
            raise ValueError(f"Human edit in managed {name}; reconcile before replacing")
        text = text[:matches[0].start()] + block + text[matches[0].end():]
    elif name == "evidence":
        # Keep the gist first, then place the navigation before long discussion sections.
        gist = re.search(r"^## Gist\s*\n.*?(?=^## |\Z)", text, re.M | re.S)
        at = gist.end() if gist else len(text)
        text = text[:at].rstrip() + "\n\n" + block + "\n\n" + text[at:].lstrip()
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    hashes[name] = digest(block.encode())
    return text


def immutable(path, content):
    data = content.encode() if isinstance(content, str) else content
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Source revision conflict at {path}")
    else:
        atomic(path, data)


def archive_inputs(node, raw, transcript_response):
    sid = str(UUID(node.attrib["id"]))
    transcript = transcript_data(transcript_response, sid)
    outline = html.unescape(node.findtext("summary") or "").strip()
    private = html.unescape(node.findtext("private_notes") or "").strip()
    if not outline:
        raise ValueError(f"No outline returned for {sid}")
    revision = digest(encode({"notes": raw, "transcript": transcript_response}))[:16]
    return sid, transcript, outline, private, revision


def preflight_archive(cfg, node, raw, response, transcript_response):
    """Validate every existing immutable source artifact without writing anything."""
    sid, transcript, outline, private, revision = archive_inputs(node, raw, transcript_response)
    folder = cfg["vault"] / f"Sources/Granola/{sid}/{revision}"
    immutable_inputs = {
        folder / "original-notes.xml": raw,
        folder / ("original-meeting-response-" + digest(encode(response))[:16] + ".json"): json.dumps(response, ensure_ascii=False, indent=2),
        folder / "original-transcript-response.json": json.dumps(transcript_response, ensure_ascii=False, indent=2),
    }
    for path, content in immutable_inputs.items():
        if path.exists() and path.read_bytes() != content.encode():
            raise ValueError(f"Source revision conflict at {path}")
    validate_notes_projection(folder / "Notes.md", sid, node.attrib["url"], private, outline, revision)
    return sid, transcript, outline, private, revision, folder


def archive(cfg, node, raw, response, transcript_response, meeting):
    sid, transcript, outline, private, revision, folder = preflight_archive(cfg, node, raw, response, transcript_response)
    rel = f"Sources/Granola/{sid}/{revision}"
    # Keep existing archived projections byte-for-byte. Missing new projections are
    # published with descriptive titles; the exact response remains alongside them.
    immutable(folder / "original-notes.xml", raw)
    # Identical meeting content may arrive in a different batch on refresh. Keep
    # both response envelopes without treating unrelated batch members as a conflict.
    immutable(folder / ("original-meeting-response-" + digest(encode(response))[:16] + ".json"), json.dumps(response, ensure_ascii=False, indent=2))
    immutable(folder / "original-transcript-response.json", json.dumps(transcript_response, ensure_ascii=False, indent=2))
    title = meeting.rsplit("/", 1)[-1]
    if not (folder / "Notes.md").exists():
        text = frontmatter("\n# " + title + " — original Granola outline\n\n", {
            "title": title + " — original Granola outline", "type": "source", "retrieval_layer": "source",
            "source_id": sid, "source_revision": revision,
        })
        text += f"[Original meeting]({node.attrib['url']})\n\n## Private notes\n\n{private or 'No private notes returned.'}\n\n## Summary\n\n{outline}\n\n## Related synthesis\n\n[[{meeting}]]\n"
        immutable(folder / "Notes.md", text)
    else:
        validate_notes_projection(folder / "Notes.md", sid, node.attrib["url"], private, outline, revision)
    if not (folder / "Transcript.md").exists():
        text = frontmatter("\n# " + title + " — full transcript\n\n", {
            "title": title + " — full transcript", "type": "source", "retrieval_layer": "transcript",
            "source_id": sid, "source_revision": revision,
        })
        text += "Source-provided speaker labels are retained; microphone labels do not establish identity. No timestamps are invented.\n\n"
        text += "## Recording context\n\n```json\n" + json.dumps(transcript.get("recording_context", {}), ensure_ascii=False, indent=2) + "\n```\n\n## Transcript\n\n"
        for i, paragraph in enumerate(transcript["transcript"].split("\n\n"), 1):
            text += paragraph + f"\n\n^utterance-{i:05d}\n\n"
        immutable(folder / "Transcript.md", text + f"## Related synthesis\n\n[[{meeting}]]\n")
    # Verify every paragraph against the local Markdown projection, not file existence.
    projected = (folder / "Transcript.md").read_text().split("## Transcript\n\n", 1)[1].split("## Related synthesis", 1)[0]
    projected = re.sub(r"\n\n\^utterance-\d+\n\n", "\n\n", projected).strip()
    if projected != transcript["transcript"].strip():
        raise ValueError(f"Transcript projection is incomplete for {sid}")
    return rel, revision, outline, private, len(transcript["transcript"].split("\n\n"))


def publish(cfg, staging):
    nodes = staged_nodes(staging)
    registry_path = cfg["state"] / "granola/layers.json"
    results = []
    with locked(cfg):
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
        # Preflight source availability before changing any meeting notes.
        meetings = []
        for path in sorted((cfg["vault"] / "Meetings").glob("*.md")):
            old = path.read_text()
            sid = source_id(old)
            if not sid:
                continue
            if sid not in nodes:
                raise ValueError(f"Missing staged notes for {path.name}")
            tp = staging / f"{sid}-transcript.json"
            if not tp.exists():
                raise ValueError(f"Missing local transcript for {sid}; fetch it or record unavailability explicitly")
            tr = json.loads(tp.read_text())
            transcript_data(tr, sid)
            meetings.append((path, old, sid, tr))
        for path, old, sid, tr in meetings:
            meeting = str(path.relative_to(cfg["vault"]))[:-3]
            node, raw, response = nodes[sid]
            preflight_archive(cfg, node, raw, response, tr)
        for path, old, sid, tr in meetings:
            meeting = str(path.relative_to(cfg["vault"]))[:-3]
            node, raw, response = nodes[sid]
            rel, revision, outline, private, paragraphs = archive(cfg, node, raw, response, tr, meeting)
            prior = registry.get(sid, {})
            hashes = dict(prior.get("managed_hashes", {}))
            text = old
            # Migrate only the old embed-only outline section; leave added prose intact.
            text = re.sub(r"^## Original Granola (?:notes and outline|outline)\n\n!\[\[[^\n]+\]\]\n", "", text, flags=re.M)
            text = text.replace("The outline above preserves Granola's summary.", "The original outline below preserves Granola's summary.")
            text = text.replace("The full transcript remains in Granola; it is not copied into this note.", f"The full transcript is archived locally at [[{rel}/Transcript]].")
            text = frontmatter(text, {"title": path.stem, "type": "meeting", "retrieval_layer": "meeting",
                                     "source_revision": revision, "local_outline": True, "local_transcript": True})
            stale = bool(prior.get("needs_review") or (prior.get("revision") and prior["revision"] != revision))
            # The first migration preserves prior synthesis and labels its review boundary.
            review = "Source revision changed; review the existing synthesis." if stale else "Existing synthesis retained; source claims remain attributed and dated."
            evidence = f"## Local evidence and reading depth\n\n- **Start here:** [[{meeting}#Gist]] and the discussion/Q&A below.\n- **Full original outline:** [[{meeting}#Original Granola outline (verbatim)]] — complete text is in this Markdown file.\n- **Full local transcript:** [[{rel}/Transcript]] — {paragraphs} source paragraphs; no Granola call needed.\n- **Original source:** [[{rel}/Notes]]; revision `{revision}`.\n- **Review boundary:** {review}\n\nRead [[System/Retrieval guide]] for summary-first lookup. Source wording can contain transcription errors; later updates and human reflections remain separate."
            text = managed(text, "evidence", evidence, hashes)
            full_outline = "## Original Granola outline (verbatim)\n\nPreserved source text; claims are not independently verified. This is the detail layer, below the abstraction.\n\n"
            if private:
                full_outline += "### Original private notes\n\n" + private + "\n\n### Original summary\n\n"
            full_outline += outline
            text = managed(text, "outline", full_outline, hashes)
            if text != old:
                write_note(cfg, {"path": meeting + ".md", "expected_sha256": digest(old.encode()), "content": text})
            record = {"meeting": meeting, "source": rel, "revision": revision, "paragraphs": paragraphs,
                      "outline_sha256": digest(outline.encode()), "managed_hashes": hashes, "needs_review": stale}
            registry[sid] = record
            # Persist per meeting so an interrupted run still detects manual edits on rerun.
            atomic(registry_path, json.dumps(registry, ensure_ascii=False, indent=2))
            results.append({"id": sid, **record})
    return {"meetings": len(results), "local_transcripts": len(results), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path)
    args = parser.parse_args()
    cfg = settings()
    print(json.dumps(publish(cfg, args.staging or cfg["state"] / "granola"), ensure_ascii=False))


if __name__ == "__main__":
    main()
