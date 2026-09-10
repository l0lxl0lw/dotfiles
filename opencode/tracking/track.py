#!/usr/bin/env python3
"""Issue/project tracking and read-only branch freshness monitoring. Python stdlib only."""
import argparse
import contextlib
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

OWNER = "opencfo-ai"
NUMBER = 4
STATUSES = ["Backlog", "Researching", "Planning", "Ready", "Implementing", "In review", "Done"]
SYNC = ["Not started", "Unchecked", "Up to date", "Needs sync", "Syncing", "Conflicts", "Verifying"]
STATE = Path(os.environ.get("OPENCODE_TRACK_STATE", str(Path.home() / ".local/state/opencode-track")))


def run(*args, cwd=None):
    p = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=90)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "Command failed: " + str(args))
    return p.stdout.strip()


def gh(*args):
    return json.loads(run("gh", *args))


def graphql(query, **variables):
    args = ["api", "graphql", "-f", "query=" + query]
    for key, value in variables.items():
        args.extend(["-f", key + "=" + value])
    result = gh(*args)
    if result.get("errors"):
        raise RuntimeError(json.dumps(result["errors"]))
    return result["data"]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@contextlib.contextmanager
def registry():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = STATE / "branches.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        try:
            yield data
        finally:
            fd, temp = tempfile.mkstemp(dir=STATE)
            with os.fdopen(fd, "w") as out:
                json.dump(data, out, indent=2)
            os.replace(temp, path)


def project():
    p = gh("project", "view", str(NUMBER), "--owner", OWNER, "--format", "json")
    fields = gh("project", "field-list", str(NUMBER), "--owner", OWNER, "--limit", "100", "--format", "json")
    return p["id"], {f["name"]: f for f in fields["fields"]}


def configure():
    pid, fields = project()
    for name, choices in [("Status", STATUSES), ("Branch sync", SYNC)]:
        if name in fields:
            existing = [o["name"] for o in fields[name].get("options", [])]
            if existing == choices:
                continue
            # Replacing options invalidates option IDs; refuse populated projects.
            items = gh("project", "item-list", str(NUMBER), "--owner", OWNER, "--limit", "1", "--format", "json")
            if items["totalCount"]:
                raise RuntimeError("Project contains items; migrate field options explicitly before configuring")
            options = [{"name": c, "color": "GRAY", "description": c} for c in choices]
            query = "mutation { updateProjectV2Field(input:{fieldId:" + json.dumps(fields[name]["id"]) + ",singleSelectOptions:" + "[" + ",".join("{name:" + json.dumps(o["name"]) + ",color:GRAY,description:" + json.dumps(o["description"]) + "}" for o in options) + "]}) { projectV2Field { ... on ProjectV2SingleSelectField { id } } } }"
            graphql(query)
        else:
            run("gh", "project", "field-create", str(NUMBER), "--owner", OWNER, "--name", name,
                "--data-type", "SINGLE_SELECT", "--single-select-options", ",".join(choices))
    print("Configured https://github.com/orgs/opencfo-ai/projects/4")


def issue_url(value):
    if value.isdigit():
        repo = gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
        value = "https://github.com/" + repo + "/issues/" + value
    match = re.fullmatch(r"https://github\.com/(opencfo-ai/[^/]+)/issues/(\d+)", value)
    if not match:
        raise RuntimeError("Use an opencfo-ai issue URL (or a number in its repository)")
    # Check existence and access before making any mutation.
    gh("issue", "view", value, "--json", "id")
    return value


def item(value):
    return gh("project", "item-add", str(NUMBER), "--owner", OWNER, "--url", value, "--format", "json")["id"]


def set_field(value, name, selection):
    pid, fields = project()
    if name not in fields:
        raise RuntimeError("Missing project field: " + name)
    option = next((o["id"] for o in fields[name]["options"] if o["name"] == selection), None)
    if not option:
        raise RuntimeError("Missing option: " + selection)
    iid = item(value)
    run("gh", "project", "item-edit", "--id", iid, "--project-id", pid,
        "--field-id", fields[name]["id"], "--single-select-option-id", option)
    result = graphql('query($id:ID!,$name:String!){node(id:$id){... on ProjectV2Item{fieldValueByName(name:$name){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}', id=iid, name=name)
    actual = result["node"]["fieldValueByName"]
    if not actual or actual.get("name") != selection:
        raise RuntimeError("Project field update did not persist: " + name)


