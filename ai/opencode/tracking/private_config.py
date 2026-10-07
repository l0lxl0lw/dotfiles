"""Optional machine configuration. Never copied into public resource bundles."""
import json
import os
from pathlib import Path


def load(environ=None):
    env = os.environ if environ is None else environ
    home = Path(env.get("HOME", str(Path.home())))
    path = Path(env.get("OPENCODE_PRIVATE_CONFIG", str(home / "dotfiles-private/opencode/config.json"))).expanduser()
    if not path.exists():
        if "OPENCODE_PRIVATE_CONFIG" in env:
            raise RuntimeError("Explicit private workflow configuration does not exist")
        return {}
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError) as error:
        raise RuntimeError("Cannot read private workflow configuration") from error
    if not isinstance(data, dict) or data.get("version") != 1:
        raise RuntimeError("Private workflow configuration requires version 1")
    allowed = {"version", "skills_paths", "tracking"}
    if set(data) - allowed:
        raise RuntimeError("Unknown private workflow configuration field")
    paths = data.get("skills_paths", [])
    if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
        raise RuntimeError("skills_paths must contain paths")
    resolved = []
    for raw in paths:
        p = home / raw[2:] if raw.startswith("~/") else Path(raw)
        p = p if p.is_absolute() else path.parent / p
        if not p.is_dir():
            raise RuntimeError("Configured private skills directory does not exist")
        resolved.append(str(p.resolve()))
    return {**data, "skills_paths": resolved}


def tracking_project():
    value = load().get("tracking", {})
    if (not isinstance(value, dict) or not isinstance(value.get("owner"), str)
            or not value["owner"] or type(value.get("number")) is not int or value["number"] < 1):
        raise RuntimeError("Configure tracking.owner and tracking.number in private workflow configuration")
    return value["owner"], value["number"]
