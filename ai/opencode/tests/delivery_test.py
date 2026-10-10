"""Delivery protocol with real Git/runner evidence and a bounded fake GitHub transport."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TRACKING = Path(__file__).resolve().parents[1] / 'tracking'
sys.path.insert(0, str(TRACKING))
import delivery
import handoff
import packet
import verify
import workflow_state as evidence
sys.path.pop(0)


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='delivery fixture ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        env = patch.dict(os.environ, {'OPENCODE_WORKFLOW_STATE': str(self.root / 'evidence'),
            'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_AUTHOR_NAME': 'Fixture', 'GIT_COMMITTER_NAME': 'Fixture',
            'GIT_AUTHOR_EMAIL': 'fixture@example.invalid', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
            'ORCA_ENVIRONMENT': '', 'ORCA_PAIRING_CODE': ''})
        env.start(); self.addCleanup(env.stop)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.git(self.source, 'init', '-b', 'main')
        (self.source / 'value.txt').write_text('1\n')
        self.git(self.source, 'add', '.')
        self.git(self.source, 'commit', '-m', 'initial')
        self.remote = self.root / 'origin.git'
        self.git(self.root, 'init', '--bare', str(self.remote))
        self.git(self.source, 'remote', 'add', 'origin', str(self.remote))
        self.git(self.source, 'push', '-u', 'origin', 'main')
        self.work = self.root / 'feature'
        self.git(self.source, 'worktree', 'add', '-b', 'feature', str(self.work), 'main')
        old = Path.cwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, old)
        self.issue = {'url': 'https://github.com/example/repo/issues/1', 'body': 'Return two', 'title': 'Fixture', 'state': 'OPEN'}
        self.comments = []
        contract = self.record('contract', {'version': 2, 'outcome': 'Return two',
            'requirements': [{'id': 'R1', 'expected': 'Return two', 'required': True}],
            'constraints': [], 'exclusions': [], 'decisions': [], 'unresolved': [],
            'checkpoint': packet.checkpoint(self.issue, self.comments)})
        self.contract = contract['metadata']['record']
        program = ('import unittest,pathlib\nclass Check(unittest.TestCase):\n'
                   ' def test_result(self): self.assertEqual(pathlib.Path("value.txt").read_text().strip(),"2")\nunittest.main()')
        self.plan = {'version': 2, 'contract_revision': self.contract['revision'],
            'steps': ['Implement and verify'], 'unresolved': [],
            'check_manifest': {'version': 1, 'checks': [{'id': 'BEHAVIOR', 'argv': [sys.executable, '-c', program],
                'kind': 'test', 'format': 'unittest', 'required': True}]},
            'coverage': {'R1': {'checks': ['BEHAVIOR']}}}
        self.plan_url = self.record('plan', self.plan)['url']
        self.directory = self.root / 'deliveries' / 'fixture'
        self.directory.mkdir(parents=True)
        self.state = {'version': 1, 'stage': 'execute', 'workspace': str(self.work), 'source': str(self.source),
            'source_head': self.git(self.source, 'rev-parse', 'HEAD'), 'origin': str(self.remote),
            'branch': 'feature', 'github_repo': 'example/repo', 'issue': self.issue['url'],
            'plan': self.plan_url, 'plan_digest': evidence.digest(self.plan), 'contract_revision': self.contract['revision'],
            'owner_session': 'owner', 'observed_main': self.git(self.source, 'rev-parse', 'HEAD'),
            'repairs': 0, 'resource_root': str(delivery.ROOT)}
        self.run = delivery.Delivery(self.directory, self.state)
        self.run.save()
        self.pr = None
        self.creates = 0
        self.checks = [{'name': 'unit', 'bucket': 'pass', 'state': 'SUCCESS', 'link': 'https://example.invalid/check'}]
        self.expected = ['unit']
        self.gh_failure = None
        issue_patch = patch.object(handoff, 'issue_and_comments', side_effect=lambda _: (self.issue, self.comments))
        issue_patch.start(); self.addCleanup(issue_patch.stop)
        self.real_command = delivery.command
        cmd_patch = patch.object(delivery, 'command', side_effect=self.command)
        cmd_patch.start(); self.addCleanup(cmd_patch.stop)

    def git(self, cwd, *args):
        return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.PIPE).decode().strip()

    def command(self, argv, cwd=None, allowed=(0,), timeout=180):
        if argv[0] != 'gh':
            return self.real_command(argv, cwd, allowed, timeout)
        args = argv[1:]
        if self.gh_failure == 'unavailable':
            raise RuntimeError('GitHub unavailable')
        result = None
        if args[:2] == ['repo', 'view']:
            result = {'nameWithOwner': 'example/repo'}
        elif args[:2] == ['pr', 'list']:
            result = [self.pr] if self.pr else []
        elif args[:2] == ['pr', 'create']:
            self.creates += 1
            if self.gh_failure != 'lost_before_create':
                self.pr = {'url': 'https://github.com/example/repo/pull/2', 'state': 'OPEN', 'isDraft': False,
                           'headRefName': 'feature', 'baseRefName': 'main', 'isCrossRepository': False}
            if self.gh_failure in ('lost_before_create', 'lost_after_create'):
                raise RuntimeError('Ambiguous transport failure')
            return subprocess.CompletedProcess(argv, 0, self.pr['url'], '')
        elif args[:2] == ['pr', 'view']:
            result = {**self.pr, 'headRefOid': self.git(self.remote, 'rev-parse', 'refs/heads/feature')}
        elif args[:2] == ['pr', 'checks']:
            result = self.checks
        elif args[0] == 'api' and '/rules/branches/' in args[1]:
            result = [{'type': 'required_status_checks', 'parameters': {
                'required_status_checks': [{'context': name} for name in self.expected]}}] if self.expected else []
        elif args[0] == 'api' and args[1].endswith('/protection'):
            result = {'required_status_checks': {'contexts': self.expected}}
        elif args[0] == 'api' and args[1].endswith('/branches/main'):
            result = {'protected': bool(self.expected)}
        else:
            raise AssertionError(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(result), '')

    def record(self, kind, record):
        previous = packet.select(self.comments, kind)
        supersedes = [previous['html_url']] if previous else []
        url = self.issue['url'] + '#issuecomment-' + str(len(self.comments) + 1)
        with patch.object(handoff.track, 'run', return_value=url) as gh:
            result = handoff.record_v2(self.issue, self.comments, kind, record, supersedes=supersedes, cwd=self.work)
            if gh.called:
                self.comments.append({'id': len(self.comments) + 1, 'html_url': url,
                                      'updated_at': '2026-10-09', 'body': gh.call_args.args[-1]})
        return result

    def worker(self, session):
        self.run.begin()
        attempt = self.state['attempt']['id']
        self.run.claim(attempt, session)
        return attempt

    def verification(self, session='writer-1'):
        attempt = self.worker(session)
        verify.initialize(self.work, self.plan)
        run_id, _ = verify.run_checks(self.work, self.issue, self.plan_url, self.plan, self.contract)
        url = self.record('verification', {'version': 2, 'run_id': run_id})['url']
        self.run.finish(attempt, url)
        return run_id

    def review(self, verdict='pass', session='reviewer-1', findings=None):
        attempt = self.worker(session)
        previous = packet.select(self.comments, 'review')
        record = {'version': 2, 'contract_revision': self.contract['revision'], 'plan_url': self.plan_url,
                  'verification_run': self.state['verification_run'], 'verdict': verdict, 'findings': findings or []}
        if previous:
            record['previous_review'] = previous['html_url']
        url = self.record('review', record)['url']
        self.run.finish(attempt, url)
        return url

    def ready(self):
        (self.work / 'value.txt').write_text('2\n')
        self.verification()
        self.review()

    def publish(self):
        self.run.commit('Implement fixture', ['value.txt', '.opencode/workflow/checks.json'])
        body = self.root / 'pr-body.md'
        body.write_text('Implements fixture. Closes #1.')
        self.run.publish('Fixture', body)

    def test_end_to_end_review_repair_commit_pr_and_green_ci(self):
        (self.work / 'value.txt').write_text('2\n')
        self.verification()
        finding = {'id': 'F1', 'severity': 'medium', 'required': True, 'status': 'open',
                   'location': 'value.txt:1', 'expected': 'Document new value', 'observed': 'No documentation'}
        self.review('changes_requested', findings=[finding])
        self.assertEqual(self.state['stage'], 'needs_repair')
        self.run.repair('F1: document new result')
        (self.work / 'README.md').write_text('The new result is two.\n')
        self.verification('writer-2')
        finding.update(status='resolved', evidence='README.md documents result; verified in fixture')
        self.review(session='reviewer-2', findings=[finding])
        self.run.commit('Document result', ['README.md', 'value.txt', '.opencode/workflow/checks.json'])
        self.publish()
        self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertEqual(self.state['repairs'], 1)
        self.assertEqual(self.creates, 1)
        self.assertEqual(self.git(self.source, 'show', 'main:value.txt'), '1')

    def launch_recovery_fixture(self):
        self.state.update(stage='blocked', resume_stage='launch', blocker='readiness')
        for key in ('owner_session', 'workspace', 'branch', 'observed_main'):
            self.state.pop(key, None)
        directory = self.directory / 'handoff' / self.directory.name
        directory.mkdir(parents=True)
        receipt = {'phase': 'created', 'calls': [],
                   'worktree': {'path': str(self.work)}, 'brief': 'original pinned brief'}
        (directory / 'state.json').write_text(json.dumps(receipt))
        os.chdir(self.source)
        return directory, receipt

    def test_pre_ack_recovery_retains_pin_and_ignores_new_source_edits(self):
        self.launch_recovery_fixture()
        (self.source / 'value.txt').write_text('unrelated local edit\n')
        pin = self.state['resource_root']
        def transport(argv, *args, **kwargs):
            if 'retry-ready' in argv:
                return subprocess.CompletedProcess(argv, 2, '{"accepted":true,"turn_started":false}', '')
            return self.command(argv, *args, **kwargs)
        with patch.object(delivery, 'command', side_effect=transport) as call:
            self.run.recover_launch()
        retries = [x.args[0] for x in call.call_args_list if 'retry-ready' in x.args[0]]
        self.assertEqual(len(retries), 1)
        self.assertEqual(self.state['stage'], 'launch')
        self.assertEqual(self.state['resource_root'], pin)
        self.assertNotIn('owner_session', self.state)
        self.assertTrue(self.state['handoff_result']['accepted'])
        self.assertEqual((self.source / 'value.txt').read_text(), 'unrelated local edit\n')
        self.assertEqual(self.state['repairs'], 0)

    def test_pre_ack_recovery_refuses_prior_send_or_receiver(self):
        directory, receipt = self.launch_recovery_fixture()
        receipt['calls'] = [{'mutation': 'send'}]
        (directory / 'state.json').write_text(json.dumps(receipt))
        with self.assertRaisesRegex(RuntimeError, 'prior send'):
            self.run.recover_launch()
        self.state['owner_session'] = 'receiver'
        with self.assertRaisesRegex(RuntimeError, 'pre-acknowledgement'):
            self.run.recover_launch()

    def test_stale_source_cannot_finish_review_or_publish(self):
        self.ready()
        (self.work / 'value.txt').write_text('3\n')
        with self.assertRaisesRegex(RuntimeError, 'stale'):
            self.publish()
        self.assertEqual(self.creates, 0)

    def test_failed_behavior_check_does_not_advance_to_review(self):
        with self.assertRaises(RuntimeError):
            self.verification()
        self.assertEqual(self.state['stage'], 'execute')
        self.assertTrue(self.state['attempt'])

    def test_fresh_worker_and_pending_intent_enforced(self):
        self.run.begin()
        attempt = self.state['attempt']['id']
        with self.assertRaisesRegex(RuntimeError, 'pending'):
            self.run.begin()
        with self.assertRaisesRegex(RuntimeError, 'fresh'):
            self.run.claim(attempt, 'owner')
        self.run.claim(attempt, 'writer')
        self.run.claim(attempt, 'writer')
        with self.assertRaisesRegex(RuntimeError, 'claimed'):
            self.run.claim(attempt, 'different')

    def test_reviewer_cannot_reuse_execution_session(self):
        (self.work / 'value.txt').write_text('2\n')
        self.verification()
        self.run.begin()
        with self.assertRaisesRegex(RuntimeError, 'fresh'):
            self.run.claim(self.state['attempt']['id'], 'writer-1')

    def test_shared_budget_counts_review_and_ci_and_survives_reload(self):
        for reason in ('review', 'ci', 'review'):
            self.state.update(stage='needs_repair', repair_reason=reason)
            self.run.repair('Actual diagnostic evidence', attributable=True)
        saved = json.loads((self.directory / 'state.json').read_text())
        resumed = delivery.Delivery(self.directory, saved)
        saved.update(stage='needs_repair', repair_reason='ci')
        with self.assertRaisesRegex(RuntimeError, 'exhausted'):
            resumed.repair('Fourth failure', attributable=True)
        self.assertEqual(saved['repairs'], 3)
        self.assertEqual(saved['stage'], 'blocked')

    def test_unattributed_ci_cannot_consume_repair(self):
        self.state.update(stage='needs_repair', repair_reason='ci')
        with self.assertRaisesRegex(RuntimeError, 'attribution'):
            self.run.repair('CI failed')
        self.assertEqual(self.state['repairs'], 0)

    def test_main_update_requires_new_evidence_and_current_head_ci(self):
        self.ready()
        self.publish()
        (self.source / 'main-update.txt').write_text('upstream change\n')
        self.git(self.source, 'add', 'main-update.txt')
        self.git(self.source, 'commit', '-m', 'Update main')
        self.git(self.source, 'push', 'origin', 'main')
        with self.assertRaisesRegex(RuntimeError, 'main advanced'):
            self.run.ci()
        self.run.sync()
        self.assertEqual(self.state['stage'], 'execute')
        self.assertEqual(self.state['repairs'], 0)
        with self.assertRaises(RuntimeError):
            self.run.publish('stale', self.root / 'absent')
        self.verification('writer-integration')
        self.review(session='reviewer-integration')
        self.run.publish(None, None)
        self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertEqual(self.state['observed_main'], self.git(self.source, 'rev-parse', 'main'))
        self.assertEqual(self.creates, 1)

    def test_ci_missing_pending_skipped_failed_and_green(self):
        self.ready(); self.publish()
        for checks in ([], [{'name': 'unit', 'bucket': 'pending'}], [{'name': 'unit', 'bucket': 'skipping'}]):
            self.checks = checks
            self.run.ci()
            self.assertEqual(self.state['stage'], 'ci')
        self.checks = [{'name': 'unit', 'bucket': 'fail'}]
        self.run.ci()
        self.assertEqual(self.state['stage'], 'needs_repair')
        self.assertEqual(self.state['repair_reason'], 'ci')

    def test_empty_required_policy_can_complete_but_unavailable_cannot(self):
        self.ready(); self.publish()
        self.gh_failure = 'unavailable'
        with self.assertRaises(RuntimeError):
            self.run.ci()
        self.assertEqual(self.state['stage'], 'ci')
        self.gh_failure = None
        self.expected, self.checks = [], []
        self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')

    def test_stale_remote_head_cannot_satisfy_ci(self):
        self.ready(); self.publish()
        self.git(self.work, 'commit', '--allow-empty', '-m', 'Unpushed fixture')
        with self.assertRaisesRegex(RuntimeError, 'head differs'):
            self.run.ci()
        self.assertEqual(self.state['stage'], 'ci')

    def test_ambiguous_pr_creation_reconciles_without_duplicate(self):
        self.ready()
        self.gh_failure = 'lost_after_create'
        with self.assertRaisesRegex(RuntimeError, 'Ambiguous'):
            self.publish()
        self.gh_failure = None
        self.run.publish(None, None)
        self.assertEqual(self.creates, 1)
        self.assertEqual(self.state['stage'], 'ci')

    def test_unresolved_pr_creation_is_not_repeated(self):
        self.ready()
        self.gh_failure = 'lost_before_create'
        with self.assertRaisesRegex(RuntimeError, 'Ambiguous'):
            self.publish()
        self.gh_failure = None
        with self.assertRaisesRegex(RuntimeError, 'outcome unknown'):
            self.run.publish(None, None)
        self.assertEqual(self.creates, 1)

    def test_commit_resume_does_not_create_duplicate(self):
        self.ready()
        self.run.commit('Feature', ['value.txt', '.opencode/workflow/checks.json'])
        head = self.git(self.work, 'rev-parse', 'HEAD')
        self.run.commit('Feature again', [])
        self.assertEqual(self.git(self.work, 'rev-parse', 'HEAD'), head)

    def test_contract_change_blocks_run(self):
        self.issue['body'] += ' Changed requirement'
        with self.assertRaises(RuntimeError):
            self.run.begin()

    def test_wrong_workspace_cannot_continue(self):
        os.chdir(self.source)
        with self.assertRaisesRegex(RuntimeError, 'bound feature'):
            self.run.begin()

    def test_init_requires_authorization_and_rejects_duplicate_issue(self):
        os.chdir(self.source)
        args = argparse.Namespace(authorize_through_pr=False, issue=self.issue['url'], plan=self.plan_url)
        other = self.directory.parent / 'different-key'
        other.mkdir()
        with self.assertRaisesRegex(RuntimeError, 'authorization'):
            delivery.initialize(other, args)
        args.authorize_through_pr = True
        with self.assertRaisesRegex(RuntimeError, 'already has'):
            delivery.initialize(other, args)

    def test_ack_checks_exact_workspace_and_process_and_is_idempotent(self):
        self.state.update(stage='launch')
        self.state.pop('owner_session')
        saved = self.directory / 'handoff' / self.directory.name
        saved.mkdir(parents=True)
        terminal = {'ptyId': 'pty', 'incarnationId': 'incarnation', 'worktreeId': 'repo::' + str(self.work)}
        receipt = {'phase': 'accepted', 'cli': '/fake/orca', 'handle': 'term-1', 'terminal': terminal,
                   'worktree': {'path': str(self.work)}}
        (saved / 'state.json').write_text(json.dumps(receipt))
        response = subprocess.CompletedProcess([], 0, json.dumps({'ok': True, 'result': {'terminal': terminal}}), '')
        with patch.object(delivery, 'command', side_effect=lambda argv, *a, **kw:
                          response if argv[0] == '/fake/orca' else self.command(argv, *a, **kw)):
            self.run.ack('actual-owner')
            self.run.ack('actual-owner')
            self.assertEqual(self.state['stage'], 'execute')
            with self.assertRaisesRegex(RuntimeError, 'already owns'):
                self.run.ack('different-owner')

    def test_dispatch_reuses_handoff_key_and_wait_requires_receiver_ack(self):
        os.chdir(self.source)
        self.state['stage'] = 'launch'
        self.state.pop('owner_session')
        sends = []

        def transport(argv, cwd=None, allowed=(0,), timeout=180):
            if argv[0] == sys.executable:
                sends.append(argv)
                saved = self.directory / 'handoff' / self.directory.name
                saved.mkdir(parents=True, exist_ok=True)
                (saved / 'state.json').write_text(json.dumps({'phase': 'accepted'}))
                return subprocess.CompletedProcess(argv, 2, json.dumps({'accepted': True, 'turn_started': False}), '')
            return self.command(argv, cwd, allowed, timeout)

        with patch.object(delivery, 'command', side_effect=transport):
            self.run.dispatch()
            self.run.dispatch()
        self.assertEqual([args[3] for args in sends], ['start', 'resume'])
        self.assertEqual(self.state['stage'], 'launch')
        brief = (self.directory / 'brief.txt').read_text()
        self.assertIn(str(delivery.ROOT / 'tracking/delivery.py'), brief)
        self.assertIn(self.plan_url, brief)
        args = ['wait-start', '--key', 'fixture', '--state-dir', str(self.directory.parent), '--timeout', '1']
        with patch.object(delivery.time, 'monotonic', side_effect=[0, 2]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(args), 2)
        self.state.update(acknowledged_at=123, workspace=str(self.work), stage='execute')
        self.run.save()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(args), 0)

    def test_cli_resume_and_abandon_do_not_clear_budget_or_duplicate_worker(self):
        self.state.update(stage='blocked', resume_stage='execute', blocker='Example', repairs=2)
        self.run.save()
        args = ['--key', 'fixture', '--state-dir', str(self.directory.parent)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(['resume', *args]), 0)
            self.assertEqual(delivery.main(['begin', *args]), 0)
            self.assertEqual(delivery.main(['begin', *args]), 2)
            self.assertEqual(delivery.main(['abandon-worker', *args, '--reason', 'Unproven']), 2)
            self.assertEqual(delivery.main(['abandon-worker', *args, '--confirm-worker-stopped',
                                            '--reason', 'Verified stopped session']), 0)
            self.assertEqual(delivery.main(['begin', *args]), 0)
        state = json.loads((self.directory / 'state.json').read_text())
        self.assertEqual(state['repairs'], 2)
        self.assertEqual(len(state['abandoned_workers']), 1)

    def test_init_is_persisted_and_wrong_target_or_dirty_main_blocks(self):
        os.chdir(self.source)
        (self.directory / 'state.json').unlink()
        args = argparse.Namespace(authorize_through_pr=True, issue=self.issue['url'], plan=self.plan_url)
        with patch.dict(os.environ, {'ORCA_ENVIRONMENT': 'remote'}):
            with self.assertRaisesRegex(RuntimeError, 'local Orca'):
                delivery.initialize(self.directory, args)
        (self.source / 'user-work.txt').write_text('Do not move this into a new worktree')
        with self.assertRaisesRegex(RuntimeError, 'planning-checkout'):
            delivery.initialize(self.directory, args)
        (self.source / 'user-work.txt').unlink()
        initialized = delivery.initialize(self.directory, args)
        self.assertEqual(initialized.state['stage'], 'launch')
        self.assertEqual(json.loads((self.directory / 'state.json').read_text())['repairs'], 0)

    def test_ci_repair_gets_new_review_and_updates_same_pr(self):
        self.ready(); self.publish()
        self.checks = [{'name': 'unit', 'bucket': 'fail'}]
        self.run.ci()
        self.run.repair('CI log demonstrates missing compatibility note', attributable=True)
        (self.work / 'compatibility.txt').write_text('CI correction\n')
        self.verification('writer-ci')
        self.review(session='reviewer-ci')
        self.run.commit('Fix CI compatibility', ['compatibility.txt'])
        self.run.publish(None, None)
        self.checks = [{'name': 'unit', 'bucket': 'pass'}]
        self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertEqual(self.state['repairs'], 1)
        self.assertEqual(self.creates, 1)

    def test_required_policy_and_pr_head_changes_during_ci_are_not_green(self):
        self.ready(); self.publish()
        self.expected.append('security')
        self.run.ci()
        self.assertEqual(self.state['ci']['missing'], ['security'])
        self.assertEqual(self.state['stage'], 'ci')
        original = self.run.view_pr
        views = [original(), {**original(), 'headRefOid': 'changed'}]
        with patch.object(self.run, 'view_pr', side_effect=views):
            with self.assertRaisesRegex(RuntimeError, 'head differs'):
                self.run.ci()

    def test_required_policy_unavailable_cannot_satisfy_ci(self):
        self.ready(); self.publish()
        with patch.object(self.run, 'required_contexts', side_effect=RuntimeError('Policy inaccessible')):
            with self.assertRaisesRegex(RuntimeError, 'inaccessible'):
                self.run.ci()
        self.assertEqual(self.state['stage'], 'ci')

    def test_integration_failure_consumes_budget_before_fix(self):
        self.state['integration'] = 'main-change'
        attempt = self.worker('integration-verifier')
        verify.initialize(self.work, self.plan)
        run_id, _ = verify.run_checks(self.work, self.issue, self.plan_url, self.plan, self.contract)
        url = self.record('verification', {'version': 2, 'run_id': run_id})['url']
        self.run.integration_failure(attempt, url)
        self.assertEqual(self.state['stage'], 'needs_repair')
        self.assertEqual(self.state['repairs'], 0)
        self.run.repair('Runner reproduced feature incompatibility', attributable=True)
        self.assertEqual(self.state['repairs'], 1)

    def test_recorded_lock_prevents_concurrent_writer(self):
        with delivery.locked(self.directory):
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                with delivery.locked(self.directory):
                    self.fail('Concurrent lock acquired')


if __name__ == '__main__':
    unittest.main()