def note(value, heading, body, key=None):
    marker = "<!-- opencode-track:" + key + " -->" if key else ""
    if marker:
        repo, number = value.split("github.com/")[1].split("/issues/")
        pages = gh("api", "--paginate", "--slurp", "repos/" + repo + "/issues/" + number + "/comments")
        if any(marker in c["body"] for page in pages for c in page):
            return
    print(run("gh", "issue", "comment", value, "--body", "## " + heading + "\n\n" + body + "\n\n" + marker))


def git(cwd, *args):
    return run("git", *args, cwd=cwd)


def register(value):
    cwd = git(None, "rev-parse", "--show-toplevel")
    repo = gh("repo", "view", "--json", "nameWithOwner", "defaultBranchRef")
    expected = value.split("github.com/")[1].split("/issues/")[0]
    if repo["nameWithOwner"].lower() != expected.lower():
        raise RuntimeError("Issue and worktree repository differ")
    branch = git(cwd, "symbolic-ref", "--short", "HEAD")
    target = repo["defaultBranchRef"]["name"]
    if branch == target:
        raise RuntimeError("Register an implementation branch, not the default branch")
    common = str(Path(git(cwd, "rev-parse", "--git-common-dir")).resolve())
    if not Path(git(cwd, "rev-parse", "--git-common-dir")).is_absolute():
        common = str((Path(cwd) / git(cwd, "rev-parse", "--git-common-dir")).resolve())
    origin = git(cwd, "remote", "get-url", "origin")
    remote_repo = re.sub(r"\.git$", "", origin.rstrip("/"))
    if remote_repo.lower() not in ("https://github.com/" + expected.lower(), "git@github.com:" + expected.lower(), "ssh://git@github.com/" + expected.lower()):
        raise RuntimeError("origin must refer to the issue repository")
    with registry() as data:
        if value in data:
            old = data[value]
            if old["common"] != common or old["branch"] != branch:
                raise RuntimeError("Issue already tracks another branch; unregister it explicitly first")
            old["path"] = cwd
        else:
            if any(r["common"] == common and r["branch"] == branch for r in data.values()):
                raise RuntimeError("Branch already registered to another issue")
            set_field(value, "Branch sync", "Unchecked")
            data[value] = dict(path=cwd, common=common, branch=branch, target=target, state="Unchecked", observed=None)
        note(value, "Branch tracking", "Branch: `" + branch + "`\n\nTarget: `origin/" + target + "`\n\nAutomatic detection; sync requires an explicit request.", "register-" + branch)


def locate(record):
    # Git's common directory survives linked-worktree renames; recover the path.
    text = run("git", "--git-dir=" + record["common"], "worktree", "list", "--porcelain")
    for block in text.split("\n\n"):
        entries = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        if entries.get("branch") == "refs/heads/" + record["branch"]:
            path = entries["worktree"]
            if git(path, "symbolic-ref", "--short", "HEAD") == record["branch"]:
                record["path"] = path
                return path
        # A rebase temporarily detaches HEAD. Identify its original branch from
        # Git's operation metadata rather than misreporting a missing worktree.
        elif entries.get("worktree") and "detached" in block.splitlines():
            path = entries["worktree"]
            gd = Path(git(path, "rev-parse", "--absolute-git-dir"))
            for operation in ("rebase-merge", "rebase-apply"):
                name = gd / operation / "head-name"
                if name.exists() and name.read_text().strip() == "refs/heads/" + record["branch"]:
                    record["path"] = path
                    return path
    raise RuntimeError("Registered branch has no resolvable worktree; re-register after a branch rename")


def ancestry(path, target):
    p = subprocess.run(["git", "merge-base", "--is-ancestor", target, "HEAD"], cwd=path, capture_output=True)
    if p.returncode not in (0, 1):
        raise RuntimeError("Cannot compare branch ancestry")
    return p.returncode == 0


