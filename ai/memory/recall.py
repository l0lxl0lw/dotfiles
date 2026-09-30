#!/usr/bin/env python3
"""Local, layered retrieval. No network, model calls, or Granola credentials.

The disposable SQLite index ranks section-sized passages. Summary is the default;
original outlines/transcripts require an explicit evidence scope.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3

from memory import digest, locked, settings, vault_path

STOP = set("a an and are as at be been by can could did do does for from had has have how i in into is it me my of on or our should that the their them there these they this to was were what when where which who why will with would you your about tell please".split())
OUTLINE = re.compile(r"<!-- life-memory:outline:start -->.*?<!-- life-memory:outline:end -->", re.S)


def metadata(text):
    import yaml
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    return (yaml.safe_load(match[1]) or {}, text[match.end():]) if match else ({}, text)


def sections(text):
    """Markdown headings outside code fences; original outline is handled separately."""
    result, heading, lines, fenced = [], "Overview", [], False
    for line in text.splitlines():
        if line.startswith("```") or line.startswith("~~~"):
            fenced = not fenced
        match = re.match(r"^#{1,6} (.+?)\s*$", line) if not fenced else None
        if match:
            if "\n".join(lines).strip():
                result.append((heading, "\n".join(lines).strip()))
            heading, lines = match[1], []
        else:
            lines.append(line)
    if "\n".join(lines).strip():
        result.append((heading, "\n".join(lines).strip()))
    return result


def chunks(text, size=1800):
    # Explicit windows, never silently discard a long source or long paragraph.
    for offset in range(0, len(text), size):
        yield offset, text[offset:offset + size]


def documents(cfg):
    for path in sorted(cfg["vault"].rglob("*.md")):
        rel = path.relative_to(cfg["vault"])
        if path.is_symlink() or not path.resolve().is_relative_to(cfg["vault"]) or any(p.startswith(".") for p in rel.parts) or rel.parts[0] in ("System", "Daily") or path.name in ("AGENTS.md", "CLAUDE.md"):
            continue
        yield path, str(rel)


def passages(rel, text):
    meta, body = metadata(text)
    h1 = re.search(r"^# (.+)$", body, re.M)
    title = meta.get("title") or (h1[1] if h1 else Path(rel).stem)
    aliases = meta.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [aliases]
    terms = " ".join(map(str, aliases))
    if rel.startswith("Sources/"):
        scope = "transcript" if "Transcript" in Path(rel).name or rel.startswith("Sources/Conversations/") else "outline"
    elif rel.startswith("Sessions/"):
        scope = "session"
    else:
        scope = "summary"
    outline = OUTLINE.search(body)
    if outline:
        for heading, content in sections(outline[0]):
            for offset, part in chunks(content):
                yield title, terms, "outline", heading, offset, part
        body = OUTLINE.sub("", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    for heading, content in sections(body):
        for offset, part in chunks(content):
            yield title, terms, scope, heading, offset, part


def index(cfg):
    db = cfg["state"] / "recall.sqlite3"
    with locked(cfg), sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, sha256 TEXT)")
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(path UNINDEXED,title,aliases,scope UNINDEXED,heading,offset UNINDEXED,content,tokenize='porter unicode61')")
        known = dict(conn.execute("SELECT path,sha256 FROM files"))
        count, changed = 0, 0
        for path, rel in documents(cfg):
            data = path.read_bytes()
            sha = digest(data)
            count += 1
            if known.pop(rel, None) == sha:
                continue
            conn.execute("DELETE FROM passages WHERE path=?", (rel,))
            for title, aliases, scope, heading, offset, content in passages(rel, data.decode()):
                conn.execute("INSERT INTO passages VALUES(?,?,?,?,?,?,?)", (rel, title, aliases, scope, heading, offset, content))
            conn.execute("INSERT OR REPLACE INTO files VALUES(?,?)", (rel, sha))
            changed += 1
        for rel in known:
            conn.execute("DELETE FROM passages WHERE path=?", (rel,))
            conn.execute("DELETE FROM files WHERE path=?", (rel,))
        total = conn.execute("SELECT count(*) FROM passages").fetchone()[0]
    return {"notes": count, "changed": changed, "removed": len(known), "passages": total}


def search(cfg, query, scope="summary", limit=5):
    index(cfg)
    words = list(dict.fromkeys(w for w in re.findall(r"\w+", query.lower()) if w not in STOP))[:24]
    if not words:
        return {"results": [], "hint": "Use a name, topic, or distinctive phrase."}
    match = " OR ".join('"' + w + '"' for w in words)
    scopes = ("summary", "session", "outline", "transcript") if scope == "all" else (scope,)
    with sqlite3.connect(cfg["state"] / "recall.sqlite3") as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"SELECT *,bm25(passages,0,6,4,0,3,0,1) AS rank FROM passages WHERE passages MATCH ? AND scope IN ({','.join('?' for _ in scopes)}) ORDER BY rank LIMIT 100", (match, *scopes)).fetchall()
    # Group sections by note, keeping matches compact; avoid one long transcript
    # consuming all top results. Native FTS stemming handles inflected words.
    results, seen = [], set()
    for row in rows:
        if row["path"] in seen:
            continue
        seen.add(row["path"])
        text = row["content"]
        pos = next((text.lower().find(w) for w in sorted(words, key=len, reverse=True) if w in text.lower()), 0)
        start = max(0, pos - 100)
        snippet = text[start:start + 650]
        block = re.search(r"\^utterance-\d+", text)
        # Heading citation is exact; block IDs are returned as locators only since a
        # window can contain multiple paragraphs and the match may precede the ID.
        results.append({"path": row["path"], "title": row["title"], "layer": row["scope"],
                        "section": row["heading"], "offset": row["offset"], "snippet": snippet,
                        "citation": f"[[{row['path'][:-3]}#{row['heading']}]]",
                        "nearby_block": block[0] if block else None})
        if row["scope"] == "summary":
            # Return the note's overview along with a historical matched passage so
            # an old next-step hit doesn't hide a later recorded outcome.
            results[-1]["overview"] = read(cfg, row["path"], limit=1000)["content"]
        if len(results) >= limit:
            break
    return {"scope": scope, "query": query, "results": results,
            "next": "Read the matched section; broaden to outline/transcript only for details or missing evidence. Results are candidates, not verified answers."}


def resolve(cfg, identifier):
    identifier = identifier.removeprefix("memory://").split("#", 1)[0]
    rel = identifier if identifier.endswith(".md") else identifier + ".md"
    direct = vault_path(cfg, rel)
    if direct.is_file():
        return direct
    matches = []
    for path, rel in documents(cfg):
        meta, _ = metadata(path.read_text())
        if meta.get("permalink") == identifier or path.stem == identifier or meta.get("title") == identifier:
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(f"Expected one exact note, found {len(matches)}. Use a vault-relative path; no fuzzy fallback.")
    return matches[0]


def read(cfg, identifier, section=None, layer="summary", offset=0, limit=4000):
    path = resolve(cfg, identifier)
    rel = str(path.relative_to(cfg["vault"]))
    meta, body = metadata(path.read_text())
    outline = OUTLINE.search(body)
    if layer == "summary" and rel.startswith("Sources/"):
        return {"path": rel, "hint": "This is original evidence. Use --layer transcript or --layer outline explicitly."}
    if layer == "outline" and outline:
        body = outline[0]
    elif layer == "summary":
        body = OUTLINE.sub("", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    available = sections(body)
    if section:
        found = [(h, c) for h, c in available if h == section]
        if len(found) != 1:
            raise ValueError("Section must resolve exactly once. Available: " + ", ".join(h for h, _ in available))
        selected = "## " + found[0][0] + "\n\n" + found[0][1]
    elif layer == "summary":
        preferred = [(h, c) for key in ("Gist", "Current understanding", "Outcome", "Quick answers", "Summary") for h, c in available if h == key]
        selected = "\n\n".join("## " + h + "\n\n" + c for h, c in (preferred or available[:1]))
    else:
        selected = body
    return {"path": rel, "layer": layer, "metadata": meta, "sections": [h for h, _ in available],
            "content": selected[offset:offset + limit], "offset": offset,
            "next_offset": offset + limit if offset + limit < len(selected) else None,
            "total_chars": len(selected)}


def context(cfg, identifier, limit=6):
    path = resolve(cfg, identifier)
    meta, body = metadata(path.read_text())
    body = OUTLINE.sub("", body)
    targets = list(dict.fromkeys(m.split("|", 1)[0].split("#", 1)[0] for m in re.findall(r"\[\[([^\]]+)\]\]", body)))
    targets.sort(key=lambda t: 0 if t.startswith("Wiki/") else 1)
    related = []
    for target in targets:
        if target.startswith(("Sources/", "System/")) or not target:
            continue
        try:
            related.append(read(cfg, target, limit=800))
        except ValueError:
            continue
        if len(related) >= limit:
            break
    return {"primary": read(cfg, str(path.relative_to(cfg["vault"])), limit=2200), "related": related,
            "evidence_links": [t for t in targets if t.startswith("Sources/")]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["index", "search", "read", "context"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--scope", choices=["summary", "session", "outline", "transcript", "all"], default="summary")
    parser.add_argument("--layer", choices=["summary", "outline", "transcript"], default="summary")
    parser.add_argument("--section")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.offset < 0 or (args.limit is not None and args.limit < 1):
        parser.error("Offset must be nonnegative and limit positive")
    if args.command != "index" and not args.value:
        parser.error("A query or exact note identifier is required")
    cfg = settings()
    if args.command == "index":
        result = index(cfg)
    elif args.command == "search":
        result = search(cfg, args.value, args.scope, min(args.limit or 5, 20))
    elif args.command == "context":
        result = context(cfg, args.value, min(args.limit or 6, 10))
    else:
        result = read(cfg, args.value, args.section, args.layer, args.offset, min(args.limit or 4000, 12000))
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
