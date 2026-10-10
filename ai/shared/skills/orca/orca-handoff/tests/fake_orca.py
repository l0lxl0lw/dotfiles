"""Executable test double for the observed Orca 1.4.206 envelopes, never real Orca."""
import json
import os
from pathlib import Path
import signal
import sys
import time

root = Path(os.environ['FAKE_ORCA_ROOT'])
config = json.loads((root / 'config.json').read_text())
args = sys.argv[1:]
with (root / 'argv.jsonl').open('a') as stream:
    stream.write(json.dumps(args) + '\n')
db_path = root / 'runtime.json'
db = json.loads(db_path.read_text()) if db_path.exists() else {'creates': 0, 'deliveries': 0, 'waits': 0}
scenario = config.get('scenario', '')
worktree = {'id': 'repo-full::/work tree/new agent', 'path': '/work tree/new agent', 'branch': 'refs/heads/new-agent'}
terminal = {'handle': config.get('handle', 'term_original'), 'ptyId': 'pty-original',
            'incarnationId': config.get('incarnation', 'process-original'),
            'worktreeId': worktree['id'], 'worktreePath': worktree['path'], 'branch': worktree['branch'],
            'connected': True, 'writable': True, 'agentIdentity': 'opencode'}


def emit(result=None, error=None):
    value = {'id': 'envelope-id-NOT-durable', 'ok': error is None}
    value['error' if error else 'result'] = error or result
    print(json.dumps(value), flush=True)


def save():
    db_path.write_text(json.dumps(db))


def crash_parent():
    os.kill(os.getppid(), signal.SIGKILL)


if '--help' in args:
    print('--agent --repo --no-parent --setup --retry-request --wait-submit')
elif args[:2] == ['skills', 'get']:
    print('Installed guide: tui-idle --retry-request --wait-submit')
elif args[0] == 'status':
    emit({'runtime': {'reachable': True, 'state': 'ready', 'appVersion': '1.4.206',
                      'capabilities': [] if scenario == 'old_host' else ['terminal.prompt-delivery.v1']}})
elif args[:2] == ['worktree', 'create']:
    db['creates'] += 1
    save()
    if scenario == 'create_timeout':
        time.sleep(5)
    elif scenario == 'create_malformed':
        print('{"ok":true,"result":', flush=True)
    elif scenario == 'create_partial':
        print(json.dumps({'ok': False, 'result': {'worktree': worktree},
                          'error': {'code': 'runtime_timeout'}}), flush=True)
    else:
        result = {'worktree': worktree}
        if scenario != 'no_handle':
            result['startupTerminal' if scenario == 'legacy_handle' else 'agentTerminalHandle'] = (
                {'handle': 'term_original'} if scenario == 'legacy_handle' else 'term_original')
        if scenario == 'conflicting_handles':
            result['startupTerminal'] = {'handle': 'term_other'}
        emit(result)
        if scenario == 'crash_after_create':
            crash_parent()
elif args[:2] == ['worktree', 'show']:
    emit({'worktree': worktree})
elif args[:2] == ['terminal', 'list']:
    listed = {k: v for k, v in terminal.items() if k != 'incarnationId'}
    terminals = [listed]
    if scenario == 'multiple_agents':
        terminals.append(dict(listed, handle='term_second', ptyId='pty-second'))
    emit({'terminals': terminals, 'truncated': scenario == 'truncated'})
elif args[:2] == ['terminal', 'show']:
    if scenario == 'background_renderer' and not db.get('revealed'):
        terminal['paneRuntimeId'] = -1
    if scenario == 'startup_race' and db['waits'] == 0:
        terminal['paneRuntimeId'] = -1
    if scenario == 'replaced_after_wait' and db['waits']:
        terminal['incarnationId'] = 'replacement-process'
    emit({'terminal': terminal})
elif args[:2] == ['terminal', 'switch']:
    db['revealed'] = True
    save()
    emit({'terminal': terminal})
elif args[:2] == ['terminal', 'read']:
    tail = ['Ask anything… "Fix broken tests"', 'Build auto', 'tab agents  ctrl+p commands']
    if scenario == 'startup_race' and db['waits'] == 0:
        tail = []
    if scenario == 'startup_race' and db['waits']:
        reads = db.get('startup_reads', 0)
        db['startup_reads'] = reads + 1
        save()
        if reads == 0:
            tail = []
    emit({'terminal': {'tail': tail, 'source': 'screen', 'handle': terminal['handle']}})
elif args[:2] == ['terminal', 'wait']:
    db['waits'] += 1
    save()
    if scenario == 'wait_error':
        emit(error={'code': 'terminal_handle_stale'})
        sys.exit(1)
    satisfied = scenario != 'not_ready' and (scenario != 'retry_ready' or db['waits'] > 1)
    emit({'wait': {'satisfied': satisfied}})
    if not satisfied:
        sys.exit(1)
elif args[:2] == ['terminal', 'send']:
    replay = '--retry-request' in args
    payload = args[args.index('--text') + 1]
    if replay:
        assert args[args.index('--retry-request') + 1] == 'durable-request-1'
        assert payload == db['payload']
        assert args[args.index('--terminal') + 1] == db['handle']
    else:
        db['deliveries'] += 1
        db['payload'] = payload
        db['handle'] = args[args.index('--terminal') + 1]
        save()
    if scenario == 'send_timeout':
        time.sleep(5)
    elif scenario == 'send_malformed':
        print('{"ok":true', flush=True)
    elif scenario in ('send_ambiguous', 'send_no_id') and not replay:
        emit(error={'code': 'runtime_timeout', 'data': (
            {'orchestrationRequestId': 'durable-request-1'} if scenario == 'send_ambiguous' else {})})
        sys.exit(1)
    else:
        stages = ['input_accepted'] + ([] if scenario in ('accepted_only', 'unsupported') else ['turn_started'])
        emit({'send': {'accepted': True, 'handle': terminal['handle'],
                       'prompt': {'requestId': 'durable-request-1', 'stages': stages,
                                   'provider': 'unsupported' if scenario == 'unsupported' else 'opencode',
                                   'observation': 'unsupported' if scenario == 'unsupported' else 'observed'}},
              'warnings': ['fixture warning'] if scenario == 'accepted_only' else []})
        if scenario == 'crash_after_send':
            crash_parent()
else:
    raise AssertionError(f'Unexpected CLI action: {args}')
