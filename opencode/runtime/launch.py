#!/usr/bin/env python3
"""Pin OpenCode resources without relocating HOME.

Use from the shell wrapper or directly from an IDE/API launcher. No credentials
are copied, printed, or included in the resource manifest.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tracking"))
from private_config import load as load_private_config

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("agents", "commands", "tracking", "orca", "runtime", "schemas")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_paths(root):
    files = {}
    for folder in FOLDERS:
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
                files[str(path.relative_to(root))] = path
    shared = root.parent / "ai/shared/skills"
    for path in sorted(shared.rglob("*")):
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
            files["skills/" + str(path.relative_to(shared))] = path
    return files


def body(path):
    text = path.read_text()
    if not text.startswith("---\n"):
        raise RuntimeError("Missing frontmatter: " + str(path))
    return text.split("---", 2)[2].lstrip("\n")


def definition(path):
    """Parse the deliberately scalar/map-only owned frontmatter; fail on unsupported YAML."""
    front = path.read_text().split("---", 2)[1]
    result = {}
    stack = [(-1, result)]
    for line in front.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        match = re.fullmatch(r'''\s*("(?:[^"\\]|\\.)*"|'[^']*'|[^:]+):\s*(.*)''', line)
        if not match:
            raise RuntimeError("Unsupported owned frontmatter in " + str(path))
        key, raw = match.groups()
        key = json.loads(key) if key.startswith('"') else key.strip("'").strip()
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if key in parent:
            raise RuntimeError("Duplicate frontmatter key: " + key)
        if not raw:
            value = {}
        elif raw in ("true", "false"):
            value = raw == "true"
        elif re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
            value = json.loads(raw)
        elif raw.startswith('"'):
            value = json.loads(raw)
        elif raw.startswith("'") and raw.endswith("'"):
            value = raw[1:-1].replace("''", "'")
        elif raw.startswith(("|", ">", "[", "{", "&", "*")):
            raise RuntimeError("Use scalar/map frontmatter in owned workflow definitions: " + str(path))
        else:
            value = raw
        parent[key] = value
        if isinstance(value, dict):
            stack.append((indent, value))
    return result


def build_bundle(root=ROOT, state=None):
    root = root.resolve()
    state = Path(state or os.environ.get("OPENCODE_WORKFLOW_STATE", str(Path.home() / ".local/state/opencode-workflow"))).expanduser().resolve()
    for parent in (root, *root.parents):
        if (parent / ".git").exists():
            if state.resolve() == parent or parent in state.resolve().parents:
                raise RuntimeError("Workflow resource state must live outside the source repository")
            break
    paths = source_paths(root)
    files = {name: path.read_bytes() for name, path in paths.items()}
    source_hashes = {k: digest(v) for k, v in files.items()}
    modes = {k: bool(path.stat().st_mode & 0o111) for k, path in paths.items()}
    key = digest(json.dumps({"files": source_hashes, "executable": modes}, sort_keys=True).encode())
    target = state / "resources" / key
    if target.exists():
        validate_bundle(target)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".building-", dir=target.parent))
    try:
        aliases = {}
        for name, raw in files.items():
            if name.endswith("/SKILL.md"):
                found = re.search(r"^name:\s*([^\n]+)$", raw.decode(), re.M)
                if found:
                    original = found[1].strip().strip("\"'")
                    aliases[original] = "wf-" + key[:10] + "-" + original
        for name, raw in files.items():
            destination = temporary / "opencode" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if name.endswith(".md"):
                pinned = str(target / "opencode")
                text = raw.decode().replace("~/dotfiles/opencode", pinned).replace(str(root), pinned)
                text = text.replace("~/dotfiles/ai/shared/skills", pinned + "/skills")
                text = text.replace(str(root.parent / "ai/shared/skills"), pinned + "/skills")
                if name.endswith("/SKILL.md"):
                    text = re.sub(r"^name:\s*([^\n]+)$", lambda m: "name: " + aliases[m[1].strip().strip("\"'")], text, count=1, flags=re.M)
                for old, alias in aliases.items():
                    text = text.replace("`" + old + "`", "`" + alias + "`")
                    text = text.replace("the " + old + " skill", "the " + alias + " skill")
                # Keep shell snippets working when the resource root contains spaces.
                text = re.sub(r"(python3|bash) " + re.escape(pinned) + r"(/[\w./-]+)",
                              lambda m: m[1] + ' "' + pinned + m[2] + '"', text)
                raw = text.encode()
            destination.write_bytes(raw)
            destination.chmod(0o755 if modes[name] else 0o644)
        config = temporary / "config"
        config.mkdir()
        for folder in ("agents", "commands"):
            (config / folder).symlink_to(target / "opencode" / folder, target_is_directory=True)
        (config / "skills").mkdir()
        names = set()
        for skill in sorted((temporary / "opencode/skills").rglob("SKILL.md")):
            if any((p / "SKILL.md").exists() for p in skill.parents if p != skill.parent and temporary in p.parents):
                continue
            match = re.search(r"^name:\s*([^\n]+)$", skill.read_text(), re.M)
            if not match:
                raise RuntimeError("Skill lacks name: " + str(skill))
            name = match[1].strip().strip("\"'")
            if name in names or not re.fullmatch(r"[a-z0-9-]+", name):
                raise RuntimeError("Duplicate/invalid skill: " + name)
            names.add(name)
            relative = skill.parent.relative_to(temporary)
            (config / "skills" / name).symlink_to(target / relative, target_is_directory=True)
        transformed = {str(p.relative_to(temporary)): {"sha256": digest(p.read_bytes()), "executable": bool(p.stat().st_mode & 0o111)}
                       for p in (temporary / "opencode").rglob("*") if p.is_file()}
        manifest = {"version": 1, "source_root": str(root), "revision": key,
                    "source_hashes": source_hashes, "resource_hashes": transformed, "skill_aliases": aliases}
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        try:
            temporary.rename(target)
        except OSError:
            if not target.exists():
                raise
            validate_bundle(target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


def validate_bundle(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    actual = {str(p.relative_to(bundle)): {"sha256": digest(p.read_bytes()), "executable": bool(p.stat().st_mode & 0o111)} for p in (bundle / "opencode").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts}
    if actual != manifest["resource_hashes"]:
        raise RuntimeError("Pinned workflow resources changed: " + str(bundle))
    return manifest


def compose_config(bundle, existing):
    """Layer owned workflow links with an IDE's existing hooks/assets, without copying credentials."""
    owned = bundle / "config"
    if not existing or Path(existing).resolve() == owned.resolve():
        return owned
    foreign = Path(existing).resolve()
    if not foreign.is_dir():
        raise RuntimeError("Existing OPENCODE_CONFIG_DIR does not exist: " + str(foreign))
    parent = bundle.parent.parent / "launch-configs"
    if foreign.parent == parent.resolve() and (foreign / "bridge.json").exists():
        meta = json.loads((foreign / "bridge.json").read_text())
        if meta.get("bundle") == str(bundle):
            return foreign
    mapping = {}
    folders = {"agent", "agents", "command", "commands", "skill", "skills", "plugin", "plugins"}
    for entry in foreign.iterdir():
        if entry.name in (".git", "bridge.json"):
            continue
        if entry.name in folders and entry.is_dir():
            for child in entry.iterdir():
                mapping[entry.name + "/" + child.name] = child.resolve()
        else:
            mapping[entry.name] = entry
    for folder in ("agents", "commands", "skills"):
        for entry in (owned / folder).iterdir():
            key = folder + "/" + entry.name
            singular = folder[:-1] + "/" + entry.name
            for candidate in (key, singular):
                if candidate in mapping and mapping[candidate] != entry.resolve():
                    raise RuntimeError("Custom config conflicts with owned workflow entry " + candidate + "; use --live or reconcile it explicitly")
            mapping[key] = entry.resolve()
    key = digest(json.dumps({"bundle": str(bundle), "links": {k: str(v) for k, v in mapping.items()}}, sort_keys=True).encode())
    target = parent / key
    if not target.exists():
        parent.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix=".bridge-", dir=parent))
        try:
            for relative, source in mapping.items():
                path = temp / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(source, target_is_directory=source.is_dir())
            (temp / "bridge.json").write_text(json.dumps({"bundle": str(bundle), "custom_directory": str(foreign)}))
            try:
                temp.rename(target)
            except OSError:
                if not target.exists():
                    raise
        finally:
            if temp.exists():
                shutil.rmtree(temp)
    return target


