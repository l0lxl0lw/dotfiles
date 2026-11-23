#!/usr/bin/env python3
"""Print one line per Codex tier model missing from Codex's cached model list.

    check_models.py <models_cache.json> <machine tiers.json or absent> <hub>...

Never fails: an unreadable cache or hub tiers file produces no output.
"""
import importlib.util
import json
from pathlib import Path
import sys


def main(argv):
    cache, overlay, *hubs = argv[1:]
    try:
        known = {m["slug"] for m in json.load(open(cache))["models"]}
    except (OSError, ValueError, KeyError, TypeError):
        return 0
    spec = importlib.util.spec_from_file_location("hub_render", Path(__file__).with_name("render.py"))
    render = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render)
    overlays = [overlay] if Path(overlay).is_file() else []
    for hub in hubs:
        try:
            tiers = render.load_tiers(Path(hub), overlays).get("codex", {})
        except (SystemExit, OSError, ValueError):
            continue
        for tier, spec_ in sorted(tiers.items()):
            if known and spec_.get("model") not in known:
                print(f"hubs_sync: {hub}: codex tier '{tier}' model {spec_.get('model')!r} "
                      f"is not in Codex's model list; fix {hub}/tiers.json or {overlay}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