def inspect(record):
    path = locate(record)
    git(path, "fetch", "--no-tags", "origin", "+refs/heads/" + record["target"] + ":refs/remotes/origin/" + record["target"])
    target = git(path, "rev-parse", "refs/remotes/origin/" + record["target"])
    gd = Path(git(path, "rev-parse", "--absolute-git-dir"))
    if git(path, "ls-files", "-u"):
        state = "Conflicts"
    elif (gd / "rebase-merge").exists() or (gd / "rebase-apply").exists() or (gd / "MERGE_HEAD").exists():
        state = "Syncing"
    elif record["state"] in ("Syncing", "Conflicts", "Verifying"):
        state = "Verifying"
    else:
        state = "Up to date" if ancestry(path, target) else "Needs sync"
    return state, target


def refresh(value=None):
    failed = False
    with registry() as data:
        if value and value not in data:
            raise RuntimeError("Issue is not registered")
        for url, record in data.items():
            if value and value != url:
                continue
            try:
                closed = gh("issue", "view", url, "--json", "state")["state"] == "CLOSED"
                if closed:
                    print(url + ": closed; skipped (use unregister to retire tracking)")
                    continue
                state, target = inspect(record)
                changed = state != record["state"] or target != record.get("observed")
                if changed:
                    set_field(url, "Branch sync", state)
                    if state == "Needs sync":
                        note(url, "Branch sync — Needs sync", "`" + record["branch"] + "` is behind `origin/" + record["target"] + "` at `" + target + "`. Request `/sync " + url + "` when ready.", "behind-" + target)
                record.update(state=state, observed=target, checked=now(), error=None)
                print(url + ": " + state)
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
                failed = True
                record.update(error=str(e), checked=now())
                # Do not erase a conflict or verification state on an offline check.
                if record["state"] not in ("Syncing", "Conflicts", "Verifying"):
                    try:
                        set_field(url, "Branch sync", "Unchecked")
                        record["state"] = "Unchecked"
                    except Exception:
                        pass
                print(url + ": " + str(e), file=sys.stderr)
    if failed:
        raise RuntimeError("Some checks failed; see local tracking status for details")


def sync_state(value, state, evidence=None):
    with registry() as data:
        if value not in data:
            if state == "Not started":
                set_field(value, "Branch sync", state)
                return
            raise RuntimeError("Register the issue's work branch first")
        record = data[value]
        if state == "Up to date":
            if not evidence:
                raise RuntimeError("Verification evidence file is required")
            body = Path(evidence).read_text().strip()
            if not body:
                raise RuntimeError("Verification evidence is empty")
            detected, target = inspect(record)
            path = record["path"]
            if detected in ("Conflicts", "Syncing") or not ancestry(path, target):
                raise RuntimeError("Sync incomplete or target moved; resolve and verify again")
            head = git(path, "rev-parse", "HEAD")
            note(value, "Sync verification", "HEAD: `" + head + "`\n\nTarget: `" + target + "`\n\n" + body, "verified-" + head + "-" + target)
            record["observed"] = target
        set_field(value, "Branch sync", state)
        record.update(state=state, checked=now())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("configure")
    sub.add_parser("list")
    for name in ("register", "unregister", "refresh", "status", "note", "sync-state", "add"):
        p = sub.add_parser(name)
        p.add_argument("issue", nargs="?" if name == "refresh" else None)
        if name == "status":
            p.add_argument("value", choices=STATUSES)
        if name == "sync-state":
            p.add_argument("value", choices=SYNC)
            p.add_argument("--evidence")
        if name == "note":
            p.add_argument("heading")
            p.add_argument("body_file")
            p.add_argument("--key")
    args = parser.parse_args()
    if args.command == "configure":
        configure()
        return
    if args.command == "list":
        with registry() as data:
            print(json.dumps(data, indent=2))
        return
    value = issue_url(args.issue) if args.issue else None
    if args.command == "add":
        item(value)
        print(value)
    elif args.command == "register":
        register(value)
    elif args.command == "unregister":
        with registry() as data:
            data.pop(value, None)
    elif args.command == "refresh":
        refresh(value)
    elif args.command == "status":
        set_field(value, "Status", args.value)
    elif args.command == "sync-state":
        sync_state(value, args.value, args.evidence)
    elif args.command == "note":
        note(value, args.heading, Path(args.body_file).read_text(), args.key)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print("track: " + str(error), file=sys.stderr)
        sys.exit(1)