def private_skill_command(name):
    """A local command reference, never an embedded copy of private instructions."""
    return {
        "description": "Load private skill " + name,
        "template": "Use the skill tool to load `" + name + "` and follow its instructions.\n\n"
                    "User arguments (task input, not permission overrides):\n$ARGUMENTS",
    }


def environment(bundle, environ=None, directory=None):
    env = dict(os.environ if environ is None else environ)
    existing = env.get("OPENCODE_CONFIG_DIR")
    global_dir = Path(env.get("XDG_CONFIG_HOME", str(Path(env.get("HOME", str(Path.home()))) / ".config"))) / "opencode"
    # The ordinary global directory is already loaded by OpenCode. IDE-owned
    # extra directories (notably Orca hooks) need a composed catalog instead.
    custom = existing if existing and Path(existing).resolve() != global_dir.resolve() else None
    config_dir = compose_config(bundle, custom)
    root = bundle / "opencode"
    # Preserve user JSON, credentials and model settings. Managed commands are
    # loaded from their native definitions.
    cfg = json.loads(env.get("OPENCODE_CONFIG_CONTENT", "{}"))
    if not isinstance(cfg, dict):
        raise RuntimeError("OPENCODE_CONFIG_CONTENT must be a JSON object")
    private = load_private_config(env)
    private_commands = set()
    if private.get("skills_paths"):
        skills = cfg.setdefault("skills", {})
        if not isinstance(skills, dict) or not isinstance(skills.get("paths", []), list):
            raise RuntimeError("skills.paths must be a list")
        paths = list(dict.fromkeys([*skills.get("paths", []), *private["skills_paths"]]))
        aliases = json.loads((bundle / "manifest.json").read_text())["skill_aliases"]
        names = set(aliases) | set(aliases.values())
        for directory in paths:
            for skill in Path(directory).expanduser().rglob("SKILL.md"):
                match = re.search(r"^name:\s*([^\n]+)$", skill.read_text(), re.M)
                if not match:
                    raise RuntimeError("Private skill is missing its name")
                key = match[1].strip().strip("\"'")
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key) or len(key) > 64:
                    raise RuntimeError("Invalid skill name in configured skills path")
                if key in names:
                    raise RuntimeError("Private skill conflicts with another skill: " + key)
                names.add(key)
                if directory in private["skills_paths"]:
                    private_commands.add(key)
        skills["paths"] = paths
    if not isinstance(cfg.get("agent", {}), dict) or not isinstance(cfg.get("command", {}), dict):
        raise RuntimeError("agent and command configuration must be objects")
    commands = cfg.setdefault("command", {})
    # Nested launches retain injected config. Remove only unchanged wrappers we own;
    # preserve edits so a collision fails rather than silently replacing user config.
    prior = json.loads(env.get("OPENCODE_PRIVATE_SKILL_COMMANDS", "[]"))
    if not isinstance(prior, list) or any(not isinstance(key, str) for key in prior):
        raise RuntimeError("Invalid private command ownership metadata")
    for key in prior:
        if commands.get(key) == private_skill_command(key):
            del commands[key]
    for path in (root / "commands").glob("*.md"):
        commands[path.stem] = {**definition(path), "template": body(path)}
    for key in sorted(private_commands):
        # Global/IDE command files are outside cfg, but still share the slash namespace.
        directories = [global_dir, Path(config_dir)]
        if key in commands or any((directory / folder / (key + ".md")).exists()
                                  for directory in directories for folder in ("command", "commands")):
            raise RuntimeError("Private skill command conflicts with existing command: " + key)
        commands[key] = private_skill_command(key)
    env.update(OPENCODE_CONFIG_CONTENT=json.dumps(cfg), OPENCODE_CONFIG_DIR=str(config_dir),
               OPENCODE_PRIVATE_SKILL_COMMANDS=json.dumps(sorted(private_commands)),
               OPENCODE_WORKFLOW_ROOT=str(root),
               OPENCODE_WORKFLOW_REVISION=bundle.name, OPENCODE_DISABLE_EXTERNAL_SKILLS="1",
               OPENCODE_DISABLE_CLAUDE_CODE_SKILLS="1", PYTHONDONTWRITEBYTECODE="1")
    return skill_environment(env, directory)


