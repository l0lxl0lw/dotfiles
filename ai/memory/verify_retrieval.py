#!/usr/bin/env python3
"""Verify local Granola completeness, citation targets, and reviewed recall cases.

Optional --cases JSON lives in private state, not this public repository. Each case
has query, expected_paths (any one must rank within top_k), optional scope, and
optional required_terms checked against the expected note's requested layer/section.
This is a regression check, not a semantic truth or universal recall guarantee.
"""
import argparse
import json
from pathlib import Path
import re

from granola_layers import OUTLINE_START, OUTLINE_END, transcript_data
from memory import digest, settings
from recall import OUTLINE, index, read, search, sections


def audit(cfg):
    registry_path = cfg["state"] / "granola/layers.json"
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
    results, problems = [], []
    for sid, row in registry.items():
        folder = cfg["vault"] / row["source"]
        note = (cfg["vault"] / (row["meeting"] + ".md")).read_text()
        original = transcript_data(json.loads((folder / "original-transcript-response.json").read_text()), sid)["transcript"]
        projection = (folder / "Transcript.md").read_text().split("## Transcript\n\n", 1)[1].split("## Related synthesis", 1)[0]
        projection = re.sub(r"\n\n\^utterance-\d+\n\n", "\n\n", projection).strip()
        outline = note.split(OUTLINE_START, 1)[1].split(OUTLINE_END, 1)[0]
        import html
        import xml.etree.ElementTree as ET
        source_outline = html.unescape(ET.fromstring((folder / "original-notes.xml").read_text()).findtext("summary") or "").strip()
        good = projection == original.strip() and source_outline in outline and digest(source_outline.encode()) == row["outline_sha256"]
        if not good:
            problems.append({"meeting": row["meeting"], "issue": "Local source content differs"})
        results.append({"meeting": row["meeting"], "complete": good, "paragraphs": row["paragraphs"], "needs_review": row.get("needs_review", False)})
    # Assert file and anchor targets for synthesized notes; original quoted material
    # is evidence, not an authored relationship declaration.
    notes = {str(p.relative_to(cfg["vault"]))[:-3]: p for p in cfg["vault"].rglob("*.md") if not any(x.startswith(".") for x in p.relative_to(cfg["vault"]).parts)}
    citations = 0
    for key, path in notes.items():
        if key.startswith(("Sources/", "System/Templates/")):
            continue
        text = OUTLINE.sub("", path.read_text())
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`\n]+`", "", text)
        for target in re.findall(r"\[\[([^\]]+)\]\]", text):
            target = target.split("|", 1)[0]
            rel, _, anchor = target.partition("#")
            rel = rel.removesuffix(".md") or key
            matches = [notes[rel]] if rel in notes else [p for k, p in notes.items() if k.rsplit("/", 1)[-1] == rel]
            if len(matches) != 1:
                attachment = (cfg["vault"] / rel).resolve()
                if attachment.is_relative_to(cfg["vault"]) and attachment.is_file():
                    continue
                problems.append({"from": key, "target": target, "issue": "Missing or ambiguous file"})
                continue
            citations += 1
            if anchor:
                dest = matches[0].read_text()
                exists = re.search(r"^" + re.escape(anchor) + r"\s*$", dest, re.M) if anchor.startswith("^") else anchor in [h for h, _ in sections(dest)] or bool(re.search(r"^#{1,6} " + re.escape(anchor) + r"\s*$", dest, re.M))
                if not exists:
                    problems.append({"from": key, "target": target, "issue": "Missing anchor"})
    return {"meetings": len(results), "complete": sum(r["complete"] for r in results), "transcript_paragraphs": sum(r["paragraphs"] for r in results), "citations_checked": citations, "problems": problems, "results": results}


def evaluate(cfg, cases):
    results = []
    for case in cases:
        result = search(cfg, case["query"], case.get("scope", "summary"), case.get("top_k", 3))
        paths = [r["path"] for r in result["results"]]
        hits = [p for p in paths if p in case["expected_paths"]]
        supported = True
        if case.get("required_terms"):
            supported = False
            for path in hits:
                evidence = read(cfg, path, case.get("section"), case.get("layer", "summary"), limit=1000000)["content"].casefold()
                if all(term.casefold() in evidence for term in case["required_terms"]):
                    supported = True
        results.append({"query": case["query"], "scope": result["scope"], "pass": bool(hits) and supported, "retrieved": paths, "expected": case["expected_paths"], "support_terms": supported})
    return {"passed": sum(r["pass"] for r in results), "total": len(results), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path)
    args = parser.parse_args()
    cfg = settings()
    result = {"index": index(cfg), "audit": audit(cfg)}
    if args.cases:
        result["evaluation"] = evaluate(cfg, json.loads(args.cases.read_text()))
    print(json.dumps(result, ensure_ascii=False, default=str))
    if result["audit"]["problems"] or (args.cases and result["evaluation"]["passed"] != result["evaluation"]["total"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
