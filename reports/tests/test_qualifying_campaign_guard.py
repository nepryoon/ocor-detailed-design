"""Fail-closed regression controls for the real-stack campaign supervisor."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
SPEC = importlib.util.spec_from_file_location('ocor_campaign_guard', Path(__file__).resolve().parents[2] / 'scripts/run_qualifying_campaign.py')
assert SPEC is not None and SPEC.loader is not None
GUARD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GUARD
SPEC.loader.exec_module(GUARD)


def state(*, running=True, oom=False, restarts=0, identity='abc'):
    return {'Id': identity, 'RestartCount': restarts, 'State': {'Running': running, 'OOMKilled': oom}}


def test_running_same_incarnation_is_accepted():
    GUARD.check_stack({'service': state()}, {'service': state()})


@pytest.mark.parametrize('current', [{}, {'service': state(running=False)}, {'service': state(oom=True)}, {'service': state(restarts=1)}, {'service': state(identity='other')}])
def test_loss_oom_restart_or_replacement_is_rejected(current):
    with pytest.raises(GUARD.CampaignError):
        GUARD.check_stack({'service': state()}, current)


def test_empty_stack_is_not_qualifying():
    with pytest.raises(GUARD.CampaignError):
        GUARD.check_stack({}, {})


def test_zero_skip_junit_is_accepted(tmp_path):
    path = tmp_path / 'run.xml'
    path.write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase name="positive"/></testsuite></testsuites>')
    assert GUARD.check_junit(path)['skipped'] == 0


@pytest.mark.parametrize('xml', ['<testsuites/>', '<testsuite tests="1" failures="1"/>', '<testsuite tests="1" skipped="1"/>', '<testsuite tests="1"><testcase><skipped/></testcase></testsuite>', 'invalid'])
def test_nonqualifying_junit_is_rejected(tmp_path, xml):
    path = tmp_path / 'run.xml'
    path.write_text(xml)
    with pytest.raises(GUARD.CampaignError):
        GUARD.check_junit(path)


def test_missing_junit_is_rejected(tmp_path):
    with pytest.raises(GUARD.CampaignError):
        GUARD.check_junit(tmp_path / 'missing.xml')


def test_manual_restart_is_rejected_even_without_restart_counter_change():
    before = state()
    before['State']['StartedAt'] = '2026-10-07T02:00:00Z'
    after = state()
    after['State']['StartedAt'] = '2026-10-07T02:00:05Z'
    with pytest.raises(GUARD.CampaignError):
        GUARD.check_stack({'service': before}, {'service': after})


def test_credential_redaction_preserves_failure_and_counts():
    from bootstrap_ci_environment import redact
    assert redact('FAIL: secret-token; 1 failed, 0 skipped', ['secret-token']) == 'FAIL: [REDACTED]; 1 failed, 0 skipped'


def test_pem_redaction_removes_key_material():
    from bootstrap_ci_environment import redact
    begin = '-'.join(['-----BEGIN PRIVATE KEY', '----'])
    end = '-'.join(['-----END PRIVATE KEY', '----'])
    assert 'private-data' not in redact(begin + '\nprivate-data\n' + end, [])