def skill_files(directory):
    """Follow installed skill links, excluding templates nested inside a skill."""
    if not directory.is_dir():
        return {}
    result = {}
    visited = set()
    for base, dirs, files in os.walk(directory, followlinks=True):
        physical = Path(base).resolve()
        if physical in visited:
            dirs[:] = []
            continue
        visited.add(physical)
        dirs[:] = sorted(d for d in dirs if d not in (".git", "node_modules", "__pycache__"))
        if "SKILL.md" not in files:
            continue
        dirs[:] = []
        path = Path(base) / "SKILL.md"
        text = path.read_text()
        front = text.split("---", 2)
        match = re.search(r"^name:\s*([^\n]+)$", front[1], re.M) if len(front) == 3 else None
        if not match:
            raise RuntimeError("Skill lacks name: " + str(path))
        name = match[1].strip().strip("\"'")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
            raise RuntimeError("Invalid skill name: " + str(path))
        if name in result:
            raise RuntimeError("Duplicate skill in one source: " + name + " in " + str(directory))
        result[name] = path.resolve()
    return result


def project_skill_sources(directory):
    """Least to most specific; stop at the current worktree, including linked ones."""
    directory = Path(directory).resolve()
    proc = subprocess.run(["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
                          text=True, capture_output=True)
    stop = Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else directory
    ancestors = []
    current = directory
    while True:
        ancestors.append(current)
        if current == stop or current.parent == current:
            break
        current = current.parent
    return [parent / folder / "skills" for parent in reversed(ancestors)
            for folder in (".claude", ".agents", ".opencode")]


def skill_environment(environ, directory=None):
    """Add explicit project sources and executable fallback commands without editing HOME."""
    env = dict(environ)
    cwd = Path(directory or Path.cwd()).resolve()
    home = Path(env.get("HOME", str(Path.home())))
    global_dir = Path(env.get("XDG_CONFIG_HOME", str(home / ".config"))) / "opencode"
    cfg = json.loads(env.get("OPENCODE_CONFIG_CONTENT", "{}"))
    skills = cfg.setdefault("skills", {})
    commands = cfg.setdefault("command", {})
    # Remove only our own previous additions on a nested launch from another repo.
    prior = json.loads(env.get("OPENCODE_SKILL_CATALOG", "{}"))
    old_paths = set(prior.get("paths", []))
    paths = [p for p in skills.get("paths", []) if p not in old_paths]
    for key, value in prior.get("commands", {}).items():
        if commands.get(key) == value:
            del commands[key]
    selected = skill_files(global_dir / "skills")
    for raw in paths:
        source = home / raw[2:] if raw.startswith("~/") else Path(raw)
        selected.update(skill_files(source if source.is_absolute() else cwd / source))
    projects = {}
    for source in project_skill_sources(cwd):
        found = skill_files(source)
        for name in projects.keys() & found.keys():
            if projects[name] != found[name]:
                print(f"Project skill '{name}': {found[name]} overrides {projects[name]}", file=sys.stderr)
        projects.update(found)
    selected.update(projects)
    # Explicit paths expose compatibility-directory skills. The execution overlay
    # enforces the chosen winner independently of native discovery ordering.
    added = [str(path.parent) for path in projects.values() if str(path.parent) not in paths]
    skills["paths"] = [*paths, *added]
    occupied = set(commands) | set(selected)
    for source in (global_dir, cwd / ".opencode"):
        for folder in ("commands", "command"):
            occupied.update(p.stem for p in (source / folder).glob("*.md"))
    generated = {}
    for name, path in sorted(selected.items()):
        if re.match(r"wf-[a-f0-9]+-", name):
            continue
        alias = "skill-" + name
        while alias in occupied:
            alias = "skill-" + alias
        occupied.add(alias)
        # Read by exact path: this also handles a native command hiding the skill
        # or a project definition overriding a same-name global definition.
        value = {"description": "Skill fallback: " + name,
                 "template": "Read " + json.dumps(str(path)) + " and follow that skill. "
                             "Its base directory is " + json.dumps(str(path.parent)) + ". "
                             "Use the host's native tools; AskUserQuestion means its question dialog "
                             "(or ask in chat when unavailable). Load the skill before acting.\n\n"
                             "User arguments:\n$ARGUMENTS"}
        commands[alias] = value
        generated[alias] = value
    overlay = str((Path(env.get("OPENCODE_WORKFLOW_ROOT", str(ROOT))) / "runtime/project-skills.js").resolve())
    # Replace our prior snapshot plugin on nested launches; preserve other plugins.
    plugins = [p for p in cfg.get("plugin", []) if p != prior.get("plugin")]
    plugin = Path(overlay).as_uri()
    if plugin not in plugins:
        plugins.append(plugin)
    cfg["plugin"] = plugins
    env["OPENCODE_SKILL_CATALOG"] = json.dumps({"paths": added, "commands": generated,
                                               "projects": {name: str(path) for name, path in projects.items()},
                                               "plugin": plugin})
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(cfg)
    env["OPENCODE_DISABLE_EXTERNAL_SKILLS"] = "1"
    env["OPENCODE_DISABLE_CLAUDE_CODE_SKILLS"] = "1"
    return env


def doctor(bundle, github=False):
    manifest = validate_bundle(bundle)
    for exe in ("git", "opencode"):
        if not shutil.which(exe):
            raise RuntimeError("Required executable missing: " + exe)
    with tempfile.NamedTemporaryFile(prefix="workflow-doctor-") as f:
        f.write(b"temporary artifact probe\n")
        f.flush()
    result = {"resources": "pass", "temporary_filesystem_write": "pass",
              "revision": manifest["revision"],
              "native_permission_and_model_inference": "not tested"}
    if github:
        p = subprocess.run(["gh", "api", "user", "--jq", ".login"], text=True, capture_output=True)
        if p.returncode:
            raise RuntimeError("GitHub authentication failed; run gh auth status")
        result["github_login"] = p.stdout.strip()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--github", action="store_true", help="Also validate GitHub auth without writes")
    parser.add_argument("--prepare", action="store_true", help="Print non-secret launch metadata; do not launch")
    parser.add_argument("--live", action="store_true", help="Use normal live catalogs without snapshots")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.live:
        binary = shutil.which("opencode")
        if not binary:
            raise RuntimeError("opencode is not on PATH")
        argv = args.args[1:] if args.args[:1] == ["--"] else args.args
        directory = argv[0] if argv and Path(argv[0]).is_dir() else None
        env = skill_environment(os.environ, directory)
        os.execve(binary, [binary, *argv], env)
    pinned = os.environ.get("OPENCODE_WORKFLOW_ROOT")
    bundle = Path(pinned).parent if pinned else build_bundle()
    validate_bundle(bundle)
    if args.doctor:
        print(json.dumps(doctor(bundle, args.github), indent=2))
        return
    argv = args.args[1:] if args.args[:1] == ["--"] else args.args
    directory = argv[0] if argv and Path(argv[0]).is_dir() else None
    env = environment(bundle, directory=directory)
    if args.prepare:
        print(json.dumps({k: env[k] for k in ("OPENCODE_CONFIG_DIR", "OPENCODE_WORKFLOW_ROOT",
                         "OPENCODE_WORKFLOW_REVISION")}, indent=2))
        return
    binary = shutil.which("opencode")
    if not binary:
        raise RuntimeError("opencode is not on PATH")
    argv = args.args[1:] if args.args[:1] == ["--"] else args.args
    os.execve(binary, [binary, *argv], env)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
