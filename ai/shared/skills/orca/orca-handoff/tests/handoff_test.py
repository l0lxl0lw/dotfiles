import contextlib
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/handoff.py'
spec = importlib.util.spec_from_file_location('orca_handoff', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class HandoffTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='orca handoff test ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fake = self.root / 'fake orca'
        self.fake.write_text(f'#!{sys.executable}\n' + (ROOT / 'tests/fake_orca.py').read_text())
        self.fake.chmod(0o700)
        self.brief = self.root / 'task brief.txt'
        self.text = 'Implement "quoted task"; $(touch NEVER)\nDo not commit. Café 🚀'
        self.brief.write_text(self.text)
        self.env = dict(os.environ, ORCA_CLI_COMMAND=str(self.fake), FAKE_ORCA_ROOT=str(self.root))
        self.configure()

    def configure(self, **kwargs):
        (self.root / 'config.json').write_text(json.dumps(kwargs))

    def argv(self, action='start', extra=()):
        args = [action, '--key', 'one-task', '--state-dir', str(self.root / 'state')]
        if action == 'start':
            args += ['--brief-file', str(self.brief)]
            if '--terminal' not in extra:
                args += ['--repo', 'path:/repo with spaces', '--name', 'task name']
        return args + list(extra)

    def run_helper(self, action='start', extra=(), expected=0):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), *self.argv(action, extra)],
                                env=self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else None

    def state(self):
        return json.loads((self.root / 'state/one-task/state.json').read_text())

    def runtime(self):
        return json.loads((self.root / 'runtime.json').read_text())

    def calls(self, kind=None):
        path = self.root / 'argv.jsonl'
        calls = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        calls = [c for c in calls if '--help' not in c]
        return [c for c in calls if c[:2] == kind] if kind else calls

    def test_happy_path_literal_argv_and_identities(self):
        result = self.run_helper()
        self.assertTrue(result['accepted'])
        self.assertTrue(result['turn_started'])
        self.assertEqual(result['request_id'], 'durable-request-1')
        self.assertEqual(result['workspace']['id'], 'repo-full::/work tree/new agent')
        self.assertEqual(result['workspace']['branch'], 'refs/heads/new-agent')
        create = self.calls(['worktree', 'create'])[0]
        self.assertIn('--no-parent', create)
        self.assertEqual(create[create.index('--agent') + 1], 'opencode')
        for forbidden in ('--prompt', '--setup', '--base-branch', '--model'):
            self.assertNotIn(forbidden, create)
        send = self.calls(['terminal', 'send'])[0]
        self.assertEqual(send[send.index('--text') + 1], self.text)
        self.assertEqual(send[-4:], ['--enter', '--wait-submit', '10', '--json'])
        self.assertFalse(any(c[0] == 'orchestration' for c in self.calls()))
        self.assertFalse(self.calls(['terminal', 'create']))
        self.assertEqual(self.runtime()['deliveries'], 1)
        self.assertEqual((self.root / 'state/one-task/state.json').stat().st_mode & 0o777, 0o600)

    def test_accepted_not_started_is_blocked_and_resume_observes_same_request(self):
        self.configure(scenario='accepted_only')
        result = self.run_helper(expected=2)
        self.assertTrue(result['accepted'])
        self.assertFalse(result['turn_started'])
        self.assertIn('fixture warning', result['warnings'])
        self.run_helper('resume', expected=2)
        sends = self.calls(['terminal', 'send'])
        self.assertEqual(sends[1], sends[0] + ['--retry-request', 'durable-request-1'])
        self.assertEqual(self.runtime()['deliveries'], 1)
        before = self.calls()
        self.run_helper('inspect')
        self.assertEqual(self.calls(), before)

    def test_accepted_receipt_can_later_confirm_start(self):
        self.configure(scenario='accepted_only')
        self.run_helper(expected=2)
        self.configure()
        self.assertEqual(self.run_helper('resume')['phase'], 'started')
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_legacy_accepted_started_state_never_resends(self):
        self.run_helper()
        state = self.state()
        state['phase'] = 'accepted'
        (self.root / 'state/one-task/state.json').write_text(json.dumps(state))
        self.assertEqual(self.run_helper('resume')['phase'], 'started')
        self.assertEqual(len(self.calls(['terminal', 'send'])), 1)

    def test_unsupported_provider_never_reports_success(self):
        self.configure(scenario='unsupported')
        result = self.run_helper(expected=2)
        self.assertTrue(result['accepted'])
        self.assertFalse(result['turn_started'])
        self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_false_idle_waits_for_rendered_prompt(self):
        self.configure(scenario='startup_race')
        self.run_helper()
        self.assertGreaterEqual(self.runtime()['startup_reads'], 2)
        self.assertEqual(self.runtime()['deliveries'], 1)
        commands = [c[:2] for c in self.calls()]
        self.assertEqual(commands[-2:], [['terminal', 'read'], ['terminal', 'send']])

    def test_replacement_during_wait_blocks_send(self):
        self.configure(scenario='replaced_after_wait')
        self.run_helper(expected=2)
        self.assertEqual(self.runtime()['deliveries'], 0)

    def test_ready_requires_opencode_prompt_not_merely_output(self):
        handoff = helper.Handoff(self.root, {'agent': 'opencode', 'terminal': {},
                                           'terminal_read': {'terminal': {'source': 'screen', 'tail': ['Starting OpenCode']}}})
        self.assertFalse(handoff.input_ready())
        handoff.state['terminal_read']['terminal']['tail'] = [
            'Ask anything…', 'tab agents  ctrl+p commands']
        self.assertTrue(handoff.input_ready())
        handoff.state['terminal_read']['terminal']['source'] = 'stream'
        self.assertFalse(handoff.input_ready())
        handoff.state['terminal_read']['terminal']['source'] = 'screen'
        handoff.state['terminal']['paneRuntimeId'] = -1
        self.assertFalse(handoff.input_ready())

    def test_explicit_recovery_retains_receipt_and_reuses_workspace(self):
        self.configure(scenario='unsupported')
        self.run_helper(expected=2)
        self.run_helper('recover', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 1)
        self.configure()
        self.run_helper('recover', extra=['--confirm-undelivered'])
        self.assertEqual(self.runtime()['creates'], 1)
        self.assertEqual(self.runtime()['deliveries'], 2)
        self.assertEqual(self.state()['recovery_history'][0]['request_id'], 'durable-request-1')
        self.run_helper('resume')
        self.assertEqual(self.runtime()['deliveries'], 2)

    def test_recovery_refuses_replaced_process(self):
        self.configure(scenario='unsupported')
        self.run_helper(expected=2)
        self.configure(incarnation='replaced')
        self.run_helper('recover', extra=['--confirm-undelivered'], expected=2)
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_crash_during_explicit_recovery_consumes_saved_receipt(self):
        self.configure(scenario='unsupported')
        self.run_helper(expected=2)
        self.configure(scenario='crash_after_send')
        self.run_helper('recover', extra=['--confirm-undelivered'], expected=-9)
        self.configure()
        self.assertEqual(self.run_helper('resume')['phase'], 'started')
        self.assertEqual(self.runtime()['deliveries'], 2)
        self.assertEqual(len(self.state()['recovery_history']), 1)

    def test_readiness_exhaustion_despite_satisfied_wait_never_sends(self):
        with patch.dict(os.environ, self.env, clear=True), \
                patch.object(helper.Handoff, 'input_ready', return_value=False), \
                patch.object(helper.time, 'monotonic', side_effect=[0, 61, 62, 183]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(helper.main(self.argv()), 2)
        self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 0)

    def test_existing_terminal_inspected_before_send(self):
        self.run_helper(extra=['--terminal', 'term_original'])
        self.assertFalse(self.calls(['worktree', 'create']))
        commands = [c[:2] for c in self.calls()]
        self.assertLess(commands.index(['terminal', 'read']), commands.index(['terminal', 'send']))

    def test_explicit_setup_override(self):
        self.run_helper(extra=['--setup', 'skip'])
        create = self.calls(['worktree', 'create'])[0]
        self.assertEqual(create[create.index('--setup') + 1], 'skip')

    def test_legacy_create_handle(self):
        self.configure(scenario='legacy_handle')
        self.assertEqual(self.run_helper()['agent_handle'], 'term_original')

    def test_missing_handle_uses_single_agent_inventory(self):
        self.configure(scenario='no_handle')
        self.assertEqual(self.run_helper()['agent_handle'], 'term_original')

    def test_conflicting_handles_block_delivery(self):
        self.configure(scenario='conflicting_handles')
        self.run_helper(expected=2)
        self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime()['creates'], 1)
        self.assertEqual(self.runtime()['deliveries'], 0)

    def test_bounded_readiness_retry(self):
        self.configure(scenario='retry_ready')
        self.run_helper()
        waits = self.calls(['terminal', 'wait'])
        self.assertEqual([a[a.index('--timeout-ms') + 1] for a in waits], ['60000', '120000'])

    def test_explicit_pre_send_retry_reuses_original_workspace(self):
        self.configure(scenario='not_ready')
        self.run_helper(expected=2)
        self.configure()
        result = self.run_helper('retry-ready')
        self.assertTrue(result['turn_started'])
        self.assertEqual(self.runtime()['creates'], 1)
        self.assertEqual(self.runtime()['deliveries'], 1)
        self.assertEqual(self.state()['readiness_retries'][0]['waits'], 2)
        self.run_helper('retry-ready', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_pre_send_retry_refuses_prior_send_and_replaced_process(self):
        self.configure(scenario='not_ready')
        self.run_helper(expected=2)
        self.configure(incarnation='different-process')
        self.run_helper('retry-ready', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 0)
        self.configure()
        state = self.state()
        state['calls'].append({'mutation': 'send'})
        (self.root / 'state/one-task/state.json').write_text(json.dumps(state))
        self.run_helper('retry-ready', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 0)

    def test_background_renderer_is_revealed_before_wait_and_send(self):
        self.configure(scenario='background_renderer')
        result = self.run_helper()
        self.assertTrue(result['turn_started'])
        commands = [c[:2] for c in self.calls()]
        self.assertLess(commands.index(['terminal', 'switch']), commands.index(['terminal', 'wait']))
        self.assertEqual(self.runtime()['creates'], 1)
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_unsatisfied_waits_never_send_even_after_resume(self):
        self.configure(scenario='not_ready')
        self.run_helper(expected=2)
        self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime(), {'creates': 1, 'deliveries': 0, 'waits': 2})

    def test_ambiguous_send_keyed_replay_no_second_delivery(self):
        self.configure(scenario='send_ambiguous')
        result = self.run_helper(expected=2)
        self.assertEqual(result['request_id'], 'durable-request-1')
        self.run_helper('resume')
        sends = self.calls(['terminal', 'send'])
        self.assertEqual(sends[1], sends[0] + ['--retry-request', 'durable-request-1'])
        self.assertEqual(self.runtime()['deliveries'], 1)
        self.run_helper('resume')
        self.assertEqual(len(self.calls(['terminal', 'send'])), 2)

    def test_ambiguous_send_without_id_never_replays(self):
        self.configure(scenario='send_no_id')
        self.run_helper(expected=2)
        self.run_helper('resume', expected=2)
        self.assertEqual(len(self.calls(['terminal', 'send'])), 1)
        self.assertIsNone(self.run_helper('inspect')['request_id'])

    def test_malformed_send_never_replays(self):
        self.configure(scenario='send_malformed')
        self.run_helper(expected=2)
        self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_partial_creation_retains_identifiers_and_adopts(self):
        self.configure(scenario='create_partial')
        result = self.run_helper(expected=2)
        self.assertEqual(result['workspace']['id'], 'repo-full::/work tree/new agent')
        self.run_helper('resume', expected=2)
        self.configure()
        self.run_helper('adopt', ['--worktree-id', result['workspace']['id']])
        self.assertFalse(self.calls(['terminal', 'send']))
        self.run_helper('resume')
        self.assertEqual(self.runtime()['creates'], 1)

    def test_malformed_creation_never_creates_again(self):
        self.configure(scenario='create_malformed')
        self.run_helper(expected=2)
        self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime()['creates'], 1)

    def test_crash_after_creation_recovers_raw_receipt(self):
        self.configure(scenario='crash_after_create')
        self.run_helper(expected=-9)
        self.configure()
        self.run_helper('resume')
        self.assertEqual(self.runtime()['creates'], 1)
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_crash_after_send_recovers_without_resend(self):
        self.configure(scenario='crash_after_send')
        self.run_helper(expected=-9)
        self.configure()
        self.assertTrue(self.run_helper('resume')['accepted'])
        self.assertEqual(self.runtime()['deliveries'], 1)

    def timeout_start(self, mutation):
        self.configure(scenario=mutation + '_timeout')
        original = subprocess.run

        def bounded(argv, **kwargs):
            if argv[1:3] == (['worktree', 'create'] if mutation == 'create' else ['terminal', 'send']):
                kwargs['timeout'] = 0.15
            return original(argv, **kwargs)

        # Keep the real subprocess and fake executable; shorten only the test deadline.
        with patch.dict(os.environ, self.env, clear=True), patch.object(helper.subprocess, 'run', side_effect=bounded):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(helper.main(self.argv()), 2)
        self.run_helper('resume', expected=2)

    def test_real_subprocess_create_timeout_no_duplicate(self):
        self.timeout_start('create')
        self.assertEqual(self.runtime()['creates'], 1)
        self.assertEqual(self.runtime()['deliveries'], 0)

    def test_real_subprocess_send_timeout_no_duplicate(self):
        self.timeout_start('send')
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_stale_handle_before_send_relisted_once(self):
        self.configure(scenario='wait_error')
        self.run_helper(expected=2)
        self.configure(handle='term_replacement')
        result = self.run_helper('resume')
        self.assertEqual(result['agent_handle'], 'term_replacement')
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_stale_handle_after_send_does_not_redirect(self):
        self.configure(scenario='send_ambiguous')
        self.run_helper(expected=2)
        self.configure(handle='term_replacement')
        self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 1)
        self.assertEqual(len(self.calls(['terminal', 'send'])), 1)

    def test_replaced_process_cannot_receive_keyed_retry(self):
        self.configure(scenario='send_ambiguous')
        self.run_helper(expected=2)
        self.configure(incarnation='different-process')
        self.run_helper('resume', expected=2)
        self.assertEqual(len(self.calls(['terminal', 'send'])), 1)

    def test_old_host_blocks_before_create(self):
        self.configure(scenario='old_host')
        self.run_helper(expected=2)
        self.assertFalse(self.calls(['worktree', 'create']))

    def test_duplicate_key_and_concurrent_resume_are_blocked(self):
        self.run_helper()
        self.run_helper(expected=2)
        with (self.root / 'state/one-task/lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.run_helper('resume', expected=2)
        self.assertEqual(self.runtime()['deliveries'], 1)

    def test_target_change_blocks_resume(self):
        self.configure(scenario='send_ambiguous')
        self.run_helper(expected=2)
        self.env['ORCA_ENVIRONMENT'] = 'different-host'
        self.run_helper('resume', expected=2)
        self.assertEqual(len(self.calls(['terminal', 'send'])), 1)

    def test_state_inside_repository_is_refused(self):
        (self.root / '.git').mkdir()
        result = self.run_helper(expected=2)
        self.assertIn('outside source repositories', result['error'])
        self.assertEqual(self.calls(), [])

    def test_executable_override_is_not_shell_code(self):
        self.env['ORCA_CLI_COMMAND'] = str(self.fake) + ' --some-flag'
        self.run_helper(expected=2)
        self.assertEqual(self.calls(), [])

    def test_truncated_inventory_blocks_send(self):
        self.configure(scenario='truncated')
        self.run_helper(expected=2)
        self.assertEqual(self.runtime()['deliveries'], 0)

    def test_ambiguous_replacement_agent_inventory_blocks_send(self):
        self.configure(scenario='multiple_agents', handle='term_replacement')
        self.run_helper(expected=2)
        self.assertEqual(self.runtime()['deliveries'], 0)

    def test_crash_after_intent_before_create_is_conservatively_blocked(self):
        original = subprocess.run

        def interrupt(argv, **kwargs):
            if argv[1:3] == ['worktree', 'create'] and '--help' not in argv:
                raise KeyboardInterrupt()
            return original(argv, **kwargs)

        with patch.dict(os.environ, self.env, clear=True), patch.object(helper.subprocess, 'run', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                helper.main(self.argv())
        self.assertEqual(self.state()['phase'], 'create_pending')
        self.run_helper('resume', expected=2)
        self.assertEqual(self.calls(['worktree', 'create']), [])

    def test_default_executable_lookup_and_override_precedence(self):
        with patch.dict(os.environ, {'ORCA_CLI_COMMAND': ''}), patch.object(helper.shutil, 'which', return_value='/bin/orca') as which:
            self.assertEqual(helper.resolve_cli(), '/bin/orca')
            which.assert_called_once_with('orca')
        with patch.dict(os.environ, {'ORCA_CLI_COMMAND': str(self.fake)}):
            self.assertEqual(helper.resolve_cli(), str(self.fake))


if __name__ == '__main__':
    unittest.main()
