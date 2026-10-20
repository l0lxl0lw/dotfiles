#!/usr/bin/env python3
"""Apply portable OpenCode preferences; import local preferences only explicitly."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MISSING = object()
IMPORTABLE = {"websearch", "model", "default_agent", "update", "snapshots", "watcher", "formatter", "media",
              "tool_output", "compaction", "warming", "theme", "keybinds", "leader", "input", "sessions",
              "tabs", "diffs", "alerts", "mini"}


def encode(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def atomic(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".dotfiles-settings-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def object_file(path):
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def pointer(parts):
    return "/" + "/".join(p.replace("~", "~0").replace("/", "~1") for p in parts)


def parts(key):
    if not key.startswith("/") or key == "/" or re.search(r"~(?![01])", key):
        raise ValueError("Keys must be nonempty JSON pointers, for example /websearch")
    return tuple(p.replace("~1", "/").replace("~0", "~") for p in key[1:].split("/"))


def flatten(data, prefix=()):
    result = {}
    for key, value in data.items():
        at = (*prefix, key)
        if isinstance(value, dict) and value:
            result.update(flatten(value, at))
        else:
            result[pointer(at)] = value
    return result


def get(data, at):
    for key in at:
        if not isinstance(data, dict) or key not in data:
            return MISSING
        data = data[key]
    return data


def put(data, at, value):
    parent = data
    for key in at[:-1]:
        parent = parent.setdefault(key, {})
        if not isinstance(parent, dict):
            raise ValueError(f"Non-object parent for {pointer(at)}")
    if value is MISSING:
        parent.pop(at[-1], None)
    else:
        parent[at[-1]] = deepcopy(value)


def render(value, config_dir, root):
    if isinstance(value, str):
        rendered = value.replace("{config_dir}", str(config_dir)).replace("{repo}", str(root.parents[1]))
        if value.startswith("file://") and ("{config_dir}" in value or "{repo}" in value):
            return Path(unquote(urlparse(rendered).path)).as_uri()
        return rendered
    if isinstance(value, list):
        return [render(v, config_dir, root) for v in value]
    if isinstance(value, dict):
        return {k: render(v, config_dir, root) for k, v in value.items()}
    return value


def rendered_config(data, name, config_dir, root):
    data = render(data, config_dir, root)
    if name == "cli.json" and isinstance(data.get("plugins"), list):
        # Orca installs this optional integration separately. A new machine must
        # not try to load a local plugin before its installer has supplied it.
        data["plugins"] = [plugin for plugin in data["plugins"]
                           if not isinstance(plugin, str) or not plugin.startswith("file://")
                           or Path(unquote(urlparse(plugin).path)).is_file()]
    return data


class Settings:
    def __init__(self, root=ROOT, config_dir=None, state_dir=None):
        self.root = Path(root)
        self.config = Path(config_dir or Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "opencode").absolute()
        state = Path(state_dir or Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "dotfiles/opencode-settings")
        identity = hashlib.sha256(str(self.config).encode()).hexdigest()[:16]
        self.state = state / identity

    @contextmanager
    def lock(self):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.state / "lock").open("a") as stream:
            os.chmod(stream.name, 0o600)
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def check(self):
        for parent in (self.config, *self.config.parents):
            if sys.platform == "darwin" and parent in (Path("/var"), Path("/tmp"), Path("/etc")):
                continue  # Standard macOS aliases into /private, not user config links.
            if parent.is_symlink():
                raise ValueError(f"Symlinked config directory requires manual reconciliation: {parent}")
        for name in ("opencode.jsonc", "cli.jsonc"):
            if (self.config / name).exists() or (self.config / name).is_symlink():
                raise ValueError(f"{name} exists; reconcile it into JSON before settings sync (JSONC is never rewritten)")

    def sources(self):
        return {"opencode.json": self.root / "settings/opencode.json", "cli.json": self.root / "cli.json",
                "browser-preferences.md": self.root / "settings/browser-preferences.md"}

    def plan(self, force=False):
        self.check()
        previous = object_file(self.state / "applied.json")
        baseline = deepcopy(previous)
        writes, reports, conflicts = [], [], []
        for name, source in self.sources().items():
            if not source.is_file():
                raise ValueError(f"Tracked settings source is missing: {source}")
            target = self.config / name
            before = target.read_text() if target.exists() else None
            if target.is_symlink():
                owned_cli = name == "cli.json" and target.resolve() == source.resolve()
                if not owned_cli or not force:
                    conflicts.append(f"{name}: settings symlink; run apply --force to migrate an owned CLI link" if owned_cli else f"{name}: foreign symlink preserved")
                    continue
            old = previous.get(name, {})
            if name.endswith(".md"):
                desired = source.read_text()
                prior = old.get("text", MISSING)
                if before != desired and before is not None and before != prior and not force:
                    conflicts.append(f"{name}: local changes (use apply --force to replace after backup)")
                    continue
                baseline[name] = {"text": desired}
                after = desired
            else:
                local = object_file(target)
                if target.is_symlink():
                    local = rendered_config(local, name, self.config, self.root)
                desired = flatten(rendered_config(object_file(source), name, self.config, self.root))
                result = deepcopy(local)
                accepted = deepcopy(old)
                rejected = []
                for key in sorted(old.keys() | desired.keys(), key=lambda k: (len(parts(k)), k)):
                    if any(key.startswith(parent + "/") for parent in rejected):
                        continue
                    at = parts(key)
                    # A new managed parent replaces its formerly managed children.
                    ancestor = next((pointer(at[:n]) for n in range(1, len(at)) if pointer(at[:n]) in desired), None)
                    if ancestor and ancestor in accepted and accepted[ancestor] == desired[ancestor]:
                        accepted.pop(key, None)
                        continue
                    prior, want, current = old.get(key, MISSING), desired.get(key, MISSING), get(local, at)
                    if key == "/instructions" and isinstance(current, list):
                        current = [str(Path(v).expanduser()) if isinstance(v, str) and v.startswith("~/") else v for v in current]
                    if prior is MISSING:
                        subtree = {}
                        for old_key, old_value in old.items():
                            if old_key.startswith(key + "/"):
                                put(subtree, parts(old_key)[len(at):], old_value)
                        if subtree:
                            prior = subtree
                    blocked = any(get(result, at[:n]) is not MISSING and not isinstance(get(result, at[:n]), dict) for n in range(1, len(at)))
                    safe = current == want or current == prior
                    proposed = want
                    # Arrays contribute owned entries without removing local/vendor entries.
                    additive = key in {"/instructions", "/plugins", "/plugin", "/skills", "/skills/paths", "/watcher/ignore"}
                    if additive and isinstance(want, list) and isinstance(current, list) and (prior is MISSING or isinstance(prior, list)):
                        owned = [] if prior is MISSING else prior
                        safe = safe or all(item in current for item in owned)
                        if want == prior:
                            proposed = [*current, *(item for item in want if item not in current)]
                        else:
                            # Honor repo ordering when its contribution changes,
                            # keeping foreign entries in their own relative order.
                            extras = [item for item in current if item not in owned and item not in want]
                            first = next((n for n, item in enumerate(current) if item in owned or item in want), len(current))
                            index = sum(item not in owned and item not in want for item in current[:first])
                            proposed = extras[:index] + want + extras[index:]
                    elif additive and want is MISSING and isinstance(prior, list) and isinstance(current, list):
                        safe = all(item in current for item in prior)
                        proposed = [item for item in current if item not in prior]
                        if not proposed:
                            proposed = MISSING
                    if (blocked or not safe) and not force:
                        conflicts.append(f"{name}{key}: local change/conflict")
                        rejected.append(key)
                        continue
                    if blocked:
                        if want is MISSING:
                            accepted.pop(key, None)
                            continue
                        for n in range(1, len(at)):
                            parent = get(result, at[:n])
                            if parent is not MISSING and not isinstance(parent, dict):
                                put(result, at[:n], {})
                    put(result, at, proposed)
                    if want is MISSING:
                        accepted.pop(key, None)
                    else:
                        accepted[key] = want
                baseline[name] = accepted
                after = before if result == local and before is not None and not target.is_symlink() else encode(result)
            if after != before or target.is_symlink():
                reports.append(f"update {name}")
                writes.append((target, before, target.is_symlink(), after))
        return writes, reports, conflicts, baseline

    def backup(self, path, text):
        if text is not None:
            digest = hashlib.sha256(text.encode()).hexdigest()
            destination = self.state / "backups" / (path.name + "." + digest)
            if not destination.exists():
                atomic(destination, text)

    def local_only(self):
        reports = []
        for name in ("opencode.json", "cli.json"):
            tracked = object_file(self.sources()[name])
            for key in sorted((object_file(self.config / name).keys() & IMPORTABLE) - tracked.keys()):
                reports.append(f"local-only {name}{pointer((key,))} (not tracked; import explicitly)")
        return reports

    def apply(self, force=False, sync=False, yes=False):
        if sync and not self.config.is_dir():
            return 0
        with self.lock():
            writes, reports, conflicts, baseline = self.plan(force)
            for message in conflicts:
                print("opencode_settings: " + message, file=sys.stderr)
            if conflicts and not sync:
                return 2
            if not sync:
                print("\n".join(reports) if reports else "Settings are up to date.")
                if os.environ.get("DOTFILES_INSTALL") == "1":
                    adapter = Path(os.environ["DOTFILES_INSTALL_ROOT"]) / "install/link.sh"
                    for path, before, _, _ in writes:
                        if before is not None:
                            approval = subprocess.run(["bash", str(adapter), "approve", str(path)])
                            if approval.returncode:
                                return approval.returncode
                elif writes and not yes and input("Apply these changes (existing files will be backed up)? [y/N] ").lower() != "y":
                    return 2
            # Check all destinations before writing, including externally edited files.
            for path, before, linked, _ in writes:
                if path.is_symlink() != linked or (path.read_text() if path.exists() else None) != before:
                    raise ValueError(f"Settings changed during apply; retry: {path}")
            for path, before, _, after in writes:
                self.backup(path, before)
                atomic(path, after)
            state = self.state / "applied.json"
            if object_file(state) != baseline:
                atomic(state, encode(baseline))
            if sync and writes:
                print("opencode_settings: " + ", ".join(reports))
        return 0

    def import_keys(self, name, keys, yes=False):
        self.check()
        source = self.sources()[name]
        original = source.read_text()
        tracked = object_file(source)
        local = object_file(self.config / name)
        for key in keys:
            at = parts(key)
            value = get(local, at)
            self.portable(at, None if value is MISSING else value)
            if value is MISSING:
                put(tracked, at, MISSING)
            else:
                put(tracked, at, value)
        after = encode(tracked)
        # Values have passed the conservative import check before displaying them.
        print(encode({key: get(tracked, parts(key)) if get(tracked, parts(key)) is not MISSING else "<remove>" for key in keys}), end="")
        if not yes and input(f"Import these keys into {source} (no commit)? [y/N] ").lower() != "y":
            return 2
        if source.read_text() != original:
            raise ValueError("Tracked settings changed during import; retry")
        self.backup(source, original)
        atomic(source, after, source.stat().st_mode & 0o777)
        # An approved import adopts these keys, including object/scalar transitions.
        baseline = object_file(self.state / "applied.json")
        owned = baseline.setdefault(name, {})
        desired = flatten(rendered_config(tracked, name, self.config, self.root))
        for selected in keys:
            for key in list(owned):
                if key == selected or key.startswith(selected + "/"):
                    del owned[key]
            for key, value in desired.items():
                if key == selected or key.startswith(selected + "/"):
                    owned[key] = value
        atomic(self.state / "applied.json", encode(baseline))
        return 0

    @staticmethod
    def portable(at, value):
        # Import ordinary preferences, not arbitrary credential-bearing integrations.
        if at[0] not in IMPORTABLE:
            raise ValueError(f"Import of {pointer(at)} is not allowed; edit portable integration definitions in the repo manually")
        if any(re.search(r"token|secret|password|authorization|credential|header|apikey|api_key|prompt", key, re.I) for key in at[1:]):
            raise ValueError("Potentially sensitive setting; edit the tracked source manually")
        def inspect(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    if re.search(r"key|token|secret|password|authorization|credential|header|prompt", key, re.I):
                        raise ValueError("Potentially sensitive setting; edit the tracked source manually")
                    inspect(child)
            elif isinstance(item, list):
                for child in item:
                    inspect(child)
            elif isinstance(item, str) and (re.search(r"(?:/Users/|/home/|file://|[A-Za-z]:\\|sk-|Bearer )", item) or item.startswith(("/", "~/"))):
                raise ValueError("Machine-specific path or potential credential; edit the tracked source manually")
        inspect(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "apply", "sync", "import"))
    parser.add_argument("--file", choices=("opencode.json", "cli.json"), default="opencode.json")
    parser.add_argument("--key", action="append", default=[], help="Explicit JSON pointer to import, e.g. /model")
    parser.add_argument("--yes", action="store_true", help="Approve the displayed changes without prompting")
    parser.add_argument("--force", action="store_true", help="Explicit apply only: replace locally changed managed values after backup")
    args = parser.parse_args()
    if args.force and args.action != "apply":
        parser.error("--force is available only for explicit apply")
    settings = Settings()
    try:
        if args.action == "status":
            _, reports, conflicts, _ = settings.plan()
            print("\n".join([*reports, *conflicts, *settings.local_only()]) or "Settings are up to date.")
            return 2 if conflicts else 0
        if args.action == "import":
            if not args.key:
                parser.error("import requires at least one --key; whole-file import is intentionally unavailable")
            with settings.lock():
                return settings.import_keys(args.file, args.key, args.yes)
        return settings.apply(args.force, args.action == "sync", args.yes)
    except (ValueError, OSError, EOFError) as error:
        print("opencode_settings: " + str(error), file=sys.stderr)
        return 0 if args.action == "sync" else 2


if __name__ == "__main__":
    sys.exit(main())
