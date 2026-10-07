#!/usr/bin/env python3
"""Locate the live or pinned evidence integration without changing state."""
import os
from pathlib import Path
import sys


def resolve_root(library=None, environ=None):
    env = os.environ if environ is None else environ
    library = Path(library or __file__).resolve().parent
    required = ("tracking/handoff.py", "tracking/verify.py", "tracking/WORKFLOW.md",
                "schemas/plan.example.json")

    def valid(path):
        return all((path / name).is_file() for name in required)

    if env.get("OPENCODE_WORKFLOW_ROOT"):
        root = Path(env["OPENCODE_WORKFLOW_ROOT"]).expanduser().resolve()
        if not valid(root):
            raise RuntimeError("Invalid inherited OPENCODE_WORKFLOW_ROOT: " + str(root))
        return root
    for parent in (library, *library.parents):
        for root in (parent, parent / "opencode", parent / "ai/opencode"):
            if valid(root):
                return root.resolve()
    raise RuntimeError("Development evidence integration unavailable; supply a valid OPENCODE_WORKFLOW_ROOT")


if __name__ == "__main__":
    try:
        print(resolve_root())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
