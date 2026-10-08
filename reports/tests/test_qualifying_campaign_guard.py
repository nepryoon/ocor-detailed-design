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


def test_required_guard_is_executed(tmp_path):
    path = tmp_path / 'run.xml'
    path.write_text('<testsuite tests="1"><testcase classname="tests.tasks.test_ocor_dev_0049" name="live"/></testsuite>')
    assert GUARD.check_junit(path, required_modules=['test_ocor_dev_0049'])['tests'] == 1


def test_missing_guard_cannot_be_hidden_by_other_passing_tests(tmp_path):
    path = tmp_path / 'run.xml'
    path.write_text('<testsuite tests="1"><testcase classname="tests.tasks.test_ocor_dev_0048" name="live"/></testsuite>')
    with pytest.raises(GUARD.CampaignError, match='required guard'):
        GUARD.check_junit(path, required_modules=['test_ocor_dev_0049'])


def test_candidate_head_is_bound_before_execution(tmp_path):
    import subprocess
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'test'], check=True)
    head = subprocess.check_output(['git', '-C', str(tmp_path), 'rev-parse', 'HEAD'], text=True).strip()
    GUARD.verify_revision(tmp_path, head)
    with pytest.raises(GUARD.CampaignError, match='HEAD'):
        GUARD.verify_revision(tmp_path, '0' * 40)


def test_candidate_tracked_changes_are_rejected(tmp_path):
    import subprocess
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    file = tmp_path / 'file'
    file.write_text('original')
    subprocess.run(['git', '-C', str(tmp_path), 'add', 'file'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'test'], check=True)
    head = subprocess.check_output(['git', '-C', str(tmp_path), 'rev-parse', 'HEAD'], text=True).strip()
    file.write_text('changed')
    with pytest.raises(GUARD.CampaignError, match='tracked'):
        GUARD.verify_revision(tmp_path, head)


def test_download_digest_matches_and_mismatch_fails_closed():
    import hashlib
    from provision_qualification_tools import checked_digest
    data = b'qualification-tool'
    checked_digest(data, hashlib.sha256(data).hexdigest())
    with pytest.raises(ValueError, match='checksum mismatch'):
        checked_digest(data + b'tampered', hashlib.sha256(data).hexdigest())


def test_qualification_lock_checks_are_non_mutating_and_fail_closed(tmp_path):
    import json
    from copy import deepcopy
    from provision_qualification_tools import load_lock
    lock = json.loads((Path(__file__).resolve().parents[2] / 'infra/qualification_tools.lock.json').read_text())
    (tmp_path / 'infra').mkdir()
    path = tmp_path / 'infra/qualification_tools.lock.json'
    path.write_text(json.dumps(lock))
    assert len(load_lock(tmp_path)) == 3
    assert not (tmp_path / '.ocor').exists()
    for field, value in [('source_sha256', 'wrong'), ('source', 'http://untrusted.invalid/tool'), ('archive_member', '../helm')]:
        damaged = deepcopy(lock)
        damaged['tools'][0][field] = value
        path.write_text(json.dumps(damaged))
        with pytest.raises(ValueError):
            load_lock(tmp_path)
    path.unlink()
    with pytest.raises(OSError):
        load_lock(tmp_path)


def test_fuseki_resource_validation_uses_java_not_init():
    from bootstrap_ci_environment import running_jvm_args
    assert running_jvm_args('PID COMMAND\n1 /sbin/docker-init -- /opt/fuseki/fuseki-server\n41 /opt/java/bin/java -Xms128m -Xmx1G -jar server.jar\n')[:3] == ['/opt/java/bin/java', '-Xms128m', '-Xmx1G']


