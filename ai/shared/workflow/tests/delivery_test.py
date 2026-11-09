"""Delivery protocol with real Git/runner evidence and a bounded fake GitHub transport."""
import argparse
import contextlib
import copy
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
            self.assertNotIn('--required', args, 'Optional CI must not be hidden by an empty policy')
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
        self.run.commit('Implement fixture', ['value.txt'])
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
        self.run.commit('Document result', ['README.md', 'value.txt'])
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

    def test_optional_ci_failure_pending_skipped_and_green_under_empty_policy(self):
        self.ready(); self.publish()
        self.expected = []
        for bucket in ('pending', 'skipping'):
            self.checks = [{'name': 'repository-ci', 'bucket': bucket}]
            self.run.ci()
            self.assertEqual(self.state['stage'], 'ci')
        self.checks = [{'name': 'repository-ci', 'bucket': 'fail'}]
        self.run.ci()
        self.assertEqual(self.state['stage'], 'needs_repair')
        self.assertEqual(self.state['repairs'], 0)

    def test_ci_failure_cross_pin_cli_preserves_identity_budget_and_requires_attribution(self):
        self.ready(); self.publish()
        pin = self.root / 'old-resource'
        (pin / 'tracking').mkdir(parents=True)
        (pin / 'tracking/delivery.py').write_text('# original pinned helper\n')
        self.state.update(resource_root=str(pin), stage='blocked', resume_stage='ci',
                          blocker='Optional CI ignored', repairs=1)
        self.run.save()
        self.expected = []
        self.checks = [{'name': 'repository-ci', 'bucket': 'fail'}]
        args = ['--key', 'fixture', '--state-dir', str(self.directory.parent)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(['resume', *args]), 2)
            self.assertEqual(delivery.main(['ci-failure', *args, '--reason', 'Observed introduced compiler error']), 0)
        saved = json.loads((self.directory / 'state.json').read_text())
        self.assertEqual(saved['stage'], 'needs_repair')
        self.assertEqual(saved['repair_reason'], 'ci')
        self.assertEqual(saved['resource_root'], str(pin))
        for key in ('repairs', 'plan', 'plan_digest', 'contract_revision', 'review', 'verification', 'pr', 'published_head'):
            self.assertEqual(saved[key], self.state[key])
        self.assertEqual(saved['ci']['head'], self.state['published_head'])
        self.assertEqual(len(saved['ci_failure_recoveries']), 1)
        self.assertNotIn('blocker', saved)
        recovered = delivery.Delivery(self.directory, saved)
        with self.assertRaisesRegex(RuntimeError, 'attribution'):
            recovered.repair('Missing attribution')
        recovered.repair('Compiler log proves introduced defect', attributable=True)
        self.assertEqual(saved['repairs'], 2)

    def test_ci_failure_recovery_rejects_no_failure_active_worker_dirty_or_stale_head(self):
        self.ready(); self.publish()
        self.state.update(stage='blocked', resume_stage='ci')
        for bucket in ('pass', 'pending', 'skipping'):
            self.checks = [{'name': 'repository-ci', 'bucket': bucket}]
            with self.assertRaisesRegex(RuntimeError, 'No current-head CI failure'):
                self.run.ci_failure('Diagnosis')
        self.checks = [{'name': 'repository-ci', 'bucket': 'fail'}]
        self.state['attempt'] = {'id': 'active'}
        with self.assertRaisesRegex(RuntimeError, 'pending worker'):
            self.run.ci_failure('Diagnosis')
        self.state.pop('attempt')
        (self.work / 'unexpected.txt').write_text('local user work')
        with self.assertRaisesRegex(RuntimeError, 'uncommitted'):
            self.run.ci_failure('Diagnosis')
        (self.work / 'unexpected.txt').unlink()
        self.state['published_head'] = 'stale'
        with self.assertRaisesRegex(RuntimeError, 'Published CI head changed'):
            self.run.ci_failure('Diagnosis')
        self.assertEqual(self.state['stage'], 'blocked')
        self.assertEqual(self.state['repairs'], 0)
        self.assertNotIn('ci_failure_recoveries', self.state)

    def test_ci_failure_recovery_rejects_wrong_stage_or_head_change_during_observation(self):
        self.ready(); self.publish()
        self.state.update(stage='blocked', resume_stage='execute')
        with self.assertRaisesRegex(RuntimeError, 'CI-stage'):
            self.run.ci_failure('Diagnosis')
        self.state['resume_stage'] = 'ci'
        self.checks = [{'name': 'repository-ci', 'bucket': 'fail'}]
        original = self.run.view_pr()
        with patch.object(self.run, 'view_pr', side_effect=[original, {**original, 'headRefOid': 'changed'}]):
            with self.assertRaisesRegex(RuntimeError, 'head differs'):
                self.run.ci_failure('Diagnosis')
        self.assertEqual(self.state['stage'], 'blocked')

    def test_ci_empty_response_requires_observed_empty_policy_and_valid_gh_result(self):
        self.ready(); self.publish()
        self.expected = []
        def transport(argv, *args, **kwargs):
            if argv[:3] == ['gh', 'pr', 'checks']:
                return subprocess.CompletedProcess(argv, 1, '', 'no checks reported on branch')
            return self.command(argv, *args, **kwargs)
        with patch.object(delivery, 'command', side_effect=transport):
            self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')

    def revision_fixture(self):
        self.ready(); self.publish()
        self.state.update(stage='blocked', resume_stage='ci', blocker='Scope decision', repairs=2)
        self.old = json.loads(json.dumps(self.state))
        self.plan = {**self.plan, 'steps': ['Implement approved revised scope and remove historical fixture']}
        self.plan_url = self.record('plan', self.plan)['url']
        self.run.save()

    def authorize_revision(self):
        self.run.authorize_revision(self.plan_url, True, True, 'User explicitly approved revised scope and feature rewrite')

    def rewrite_fixture(self):
        self.authorize_revision()
        (self.work / 'scope.txt').write_text('Approved revised scope\n')
        self.git(self.work, 'add', 'scope.txt')
        self.git(self.work, 'commit', '--fixup', self.old['published_head'])
        tree = self.git(self.work, 'rev-parse', 'HEAD^{tree}')
        self.git(self.work, '-c', 'sequence.editor=true', 'rebase', '-i', '--autosquash', self.state['source_head'])
        self.assertEqual(self.git(self.work, 'rev-parse', 'HEAD^{tree}'), tree)
        self.verification('writer-revision')
        self.review(session='reviewer-revision')

    def test_revision_requires_explicit_flags_reason_new_exact_plan(self):
        self.revision_fixture()
        for authorized, rewrite, reason, plan in ((False, True, 'Approved', self.plan_url),
                (True, False, 'Approved', self.plan_url), (True, True, '', self.plan_url),
                (True, True, 'Approved', self.old['plan'])):
            with self.assertRaises(RuntimeError):
                self.run.authorize_revision(plan, authorized, rewrite, reason)
        self.assertEqual(self.state['plan'], self.old['plan'])
        self.assertNotIn('revisions', self.state)

    def test_revision_preserves_budget_pin_identity_and_archives_old_evidence(self):
        self.revision_fixture()
        self.authorize_revision()
        revision = self.state['history_revision']
        for key in ('repairs', 'source_head', 'resource_root', 'pr', 'workers', 'worker_sessions', 'published_head'):
            self.assertEqual(self.state[key], self.old[key])
        for key in ('plan', 'plan_digest', 'contract_revision', 'review', 'verification', 'verification_run'):
            self.assertEqual(revision['prior'][key], self.old[key])
        self.assertEqual(revision['lease'], self.old['published_head'])
        self.assertEqual(self.state['plan'], self.plan_url)
        self.assertEqual(self.state['stage'], 'execute')
        self.assertNotIn('review', self.state)
        self.assertNotIn('verification', self.state)
        self.assertEqual(len(revision['helper_sha256']), 64)
        self.assertEqual(len(revision['pinned_helper_sha256']), 64)
        with self.assertRaisesRegex(RuntimeError, 'passing review'):
            self.run.rewrite_publish('Approved rewrite')

    def test_revision_rejects_pending_dirty_wrong_branch_local_head_or_remote(self):
        self.revision_fixture()
        self.state['attempt'] = {'id': 'pending'}
        with self.assertRaisesRegex(RuntimeError, 'pending worker'):
            self.authorize_revision()
        self.state.pop('attempt')
        (self.work / 'untracked').write_text('user work')
        with self.assertRaisesRegex(RuntimeError, 'clean source'):
            self.authorize_revision()
        (self.work / 'untracked').unlink()
        self.state['branch'] = 'other'
        with self.assertRaisesRegex(RuntimeError, 'Branch changed'):
            self.authorize_revision()
        self.state['branch'] = 'feature'
        self.state['published_head'] = self.state['source_head']
        with self.assertRaisesRegex(RuntimeError, 'Original published head'):
            self.authorize_revision()
        self.state['published_head'] = self.old['published_head']
        with patch.object(self.run, 'remote_head', return_value='changed'):
            with self.assertRaisesRegex(RuntimeError, 'Remote head changed'):
                self.authorize_revision()
        self.pr['baseRefName'] = 'other'
        with self.assertRaisesRegex(RuntimeError, 'PR branch mismatch'):
            self.authorize_revision()
        self.assertNotIn('revisions', self.state)

    def test_revision_rejects_modified_old_plan_and_new_plan_integrity(self):
        self.revision_fixture()
        comment = self.comments[-1]
        body = comment['body']
        comment['body'] = body.replace('Implement approved', 'Tampered approved')
        with self.assertRaises(RuntimeError):
            self.authorize_revision()
        comment['body'] = body
        self.comments[1]['body'] = self.comments[1]['body'].replace('Implement and verify', 'Tampered old plan')
        with self.assertRaises(RuntimeError):
            self.authorize_revision()
        self.assertEqual(self.state['plan'], self.old['plan'])

    def test_rewrite_publication_uses_original_lease_same_pr_and_keeps_main(self):
        self.revision_fixture(); self.rewrite_fixture()
        with patch.object(delivery, 'command', side_effect=self.command) as call:
            self.run.rewrite_publish('Publish approved feature-only rewrite')
        pushes = [c.args[0] for c in call.call_args_list if c.args[0][:2] == ['git', 'push']]
        self.assertEqual(len(pushes), 1)
        self.assertIn('--force-with-lease=refs/heads/feature:' + self.old['published_head'], pushes[0])
        self.assertNotIn('--no-verify', pushes[0])
        self.assertEqual(self.state['stage'], 'ci')
        self.assertEqual(self.creates, 1)
        self.assertEqual(self.state['pr'], self.old['pr'])
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), self.state['source_head'])
        self.assertEqual(self.state['repairs'], 2)
        self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')

    def test_rewrite_requires_authorization_review_and_unchanged_remote(self):
        with self.assertRaisesRegex(RuntimeError, 'authorization'):
            self.run.rewrite_publish('No authorization')
        self.revision_fixture(); self.rewrite_fixture()
        self.state['review'] = self.old['review']
        with self.assertRaises(RuntimeError):
            self.run.rewrite_publish('Stale review')
        self.state['review'] = self.comments[-1]['html_url']
        with patch.object(self.run, 'remote_head', return_value='moved'):
            with self.assertRaisesRegex(RuntimeError, 'originally authorized lease'):
                self.run.rewrite_publish('Remote moved')
        self.assertNotIn('intent', self.state['history_revision'])

    def test_rewrite_ambiguous_success_reconciles_without_repeating_push(self):
        self.revision_fixture(); self.rewrite_fixture()
        def transport(argv, *args, **kwargs):
            result = self.command(argv, *args, **kwargs)
            if argv[:2] == ['git', 'push']:
                raise RuntimeError('Lost successful push response')
            return result
        with patch.object(delivery, 'command', side_effect=transport):
            with self.assertRaisesRegex(RuntimeError, 'Lost successful'):
                self.run.rewrite_publish('Approved rewrite')
        self.assertEqual(self.state['published_head'], self.old['published_head'])
        saved = json.loads((self.directory / 'state.json').read_text())
        self.run = delivery.Delivery(self.directory, saved)
        with patch.object(delivery, 'command', side_effect=self.command) as call:
            self.run.rewrite_publish('Reconcile lost response')
        self.assertFalse(any(c.args[0][:2] == ['git', 'push'] for c in call.call_args_list))
        self.assertEqual(saved['stage'], 'ci')
        self.assertEqual(self.creates, 1)

    def test_revision_cross_pin_cli_keeps_pin_and_limits_other_actions(self):
        self.revision_fixture()
        pin = self.root / 'original-pin'
        (pin / 'tracking').mkdir(parents=True)
        (pin / 'tracking/delivery.py').write_text('# immutable original helper\n')
        self.state['resource_root'] = str(pin)
        self.run.save()
        args = ['--key', 'fixture', '--state-dir', str(self.directory.parent)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(['authorize-revision', *args, '--plan', self.plan_url,
                '--authorize-through-pr', '--allow-history-rewrite', '--reason', 'Approved revision']), 0)
            self.assertEqual(delivery.main(['begin', *args]), 2)
            self.assertEqual(delivery.main(['rewrite-publish', *args, '--reason', 'No fresh review yet']), 2)
        saved = json.loads((self.directory / 'state.json').read_text())
        self.assertEqual(saved['resource_root'], str(pin))
        self.assertEqual((pin / 'tracking/delivery.py').read_text(), '# immutable original helper\n')

    def test_revision_accepts_changed_contract_and_pins_exact_new_record(self):
        self.revision_fixture()
        self.issue['body'] = 'Return two with revised Live-only scope'
        contract = self.record('contract', {'version': 2, 'outcome': 'Revised scope',
            'requirements': [{'id': 'R1', 'expected': 'Return two', 'required': True}],
            'constraints': [], 'exclusions': ['Historical fixture'], 'decisions': [], 'unresolved': [],
            'checkpoint': packet.checkpoint(self.issue, self.comments)})
        self.contract = contract['metadata']['record']
        self.plan = {**self.plan, 'contract_revision': self.contract['revision']}
        self.plan_url = self.record('plan', self.plan)['url']
        self.authorize_revision()
        self.assertNotEqual(self.state['contract_revision'], self.old['contract_revision'])
        self.assertEqual(self.state['history_revision']['prior']['contract_revision'], self.old['contract_revision'])
        self.assertEqual(self.state['history_revision']['plan_digest'], evidence.digest(self.plan))
        self.run.plan()
        self.plan['steps'] = ['Unauthorized later scope']
        self.record('plan', self.plan)
        with self.assertRaises(RuntimeError):
            self.run.plan()

    def test_rewrite_waits_for_matching_pr_after_push_and_rejects_changed_intent(self):
        self.revision_fixture(); self.rewrite_fixture()
        original = self.run.revision_pr
        count = 0
        def observe(head):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError('PR not yet updated')
            return original(head)
        with patch.object(self.run, 'revision_pr', side_effect=observe):
            with self.assertRaisesRegex(RuntimeError, 'not yet updated'):
                self.run.rewrite_publish('Approved rewrite')
        self.assertEqual(self.state['stage'], 'publish')
        self.assertEqual(self.state['published_head'], self.old['published_head'])
        self.state['history_revision']['intent']['expected_head'] = 'different'
        with self.assertRaisesRegex(RuntimeError, 'intent head changed'):
            self.run.rewrite_publish('Reconcile')
        self.state['history_revision']['intent']['expected_head'] = self.git(self.work, 'rev-parse', 'HEAD')
        with patch.object(delivery, 'command', side_effect=self.command) as call:
            self.run.rewrite_publish('Reconcile actual matching PR')
        self.assertFalse(any(c.args[0][:2] == ['git', 'push'] for c in call.call_args_list))
        self.assertEqual(self.state['stage'], 'ci')

    def test_revision_rejects_unrelated_prepared_source_or_advanced_main(self):
        self.revision_fixture()
        self.state['source_head'] = self.old['published_head']
        with self.assertRaisesRegex(RuntimeError, 'Prepared main revision'):
            self.authorize_revision()
        self.state['source_head'] = self.old['source_head']
        (self.source / 'main-new.txt').write_text('main advanced\n')
        self.git(self.source, 'add', 'main-new.txt')
        self.git(self.source, 'commit', '-m', 'Advance main')
        self.git(self.source, 'push', 'origin', 'main')
        with self.assertRaisesRegex(RuntimeError, 'main advanced'):
            self.authorize_revision()
        self.assertNotIn('revisions', self.state)

    def test_standard_publication_still_has_no_force_or_hook_bypass(self):
        self.ready()
        with patch.object(delivery, 'command', side_effect=self.command) as call:
            self.publish()
        pushes = [c.args[0] for c in call.call_args_list if c.args[0][:2] == ['git', 'push']]
        self.assertEqual(len(pushes), 1)
        self.assertEqual(pushes[0], ['git', 'push', '-u', 'origin', 'HEAD:refs/heads/feature'])

    def additive_fixture(self):
        self.ready(); self.publish(); self.run.ci()
        self.state['repairs'] = 2
        self.old = json.loads(json.dumps(self.state))
        self.plan = {**self.plan, 'steps': ['Implement approved additive installer and preview release']}
        self.plan_url = self.record('plan', self.plan)['url']
        self.run.save()

    def authorize_additive(self):
        self.run.authorize_revision(self.plan_url, True, False, 'User approved exact additive plan through same PR')

    def correction_fixture(self):
        self.additive_fixture()
        self.authorize_additive()
        attempt = self.worker('stopped-initial-writer')
        self.state.setdefault('abandoned_workers', []).append({**self.state.pop('attempt'),
            'reason': 'Stopped on ZIP metadata feasibility blocker'})
        self.state.update(stage='blocked', resume_stage='execute', blocker='ZIP-01 artifact', repairs=2)
        self.old = json.loads(json.dumps(self.state))
        self.plan = {**self.plan, 'steps': ['Allow bounded metadata reader to resolve ZIP-01']}
        self.plan_url = self.record('plan', self.plan)['url']
        self.run.save()
        return attempt

    def test_initial_execution_correction_archives_blocker_and_preserves_budget_and_history(self):
        attempt = self.correction_fixture()
        previous_rewrite = {'lease': 'original-lease', 'published_head': self.old['published_head']}
        self.state['history_revision'] = json.loads(json.dumps(previous_rewrite))
        with patch.object(self.run, 'gate', side_effect=AssertionError('No current gate exists')):
            with patch.object(delivery, 'command', side_effect=self.command) as call:
                self.authorize_additive()
        self.assertFalse(any(c.args[0][:2] in (['git', 'push'], ['git', 'commit'], ['git', 'merge'])
                             for c in call.call_args_list))
        revision = self.state['revisions'][-1]
        self.assertEqual(revision['kind'], 'initial-execution-plan-correction')
        self.assertEqual(revision['authorization'], 'through-pr-additive-no-history-rewrite')
        for key in ('blocker', 'resume_stage', 'stage', 'abandoned_workers', 'workers', 'worker_sessions'):
            self.assertEqual(revision['prior'][key], self.old.get(key, []))
        self.assertEqual(revision['prior']['abandoned_workers'][-1]['id'], attempt)
        for key in ('repairs', 'source_head', 'resource_root', 'pr', 'workers', 'worker_sessions',
                    'published_head', 'owner_session', 'workspace', 'source', 'branch', 'origin'):
            self.assertEqual(self.state[key], self.old[key])
        self.assertEqual(self.state['history_revision'], previous_rewrite)
        self.assertEqual(self.state['repairs'], 2)
        self.assertEqual(self.state['stage'], 'execute')
        self.assertNotIn('blocker', self.state)
        self.assertNotIn('resume_stage', self.state)
        self.run.plan()
        with self.assertRaisesRegex(RuntimeError, 'authorization'):
            self.run.rewrite_publish('No new rewrite permission')
        with self.assertRaises(RuntimeError):
            self.authorize_additive()

    def test_initial_execution_correction_rejects_evidence_exhaustion_and_wrong_stages(self):
        self.correction_fixture()
        for key in ('verification', 'verification_run', 'review', 'ci'):
            self.state[key] = None  # Even an incomplete current record is not initial execution.
            with self.assertRaisesRegex(RuntimeError, 'no current'):
                self.authorize_additive()
            self.state.pop(key)
        self.state['repairs'] = 3
        with self.assertRaisesRegex(RuntimeError, 'exhausted'):
            self.authorize_additive()
        self.assertEqual(self.state['repairs'], 3)
        self.state['repairs'] = 2
        for stage, resume in (('execute', None), ('review', None), ('needs_repair', None),
                              ('blocked', 'review'), ('blocked', 'needs_repair'), ('blocked', 'ci')):
            self.state.update(stage=stage, resume_stage=resume)
            with self.assertRaises(RuntimeError):
                self.authorize_additive()
        self.assertEqual(len(self.state['revisions']), 1)

    def test_initial_execution_correction_requires_approval_changed_plan_and_blocker(self):
        self.correction_fixture()
        for plan, authorized, rewrite, reason in ((self.plan_url, False, False, 'Approved'),
                (None, True, False, 'Approved'), (self.plan_url, True, False, ' '),
                (self.old['plan'], True, False, 'Approved'), (self.plan_url, True, True, 'Approved')):
            with self.assertRaises(RuntimeError):
                self.run.authorize_revision(plan, authorized, rewrite, reason)
        self.plan_url = self.record('plan', {**self.plan, 'steps':
            ['Implement approved additive installer and preview release']})['url']
        with self.assertRaisesRegex(RuntimeError, 'changed plan'):
            self.authorize_additive()
        self.state.pop('blocker')
        with self.assertRaisesRegex(RuntimeError, 'blocker'):
            self.authorize_additive()
        self.assertEqual(len(self.state['revisions']), 1)

    def test_initial_execution_correction_retains_source_remote_pr_and_prior_plan_guards(self):
        self.correction_fixture()
        self.state['attempt'] = {'id': 'pending'}
        with self.assertRaisesRegex(RuntimeError, 'pending worker'):
            self.authorize_additive()
        self.state.pop('attempt')
        (self.work / 'user-work.txt').write_text('Preserve me')
        with self.assertRaisesRegex(RuntimeError, 'clean source'):
            self.authorize_additive()
        (self.work / 'user-work.txt').unlink()
        self.state['published_head'] = self.state['source_head']
        with self.assertRaisesRegex(RuntimeError, 'Original published head'):
            self.authorize_additive()
        self.state['published_head'] = self.old['published_head']
        for heads in (['moved'], [self.old['published_head'], 'moved']):
            with patch.object(self.run, 'remote_head', side_effect=heads):
                with self.assertRaisesRegex(RuntimeError, 'Remote head changed'):
                    self.authorize_additive()
        self.pr['state'] = 'CLOSED'
        with self.assertRaisesRegex(RuntimeError, 'Original open'):
            self.authorize_additive()
        self.pr['state'] = 'OPEN'
        prior = next(c for c in self.comments if c['html_url'] == self.old['plan'])
        prior['body'] = prior['body'].replace('Implement approved', 'Tampered approved')
        with self.assertRaises(RuntimeError):
            self.authorize_additive()
        self.assertEqual(len(self.state['revisions']), 1)

    def test_completed_additive_archives_completion_without_review_gate_or_rewrite_grant(self):
        self.additive_fixture()
        previous_rewrite = {'lease': 'original-lease', 'published_head': self.old['published_head'],
                            'authorization': 'through-pr-and-branch-history-rewrite'}
        self.state['history_revision'] = json.loads(json.dumps(previous_rewrite))
        with patch.object(self.run, 'gate', side_effect=AssertionError('Superseded review must not gate new scope')):
            with patch.object(delivery, 'command', side_effect=self.command) as call:
                self.authorize_additive()
        self.assertFalse(any(c.args[0][:2] in (['git', 'push'], ['git', 'commit'], ['git', 'merge'])
                             for c in call.call_args_list))
        self.assertEqual(self.state['stage'], 'execute')
        for key in ('repairs', 'source_head', 'resource_root', 'pr', 'workers', 'worker_sessions',
                    'published_head', 'owner_session', 'workspace', 'source', 'branch', 'origin'):
            self.assertEqual(self.state[key], self.old[key])
        self.assertEqual(self.state['repairs'], 2)
        revision = self.state['revisions'][-1]
        self.assertEqual(revision['authorization'], 'through-pr-additive-no-history-rewrite')
        self.assertEqual(revision['prior']['stage'], 'complete')
        for key in ('completed_at', 'plan', 'plan_digest', 'contract_revision', 'verification',
                    'verification_run', 'review', 'ci', 'published_head'):
            self.assertEqual(revision['prior'][key], self.old[key])
        self.assertEqual(revision['lease'], self.old['published_head'])
        self.assertEqual(self.state['history_revision'], previous_rewrite)
        for key in ('verification', 'verification_run', 'review', 'ci', 'completed_at'):
            self.assertNotIn(key, self.state)
        self.run.plan()
        with self.assertRaisesRegex(RuntimeError, 'authorization'):
            self.run.rewrite_publish('Old rewrite grant cannot be reused')
        with self.assertRaises(RuntimeError):
            self.authorize_additive()
        self.assertEqual(len(self.state['revisions']), 1)

    def test_completed_additive_requires_exact_new_authorization_and_refuses_rewrite(self):
        self.additive_fixture()
        for plan, authorized, rewrite, reason in ((self.plan_url, False, False, 'Approved'),
                (None, True, False, 'Approved'), (self.plan_url, True, False, ''),
                (self.old['plan'], True, False, 'Approved'), (self.plan_url, True, True, 'Approved')):
            with self.assertRaises(RuntimeError):
                self.run.authorize_revision(plan, authorized, rewrite, reason)
        self.assertEqual(self.state['stage'], 'complete')
        self.assertEqual(self.state['completed_at'], self.old['completed_at'])
        self.assertNotIn('revisions', self.state)

    def test_completed_additive_rejects_pending_dirty_local_head_and_remote_drift(self):
        self.additive_fixture()
        self.state['attempt'] = {'id': 'pending'}
        with self.assertRaisesRegex(RuntimeError, 'pending worker'):
            self.authorize_additive()
        self.state.pop('attempt')
        (self.work / 'user-work.txt').write_text('Keep user work\n')
        with self.assertRaisesRegex(RuntimeError, 'clean source'):
            self.authorize_additive()
        (self.work / 'user-work.txt').unlink()
        self.state['published_head'] = self.state['source_head']
        with self.assertRaisesRegex(RuntimeError, 'Original published head'):
            self.authorize_additive()
        self.state['published_head'] = self.old['published_head']
        for heads in (['changed'], [self.old['published_head'], 'changed']):
            with patch.object(self.run, 'remote_head', side_effect=heads):
                with self.assertRaisesRegex(RuntimeError, 'Remote head changed'):
                    self.authorize_additive()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertNotIn('revisions', self.state)

    def test_completed_additive_rejects_changed_or_closed_pr_including_final_observation(self):
        self.additive_fixture()
        original = self.run.view_pr()
        for change in ({'state': 'MERGED'}, {'isDraft': True}, {'isCrossRepository': True},
                       {'url': 'https://github.com/example/repo/pull/3'}, {'headRefName': 'other'},
                       {'baseRefName': 'other'}, {'headRefOid': 'changed'}):
            for views in ([{**original, **change}], [original, {**original, **change}]):
                with patch.object(self.run, 'view_pr', side_effect=views):
                    with self.assertRaises(RuntimeError):
                        self.authorize_additive()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertNotIn('revisions', self.state)

    def test_completed_additive_retains_plan_and_current_contract_integrity_checks(self):
        self.additive_fixture()
        for index, old, new in ((-1, 'Implement approved', 'Tampered approved'),
                                (1, 'Implement and verify', 'Tampered old plan')):
            body = self.comments[index]['body']
            self.comments[index]['body'] = body.replace(old, new)
            with self.assertRaises(RuntimeError):
                self.authorize_additive()
            self.comments[index]['body'] = body
        # A different URL alone is not a changed approved plan.
        self.plan_url = self.record('plan', {**self.plan, 'steps': ['Implement and verify']})['url']
        with self.assertRaisesRegex(RuntimeError, 'changed plan'):
            self.authorize_additive()
        self.plan_url = self.record('plan', self.plan)['url']
        verify.approved_plan(self.issue, self.comments, self.plan_url)
        self.issue['body'] += ' Unapproved contract change'
        with self.assertRaises(RuntimeError):
            self.authorize_additive()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertNotIn('revisions', self.state)

    def test_completed_additive_rejects_pending_rewrite_or_invalid_main_ancestry(self):
        self.additive_fixture()
        self.state['history_revision'] = {'lease': self.old['published_head']}
        with self.assertRaisesRegex(RuntimeError, 'already pending'):
            self.authorize_additive()
        self.state.pop('history_revision')
        self.state['source_head'] = self.old['published_head']
        with self.assertRaisesRegex(RuntimeError, 'Prepared main revision'):
            self.authorize_additive()
        self.state['source_head'] = self.old['source_head']
        (self.source / 'main-new.txt').write_text('main advanced\n')
        self.git(self.source, 'add', 'main-new.txt')
        self.git(self.source, 'commit', '-m', 'Advance main')
        self.git(self.source, 'push', 'origin', 'main')
        with self.assertRaisesRegex(RuntimeError, 'main advanced'):
            self.authorize_additive()
        self.assertNotIn('revisions', self.state)

    def test_completed_additive_cross_pin_only_authorizes_then_uses_original_helper(self):
        self.additive_fixture()
        pin = self.root / 'original-pin'
        (pin / 'tracking').mkdir(parents=True)
        (pin / 'tracking/delivery.py').write_text('# immutable original helper\n')
        self.state['resource_root'] = str(pin)
        self.run.save()
        args = ['--key', 'fixture', '--state-dir', str(self.directory.parent)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(['authorize-revision', *args, '--plan', self.plan_url,
                '--authorize-through-pr', '--reason', 'Approved additive plan']), 0)
            for action in ('begin', 'finish', 'commit', 'sync', 'publish', 'ci'):
                self.assertEqual(delivery.main([action, *args]), 2)
            self.assertEqual(delivery.main(['authorize-revision', *args, '--plan', self.plan_url,
                '--authorize-through-pr', '--reason', 'Repeated request']), 2)
        saved = json.loads((self.directory / 'state.json').read_text())
        self.assertEqual(saved['stage'], 'execute')
        self.assertEqual(saved['resource_root'], str(pin))
        self.assertEqual(saved['repairs'], 2)
        self.assertEqual(len(saved['revisions']), 1)
        self.assertNotIn('history_revision', saved)
        self.assertEqual((pin / 'tracking/delivery.py').read_text(), '# immutable original helper\n')

    def test_completed_additive_full_lifecycle_updates_same_pr_without_force(self):
        # Start from a real previously authorized and published rewrite, not a fresh run.
        self.revision_fixture(); self.rewrite_fixture()
        self.run.rewrite_publish('Publish previously approved rewrite')
        self.run.ci()
        old_rewrite = json.loads(json.dumps(self.state['history_revision']))
        old_revisions = json.loads(json.dumps(self.state['revisions']))
        self.old = json.loads(json.dumps(self.state))
        self.plan = {**self.plan, 'steps': ['Add installer and preview release without rewriting history']}
        self.plan_url = self.record('plan', self.plan)['url']
        self.authorize_additive()
        with self.assertRaisesRegex(RuntimeError, 'Passing review'):
            self.run.publish(None, None)
        with self.assertRaisesRegex(RuntimeError, 'authorization'):
            self.run.rewrite_publish('No new force permission')
        self.run.sync()
        (self.work / 'installer.txt').write_text('Approved additive installer\n')
        self.verification('writer-additive')
        self.review(session='reviewer-additive')
        self.run.commit('Add installer', ['installer.txt'])
        with self.assertRaisesRegex(RuntimeError, 'authorization'):
            self.run.rewrite_publish('Old grant still cannot force')
        with patch.object(delivery, 'command', side_effect=self.command) as call:
            self.run.publish(None, None)
        pushes = [c.args[0] for c in call.call_args_list if c.args[0][:2] == ['git', 'push']]
        self.assertEqual(pushes, [['git', 'push', '-u', 'origin', 'HEAD:refs/heads/feature']])
        self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertGreater(self.state['completed_at'], self.old['completed_at'])
        self.assertEqual(self.state['pr'], self.old['pr'])
        self.assertEqual(self.state['history_revision'], old_rewrite)
        self.assertEqual(self.state['revisions'][:-1], old_revisions)
        self.assertEqual(self.state['repairs'], 2)
        self.assertEqual(self.creates, 1)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), self.old['source_head'])
        self.git(self.work, 'merge-base', '--is-ancestor', self.old['published_head'], 'HEAD')

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
        self.run.commit('Feature', ['value.txt'])
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

    def test_receiver_defaults_to_dispatching_host_and_accepts_override(self):
        choose = delivery.receiver_agent
        self.assertEqual(choose(environ={}), 'opencode')
        self.assertEqual(choose(environ={'CLAUDECODE': '1'}), 'claude')
        self.assertEqual(choose(environ={'CODEX_THREAD_ID': 'thread'}), 'codex')
        self.assertEqual(choose(environ={'CLAUDECODE': '1', 'DEVELOP_RECEIVER_AGENT': 'opencode'}), 'opencode')
        self.assertEqual(choose('codex', {'CLAUDECODE': '1'}), 'codex')
        with self.assertRaisesRegex(RuntimeError, 'Unsupported receiver'):
            choose(environ={'DEVELOP_RECEIVER_AGENT': 'grok'})

    def test_dispatch_launches_receiver_and_keeps_it_on_resume(self):
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
                return subprocess.CompletedProcess(argv, 2, json.dumps({'accepted': True}), '')
            return self.command(argv, cwd, allowed, timeout)

        host = {'CLAUDECODE': '1', 'CODEX_THREAD_ID': '', 'DEVELOP_RECEIVER_AGENT': ''}
        with patch.dict(os.environ, host), patch.object(delivery, 'command', side_effect=transport):
            self.run.dispatch()
            with self.assertRaisesRegex(RuntimeError, 'already targets claude'):
                self.run.dispatch('codex')
            self.run.dispatch()
        self.assertEqual(sends[0][sends[0].index('--agent') + 1], 'claude')
        self.assertNotIn('--agent', sends[1])  # The handoff journal keeps its own agent.
        self.assertEqual(self.state['receiver_agent'], 'claude')
        brief = (self.directory / 'brief.txt').read_text()
        self.assertIn('$CLAUDE_CODE_SESSION_ID', brief)
        self.assertNotIn('Task workers', brief)

    def test_adopt_hands_run_to_another_coordinator_without_resetting_it(self):
        self.state.update(repairs=2, receiver_agent='claude')
        self.run.begin()
        attempt = self.state['attempt']['id']
        self.run.claim(attempt, 'writer-1')
        with self.assertRaisesRegex(RuntimeError, 'Confirm the previous coordinator'):
            self.run.adopt('codex-thread', '', True)
        for session in ('owner', 'writer-1', ''):
            with self.assertRaisesRegex(RuntimeError, 'new session'):
                self.run.adopt(session, 'Claude usage limit', True)
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'codex-thread', 'CLAUDECODE': '', 'DEVELOP_RECEIVER_AGENT': ''}):
            self.run.adopt('codex-thread', 'Claude usage limit', True)
        self.assertEqual((self.state['owner_session'], self.state['receiver_agent']), ('codex-thread', 'codex'))
        self.assertEqual(self.state['owner_history'][0]['session'], 'owner')
        self.assertEqual(self.state['owner_history'][0]['agent'], 'claude')
        self.assertEqual((self.state['repairs'], self.state['attempt']['id']), (2, attempt))
        self.state.pop('attempt')  # Reconciled: the writer stopped with its coordinator.
        self.run.begin()
        with self.assertRaisesRegex(RuntimeError, 'fresh'):
            self.run.claim(self.state['attempt']['id'], 'owner')
        with self.assertRaisesRegex(RuntimeError, 'new session'):
            self.run.adopt('owner', 'Back to Claude', True)
        os.chdir(self.source)
        with self.assertRaisesRegex(RuntimeError, 'bound feature workspace'):
            self.run.adopt('third', 'Wrong checkout', True)

    def test_locate_finds_runs_bound_to_the_current_workspace(self):
        self.state['receiver_agent'] = 'codex'
        self.run.save()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(delivery.main(['locate', '--state-dir', str(self.directory.parent)]), 0)
        found = json.loads(output.getvalue())
        self.assertEqual([(r['key'], r['owner_agent']) for r in found], [('fixture', 'codex')])
        self.assertEqual(found[0]['helper'], str(delivery.ROOT / 'tracking/delivery.py'))
        os.chdir(self.source)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            delivery.main(['locate', '--state-dir', str(self.directory.parent)])
        self.assertEqual(json.loads(output.getvalue()), [])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(['inspect', '--state-dir', str(self.directory.parent)]), 2)

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
        run_id, _ = verify.run_checks(self.work, self.issue, self.plan_url, self.plan, self.contract)
        url = self.record('verification', {'version': 2, 'run_id': run_id})['url']
        self.run.integration_failure(attempt, url)
        self.assertEqual(self.state['stage'], 'needs_repair')
        self.assertEqual(self.state['repairs'], 0)
        self.run.repair('Runner reproduced feature incompatibility', attributable=True)
        self.assertEqual(self.state['repairs'], 1)

    # Tooling-stale evidence before publication (reverify).
    REVERIFY_PRESERVED = ('resource_root', 'plan', 'plan_digest', 'contract_revision', 'owner_session', 'workspace',
                          'branch', 'source', 'source_head', 'origin', 'workers', 'worker_sessions', 'pr',
                          'published_head', 'observed_main', 'integration', 'repairs')

    def legacy_manifest(self):
        path = self.work / delivery.LEGACY_MANIFEST
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.plan['check_manifest'], indent=2) + '\n')
        return path

    def stale_publish(self, exclude=False):
        """Reproduce a run verified while the retired helper's manifest sat in the worktree."""
        if exclude:
            common = Path(self.git(self.work, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
            (common / 'info').mkdir(exist_ok=True)
            with (common / 'info/exclude').open('a') as stream:
                stream.write('/.opencode/\n')
        manifest = self.legacy_manifest()
        self.ready()
        head = self.git(self.work, 'rev-parse', 'HEAD')
        if exclude:
            self.run.commit('Implement fixture', ['value.txt'])
            self.state['commit_pending'] = {'head': self.git(self.work, 'rev-parse', 'HEAD'),
                                            'message': 'Implement fixture', 'paths': ['value.txt']}
        else:
            with self.assertRaisesRegex(RuntimeError, 'Uncommitted work remains'):
                self.run.commit('Implement fixture', ['value.txt'])
            self.assertEqual(self.state['commit_pending']['head'], head)
            self.assertNotEqual(self.git(self.work, 'rev-parse', 'HEAD'), head)
        self.state.update(stage='blocked', resume_stage='publish', blocker='Legacy manifest blocks publication')
        self.run.save()
        return manifest

    def reload(self):
        self.state = json.loads((self.directory / 'state.json').read_text())
        self.run = delivery.Delivery(self.directory, self.state)
        return self.state

    def observed(self):
        manifest = self.work / delivery.LEGACY_MANIFEST
        return ((self.directory / 'state.json').read_bytes(), copy.deepcopy(self.state),
                self.git(self.work, 'status', '--porcelain', '--untracked-files=all', '--ignored'),
                self.git(self.work, 'rev-parse', 'HEAD'), self.git(self.work, 'rev-parse', 'HEAD:value.txt'),
                os.readlink(manifest) if manifest.is_symlink() else manifest.read_bytes() if manifest.is_file() else None,
                self.git(self.remote, 'for-each-ref'), self.creates)

    def assert_reverify_refused(self, pattern, reason='Legacy manifest from retired verify init'):
        before = self.observed()
        with self.assertRaisesRegex(RuntimeError, pattern):
            self.run.reverify(reason)
        self.assertEqual(self.observed(), before)

    def finish_loop(self, suffix):
        self.run.sync()
        self.assertEqual(self.state['stage'], 'execute')
        self.verification('writer-' + suffix)
        self.review(session='reviewer-' + suffix)
        self.run.commit('Implement fixture', ['value.txt'])
        self.assertNotIn('commit_pending', self.state)
        body = self.root / 'pr-body.md'
        body.write_text('Implements fixture. Closes #1.')
        self.run.publish('Fixture', body)
        self.run.ci()
        self.assertEqual(self.state['stage'], 'complete')
        self.assertEqual(self.state['repairs'], 0)
        self.assertEqual(self.creates, 1)

    def test_reverify_blocked_publish_removes_matching_manifest_and_completes_without_repair(self):
        self.stale_publish()
        preserved = {k: copy.deepcopy(self.state.get(k)) for k in self.REVERIFY_PRESERVED}
        prior = {k: copy.deepcopy(self.state[k]) for k in ('verification', 'verification_run', 'review',
                                                          'blocker', 'resume_stage', 'commit_pending')}
        args = ['--key', 'fixture', '--state-dir', str(self.directory.parent)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(delivery.main(['reverify', *args, '--reason', 'Legacy manifest from retired verify init']), 0)
        saved = self.reload()
        self.assertEqual(saved['stage'], 'execute')
        for key in ('verification', 'verification_run', 'review', 'ci', 'blocker', 'resume_stage',
                    'reverify_pending', 'commit_pending'):
            self.assertNotIn(key, saved)
        entry = saved['tooling_reverifications'][-1]
        self.assertEqual(entry['reason'], 'Legacy manifest from retired verify init')
        self.assertEqual(entry['prior_stage'], 'blocked')
        self.assertEqual({k: v for k, v in entry['removed'].items() if k != 'reverify_pending'}, prior)
        self.assertEqual(entry['removed']['reverify_pending']['resume_stage'], 'publish')
        self.assertEqual(entry['removed_path'], delivery.LEGACY_MANIFEST)
        self.assertEqual(entry['old_verifier_sha256'], verify.verifier_hash())
        self.assertEqual(entry['new_verifier_sha256'], verify.verifier_hash())
        self.assertTrue(entry['helper_sha256'])
        self.assertEqual(saved['history'][-1]['event'], 'tooling_reverify')
        self.assertEqual({k: saved.get(k) for k in self.REVERIFY_PRESERVED}, preserved)
        self.assertFalse(os.path.lexists(self.work / '.opencode'))
        self.assertEqual(self.git(self.work, 'status', '--porcelain', '--untracked-files=all'), '')
        self.assertEqual(self.git(self.remote, 'for-each-ref', 'refs/heads/feature'), '')
        self.assertEqual(self.creates, 0)
        self.finish_loop('reverify')

    def test_reverify_with_excluded_manifest_keeps_current_commit_intent_until_commit_reconciles(self):
        self.stale_publish(exclude=True)
        self.assertEqual(self.git(self.work, 'status', '--porcelain', '--untracked-files=all'), '')
        pending = copy.deepcopy(self.state['commit_pending'])
        self.run.reverify('Excluded legacy manifest from retired verify init')
        self.assertEqual(self.state['stage'], 'execute')
        self.assertEqual(self.state['commit_pending'], pending)
        self.assertNotIn('commit_pending', self.state['tooling_reverifications'][-1]['removed'])
        self.assertEqual(self.state['tooling_reverifications'][-1]['removed_path'], delivery.LEGACY_MANIFEST)
        self.assertFalse(os.path.lexists(self.work / '.opencode'))
        self.finish_loop('excluded')

    def test_reverify_ci_stage_with_changed_verifier_keeps_pr_head_and_budget(self):
        self.ready(); self.publish()
        self.checks = [{'name': 'unit', 'bucket': 'pending'}]
        self.run.ci()
        self.assertEqual(self.state['stage'], 'ci')
        preserved = {k: copy.deepcopy(self.state.get(k)) for k in self.REVERIFY_PRESERVED}
        real = verify.verifier_hash()
        with patch.object(verify, 'verifier_hash', return_value='f' * 64):
            self.run.reverify('Verifier implementation changed after publication')
        self.assertEqual(self.state['stage'], 'execute')
        for key in ('ci', 'verification', 'verification_run', 'review'):
            self.assertNotIn(key, self.state)
        self.assertEqual({k: self.state.get(k) for k in self.REVERIFY_PRESERVED}, preserved)
        self.assertTrue(self.state['pr'] and self.state['published_head'])
        entry = self.state['tooling_reverifications'][-1]
        self.assertEqual((entry['old_verifier_sha256'], entry['new_verifier_sha256'], entry['removed_path']),
                         (real, 'f' * 64, None))
        self.assertEqual(entry['prior_stage'], 'ci')
        self.assertEqual(self.creates, 1)

    def test_reverify_refuses_ineligible_run_state_without_mutation(self):
        self.stale_publish()
        original = copy.deepcopy(self.state)
        head = self.git(self.work, 'rev-parse', 'HEAD')

        def case(pattern, reason='Legacy manifest from retired verify init', **changes):
            self.state.clear(); self.state.update(copy.deepcopy(original)); self.state.update(changes)
            for key in [k for k, v in changes.items() if v is None]:
                self.state.pop(key)
            self.run.save()
            with self.subTest(pattern=pattern, changes=sorted(changes)):
                self.assert_reverify_refused(pattern, reason)

        case('pending worker', attempt={'id': 'a', 'stage': 'execute', 'session': None})
        for stage in ('execute', 'review', 'needs_repair', 'complete', 'launch'):
            case('Reverify requires', stage=stage, resume_stage=None, blocker=None)
        for resume in ('launch', 'review', 'execute', 'needs_repair'):
            case('Reverify requires', resume_stage=resume)
        case('why the evidence is stale', reason='')
        case('why the evidence is stale', reason='   ')
        case('published head', stage='publishing', resume_stage=None, published_head='0' * 40)
        case('published head', stage='ci', resume_stage=None, published_head='0' * 40)
        case('published head', resume_stage='ci', published_head='0' * 40)
        case('published head', stage='ci', resume_stage=None)
        case('history revision', history_revision={'branch': 'feature', 'lease': head})
        case('leftover reverify intent', reverify_pending={'prior_stage': 'blocked', 'resume_stage': 'publish',
             'verification_run': '0' * 64, 'manifest_sha256': None})
        case('leftover reverify intent', reverify_pending={'prior_stage': 'ci', 'resume_stage': None,
             'verification_run': original['verification_run'], 'manifest_sha256': None})
        case('leftover reverify intent', reverify_pending={'prior_stage': 'blocked', 'resume_stage': 'publish',
             'verification_run': original['verification_run'], 'manifest_sha256': '0' * 64})
        case('Verification evidence unavailable', verification_run=None)
        self.state.clear(); self.state.update(copy.deepcopy(original)); self.run.save()
        load = verify.load_run
        for field in ('issue', 'plan_url', 'plan_digest', 'contract_revision'):
            with self.subTest(field=field), patch.object(verify, 'load_run',
                                                         side_effect=lambda r, i, f=field: {**load(r, i), f: 'other'}):
                self.assert_reverify_refused('another issue, plan or contract')
        self.issue['body'] += ' Changed requirement'
        self.assert_reverify_refused('.')
        self.issue['body'] = self.issue['body'].replace(' Changed requirement', '')
        os.chdir(self.source)
        self.assert_reverify_refused('bound feature')
        os.chdir(self.work)
        self.run.reverify('Eligible after all refusals')
        self.assertEqual(self.state['stage'], 'execute')

    def test_reverify_refuses_unqualified_manifest_or_other_changes_without_mutation(self):
        manifest = self.stale_publish()
        good = manifest.read_bytes()
        for content, pattern in ((b'{"version": 1, "checks": []}\n', 'does not match'), (b'{', 'not valid JSON')):
            manifest.write_bytes(content)
            with self.subTest(content=content):
                self.assert_reverify_refused(pattern)
            self.assertEqual(manifest.read_bytes(), content)
        manifest.write_bytes(good)
        extra = self.work / 'extra.txt'
        extra.write_text('user work\n')
        self.assert_reverify_refused('Source changed|Only the qualifying')
        extra.unlink()
        (self.work / 'value.txt').write_text('3\n')
        self.assert_reverify_refused('Source changed')
        (self.work / 'value.txt').write_text('2\n')
        head = self.git(self.work, 'rev-parse', 'HEAD')
        self.git(self.work, 'reset', '--soft', 'HEAD~1')
        self.assert_reverify_refused('Only the qualifying')
        self.git(self.work, 'reset', '--soft', head)
        real = manifest.with_name('real.json')
        manifest.rename(real); manifest.symlink_to('real.json')
        self.assert_reverify_refused('not a regular file')
        manifest.unlink(); real.rename(manifest)
        opencode, moved = self.work / '.opencode', self.work / 'moved-opencode'
        opencode.rename(moved); opencode.symlink_to('moved-opencode')
        self.assert_reverify_refused('not a real directory')
        opencode.unlink(); moved.rename(opencode)
        held = self.root / 'held.json'
        manifest.rename(held); manifest.parent.rmdir(); opencode.rmdir()
        self.assert_reverify_refused('No tooling staleness; use resume')
        manifest.parent.mkdir(parents=True); held.rename(manifest)
        self.run.reverify('Eligible after all refusals')
        self.assertEqual(self.state['stage'], 'execute')

    def test_reverify_refuses_tracked_manifest(self):
        self.stale_publish()
        self.git(self.work, 'add', delivery.LEGACY_MANIFEST)
        self.git(self.work, 'commit', '-m', 'Track legacy manifest')
        self.assert_reverify_refused('tracked')

    def test_reverify_refuses_source_changed_since_verification(self):
        self.stale_publish()
        (self.work / 'later.txt').write_text('later\n')
        self.git(self.work, 'add', 'later.txt')
        self.git(self.work, 'commit', '-m', 'Unreviewed change')
        self.assert_reverify_refused('Source changed since verification')

    def test_reverify_refuses_unloadable_run_or_missing_snapshot(self):
        self.stale_publish()
        run = verify.load_run(self.work, self.state['verification_run'])
        snapshot = evidence.storage(self.work) / 'snapshots' / (run['source']['snapshot_id'] + '.json')
        snapshot.rename(snapshot.with_suffix('.held'))
        self.assert_reverify_refused('Verification evidence unavailable')
        snapshot.with_suffix('.held').rename(snapshot)
        Path(run['checks'][0]['stdout_path']).unlink()
        self.assert_reverify_refused('Verification evidence unavailable')

    def test_reverify_interrupted_removal_honors_matching_intent_once(self):
        manifest = self.stale_publish()
        real = delivery.Delivery.save

        def interrupted(run, event=None):
            if event == 'tooling_reverify':
                raise OSError('Interrupted before entering execute')
            return real(run, event)
        with patch.object(delivery.Delivery, 'save', interrupted):
            with self.assertRaisesRegex(OSError, 'Interrupted'):
                self.run.reverify('Legacy manifest from retired verify init')
        saved = self.reload()
        self.assertEqual((saved['stage'], saved['resume_stage']), ('blocked', 'publish'))
        self.assertTrue(saved['reverify_pending']['manifest_sha256'])
        self.assertFalse(os.path.lexists(manifest))
        self.assertFalse(os.path.lexists(self.work / '.opencode'))
        self.run.reverify('Resume the interrupted reverify')
        self.assertEqual(self.state['stage'], 'execute')
        self.assertNotIn('reverify_pending', self.state)
        entry = self.state['tooling_reverifications'][-1]
        self.assertEqual(entry['removed_path'], delivery.LEGACY_MANIFEST)
        self.assertIn('reverify_pending', entry['removed'])
        self.assertEqual(len(self.state['tooling_reverifications']), 1)
        # The intent was cleared when entering execute: identical evidence is no longer tooling-stale.
        self.state.update(stage='blocked', resume_stage='publish', verification_run=entry['removed']['verification_run'])
        self.run.save()
        self.assert_reverify_refused('No tooling staleness; use resume')

    def test_reverify_accepts_publishing_without_published_head(self):
        self.stale_publish()
        self.state.update(stage='publishing')
        for key in ('resume_stage', 'blocker'):
            self.state.pop(key)
        self.run.save()
        self.run.reverify('Legacy manifest from retired verify init')
        self.assertEqual(self.state['stage'], 'execute')
        self.assertEqual(self.state['tooling_reverifications'][-1]['prior_stage'], 'publishing')

    def test_reverify_cli_from_another_pin_is_refused_without_mutation(self):
        self.stale_publish()
        pin = self.root / 'other-pin'
        (pin / 'tracking').mkdir(parents=True)
        (pin / 'tracking/delivery.py').write_text('# recorded helper\n')
        self.state['resource_root'] = str(pin)
        self.run.save()
        before = self.observed()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(delivery.main(['reverify', '--key', 'fixture', '--state-dir', str(self.directory.parent),
                                            '--reason', 'Legacy manifest from retired verify init']), 2)
        self.assertIn('recorded resource revision', json.loads(output.getvalue())['error'])
        self.assertEqual(self.observed(), before)

    def test_recorded_lock_prevents_concurrent_writer(self):
        with delivery.locked(self.directory):
            with self.assertRaisesRegex(RuntimeError, 'already running'):
                with delivery.locked(self.directory):
                    self.fail('Concurrent lock acquired')


if __name__ == '__main__':
    unittest.main()
