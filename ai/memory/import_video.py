#!/usr/bin/env python3
"""Archive a YouTube caption track through yt-dlp metadata; never downloads video."""
import argparse
import html
import json
import re
import subprocess
import urllib.request
from memory import atomic, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", args.id):
        raise SystemExit("Expected YouTube video ID")
    cfg = settings()
    folder = cfg["vault"] / "Sources/Videos"
    dest = folder / (args.id + ".md")
    if dest.exists():
        print("Already archived:", dest)
        return
    data = json.loads(subprocess.check_output(["yt-dlp", "--ignore-config", "--no-cache-dir", "--skip-download", "--dump-single-json", "https://www.youtube.com/watch?v=" + args.id], text=True))
    manual = data.get("subtitles", {})
    auto = data.get("automatic_captions", {})
    originals = [k for k in auto if k.endswith("-orig")]
    language = next((k for k in manual if k.startswith("en")), None)
    automatic = not bool(language)
    if automatic:
        language = next((k for k in originals if k.startswith("en")), next(iter(originals), "en"))
    tracks = (auto if automatic else manual)[language]
    track = next(t for t in tracks if t["ext"] == "vtt")
    req = urllib.request.Request(track["url"], headers=data.get("http_headers", {}))
    vtt = urllib.request.urlopen(req, timeout=45).read().decode()
    # Preserve exact VTT before projecting overlapping rolling captions.
    atomic(folder / (args.id + ".vtt"), vtt)
    metadata = {k: data.get(k) for k in ("id", "title", "channel", "duration", "description", "upload_date")}
    metadata.update(language=language, automatic_captions=automatic)
    atomic(folder / (args.id + ".json"), json.dumps(metadata, ensure_ascii=False, indent=2))
    minutes = {}
    previous = []
    for block in re.split(r"\n\s*\n", vtt):
        lines = block.splitlines()
        time_index = next((i for i, line in enumerate(lines) if " --> " in line), None)
        if time_index is None:
            continue
        stamp = lines[time_index].split(" --> ")[0]
        plain = " ".join(html.unescape(re.sub(r"<[^>]+>", "", line)).strip() for line in lines[time_index + 1:]).split()
        # Rolling VTT repeats the preceding caption. Only remove adjacent overlap.
        overlap = 0
        for n in range(1, min(len(previous), len(plain)) + 1):
            if previous[-n:] == plain[:n]:
                overlap = n
        fresh = plain[overlap:]
        if fresh:
            minutes.setdefault(stamp[:5], []).extend(fresh)
        previous = plain
    text = ["---", "type: source", "title: " + json.dumps(data["title"], ensure_ascii=False),
            "caption_language: " + language, "automatic_captions: " + str(automatic).lower(), "---",
            "# " + data["title"], "", "Channel: " + data.get("channel", ""),
            "", "URL: https://www.youtube.com/watch?v=" + args.id, "",
            "Auto-captions may misrecognize names and technical terms. Exact VTT is stored alongside this note.",
            "", "Why saved: inform the design of [[Wiki/Projects/Connected memory setup]].", "",
            "Related synthesis: [[Wiki/Concepts/Meaningful cross-links]], [[Wiki/Concepts/Progressive memory]], [[Wiki/Concepts/Context-aware ingestion]].", ""]
    for stamp, words in minutes.items():
        hours, minute = map(int, stamp.split(":"))
        text += ["## " + stamp, "", f"[Watch](https://www.youtube.com/watch?v={args.id}&t={hours*3600+minute*60})", "", " ".join(words), ""]
    atomic(dest, "\n".join(text))
    print(json.dumps({"path": str(dest), "caption_language": language, "minutes": len(minutes)}))


if __name__ == "__main__":
    main()