@pytest.mark.parametrize('processes', [
    'COMMAND\n/sbin/docker-init -- server\n',
    'COMMAND\njava -Xms128m -Xmx4G -jar server.jar\n',
    'COMMAND\njava -Xms128m -Xmx1G -Xmx4G -jar server.jar\n',
    'COMMAND\njava -Xms128m -Xmx1G -XX:MaxHeapSize=4G -jar server.jar\n',
    'COMMAND\njava -Xms128m -Xmx1G\njava -Xms128m -Xmx1G\n',
])
def test_fuseki_unbounded_absent_or_ambiguous_jvm_fails_closed(processes):
    from bootstrap_ci_environment import running_jvm_args
    from ocor_bootstrap_lib import BootstrapError
    with pytest.raises(BootstrapError):
        running_jvm_args(processes)


@pytest.mark.parametrize("resource_kind", ["containers", "volumes", "networks"])
def test_ci_teardown_missing_credentials_with_resources_fails_closed(tmp_path, monkeypatch, resource_kind):
    import bootstrap_ci_environment as ci
    from ocor_bootstrap_lib import BootstrapError
    resources = {kind: [] for kind in ("containers", "volumes", "networks")}
    resources[resource_kind] = ["owned-resource"]
    monkeypatch.setattr(ci, "owned_resources", lambda repository: resources, raising=False)
    monkeypatch.setattr(ci, "execute", lambda *args: pytest.fail("must not mutate without credentials"))
    with pytest.raises(BootstrapError, match="credentials absent.*resources remain"):
        ci.teardown(tmp_path)


def test_ci_teardown_absent_credentials_and_no_resources_is_verified_noop(tmp_path, monkeypatch):
    import bootstrap_ci_environment as ci
    monkeypatch.setattr(ci, "owned_resources", lambda repository: {
        "containers": [], "volumes": [], "networks": []
    }, raising=False)
    monkeypatch.setattr(ci, "execute", lambda *args: pytest.fail("empty stack must not call Compose"))
    assert ci.teardown(tmp_path) == {"status": "PASS", "operation": "teardown", "result": "ALREADY_REMOVED",
                                    "residual": {"containers": [], "volumes": [], "networks": []}}


def test_ci_teardown_inventory_failure_is_not_an_empty_stack(tmp_path, monkeypatch):
    import bootstrap_ci_environment as ci
    from ocor_bootstrap_lib import BootstrapError
    def fail(*args):
        raise BootstrapError("docker inventory failed")
    monkeypatch.setattr(ci, "execute", fail)
    with pytest.raises(BootstrapError, match="docker inventory failed"):
        ci.teardown(tmp_path)


def test_ci_teardown_existing_credentials_runs_governed_reset_and_checks_residue(tmp_path, monkeypatch):
    import bootstrap_ci_environment as ci
    (tmp_path / ".ocor").mkdir()
    (tmp_path / ".ocor/bootstrap.env").touch()
    calls = []
    monkeypatch.setattr(ci, "execute", lambda *args: calls.append(args) or "")
    monkeypatch.setattr(ci, "owned_resources", lambda repository: {
        "containers": [], "volumes": [], "networks": []
    }, raising=False)
    assert ci.teardown(tmp_path)["result"] == "REMOVED"
    assert calls[0][1] == [sys.executable, "scripts/reset_test_environment.py", "--execute"]
    assert calls[0][3] == 180


def test_ci_teardown_residual_resources_are_a_failure(tmp_path, monkeypatch):
    import bootstrap_ci_environment as ci
    from ocor_bootstrap_lib import BootstrapError
    (tmp_path / ".ocor").mkdir()
    (tmp_path / ".ocor/bootstrap.env").touch()
    monkeypatch.setattr(ci, "execute", lambda *args: "")
    monkeypatch.setattr(ci, "owned_resources", lambda repository: {
        "containers": [], "volumes": ["residue"], "networks": []
    }, raising=False)
    with pytest.raises(BootstrapError, match="resources remain after teardown"):
        ci.teardown(tmp_path)


@pytest.mark.parametrize("exit_code", [0, 4])
def test_build_log_survives_success_and_nonzero_exit(tmp_path, exit_code):
    import bootstrap_ci_environment as ci
    from ocor_bootstrap_lib import BootstrapError
    (tmp_path / "reports/tests").mkdir(parents=True)
    command = [sys.executable, "-c", f"import sys; print('locked recipe step', flush=True); sys.exit({exit_code})"]
    if exit_code:
        with pytest.raises(BootstrapError, match="build failed"):
            ci.execute_logged(tmp_path, command, "build", 5, "ci_fuseki_build.log")
    else:
        ci.execute_logged(tmp_path, command, "build", 5, "ci_fuseki_build.log")
    assert (tmp_path / "reports/tests/ci_fuseki_build.log").read_text() == "locked recipe step\n"


