#!/usr/bin/env python3
"""Fail-closed, resumable dispatcher for the approved OCOR development backlog.

The default operation is read-only. Mutating preparation, agent execution, remote
push, pull-request creation, and merge all require ``--execute`` plus their
specific opt-in flags. The runner never derives runtime-conformance claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


TASK_ID = re.compile(r"^OCOR-DEV-[0-9]{4}$")
TERMINAL_SUCCESS = {"ACCEPTED"}
ACTIVE = {"PREPARED", "RUNNING", "VALIDATING"}
FAILURE = {"FAILED_IMPLEMENTATION", "BLOCKED_INFRASTRUCTURE", "BLOCKED_CI"}
FORBIDDEN_RESULT = {"SKIPPED", "UNAVAILABLE", "NOT_EXECUTED", "XFAIL"}
IMMUTABLE_PATHS = (
    "inputs/",
    "docs/OCOR_LLD_v1.1.md",
    "ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.3_APPROVED_BASELINE.md",
)


class DeliveryError(RuntimeError):
    """A fail-closed delivery control rejected an operation."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def repository_root(start: Path | None = None) -> Path:
    probe = start or Path(__file__).resolve().parent
    result = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise DeliveryError(f"not a Git worktree: {probe}")
    return Path(result.stdout.strip()).resolve()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DeliveryError(f"expected a JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    temporary.replace(path)


def path_overlap(left: str, right: str) -> bool:
    a = left.rstrip("/")
    b = right.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def status_is_qualifying(value: str) -> bool:
    return value == "PASS"


def ci_is_green(checks: Sequence[dict[str, Any]], required: Iterable[str]) -> tuple[bool, str]:
    indexed = {str(item.get("name")): item for item in checks}
    for context in required:
        check = indexed.get(context)
        if check is None:
            return False, f"required check absent: {context}"
        status = str(check.get("status", "")).upper()
        conclusion = str(check.get("conclusion", "")).upper()
        if status != "COMPLETED" or conclusion != "SUCCESS":
            return False, f"required check is red or incomplete: {context}"
    return True, "all required checks are green"


def evidence_qualifies(root: Path, task: dict[str, Any]) -> tuple[bool, str]:
    manifest_path = root / "reports/evidence" / task["delivery_gate"] / "MANIFEST.json"
    try:
        manifest = load_json(manifest_path)
        entry = next(
            item for item in manifest.get("artifacts", []) if item.get("task_id") == task["id"]
        )
        evidence_path = manifest_path.parent / entry["path"]
        if sha256_file(evidence_path) != entry["sha256"]:
            return False, "evidence digest mismatch"
        record = load_json(evidence_path)
        raw_entry = next(
            item
            for item in manifest.get("artifacts", [])
            if item.get("task_id") == f"{task['id']}-RAW"
        )
        raw_path = manifest_path.parent / raw_entry["path"]
        raw_digest = sha256_file(raw_path)
        if raw_digest != raw_entry["sha256"] or raw_digest != record.get("raw_output_sha256"):
            return False, "raw evidence digest mismatch"
        statuses = {str(item.get("status", "")).upper() for item in record.get("commands", [])}
        if not statuses or statuses != {"PASS"} or statuses & FORBIDDEN_RESULT:
            return False, f"non-qualifying command statuses: {sorted(statuses)}"
        if record.get("result") != "PASS" or record.get("task_id") != task["id"]:
            return False, "evidence identity or result mismatch"
        return True, str(record.get("commit", ""))
    except (DeliveryError, KeyError, StopIteration, OSError) as exc:
        return False, str(exc)


@dataclass(frozen=True)
class Plan:
    root: Path
    backlog: dict[str, Any]
    context: dict[str, Any]
    config: dict[str, Any]
    tasks: dict[str, dict[str, Any]]
    dag_nodes: set[str]
    dag_edges: set[tuple[str, str]]

    @classmethod
    def load(cls, root: Path) -> "Plan":
        development = root / "docs/development_plan"
        backlog_path = development / "OCOR_IMPLEMENTATION_BACKLOG.json"
        schema_path = development / "OCOR_IMPLEMENTATION_BACKLOG.schema.json"
        context_path = development / "OCOR_AGENT_CONTEXT_MANIFEST.json"
        dag_path = development / "OCOR_DEPENDENCY_DAG.mmd"
        config_path = development / "OCOR_DELIVERY_RUNNER_CONFIG.json"
        backlog = load_json(backlog_path)
        schema = load_json(schema_path)
        try:
            import jsonschema

            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(schema).validate(backlog)
        except ImportError as exc:
            raise DeliveryError("jsonschema is required to validate the backlog") from exc
        except Exception as exc:  # jsonschema exposes several validation subclasses
            raise DeliveryError(f"backlog schema validation failed: {exc}") from exc

        context = load_json(context_path)
        config = load_json(config_path)
        raw_tasks = backlog.get("tasks", [])
        tasks = {str(item.get("id")): item for item in raw_tasks}
        nodes, edges = parse_mermaid(dag_path.read_text(encoding="utf-8"))
        return cls(root, backlog, context, config, tasks, nodes, edges)

    def validate(self) -> list[str]:
        errors: list[str] = []
        raw_tasks = self.backlog.get("tasks", [])
        task_ids = [str(task.get("id", "")) for task in raw_tasks]
        if len(task_ids) != len(set(task_ids)):
            errors.append("duplicate task identifier")
        if any(not TASK_ID.fullmatch(item) for item in task_ids):
            errors.append("invalid task identifier")
        for task_id, task in self.tasks.items():
            for dependency in task.get("hard_dependencies", []) + task.get("soft_dependencies", []):
                if dependency not in self.tasks:
                    errors.append(f"{task_id}: unknown dependency {dependency}")
            for prohibited in task.get("prohibited_file_areas", []):
                if not isinstance(prohibited, str):
                    errors.append(f"{task_id}: non-string prohibited path")
            if not task.get("validation_commands"):
                errors.append(f"{task_id}: no validation command")
            if not task.get("evidence_outputs"):
                errors.append(f"{task_id}: no evidence output")
        try:
            topological_order(self.tasks)
        except DeliveryError as exc:
            errors.append(str(exc))
        context_ids = {str(item.get("task_id")) for item in self.context.get("tasks", [])}
        if context_ids != set(task_ids):
            errors.append("context manifest task universe differs from backlog")
        if self.dag_nodes != set(task_ids):
            errors.append("Mermaid node universe differs from backlog")
        for task_id, task in self.tasks.items():
            for dependency in task.get("hard_dependencies", []):
                if (dependency, task_id) not in self.dag_edges:
                    errors.append(f"Mermaid DAG lacks hard edge {dependency}->{task_id}")
        if int(self.config.get("max_retries", -1)) not in range(0, 4):
            errors.append("max_retries must be between zero and three")
        if int(self.config.get("max_parallel", 0)) < 1:
            errors.append("max_parallel must be positive")
        return errors

    def context_for(self, task_id: str) -> dict[str, Any]:
        for item in self.context.get("tasks", []):
            if item.get("task_id") == task_id:
                return item
        raise DeliveryError(f"no context manifest entry for {task_id}")


def parse_mermaid(content: str) -> tuple[set[str], set[tuple[str, str]]]:
    nodes: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for match in re.finditer(r"OCOR_DEV_(\d{4})\[", content):
        nodes.add(f"OCOR-DEV-{match.group(1)}")
    for match in re.finditer(r"OCOR_DEV_(\d{4})\s*-->\s*OCOR_DEV_(\d{4})", content):
        edges.add((f"OCOR-DEV-{match.group(1)}", f"OCOR-DEV-{match.group(2)}"))
    return nodes, edges


def topological_order(tasks: dict[str, dict[str, Any]]) -> list[str]:
    incoming = {
        task_id: set(task.get("hard_dependencies", [])) | set(task.get("soft_dependencies", []))
        for task_id, task in tasks.items()
    }
    ready = sorted(task_id for task_id, dependencies in incoming.items() if not dependencies)
    result: list[str] = []
    while ready:
        task_id = ready.pop(0)
        result.append(task_id)
        for successor in sorted(incoming):
            if task_id in incoming[successor]:
                incoming[successor].remove(task_id)
                if not incoming[successor] and successor not in result and successor not in ready:
                    ready.append(successor)
                    ready.sort()
    if len(result) != len(tasks):
        cyclic = sorted(task_id for task_id, dependencies in incoming.items() if dependencies)
        raise DeliveryError(f"dependency graph contains a cycle: {', '.join(cyclic)}")
    return result


def new_state(plan: Plan) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "integration_commit": git_output(plan.root, "rev-parse", "HEAD"),
        "emergency_stop": False,
        "stop_reason": None,
        "tasks": {task_id: {"status": "PENDING", "retries": 0} for task_id in plan.tasks},
        "ownership_locks": {},
        "history": [],
    }


