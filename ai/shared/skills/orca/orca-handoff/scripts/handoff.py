#!/usr/bin/env python3
"""Conservative, journaled Orca handoff. Python 3.9+, macOS/Linux; no dependencies."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


class Blocked(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def atomic_json(path, value):
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


def envelope(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (ValueError, OSError):
        return {}


def resolve_cli():
    name = os.environ.get('ORCA_CLI_COMMAND') or 'orca'
    executable = shutil.which(name)
    require(executable, f'Orca executable unavailable: {name!r}; use one executable, not shell code.')
    # Do not resolve symlinks: Orca launchers can depend on their invocation path.
    return os.path.abspath(executable)


class Handoff:
    def __init__(self, directory, state):
        self.directory, self.state = directory, state

    def save(self):
        atomic_json(self.directory / 'state.json', self.state)

    def call(self, args, timeout=45, mutation=None, text=False):
        number = len(self.state.setdefault('calls', []))
        record = {'args': args, 'output': f'{number:03d}.stdout',
                  'error': f'{number:03d}.stderr', 'mutation': mutation}
        self.state['calls'].append(record)
        if mutation:
            self.state['phase'] = mutation + '_pending'
        self.save()  # Write-ahead intent: never repeat an unkeyed mutation after this point.
        with (self.directory / record['output']).open('wb') as out, (self.directory / record['error']).open('wb') as err:
            try:
                process = subprocess.run([self.state['cli'], *args], stdout=out, stderr=err,
                                         timeout=timeout, check=False)
                record['returncode'] = process.returncode
            except (subprocess.TimeoutExpired, OSError) as exc:
                record['transport_error'] = str(exc)
            finally:
                out.flush()
                err.flush()
                os.fsync(out.fileno())
                os.fsync(err.fileno())
        self.save()
        if mutation:
            return record
        value = envelope(self.directory / record['output'])
        # Orca 1.4.206 prints a successful envelope but exits 1 for an unsatisfied wait.
        unsatisfied_wait = (args[:2] == ['terminal', 'wait'] and value.get('ok') is True
                            and value.get('result', {}).get('wait', {}).get('satisfied') is False
                            and record.get('returncode') == 1)
        require((record.get('returncode') == 0 or unsatisfied_wait) and (text or value.get('ok') is True),
                f'CLI read failed: {args[:2]}; inspect {record["output"]} / {record["error"]}.')
        return (self.directory / record['output']).read_text() if text else value['result']

    def preflight(self):
        require(self.state['target_env'] == target_env(),
                'ORCA_ENVIRONMENT / ORCA_PAIRING_CODE changed; restore the original target before resume.')
        status = self.call(['status', '--json'])
        runtime = status.get('runtime', {})
        require(runtime.get('reachable') is True and runtime.get('state') == 'ready', 'Orca runtime is not ready.')
        require('terminal.prompt-delivery.v1' in runtime.get('capabilities', []),
                'Runtime lacks durable prompt delivery; update Orca. No legacy raw-send fallback.')
        guide = self.call(['skills', 'get', 'orca-cli'], text=True)
        create = self.call(['worktree', 'create', '--help'], text=True)
        send = self.call(['terminal', 'send', '--help'], text=True)
        require(all(flag in create for flag in ('--agent', '--repo', '--no-parent', '--setup'))
                and all(flag in send for flag in ('--retry-request', '--wait-submit'))
                and 'tui-idle' in guide, 'Installed contract is incompatible; inspect saved guide/help before proceeding.')
        self.state['runtime'] = runtime
        self.save()

    def workspace(self, worktree):
        identifier = worktree.get('id', '')
        require(isinstance(identifier, str) and '::' in identifier and all(identifier.split('::', 1)),
                'Missing complete worktree ID; reconcile creation with worktree list, then adopt explicitly.')
        self.state['worktree'] = {key: worktree.get(key) for key in ('id', 'path', 'branch')}
        self.state['worktree']['path'] = worktree.get('path') or identifier.split('::', 1)[1]
        self.save()

    def consume_create(self):
        record = next(c for c in reversed(self.state['calls']) if c['mutation'] == 'create')
        response = envelope(self.directory / record['output'])
        result = response.get('result', {})
        if isinstance(result.get('worktree'), dict):
            self.workspace(result['worktree'])
        require(self.state.get('worktree'),
                'Creation outcome unknown. Do not create again. Inspect worktree list --repo <original repo> --json; '
                'after identifying the exact workspace, use adopt --worktree-id <full ID>. Logs retain partial output.')
        require(response.get('ok') is True,
                'Partial creation returned an error. Inspect saved workspace and logs, then explicitly adopt it; never create again.')
        handles = {h for h in (result.get('agentTerminalHandle'),
                              (result.get('startupTerminal') or {}).get('handle')) if isinstance(h, str) and h}
        require(len(handles) <= 1, 'Conflicting create handles; inspect terminal list and reconcile manually.')
        self.state['handle'] = next(iter(handles), None)
        self.state['phase'] = 'created'
        self.save()

    def terminals(self):
        result = self.call(['terminal', 'list', '--worktree', 'id:' + self.state['worktree']['id'], '--json'])
        require(result.get('truncated') is False, 'Terminal list is incomplete; cannot choose an agent safely.')
        self.state['terminal_inventory'] = result
        self.save()
        return result['terminals']

    def inspect_terminal(self):
        old = self.state.get('terminal')
        handle = self.state.get('handle')
        # Listing also recovers runtime-scoped stale handles without sending to both.
        if self.state.get('worktree'):
            terminals = self.terminals()
            if old:
                # list omits incarnationId in 1.4.206; verify incarnation with show below.
                matches = [t for t in terminals if t.get('ptyId') == old.get('ptyId')]
            elif handle:
                matches = [t for t in terminals if t.get('handle') == handle]
                if not matches:
                    matches = [t for t in terminals if t.get('agentIdentity') == self.state['agent']]
            else:
                matches = [t for t in terminals if t.get('agentIdentity') == self.state['agent']]
            require(len(matches) == 1, 'Cannot identify exactly one original agent process; inspect saved terminal inventory. No send.')
            handle = matches[0]['handle']
        terminal = self.call(['terminal', 'show', '--terminal', handle, '--json'])['terminal']
        require(terminal.get('connected') is True and terminal.get('writable') is True
                and terminal.get('agentIdentity') == self.state['agent'], 'Target is not a writable selected agent.')
        require(terminal.get('ptyId') and terminal.get('incarnationId'), 'Missing terminal process identity.')
        if old:
            require(all(terminal.get(k) == old.get(k) for k in ('ptyId', 'incarnationId', 'worktreeId')),
                    'Terminal process replaced; do not replay or send a new prompt.')
        if self.state.get('worktree'):
            require(terminal.get('worktreeId') == self.state['worktree']['id'], 'Terminal belongs to a different workspace.')
        else:
            self.workspace({'id': terminal['worktreeId'], 'path': terminal.get('worktreePath'), 'branch': terminal.get('branch')})
        self.state.update(handle=handle, terminal=terminal)
        if not self.state['worktree'].get('branch'):
            self.state['worktree']['branch'] = terminal.get('branch')
        self.save()
        self.state['terminal_read'] = self.call(['terminal', 'read', '--terminal', handle, '--json'])
        self.save()

    def consume_send(self):
        record = next(c for c in reversed(self.state['calls']) if c['mutation'] == 'send')
        value = envelope(self.directory / record['output'])
        # CLI error envelopes may be on stderr, unlike successful responses.
        if not value:
            value = envelope(self.directory / record['error'])
        result = value.get('result', {})
        require(isinstance(result, dict), 'Malformed send result; inspect saved response. Never resend without durable ID.')
        send = result.get('send', {})
        require(isinstance(send, dict), 'Malformed send receipt; inspect saved response.')
        prompt = send.get('prompt') or {}
        require(isinstance(prompt, dict), 'Malformed prompt receipt; inspect saved response.')
        request_id = prompt.get('requestId') or (value.get('error', {}).get('data') or {}).get('orchestrationRequestId')
        if isinstance(request_id, str) and request_id and request_id != 'unsupported-old-host':
            previous = self.state.get('request_id')
            require(not previous or previous == request_id, 'Replay returned a different request ID; stop and inspect logs.')
            self.state['request_id'] = request_id
            self.save()
        require(isinstance(prompt.get('stages', []), list)
                and all(isinstance(stage, str) for stage in prompt.get('stages', []))
                and isinstance(result.get('warnings', []), list), 'Malformed receipt stages/warnings; use keyed recovery only.')
        require(not send or send.get('handle') == self.state['send_args'][3],
                'Receipt target differs from original send; inspect saved response.')
        self.state['receipt'] = send
        self.state['warnings'] = result.get('warnings', [])
        if value.get('ok') is True and send.get('accepted') is True:
            self.state['phase'] = 'accepted'
            if not self.state.get('request_id'):
                self.state['warnings'].append('No durable request ID returned; accepted input cannot be safely replayed.')
            if 'turn_started' not in prompt.get('stages', []):
                self.state['warnings'].append('Input accepted; turn start is unproven. Silence is not failure; do not resend.')
        self.save()

    def run(self):
        # Consume persisted raw responses first, even if killed before saving the parsed result.
        if self.state['phase'] == 'create_pending':
            self.consume_create()
        if self.state['phase'] == 'send_pending':
            self.consume_send()
        if self.state['phase'] == 'accepted':
            return
        self.preflight()
        if self.state['phase'] == 'new':
            if self.state.get('handle'):
                self.state['phase'] = 'created'
                self.save()
            else:
                args = ['worktree', 'create', '--repo', self.state['repo'], '--name', self.state['name'],
                        '--no-parent', '--agent', self.state['agent'], '--json']
                if self.state.get('setup'):
                    args += ['--setup', self.state['setup']]
                self.call(args, timeout=180, mutation='create')
                self.consume_create()
        if self.state['phase'] == 'send_pending':
            require(self.state.get('request_id'),
                    'Send outcome unknown and durable request ID unavailable. Never resend or start a new key. '
                    'Inspect saved output/errors and terminal read; seek runtime recovery using the original identifiers.')
            original = self.state['send_args']
            # Replay is bound to the exact process and payload. Never rewrite the target on replay.
            self.inspect_terminal()
            require(self.state['handle'] == original[original.index('--terminal') + 1],
                    'Handle changed after send. Replacement listed, but exact-command replay is unsafe; inspect runtime receipt manually.')
            self.call(original + ['--retry-request', self.state['request_id']], mutation='send')
            self.consume_send()
            require(self.state['phase'] == 'accepted', 'Keyed replay remains unresolved; resume later with the same key. Never send anew.')
            return
        self.inspect_terminal()
        ready = False
        while self.state.get('waits', 0) < 2:
            attempt = self.state.get('waits', 0)
            self.state['waits'] = attempt + 1
            self.save()  # Crash also consumes the bounded attempt.
            wait = self.call(['terminal', 'wait', '--terminal', self.state['handle'], '--for', 'tui-idle',
                              '--timeout-ms', str((60000, 120000)[attempt]), '--json'], timeout=(75, 135)[attempt])
            self.state['wait'] = wait
            self.save()
            if wait.get('wait', {}).get('satisfied') is True:
                ready = True
                break
        require(ready, 'Readiness not proven within two bounded waits; no prompt sent. Inspect terminal manually. Do not restart with a new key.')
        args = ['terminal', 'send', '--terminal', self.state['handle'], '--text', self.state['brief'],
                '--enter', '--wait-submit', '10', '--json']
        self.state['send_args'] = args
        self.call(args, mutation='send')
        self.consume_send()
        require(self.state['phase'] == 'accepted', 'Send not confirmed. Resume this same key for keyed recovery when an ID is known; never resend anew.')

    def summary(self):
        receipt = self.state.get('receipt', {})
        stages = (receipt.get('prompt') or {}).get('stages', [])
        inspections = []
        if self.state.get('repo'):
            inspections.append([self.state['cli'], 'worktree', 'list', '--repo', self.state['repo'], '--json'])
        if self.state.get('worktree'):
            inspections.append([self.state['cli'], 'terminal', 'list', '--worktree',
                                'id:' + self.state['worktree']['id'], '--json'])
        if self.state.get('handle'):
            inspections.append([self.state['cli'], 'terminal', 'read', '--terminal', self.state['handle'], '--json'])
        return {'key': self.directory.name, 'state_directory': str(self.directory), 'phase': self.state['phase'],
                'cli': self.state['cli'], 'repo': self.state.get('repo'), 'name': self.state.get('name'),
                'workspace': self.state.get('worktree'), 'agent_handle': self.state.get('handle'),
                'request_id': self.state.get('request_id'), 'accepted': receipt.get('accepted') is True,
                'turn_started': 'turn_started' in stages, 'receipt_stages': stages,
                'warnings': self.state.get('warnings', []), 'inspection_argv': inspections}


def target_env():
    return {key: os.environ.get(key) for key in ('ORCA_ENVIRONMENT', 'ORCA_PAIRING_CODE')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'resume', 'inspect', 'adopt'])
    parser.add_argument('--key', required=True, help='Stable unique operation key; reuse for recovery')
    parser.add_argument('--state-dir', type=Path, default=Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'orca-handoff')
    parser.add_argument('--repo')
    parser.add_argument('--name')
    parser.add_argument('--terminal')
    parser.add_argument('--agent', default='opencode')
    parser.add_argument('--setup', choices=['inherit', 'run', 'skip'])
    parser.add_argument('--brief-file', type=Path)
    parser.add_argument('--worktree-id', help='Explicit manual reconciliation of an uncertain create (adopt only)')
    args = parser.parse_args(argv)
    helper = None
    try:
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', args.key), 'Invalid operation key.')
        directory = (args.state_dir / args.key).expanduser().resolve()
        require(not any((p / '.git').exists() for p in (directory, *directory.parents)), 'State must be outside source repositories.')
        os.umask(0o077)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / 'lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Blocked('This operation is already running; do not start a second key.')
            path = directory / 'state.json'
            if args.action == 'start':
                require(not path.exists(), 'Key already exists; use resume or inspect, never start a duplicate.')
                require(args.brief_file and (bool(args.terminal) != bool(args.repo and args.name)),
                        'Supply --brief-file and either --terminal or both --repo and --name.')
                require(not args.terminal or not (args.repo or args.name or args.setup), 'Existing terminal cannot take creation options.')
                brief = args.brief_file.read_text()
                require(brief.strip() and '\x00' not in brief, 'Brief must be nonempty text without NUL.')
                state = {'version': 1, 'phase': 'new', 'cli': resolve_cli(), 'target_env': target_env(),
                         'repo': args.repo, 'name': args.name, 'handle': args.terminal,
                         'agent': args.agent, 'setup': args.setup, 'brief': brief, 'calls': []}
                atomic_json(path, state)
            else:
                require(path.exists(), 'Unknown operation key; no saved state.')
                state = json.loads(path.read_text())
                require(state.get('version') == 1, 'Unsupported state format.')
            helper = Handoff(directory, state)
            if args.action == 'adopt':
                require(state['phase'] == 'create_pending' and args.worktree_id, 'Adopt only reconciles an uncertain creation with a full ID.')
                helper.preflight()
                worktree = helper.call(['worktree', 'show', '--worktree', 'id:' + args.worktree_id, '--json'])['worktree']
                require(worktree.get('id') == args.worktree_id, 'Returned workspace does not match the explicit adoption ID.')
                helper.workspace(worktree)
                state.update(phase='created', handle=None)
                helper.save()
            elif args.action != 'inspect':
                helper.run()
            print(json.dumps(helper.summary(), indent=2))
            return 0
    except (Blocked, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = helper.summary() if helper else {}
        result.update(error=str(exc), recovery='Preserve state and logs. Inspect/resume the same --key; never retry under a new key.')
        print(json.dumps(result, indent=2))
        return 2


if __name__ == '__main__':
    sys.exit(main())
