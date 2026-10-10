#!/usr/bin/env python3
"""Journal one explicitly authorized, local Orca delivery. Does not run an LLM."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

import handoff
import packet
import verify
import workflow_state as evidence

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def command(argv, cwd=None, allowed=(0,), timeout=180):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout,
                            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    require(result.returncode in allowed, (result.stderr or result.stdout or str(argv))[-8000:])
    return result


def git(cwd, *args):
    return command(['git', *args], cwd).stdout.strip()


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def valid_key(key):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', key), 'Invalid delivery key')


@contextlib.contextmanager
def locked(directory, wait=False):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / 'lock').open('a') as lock:
        deadline = time.monotonic() + (30 if wait else 0)
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'Delivery operation already running; resume the same key later')
                time.sleep(0.2)
        yield


class Delivery:
    def __init__(self, directory, state):
        self.directory, self.state = directory, state

    def save(self, event=None):
        if event:
            self.state.setdefault('history', []).append({'event': event, 'at': time.time(),
                                                       'stage': self.state['stage']})
        atomic(self.directory / 'state.json', self.state)

    def plan(self):
        issue, comments = handoff.issue_and_comments(self.state['issue'])
        plan, contract = verify.approved_plan(issue, comments, self.state['plan'])
        require(evidence.digest(plan) == self.state['plan_digest']
                and contract['revision'] == self.state['contract_revision'],
                'Approved plan/contract changed; new explicit authorization is required')
        return issue, comments

    def workspace(self):
        path = str(evidence.root())
        require(self.state.get('workspace') == path, 'Run from the bound feature workspace')
        require(git(path, 'remote', 'get-url', 'origin') == self.state['origin'], 'Origin changed')
        require(git(path, 'branch', '--show-current') == self.state['branch'] != 'main', 'Branch changed')
        require(not git(path, 'ls-files', '--unmerged'), 'Resolve the recorded merge conflicts first')
        return path

    def gate(self):
        issue, comments = self.plan()
        return handoff.v2_gate(issue, comments, self.state['plan'], self.state.get('review'), self.workspace())

    def dispatch(self):
        require(self.state['stage'] == 'launch', 'Already acknowledged; continue in the bound workspace')
        require(not os.environ.get('ORCA_ENVIRONMENT') and not os.environ.get('ORCA_PAIRING_CODE'),
                'Delivery target changed; local shared-state execution is required')
        self.plan()
        require(str(evidence.root()) == self.state['source'], 'Dispatch from the original planning checkout')
        require(not git(self.state['source'], 'status', '--porcelain'),
                'Planning checkout has uncommitted changes; a new worktree will not contain them')
        script = ROOT / 'skills/orca/orca-handoff/scripts/handoff.py'
        if not script.exists():
            script = ROOT.parent / 'shared/skills/orca/orca-handoff/scripts/handoff.py'
        require(script.is_file(), 'Pinned Orca handoff helper unavailable')
        # The receiver uses this exact resource revision, even if its launcher is older.
        skills = ROOT / 'skills' if (ROOT / 'skills').is_dir() else ROOT.parent / 'shared/skills'
        invocation = shlex.join([sys.executable, '-B', str(ROOT / 'tracking/delivery.py'),
                                 '--key', self.directory.name, '--state-dir', str(self.directory.parent)])
        brief = (f'You own delivery run {self.directory.name}. Read {skills / "develop/develop-deliver/SKILL.md"} '
                 f'and its protocol at {ROOT / "tracking/references/delivery.md"}. '
                 f'Use `{invocation} ACTION`. Your first action is ack --session YOUR_ACTUAL_SESSION_ID '
                 f'from your feature worktree. Then own the loop until completion or a recorded blocker. '
                 f'Issue: {self.state["issue"]}; approved plan: {self.state["plan"]}. '
                 'Authorization: execute, verify, fresh independent review, at most three shared review/CI repair '
                 'cycles, merge origin/main updates, commit, push, open a non-draft PR, wait for required CI on '
                 'the current head. No merge of the PR. Use fresh Task workers for execution and review. '
                 'Do not ask for routine stage or commit-message approval. Follow the recorded scope; report '
                 'product decisions, unrelated blockers and exhausted repairs. Never redispatch this run.')
        brief_path = self.directory / 'brief.txt'
        brief_path.write_text(brief)
        home = self.directory / 'handoff'
        saved = home / self.directory.name / 'state.json'
        action = 'resume' if saved.exists() else 'start'
        args = [sys.executable, '-B', str(script), action, '--key', self.directory.name, '--state-dir', str(home)]
        if action == 'start':
            args += ['--repo', 'path:' + self.state['source'], '--name', self.directory.name,
                     '--brief-file', str(brief_path)]
        self.save('dispatch_intent')
        response = command(args, allowed=(0, 2), timeout=600)
        self.state['handoff_result'] = json.loads(response.stdout)
        self.save('dispatch_receipt')
        # Acceptance is deliberately not acknowledgement. The caller now uses wait-start.

    def ack(self, session):
        require(session, 'Supply the actual receiving OpenCode session ID')
        saved = self.directory / 'handoff' / self.directory.name / 'state.json'
        receipt = json.loads(saved.read_text())
        require(receipt.get('phase') in ('send_pending', 'accepted', 'started'), 'No prompt delivery intent')
        terminal = receipt.get('terminal', {})
        require(terminal.get('ptyId') and terminal.get('incarnationId'), 'Missing receiver process identity')
        shown = json.loads(command([receipt['cli'], 'terminal', 'show', '--terminal', receipt['handle'], '--json']).stdout)
        live = shown.get('result', {}).get('terminal', {})
        require(shown.get('ok') is True and all(live.get(k) == terminal.get(k)
                for k in ('ptyId', 'incarnationId', 'worktreeId')), 'Receiver terminal process changed')
        path = str(evidence.root())
        require(path == str(Path(receipt['worktree']['path']).resolve()) and path != self.state['source'],
                'Acknowledgement must come from the created feature workspace')
        require(git(path, 'remote', 'get-url', 'origin') == self.state['origin'], 'Receiver origin mismatch')
        branch = git(path, 'branch', '--show-current')
        require(branch and branch != 'main', 'Receiver must be on a feature branch')
        if self.state.get('owner_session'):
            require(self.state['owner_session'] == session and self.state['workspace'] == path,
                    'Another receiver already owns this delivery')
            return
        require(self.state['stage'] == 'launch', 'Run cannot be acknowledged in this stage')
        self.state.update(owner_session=session, workspace=path, branch=branch,
                          terminal=terminal, acknowledged_at=time.time(), stage='execute')
        self.save('receiver_acknowledged')

    def recover_launch(self):
        """Repair only an unsent launch using current transport and the original pin."""
        require(not self.state.get('owner_session') and not self.state.get('attempt')
                and (self.state['stage'] == 'launch' or
                     (self.state['stage'] == 'blocked' and self.state.get('resume_stage') == 'launch')),
                'Recovery is only for a pre-acknowledgement launch')
        source = str(evidence.root())
        require(source == self.state['source'] and git(source, 'branch', '--show-current') == 'main'
                and git(source, 'remote', 'get-url', 'origin') == self.state['origin'],
                'Recover from the original main planning checkout')
        self.plan()
        home = self.directory / 'handoff'
        saved = home / self.directory.name / 'state.json'
        receipt = json.loads(saved.read_text())
        require(receipt.get('phase') == 'created' and not receipt.get('send_args')
                and not receipt.get('request_id')
                and not any(c.get('mutation') == 'send' for c in receipt.get('calls', [])),
                'Recovery requires an existing workspace with no prior send intent')
        work = str(Path(receipt['worktree']['path']).resolve())
        require(work != source and git(work, 'remote', 'get-url', 'origin') == self.state['origin']
                and git(work, 'branch', '--show-current') not in ('', 'main'),
                'Original feature workspace is unavailable or changed identity')
        script = ROOT / 'skills/orca/orca-handoff/scripts/handoff.py'
        if not script.exists():
            script = ROOT.parent / 'shared/skills/orca/orca-handoff/scripts/handoff.py'
        require(script.is_file(), 'Current recovery transport unavailable')
        # The existing worktree is already created: new main edits cannot enter it.
        # Preserve the original brief, plan, resource pin, identities and repair budget.
        self.state.setdefault('launch_recoveries', []).append({
            'at': time.time(), 'previous_blocker': self.state.get('blocker'),
            'helper': str(Path(__file__).resolve()),
            'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'transport': str(script), 'transport_sha256': hashlib.sha256(script.read_bytes()).hexdigest()})
        self.state['stage'] = 'launch'
        self.state.pop('resume_stage', None)
        self.state.pop('blocker', None)
        self.save('launch_recovery_intent')
        response = command([sys.executable, '-B', str(script), 'retry-ready', '--key', self.directory.name,
                            '--state-dir', str(home)], allowed=(0, 2), timeout=600)
        self.state['handoff_result'] = json.loads(response.stdout)
        self.save('launch_recovery_receipt')

    def begin(self):
        self.workspace()
        self.plan()
        require(self.state.get('observed_main'), 'Sync main before starting delivery workers')
        require(self.state['stage'] in ('execute', 'review'), 'Not at a worker stage')
        require(not self.state.get('attempt'),
                'Worker already pending. Reconcile its result or prove it stopped before abandon-worker; do not duplicate it')
        self.state['attempt'] = {'id': uuid.uuid4().hex, 'stage': self.state['stage'], 'session': None}
        self.save('worker_intent')

    def claim(self, attempt, session):
        self.workspace()
        current = self.state.get('attempt') or {}
        require(current.get('id') == attempt and session, 'Wrong worker attempt or missing actual session ID')
        require(self.state['stage'] == current.get('stage'), 'Delivery paused; reconcile before accepting worker results')
        require(not current.get('session') or current['session'] == session, 'Attempt already claimed')
        used = self.state.get('worker_sessions', [])
        require(session != self.state['owner_session'] and (session not in used or current.get('session') == session),
                'Each worker must be a fresh session, independent of coordinator and prior workers')
        if not current.get('session'):
            current['session'] = session
            self.state.setdefault('worker_sessions', []).append(session)
            self.save('worker_claimed')

    def finish(self, attempt, artifact):
        path = self.workspace()
        current = self.state.get('attempt') or {}
        require(current.get('id') == attempt and current.get('session'), 'Claim this exact worker before finishing')
        require(self.state['stage'] == current['stage'], 'Delivery paused; reconcile before accepting worker results')
        issue, comments = self.plan()
        kind = 'verification' if current['stage'] == 'execute' else 'review'
        selected = packet.select(comments, kind, artifact, required=True)
        meta = packet.parse(selected)
        record = meta['record']
        require(meta['source']['digest'] == evidence.snapshot(path)['digest'], 'Worker evidence is stale')
        require(record.get('plan_url') == self.state['plan'], 'Artifact belongs to another plan')
        if kind == 'verification':
            verify.readiness(evidence.repo(path), issue, comments, self.state['plan'], record['run_id'], evidence.snapshot(path))
            self.state.update(verification=artifact, verification_run=record['run_id'], stage='review')
        else:
            require(record.get('verification_run') == self.state.get('verification_run'), 'Review used a different verification')
            packet.review_record(record)
            self.state['review'] = artifact
            verdict = record['verdict']
            if verdict == 'pass':
                handoff.v2_gate(issue, comments, self.state['plan'], artifact, path)
                self.state['stage'] = 'publish'
            elif verdict == 'changes_requested':
                self.state.update(stage='needs_repair', repair_reason='review')
            else:
                self.state.update(stage='blocked', resume_stage='review', blocker='Independent review blocked: ' + artifact)
        self.state.setdefault('workers', []).append({**current, 'artifact': artifact})
        self.state.pop('attempt')
        self.save('worker_finished')

    def repair(self, reason, attributable=False):
        self.workspace()
        self.plan()
        require(self.state['stage'] == 'needs_repair', 'No recorded failure to repair')
        require(reason and reason.strip(), 'Record findings or CI attribution evidence before repair')
        require(self.state.get('repair_reason') not in ('ci', 'integration') or attributable,
                'CI/integration repair requires explicit attribution to this change; otherwise record a blocker')
        if self.state['repairs'] >= 3:
            self.state.update(stage='blocked', resume_stage='needs_repair', blocker='Three repair cycles exhausted')
            self.save('repair_limit')
            raise RuntimeError('Three repair cycles exhausted; report findings to the user')
        self.state['repairs'] += 1
        self.state.update(stage='execute', repair_evidence=reason)
        self.save('repair_authorized')

    def integration_failure(self, attempt, artifact):
        path = self.workspace()
        current = self.state.get('attempt') or {}
        require(self.state['stage'] == 'execute' and self.state.get('integration')
                and current.get('id') == attempt and current.get('session'), 'No claimed integration worker')
        issue, comments = self.plan()
        meta = packet.parse(packet.select(comments, 'verification', artifact, required=True))
        require(meta['source']['digest'] == evidence.snapshot(path)['digest'], 'Failure evidence is stale')
        record = meta['record']
        run = verify.load_run(evidence.repo(path), record['run_id'])
        require(record['plan_url'] == self.state['plan'] and run['issue'] == self.state['issue']
                and run['plan_url'] == self.state['plan'], 'Integration failure belongs to a different plan')
        require(run['source']['digest'] == meta['source']['digest'], 'Integration run source differs')
        require(any(c['status'] != 'pass' for c in run['checks']), 'No failed integration check recorded')
        self.state.setdefault('workers', []).append({**current, 'artifact': artifact})
        self.state.pop('attempt')
        self.state.update(stage='needs_repair', repair_reason='integration', integration_failure=artifact)
        self.save('integration_failed')

    def sync(self):
        path = self.workspace()
        require(not self.state.get('attempt'), 'Do not sync while a worker is active')
        require(self.state['stage'] in ('execute', 'publish', 'publishing', 'ci', 'sync_pending'), 'Cannot sync in this stage')
        require(not git(path, 'status', '--porcelain'), 'Commit reviewed changes before integrating main')
        git(path, 'fetch', '--no-tags', 'origin', 'refs/heads/main:refs/remotes/origin/main')
        target = git(path, 'rev-parse', 'origin/main')
        require(command(['git', 'merge-base', '--is-ancestor', self.state['source_head'], target], path, allowed=(0, 1)).returncode == 0,
                'Prepared main revision is not in origin/main; publish/reconcile source context before delivery')
        included = command(['git', 'merge-base', '--is-ancestor', target, 'HEAD'], path, allowed=(0, 1)).returncode == 0
        if not included:
            initial = self.state['stage'] == 'execute' and not self.state.get('verification')
            self.state.update(stage='sync_pending', sync_target=target, sync_initial=initial)
            self.save('merge_intent')
            git(path, 'merge', '--no-edit', target)
            self.state['stage'] = 'execute'
            self.state['integration'] = target
            self.save('merged_main_requires_verification')
        elif self.state['stage'] == 'sync_pending':
            self.state.update(stage='execute', integration=target)
            self.save('merge_reconciled')
        self.state['observed_main'] = target
        self.save()

    def commit(self, message, paths):
        path = self.workspace()
        require(self.state['stage'] == 'publish', 'Passing review required before commit')
        self.gate()
        if not git(path, 'status', '--porcelain'):
            self.state.pop('commit_pending', None)
            self.save('commit_reconciled')
            return
        require(message and paths, 'Supply generated commit message and explicitly reviewed file paths')
        require(all(not Path(p).is_absolute() and '..' not in Path(p).parts and p != '.' for p in paths),
                'Stage explicit repository-relative files, not the whole checkout')
        self.state['commit_pending'] = {'head': git(path, 'rev-parse', 'HEAD'), 'message': message, 'paths': paths}
        self.save('commit_intent')
        git(path, 'add', '--', *(':(literal)' + p for p in paths))
        self.gate()
        git(path, 'commit', '-m', message)
        require(not git(path, 'status', '--porcelain'), 'Uncommitted work remains; reconcile before publication')
        self.state.pop('commit_pending')
        self.save('committed')

    def gh(self, *args):
        return json.loads(command(['gh', *args], self.workspace()).stdout)

    def view_pr(self):
        return self.gh('pr', 'view', self.state['pr'], '--repo', self.state['github_repo'], '--json',
                       'url,state,isDraft,headRefOid,headRefName,baseRefName,isCrossRepository')

    def check_pr(self, pr):
        path = self.workspace()
        require(pr['state'] == 'OPEN' and not pr['isDraft'] and not pr['isCrossRepository'], 'PR is not an open, ready same-repository PR')
        require(pr['headRefName'] == self.state['branch'] and pr['baseRefName'] == 'main', 'PR branch mismatch')
        require(pr['headRefOid'] == git(path, 'rev-parse', 'HEAD'), 'PR head differs from local reviewed commit')

    def publish(self, title, body_file):
        path = self.workspace()
        require(self.state['stage'] in ('publish', 'publishing'), 'Passing review required before publication')
        self.gate()
        require(not git(path, 'status', '--porcelain'), 'Commit reviewed work first')
        self.sync_for_publication()
        repo = self.gh('repo', 'view', '--json', 'nameWithOwner')['nameWithOwner']
        require(repo == self.state['github_repo'], 'GitHub repository changed')
        self.state['stage'] = 'publishing'
        self.save('push_intent')
        git(path, 'push', '-u', 'origin', 'HEAD:refs/heads/' + self.state['branch'])
        prs = self.gh('pr', 'list', '--repo', repo, '--head', self.state['branch'], '--state', 'all',
                      '--json', 'url,state,headRefName,baseRefName', '--limit', '100')
        require(len(prs) <= 1, 'Ambiguous PR history; reconcile before publication')
        if prs:
            require(prs[0]['state'] == 'OPEN' and prs[0]['baseRefName'] == 'main', 'Existing PR is closed or targets another base')
            self.state['pr'] = prs[0]['url']
        else:
            require(not self.state.get('pr_create_pending'),
                    'Prior PR creation outcome unknown; inspect GitHub, do not create another PR automatically')
            require(title and body_file, 'Supply reviewed PR title and body file')
            self.state['pr_create_pending'] = True
            self.save('pr_create_intent')
            url = command(['gh', 'pr', 'create', '--repo', repo, '--base', 'main', '--head', self.state['branch'],
                           '--title', title, '--body-file', str(body_file)], path).stdout.strip()
            require(re.fullmatch(r'https://github\.com/' + re.escape(repo) + r'/pull/\d+', url),
                    'Unexpected PR response; reconcile on resume')
            self.state['pr'] = url
        self.check_pr(self.view_pr())
        self.state.update(stage='ci', published_head=git(path, 'rev-parse', 'HEAD'))
        self.save('pr_published')

    def sync_for_publication(self):
        path = self.workspace()
        git(path, 'fetch', '--no-tags', 'origin', 'refs/heads/main:refs/remotes/origin/main')
        require(command(['git', 'merge-base', '--is-ancestor', 'origin/main', 'HEAD'], path, allowed=(0, 1)).returncode == 0,
                'main advanced; use sync, then fresh verification and independent review before publishing')

    def required_contexts(self):
        repo = self.state['github_repo']
        rules = self.gh('api', f'repos/{repo}/rules/branches/main')
        branch = self.gh('api', f'repos/{repo}/branches/main')
        require(isinstance(rules, list), 'Required-check rules unavailable')
        require(type(branch.get('protected')) is bool, 'Branch protection metadata unavailable')
        require(not any(r.get('type') in ('workflows', 'required_workflows') for r in rules),
                'Required-workflow rules need repository-specific CI verification')
        contexts = {c['context'] for r in rules if r.get('type') == 'required_status_checks'
                    for c in r['parameters']['required_status_checks']}
        # protected includes rulesets. A 404 is only accepted when rulesets establish protection.
        if branch.get('protected'):
            result = command(['gh', 'api', f'repos/{repo}/branches/main/protection'], self.workspace(), allowed=(0, 1))
            if result.returncode == 0:
                classic = json.loads(result.stdout).get('required_status_checks') or {}
                contexts.update(classic.get('contexts', []))
                contexts.update(c['context'] for c in classic.get('checks', []))
            else:
                require('(HTTP 404)' in result.stderr and bool(rules), 'Classic required-check policy unavailable')
        return contexts

    def ci(self):
        path = self.workspace()
        require(self.state['stage'] == 'ci', 'PR publication required before CI observation')
        self.gate()
        require(not git(path, 'status', '--porcelain'), 'CI cannot cover uncommitted changes')
        pr = self.view_pr()
        self.check_pr(pr)
        expected = self.required_contexts()
        result = command(['gh', 'pr', 'checks', self.state['pr'], '--repo', self.state['github_repo'],
                          '--required', '--json', 'name,state,bucket,link'], path, allowed=(0, 1, 8))
        try:
            checks = json.loads(result.stdout)
        except ValueError:
            # An explicit empty policy plus gh's no-required-checks result is not a missing CI response.
            require(not expected and 'no required checks reported' in (result.stdout + result.stderr).lower(),
                    'Required check observation unavailable')
            checks = []
        require(isinstance(checks, list), 'Malformed check response')
        self.check_pr(self.view_pr())  # Reject a head change during observation.
        names = {c['name'] for c in checks}
        missing = sorted(expected - names)
        failed = [c for c in checks if c['bucket'] in ('fail', 'cancel')]
        waiting = missing or [c for c in checks if c['bucket'] != 'pass' and c not in failed]
        self.state['ci'] = {'head': pr['headRefOid'], 'expected': sorted(expected), 'checks': checks,
                            'missing': missing, 'observed_at': time.time()}
        if failed:
            self.state.update(stage='needs_repair', repair_reason='ci')
        elif not waiting:
            self.sync_for_publication()
            self.check_pr(self.view_pr())
            self.gate()
            self.state.update(stage='complete', completed_at=time.time(),
                              observed_main=git(path, 'rev-parse', 'origin/main'))
        self.save('ci_observed')


def initialize(directory, args):
    require(args.authorize_through_pr and args.issue and args.plan, 'Exact issue/plan and explicit through-PR authorization required')
    require(not os.environ.get('ORCA_ENVIRONMENT') and not os.environ.get('ORCA_PAIRING_CODE'),
            'Delivery acknowledgement currently requires a local Orca workspace and shared local journal')
    path = str(evidence.root())
    require(git(path, 'branch', '--show-current') == 'main', 'Prepare and authorize from main')
    require(not git(path, 'status', '--porcelain'), 'Commit or resolve planning-checkout changes before delivery')
    issue, comments = handoff.issue_and_comments(args.issue)
    plan, contract = verify.approved_plan(issue, comments, args.plan)
    match = re.fullmatch(r'https://github\.com/([^/]+/[^/]+)/issues/\d+', issue['url'])
    require(match, 'Use an exact GitHub issue URL')
    repo = json.loads(command(['gh', 'repo', 'view', '--json', 'nameWithOwner'], path).stdout)['nameWithOwner']
    require(repo == match[1], 'Issue repository differs from implementation repository')
    # Serialize issue ownership across different operation keys, not just one key.
    for saved in directory.parent.glob('*/state.json'):
        other = json.loads(saved.read_text())
        require(other.get('issue') != issue['url'],
                'This issue already has a delivery journal: ' + str(saved.parent) + '; resume it')
    state = {'version': 1, 'stage': 'launch', 'source': path, 'source_head': git(path, 'rev-parse', 'HEAD'),
             'origin': git(path, 'remote', 'get-url', 'origin'), 'github_repo': repo, 'issue': issue['url'],
             'plan': args.plan, 'plan_digest': evidence.digest(plan), 'contract_revision': contract['revision'],
             'authorization': 'execute-review-repair-commit-push-pr-ci-sync-main', 'repairs': 0,
             'resource_root': str(ROOT), 'history': []}
    helper = Delivery(directory, state)
    helper.save('authorized_through_pr')
    return helper


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['init', 'inspect', 'dispatch', 'recover-launch', 'wait-start', 'ack', 'begin', 'claim', 'finish',
                                     'repair', 'integration-failure', 'sync', 'commit', 'publish', 'ci', 'block', 'resume', 'abandon-worker'])
    p.add_argument('--key', required=True)
    p.add_argument('--state-dir', type=Path, default=Path(os.environ.get('OPENCODE_WORKFLOW_STATE',
                   str(Path.home() / '.local/state/opencode-workflow'))) / 'deliveries')
    for name in ('issue', 'plan', 'session', 'attempt', 'artifact', 'reason', 'message', 'title'):
        p.add_argument('--' + name)
    p.add_argument('--body-file', type=Path)
    p.add_argument('--file', action='append', default=[])
    p.add_argument('--authorize-through-pr', action='store_true')
    p.add_argument('--attributable', action='store_true', help='CI failure was diagnosed as caused by this change')
    p.add_argument('--confirm-worker-stopped', action='store_true')
    p.add_argument('--timeout', type=int, default=120)
    args = p.parse_args(argv)
    try:
        valid_key(args.key)
        directory = (args.state_dir / args.key).expanduser().resolve()
        require(not any((parent / '.git').exists() for parent in (directory, *directory.parents)), 'State must be outside source repositories')
        os.umask(0o077)
        path = directory / 'state.json'
        if args.action == 'wait-start':
            require(0 < args.timeout <= 300, 'Startup timeout must be 1–300 seconds')
            deadline = time.monotonic() + args.timeout
            while True:
                state = json.loads(path.read_text())
                if state.get('acknowledged_at'):
                    print(json.dumps({'started': True, 'workspace': state['workspace'], 'stage': state['stage']}))
                    return 0
                require(time.monotonic() < deadline, 'Startup unconfirmed; inspect/resume this key, never duplicate delivery')
                time.sleep(1)
        with locked(directory, wait=args.action == 'ack'):
            if args.action == 'init':
                require(not path.exists(), 'Delivery key exists; inspect/resume it')
                with locked(directory.parent):
                    helper = initialize(directory, args)
            else:
                state = json.loads(path.read_text())
                require(state['version'] == 1, 'Unsupported delivery state')
                require(state['resource_root'] == str(ROOT) or args.action == 'recover-launch',
                        'Resume with the recorded resource revision')
                helper = Delivery(directory, state)
                action = args.action
                if action == 'dispatch': helper.dispatch()
                elif action == 'recover-launch': helper.recover_launch()
                elif action == 'ack': helper.ack(args.session)
                elif action == 'begin': helper.begin()
                elif action == 'claim': helper.claim(args.attempt, args.session)
                elif action == 'finish': helper.finish(args.attempt, args.artifact)
                elif action == 'repair': helper.repair(args.reason, args.attributable)
                elif action == 'integration-failure': helper.integration_failure(args.attempt, args.artifact)
                elif action == 'sync': helper.sync()
                elif action == 'commit': helper.commit(args.message, args.file)
                elif action == 'publish': helper.publish(args.title, args.body_file)
                elif action == 'ci': helper.ci()
                elif action == 'block':
                    require(args.reason and state['stage'] != 'complete', 'Supply blocker for an active run')
                    state.update(resume_stage=state.get('resume_stage', state['stage']), stage='blocked', blocker=args.reason)
                    helper.save('blocked')
                elif action == 'resume':
                    if state['stage'] == 'blocked':
                        helper.workspace()
                        helper.plan()
                        require(state['repairs'] < 3 or state.get('resume_stage') != 'needs_repair', 'Repair budget exhausted')
                        state['stage'] = state.pop('resume_stage')
                        state.pop('blocker', None)
                        helper.save('resumed')
                elif action == 'abandon-worker':
                    helper.workspace()
                    require(args.confirm_worker_stopped and args.reason and state.get('attempt'),
                            'Confirm the exact worker stopped and record reconciliation evidence')
                    state.setdefault('abandoned_workers', []).append({**state.pop('attempt'), 'reason': args.reason})
                    helper.save('worker_reconciled_stopped')
            print(json.dumps(helper.state, indent=2))
        return 0
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error), 'key': args.key, 'recovery': 'Inspect the same delivery key; do not create another run.'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