def validate_state(plan: Plan, state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(state.get("tasks", {})) != set(plan.tasks):
        errors.append("state task universe differs from backlog")
    for task_id, value in state.get("tasks", {}).items():
        status = str(value.get("status", ""))
        if status in FORBIDDEN_RESULT:
            errors.append(f"{task_id}: forbidden promoted status {status}")
        if status not in {"PENDING", "PREPARED", "RUNNING", "VALIDATING", "ACCEPTED"} | FAILURE:
            errors.append(f"{task_id}: invalid state {status}")
        if int(value.get("retries", 0)) > int(plan.config["max_retries"]):
            errors.append(f"{task_id}: retry budget exceeded")
    locks = state.get("ownership_locks", {})
    lock_items = list(locks.items())
    for index, (left_task, left_paths) in enumerate(lock_items):
        for right_task, right_paths in lock_items[index + 1 :]:
            if any(path_overlap(a, b) for a in left_paths for b in right_paths):
                errors.append(f"file ownership collision: {left_task}/{right_task}")
    return errors


def recover_interrupted(state: dict[str, Any], max_retries: int = 2) -> list[str]:
    recovered: list[str] = []
    for task_id, value in state.get("tasks", {}).items():
        status = value.get("status")
        retryable_failure = status in FAILURE and int(value.get("retries", 0)) < max_retries
        if status in ACTIVE or retryable_failure:
            value["status"] = "PENDING"
            value["last_error"] = "recovered after interrupted runner"
            recovered.append(task_id)
    for task_id in recovered:
        state.get("ownership_locks", {}).pop(task_id, None)
    return recovered


def ready_tasks(plan: Plan, state: dict[str, Any]) -> list[dict[str, Any]]:
    if state.get("emergency_stop"):
        return []
    active_paths = [
        path
        for task_id, paths in state.get("ownership_locks", {}).items()
        if state["tasks"].get(task_id, {}).get("status") in ACTIVE
        for path in paths
    ]
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for task_id, task in plan.tasks.items():
        if state["tasks"][task_id]["status"] != "PENDING":
            continue
        gate_number = int(str(task.get("delivery_gate", "G0"))[1:])
        earlier_gate_open = any(
            int(str(other.get("delivery_gate", "G0"))[1:]) < gate_number
            and state["tasks"][other_id]["status"] not in TERMINAL_SUCCESS
            for other_id, other in plan.tasks.items()
        )
        if earlier_gate_open:
            continue
        hard = task.get("hard_dependencies", [])
        if any(state["tasks"][dependency]["status"] not in TERMINAL_SUCCESS for dependency in hard):
            continue
        paths = task.get("expected_file_areas", [])
        if any(path_overlap(path, held) for path in paths for held in active_paths):
            continue
        missing_soft = sum(
            state["tasks"][dependency]["status"] not in TERMINAL_SUCCESS
            for dependency in task.get("soft_dependencies", [])
        )
        candidates.append((missing_soft, int(task.get("parallel_wave", 0)), task_id, task))
    return [item[3] for item in sorted(candidates)]


def parallel_selection(tasks: Sequence[dict[str, Any]], maximum: int) -> list[dict[str, Any]]:
    """Select a collision-free prefix without assigning one file area twice."""
    selected: list[dict[str, Any]] = []
    owned: list[str] = []
    for task in tasks:
        paths = task.get("expected_file_areas", [])
        if any(path_overlap(path, held) for path in paths for held in owned):
            continue
        selected.append(task)
        owned.extend(paths)
        if len(selected) == maximum:
            break
    return selected


def acquire_ownership(plan: Plan, state: dict[str, Any], task_id: str) -> None:
    paths = plan.tasks[task_id].get("expected_file_areas", [])
    for owner, held in state.get("ownership_locks", {}).items():
        if owner == task_id:
            continue
        if any(path_overlap(path, locked) for path in paths for locked in held):
            raise DeliveryError(f"file ownership collision with {owner}")
    state.setdefault("ownership_locks", {})[task_id] = paths


def git_output(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise DeliveryError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def safe_command(command: str) -> list[str]:
    if re.search(r"[|;&<>`$\n]", command):
        raise DeliveryError(f"unsafe validation command rejected: {command}")
    arguments = shlex.split(command)
    if not arguments:
        raise DeliveryError("empty validation command")
    return arguments


def prepare_worktree(plan: Plan, task: dict[str, Any]) -> Path:
    task_id = task["id"]
    slug = re.sub(r"[^a-z0-9]+", "-", task["title"].lower()).strip("-")[:48]
    branch = f"{plan.config['task_branch_prefix']}{task_id}-{slug}"
    target = plan.root / plan.config["worktree_path"] / task_id
    if target.exists():
        if git_output(target, "status", "--porcelain"):
            raise DeliveryError(f"existing task worktree is dirty: {target}")
        return target
    if subprocess.run(
        ["git", "-C", str(plan.root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
    ).returncode == 0:
        raise DeliveryError(f"task branch exists without resumable worktree: {branch}")
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "-C", str(plan.root), "worktree", "add", "-b", branch, str(target), "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise DeliveryError(result.stderr.strip() or "worktree creation failed")
    return target


def bounded_prompt(plan: Plan, task: dict[str, Any]) -> str:
    context = plan.context_for(task["id"])
    payload = {
        "task": task,
        "context": context,
        "constraints": [
            "Read every applicable AGENTS.md before editing.",
            "Do not modify inputs or approved ADD/LLD baselines.",
            "Implement exactly this task; do not start a later task.",
            "Do not claim E1, E2, PoC-GO, runtime conformance, or Production readiness.",
            "Fail loudly on missing preconditions and do not promote skipped or unavailable tests.",
        ],
    }
    rendered = json.dumps(payload, indent=2)
    approximate_tokens = max(1, len(rendered) // 4)
    if approximate_tokens > int(context["max_input_tokens"]):
        raise DeliveryError(f"context pack exceeds bound for {task['id']}")
    return "Execute this single OCOR task under repository governance:\n" + rendered


def classify_failure(stderr: str) -> str:
    lowered = stderr.lower()
    infrastructure = ("authentication", "permission denied", "network", "unavailable", "timeout")
    return "BLOCKED_INFRASTRUCTURE" if any(item in lowered for item in infrastructure) else "FAILED_IMPLEMENTATION"


def run_validation_commands(worktree: Path, task: dict[str, Any], log) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in task.get("validation_commands", []):
        arguments = safe_command(command)
        if arguments[:2] == ["uv", "run"]:
            arguments[2:2] = ["--project", "ocor-runtime", "--frozen"]
        started = utc_now()
        result = subprocess.run(
            arguments,
            cwd=worktree,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            env={**os.environ, "PYTHONHASHSEED": "0", "TZ": "UTC"},
        )
        log.write(f"$ {shlex.join(arguments)}\n{result.stdout}\n")
        results.append(
            {
                "command": shlex.join(arguments),
                "started_at": started,
                "completed_at": utc_now(),
                "exit_code": result.returncode,
                "status": "PASS" if result.returncode == 0 else "FAIL",
            }
        )
        if result.returncode:
            break
    return results


def emit_evidence(
    plan: Plan,
    task: dict[str, Any],
    worktree: Path,
    command_results: list[dict[str, Any]],
    log_path: Path,
    evaluated_commit: str,
) -> None:
    if not command_results or any(not status_is_qualifying(item["status"]) for item in command_results):
        raise DeliveryError("mandatory validation is not fully PASS")
    outputs = task["evidence_outputs"]
    json_output = next((item for item in outputs if item.endswith(".json")), None)
    named_log = next((item for item in outputs if item.endswith(".log")), None)
    if not json_output or not named_log:
        raise DeliveryError("task evidence must name JSON and log outputs")
    target_log = worktree / named_log
    target_log.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(log_path, target_log)
    evidence = {
        "schema_version": "1.0",
        "task_id": task["id"],
        "commit": evaluated_commit,
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
        },
        "commands": command_results,
        "result": "PASS",
        "prohibited_claims": "No runtime conformance, E1, E2, PoC-GO, or Production readiness claim.",
        "raw_output_sha256": sha256_file(target_log),
        "created_at": utc_now(),
    }
    atomic_json(worktree / json_output, evidence)


def changed_task_paths(worktree: Path) -> list[str]:
    output = git_output(worktree, "status", "--porcelain")
    result: list[str] = []
    for line in output.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        result.append(path)
    return result


def enforce_task_scope(task: dict[str, Any], paths: Sequence[str]) -> None:
    allowed = list(task.get("expected_file_areas", [])) + list(task.get("evidence_outputs", []))
    for path in paths:
        if any(path == item.rstrip("/") or path.startswith(item.rstrip("/") + "/") for item in IMMUTABLE_PATHS):
            raise DeliveryError(f"immutable path changed: {path}")
        if not any(path == item.rstrip("/") or path.startswith(item.rstrip("/") + "/") for item in allowed):
            raise DeliveryError(f"task changed an unowned path: {path}")


def commit_task(worktree: Path, task: dict[str, Any]) -> str:
    paths = changed_task_paths(worktree)
    enforce_task_scope(task, paths)
    if not paths:
        raise DeliveryError("task produced no change")
    subprocess.run(["git", "-C", str(worktree), "add", "--", *paths], check=True)
    result = subprocess.run(
        ["git", "-C", str(worktree), "commit", "-m", f"feat(delivery): complete {task['id']}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise DeliveryError(result.stderr.strip() or "task commit failed")
    return git_output(worktree, "rev-parse", "HEAD")


def commit_implementation(worktree: Path, task: dict[str, Any], base_commit: str) -> str:
    """Seal implementation before validation so evidence names exact tested bytes."""
    paths = changed_task_paths(worktree)
    if paths:
        allowed = list(task.get("expected_file_areas", []))
        for path in paths:
            if any(path == item.rstrip("/") or path.startswith(item.rstrip("/") + "/") for item in IMMUTABLE_PATHS):
                raise DeliveryError(f"immutable path changed: {path}")
            if not any(path == item.rstrip("/") or path.startswith(item.rstrip("/") + "/") for item in allowed):
                raise DeliveryError(f"task changed an unowned implementation path: {path}")
        subprocess.run(["git", "-C", str(worktree), "add", "--", *paths], check=True)
        result = subprocess.run(
            ["git", "-C", str(worktree), "commit", "-m", f"feat(task): implement {task['id']}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise DeliveryError(result.stderr.strip() or "implementation commit failed")
    head = git_output(worktree, "rev-parse", "HEAD")
    if head == base_commit:
        raise DeliveryError("agent produced no implementation commit")
    committed = git_output(worktree, "diff", "--name-only", f"{base_commit}..{head}").splitlines()
    enforce_task_scope(task, committed)
    return head


def gh_json(worktree: Path, arguments: Sequence[str]) -> Any:
    result = subprocess.run(
        ["gh", *arguments], cwd=worktree, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise DeliveryError(result.stderr.strip() or "GitHub operation failed")
    try:
        return json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError as exc:
        raise DeliveryError("GitHub operation returned invalid JSON") from exc


def remote_delivery(plan: Plan, worktree: Path, task: dict[str, Any], args: Any) -> None:
    """Perform explicitly enabled push/PR/merge operations without bypasses."""
    branch = git_output(worktree, "branch", "--show-current")
    head = git_output(worktree, "rev-parse", "HEAD")
    remote = str(plan.config["remote"])
    if args.push:
        if not plan.config.get("allow_push"):
            raise DeliveryError("push is disabled by delivery configuration")
        result = subprocess.run(
            ["git", "-C", str(worktree), "push", "--set-upstream", remote, branch],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise DeliveryError(result.stderr.strip() or "push failed")
    if args.open_pr:
        if not plan.config.get("allow_pull_request"):
            raise DeliveryError("pull-request creation is disabled by delivery configuration")
        existing = subprocess.run(
            ["gh", "pr", "view", branch, "--json", "url"],
            cwd=worktree,
            capture_output=True,
            text=True,
            check=False,
        )
        if existing.returncode:
            created = subprocess.run(
                [
                    "gh", "pr", "create", "--base", str(plan.config["integration_branch"]),
                    "--head", branch, "--title", f"{task['id']}: {task['title']}",
                    "--body", f"Autonomous delivery for {task['id']}. Runtime and readiness claims are not made.",
                ],
                cwd=worktree,
                capture_output=True,
                text=True,
                check=False,
            )
            if created.returncode:
                raise DeliveryError(created.stderr.strip() or "pull-request creation failed")
    if args.merge:
        if not plan.config.get("allow_merge"):
            raise DeliveryError("merge is disabled by delivery configuration")
        repository = gh_json(worktree, ["repo", "view", "--json", "nameWithOwner"])["nameWithOwner"]
        protection = gh_json(
            worktree,
            ["api", f"repos/{repository}/branches/{plan.config['integration_branch']}"],
        )
        if plan.config.get("require_branch_protection_for_merge") and not protection.get("protected"):
            raise DeliveryError("integration branch protection is not effective")
        pr = gh_json(
            worktree,
            [
                "pr", "view", branch, "--json",
                "headRefOid,mergeable,statusCheckRollup,number",
            ],
        )
        if pr["headRefOid"] != head or pr["mergeable"] != "MERGEABLE":
            raise DeliveryError("pull request head or mergeability changed")
        checks = [
            {
                "name": item.get("name") or item.get("context"),
                "status": item.get("status"),
                "conclusion": item.get("conclusion"),
            }
            for item in pr.get("statusCheckRollup", [])
        ]
        green, reason = ci_is_green(checks, plan.config["mandatory_check_contexts"])
        if not green:
            raise DeliveryError(reason)
        result = subprocess.run(
            ["gh", "pr", "merge", str(pr["number"]), "--merge", "--match-head-commit", head],
            cwd=worktree,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise DeliveryError(result.stderr.strip() or "merge failed")


def execute_task(plan: Plan, state: dict[str, Any], task: dict[str, Any], args) -> None:
    task_id = task["id"]
    if state.get("emergency_stop"):
        raise DeliveryError("emergency stop is active")
    acquire_ownership(plan, state, task_id)
    state["tasks"][task_id]["status"] = "PREPARED"
    worktree = prepare_worktree(plan, task)
    log_dir = plan.root / plan.config["log_path"] / task_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"attempt-{state['tasks'][task_id]['retries'] + 1}.log"
    state["tasks"][task_id]["worktree"] = str(worktree)
    state["updated_at"] = utc_now()
    atomic_json(args.state, state)
    prompt = bounded_prompt(plan, task)
    state["tasks"][task_id]["status"] = "RUNNING"
    atomic_json(args.state, state)
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.run(
            ["codex", "--yolo", "exec", "-"],
            input=prompt,
            cwd=worktree,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            env=os.environ.copy(),
        )
        if process.returncode:
            log.flush()
            state["tasks"][task_id]["retries"] += 1
            state["tasks"][task_id]["status"] = classify_failure(log_path.read_text(errors="replace"))
            atomic_json(args.state, state)
            raise DeliveryError(f"agent failed for {task_id}; see {log_path}")
        evaluated_commit = commit_implementation(
            worktree, task, state["integration_commit"]
        )
        state["tasks"][task_id]["status"] = "VALIDATING"
        atomic_json(args.state, state)
        command_results = run_validation_commands(worktree, task, log)
    if any(item["status"] != "PASS" for item in command_results):
        state["tasks"][task_id]["retries"] += 1
        state["tasks"][task_id]["status"] = "FAILED_IMPLEMENTATION"
        atomic_json(args.state, state)
        raise DeliveryError(f"validation failed for {task_id}")
    emit_evidence(plan, task, worktree, command_results, log_path, evaluated_commit)
    accepted_commit = commit_task(worktree, task)
    remote_delivery(plan, worktree, task, args)
    state["tasks"][task_id]["status"] = "ACCEPTED"
    state["tasks"][task_id]["accepted_commit"] = accepted_commit
    state["ownership_locks"].pop(task_id, None)
    state["history"].append({"task_id": task_id, "event": "ACCEPTED", "at": utc_now()})
    state["updated_at"] = utc_now()
    atomic_json(args.state, state)


def summarize(plan: Plan, state: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in state["tasks"].values():
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    ready = ready_tasks(plan, state)
    return {
        "run_id": state["run_id"],
        "integration_commit": state["integration_commit"],
        "emergency_stop": state["emergency_stop"],
        "status_counts": counts,
        "dependency_ready": [item["id"] for item in ready],
    }


def should_stop_after(task: dict[str, Any], args: Any) -> bool:
    """Return whether a completed dispatch must yield before another selection."""
    return bool(args.stop_after_task) or args.stop_after_gate == task["delivery_gate"]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_mutually_exclusive_group()
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--status", action="store_true")
    modes.add_argument("--next", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    result.add_argument("--task", metavar="OCOR-DEV-NNNN")
    result.add_argument("--execute", action="store_true")
    result.add_argument("--resume", action="store_true")
    result.add_argument("--max-parallel", type=int, default=1)
    result.add_argument("--stop-after-task", action="store_true")
    result.add_argument("--stop-after-gate", metavar="GATE")
    result.add_argument("--emergency-stop", metavar="REASON")
    result.add_argument("--accept-evidence", metavar="OCOR-DEV-NNNN")
    result.add_argument("--push", action="store_true")
    result.add_argument("--open-pr", action="store_true")
    result.add_argument("--merge", action="store_true")
    result.add_argument("--state", type=Path)
    result.add_argument("--repo", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = repository_root(args.repo)
        plan = Plan.load(root)
        errors = plan.validate()
        if errors:
            raise DeliveryError("; ".join(errors))
        args.state = (args.state or root / plan.config["state_path"]).resolve()
        state_exists = args.state.exists()
        state = load_json(args.state) if state_exists else new_state(plan)
        state_errors = validate_state(plan, state)
        if state_errors:
            raise DeliveryError("; ".join(state_errors))

        if args.emergency_stop:
            if not args.execute:
                raise DeliveryError("--emergency-stop requires --execute")
            state["emergency_stop"] = True
            state["stop_reason"] = args.emergency_stop
            state["updated_at"] = utc_now()
            atomic_json(args.state, state)
            print(json.dumps(summarize(plan, state), indent=2))
            return 0

        if args.accept_evidence:
            if not args.execute:
                raise DeliveryError("--accept-evidence requires --execute")
            if args.accept_evidence not in plan.tasks:
                raise DeliveryError(f"unknown task: {args.accept_evidence}")
            task = plan.tasks[args.accept_evidence]
            hard = task.get("hard_dependencies", [])
            if any(state["tasks"][item]["status"] != "ACCEPTED" for item in hard):
                raise DeliveryError("cannot accept evidence before hard dependencies")
            qualifying, detail = evidence_qualifies(root, task)
            if not qualifying:
                raise DeliveryError(f"task evidence is not qualifying: {detail}")
            state["tasks"][args.accept_evidence]["status"] = "ACCEPTED"
            state["tasks"][args.accept_evidence]["accepted_commit"] = detail
            state["history"].append(
                {"task_id": args.accept_evidence, "event": "EVIDENCE_ACCEPTED", "at": utc_now()}
            )
            state["updated_at"] = utc_now()
            atomic_json(args.state, state)
            print(json.dumps(summarize(plan, state), indent=2))
            return 0

        if args.resume:
            if not args.execute:
                raise DeliveryError("--resume requires --execute")
            recovered = recover_interrupted(state, int(plan.config["max_retries"]))
            state["history"].append({"event": "RESUME", "recovered": recovered, "at": utc_now()})
            atomic_json(args.state, state)

        if args.validate:
            print(
                f"PASS: {len(plan.tasks)}-task plan, schema, context manifest "
                "and acyclic DAG validated"
            )
            return 0
        if args.status or (
            not any((args.next, args.dry_run, args.task, args.execute, args.resume, args.accept_evidence))
        ):
            print(json.dumps(summarize(plan, state), indent=2))
            return 0

        ready = ready_tasks(plan, state)
        if args.task:
            if args.task not in plan.tasks:
                raise DeliveryError(f"unknown task: {args.task}")
            if args.task not in {item["id"] for item in ready}:
                raise DeliveryError(f"task is not dependency-ready: {args.task}")
            ready = [plan.tasks[args.task]]
        if args.next:
            print(json.dumps({"next": ready[0]["id"] if ready else None}, indent=2))
            return 0
        if args.dry_run:
            selection = parallel_selection(
                ready, min(args.max_parallel, int(plan.config["max_parallel"]))
            )
            print(
                json.dumps(
                    {
                        "mode": "DRY_RUN",
                        "mutated": False,
                        "selected": [item["id"] for item in selection],
                        "promoted_claims": [],
                    },
                    indent=2,
                )
            )
            return 0
        if not args.execute:
            raise DeliveryError("task execution requires explicit --execute")
        if args.max_parallel != 1:
            raise DeliveryError("this persistent coordinator executes one task per process; use isolated processes for parallel work")
        if not ready:
            raise DeliveryError("no dependency-ready task")
        selected = ready[0]
        execute_task(plan, state, selected, args)
        if should_stop_after(selected, args):
            return 0
        return 0
    except DeliveryError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