def test_build_timeout_retains_last_step_and_fails_closed(tmp_path):
    import bootstrap_ci_environment as ci
    from ocor_bootstrap_lib import BootstrapError
    (tmp_path / "reports/tests").mkdir(parents=True)
    command = [sys.executable, "-c", "import time; print('downloading pinned archive', flush=True); time.sleep(10)"]
    with pytest.raises(BootstrapError, match="timeout after 1s.*build"):
        ci.execute_logged(tmp_path, command, "build", 1, "ci_fuseki_build.log")
    assert "downloading pinned archive" in (tmp_path / "reports/tests/ci_fuseki_build.log").read_text()


def test_full_suite_budget_is_75_minutes_and_60_minutes_requires_decision():
    assert GUARD.check_deadline(3599) is False
    assert GUARD.check_deadline(3601) is True
    assert GUARD.check_deadline(4499) is True
    with pytest.raises(GUARD.CampaignError, match="75-minute"):
        GUARD.check_deadline(4500)


def test_teardown_exports_exact_residue_even_when_reset_fails(tmp_path, monkeypatch, capsys):
    import json
    import bootstrap_ci_environment as ci
    from ocor_bootstrap_lib import BootstrapError
    (tmp_path / ".ocor").mkdir()
    (tmp_path / ".ocor/bootstrap.env").touch()
    residue = {"containers": [], "volumes": ["owned-volume"], "networks": ["owned-network"]}
    monkeypatch.setattr(ci, "owned_resources", lambda repository: residue)
    def fail(*args):
        raise BootstrapError("governed reset failed")
    monkeypatch.setattr(ci, "execute", fail)
    with pytest.raises(BootstrapError):
        ci.teardown(tmp_path)
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert records[-1]["residual"] == residue
    assert records[-1]["status"] == "FAIL"


def test_session_volume_attribution_does_not_depend_on_event_order():
    import bootstrap_ci_environment as ci
    events = [
        {"Type": "volume", "Action": "mount", "Actor": {"ID": "owned-volume", "Attributes": {"container": "test-id"}}},
        {"Type": "volume", "Action": "mount", "Actor": {"ID": "foreign-volume", "Attributes": {"container": "foreign-id"}}},
        {"Type": "container", "Action": "create", "Actor": {"ID": "test-id", "Attributes": {"name": "ocor-spike-0023-session"}}},
        {"Type": "container", "Action": "create", "Actor": {"ID": "foreign-id", "Attributes": {"name": "open-webui"}}},
    ]
    assert ci.session_resources(events) == {"containers": {"test-id": "ocor-spike-0023-session"}, "volumes": ["owned-volume"], "networks": {}}
    assert ci.session_resources(list(reversed(events))) == ci.session_resources(events)


def test_preexisting_volume_is_not_deleted_by_session_cleanup(tmp_path, monkeypatch):
    import bootstrap_ci_environment as ci
    (tmp_path / ".ocor").mkdir()
    import json
    record = {"repository": str(tmp_path.resolve()), "before_volumes": ["preexisting"],
              "resources": {"containers": {}, "volumes": ["preexisting", "created"]}}
    (tmp_path / ".ocor/campaign-resources.json").write_text(json.dumps(record))
    calls = []
    monkeypatch.setattr(ci, "execute", lambda repo, cmd, label, timeout: calls.append(cmd) or "")
    monkeypatch.setattr(ci, "session_inventory", lambda repository: {"containers": {}, "volumes": ["preexisting", "created"]} if not calls else {"containers": {}, "volumes": ["preexisting"]})
    ci.cleanup_session_resources(tmp_path)
    assert calls == [["docker", "volume", "rm", "created"]]


def test_failed_session_volume_removal_preserves_error(tmp_path, monkeypatch):
    import bootstrap_ci_environment as ci
    from ocor_bootstrap_lib import BootstrapError
    import json
    (tmp_path / ".ocor").mkdir()
    (tmp_path / ".ocor/campaign-resources.json").write_text(json.dumps({
        "repository": str(tmp_path.resolve()), "before_volumes": [],
        "resources": {"containers": {}, "volumes": ["created"]}}))
    monkeypatch.setattr(ci, "session_inventory", lambda repository: {"containers": {}, "volumes": ["created"]})
    monkeypatch.setattr(ci, "execute", lambda *args: "")
    with pytest.raises(BootstrapError, match="session resources remain"):
        ci.cleanup_session_resources(tmp_path)


def stub_completed_campaign(tmp_path, monkeypatch, *, seconds, recorder_error=False):
    import json
    import bootstrap_ci_environment as ci
    (tmp_path / "scripts").mkdir()
    (tmp_path / ".ocor").mkdir()
    (tmp_path / ".ocor/bootstrap.env").write_text("OCOR_LOCAL_POSTGRES_PASSWORD=unit-private-value\n")
    output = tmp_path / "run"
    monkeypatch.setattr(GUARD, "__file__", str(tmp_path / "scripts/campaign.py"))
    monkeypatch.setattr(sys, "argv", ["campaign.py", "--execute", "--output-dir", str(output)])
    snapshot = {str(n): state() for n in range(11)}
    monkeypatch.setattr(GUARD, "inspect_stack", lambda: snapshot)
    ticks = iter([0, seconds, seconds, seconds])
    monkeypatch.setattr(GUARD.time, "monotonic", lambda: next(ticks))
    class Recorder:
        def __init__(self, repository):
            pass
        def finish(self):
            if recorder_error:
                raise ci.BootstrapError("event capture failed")
    class Process:
        returncode = 0
        def poll(self):
            return 0
    def launch(*args, stdout, **kwargs):
        stdout.write("unit-private-value; 1 passed\n")
        (output / "runtime_junit_post_approval.xml").write_text('<testsuite tests="1"><testcase classname="tests.tasks.test_ocor_dev_0048"/></testsuite>')
        return Process()
    monkeypatch.setattr(GUARD, "SessionRecorder", Recorder)
    monkeypatch.setattr(GUARD.subprocess, "Popen", launch)
    monkeypatch.setattr(GUARD, "collect_stack_diagnostics", lambda *args: None)
    return output, json


def test_completed_process_after_deadline_is_still_rejected(tmp_path, monkeypatch):
    output, json = stub_completed_campaign(tmp_path, monkeypatch, seconds=4501)
    assert GUARD.main() == 1
    assert "75-minute" in json.loads((output / "campaign_result.json").read_text())["error"]


def test_event_capture_failure_is_fail_closed_and_logs_are_still_redacted(tmp_path, monkeypatch):
    output, json = stub_completed_campaign(tmp_path, monkeypatch, seconds=1, recorder_error=True)
    assert GUARD.main() == 1
    assert json.loads((output / "campaign_result.json").read_text())["status"] == "FAIL"
    assert "unit-private-value" not in (output / "post_remediation_runtime.log").read_text()


@pytest.mark.parametrize("event", [
    {"Type": "container", "Action": "create", "Actor": None},
    {"Type": "container", "Action": "create", "Actor": {"ID": "id", "Attributes": {"name": None}}},
    {"Type": "volume", "Action": "mount", "Actor": {"ID": "volume", "Attributes": {}}},
])
def test_malformed_ownership_event_cannot_silently_lose_attribution(event):
    import json
    from types import SimpleNamespace
    import bootstrap_ci_environment as ci
    recorder = ci.SessionRecorder.__new__(ci.SessionRecorder)
    recorder.process = SimpleNamespace(stdout=iter([json.dumps(event) + "\n"]))
    recorder.events = []
    recorder.errors = []
    recorder.observe()
    assert recorder.errors
