#!/usr/bin/env python3
"""Durable trigger-to-merge controller for Pi Graph Factory."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import fnmatch
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
FACTORY_SCHEMA = json.loads((ROOT / "schemas" / "factory.schema.json").read_text())
TERMINAL = {"human_required", "merge_ready", "merged", "failed"}
GLOB_MAGIC = re.compile(r"[*?\[]")
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
GENERATED_DIRECTORIES = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
}
GENERATED_FILES = {".DS_Store"}
GENERATED_SUFFIXES = {".pyc", ".pyo"}
SAFE_ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template"}
DEFAULT_GITIGNORE = """.factory/
.DS_Store
.env
.env.*
!.env.example
!.env.sample
!.env.template
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
node_modules/
"""


class FactoryError(RuntimeError):
    pass


@contextmanager
def run_lock(run: Path):
    path = run / ".controller.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise FactoryError(f"factory run is already active: {run}") from error
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()}\nacquired_at={now()}\n")
        handle.flush()
        os.fsync(handle.fileno())
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        raise FactoryError(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


def staged_files(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--name-only", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise FactoryError(f"cannot inspect staged changes: {result.stderr.decode(errors='replace').strip()}")
    return sorted(os.fsdecode(raw) for raw in result.stdout.split(b"\0") if raw)


def run_commands(cwd: Path, commands: list[str], label: str) -> list[dict[str, Any]]:
    receipts = []
    for command in commands:
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        receipt = {
            "command": command,
            "passed": result.returncode == 0,
            "exit_code": result.returncode,
            "output": (result.stdout + result.stderr)[-2000:],
        }
        receipts.append(receipt)
        if result.returncode:
            raise FactoryError(
                f"approved acceptance command failed for {label}: {command!r} "
                f"(exit {result.returncode})"
            )
    return receipts


def validate_repo_pattern(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise FactoryError("task file patterns must be non-empty strings")
    pattern = raw.strip().replace("\\", "/")
    parts = pattern.split("/")
    if pattern.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise FactoryError(f"task file pattern must stay inside the repository: {raw!r}")
    return pattern


def validate_acceptance_command(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise FactoryError(f"{label} must contain non-empty acceptance commands")
    command = raw.strip()
    if "`" in command or "\n" in command or re.match(r"^[A-Z][A-Za-z]+(?:\s|$)", command):
        raise FactoryError(
            f"{label} acceptance must be a raw shell command, not prose or Markdown: {raw!r}"
        )
    syntax = subprocess.run(
        ["bash", "-n", "-c", command],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if syntax.returncode:
        raise FactoryError(
            f"{label} acceptance is not valid shell syntax: {raw!r}: {syntax.stderr.strip()}"
        )
    return command


def pattern_prefix(pattern: str) -> tuple[str, ...]:
    prefix = []
    for part in pattern.split("/"):
        if GLOB_MAGIC.search(part):
            break
        prefix.append(part)
    return tuple(prefix)


def patterns_may_overlap(left: str, right: str) -> bool:
    if left == right:
        return True
    left_magic = bool(GLOB_MAGIC.search(left))
    right_magic = bool(GLOB_MAGIC.search(right))
    if not left_magic and fnmatch.fnmatchcase(left, right):
        return True
    if not right_magic and fnmatch.fnmatchcase(right, left):
        return True
    left_prefix = pattern_prefix(left)
    right_prefix = pattern_prefix(right)
    shared = min(len(left_prefix), len(right_prefix))
    return left_prefix[:shared] == right_prefix[:shared] and (left_magic or right_magic)


def matches_scope(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in patterns)


def acceptance_for_tasks(tasks: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(command for task in tasks for command in task["acceptance"]))


def is_unsafe_repository_artifact(path: str) -> bool:
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    name = parts[-1]
    if any(part in GENERATED_DIRECTORIES for part in parts[:-1]):
        return True
    if name in GENERATED_FILES or Path(name).suffix in GENERATED_SUFFIXES:
        return True
    return name == ".env" or (name.startswith(".env.") and name not in SAFE_ENV_TEMPLATES)


def validate_lane_changes(owner: str, tasks: list[dict[str, Any]], actual: list[str]) -> None:
    if not actual:
        raise FactoryError(f"implementer {owner} produced no repository change")
    unsafe = [path for path in actual if is_unsafe_repository_artifact(path)]
    if unsafe:
        raise FactoryError(
            f"implementer {owner} staged generated or secret-bearing artifacts: "
            f"{', '.join(unsafe)}"
        )
    patterns = [pattern for task in tasks for pattern in task["files"]]
    escaped = [path for path in actual if not matches_scope(path, patterns)]
    if escaped:
        raise FactoryError(
            f"implementer {owner} changed files outside approved scope: {', '.join(escaped)}"
        )


def load_config(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(FACTORY_SCHEMA).iter_errors(value),
                    key=lambda error: [str(x) for x in error.absolute_path])
    if errors:
        raise FactoryError("invalid factory contract: " + "; ".join(
            f"{'.'.join(map(str, error.absolute_path))}: {error.message}" for error in errors))
    return value


def load_state(run: Path) -> dict[str, Any]:
    try:
        return json.loads((run / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FactoryError(f"cannot read run state: {error}") from error


def load_frozen_config(run: Path, state: dict[str, Any]) -> dict[str, Any]:
    path = run / "factory.yaml"
    if digest_bytes(path.read_bytes()) != state["config_sha256"]:
        raise FactoryError("frozen factory contract drifted after initialization")
    return load_config(path)


def save_state(run: Path, state: dict[str, Any], event: str, payload: dict[str, Any] | None = None) -> None:
    state["updated_at"] = now()
    sequence = int(state.get("sequence", 0)) + 1
    state["sequence"] = sequence
    row = {"sequence": sequence, "at": state["updated_at"], "event": event,
           "phase": state["phase"], "payload": payload or {}}
    events = run / "events.jsonl"
    with events.open("a", encoding="utf-8") as output:
        output.write(json.dumps(row, separators=(",", ":")) + "\n")
        output.flush()
        os.fsync(output.fileno())
    atomic_json(run / "state.json", state)


def ensure_clean(repo: Path) -> None:
    status = git(repo, "status", "--porcelain", "--untracked-files=no")
    if status:
        raise FactoryError("target repository has tracked changes; commit or stash them before factory work")


def ensure_repo(path: Path, new_repo: bool) -> Path:
    path = path.expanduser().resolve()
    if not path.exists() and new_repo:
        path.mkdir(parents=True)
        git(path, "init", "-b", "main")
        git(path, "config", "user.email", "factory@example.invalid")
        git(path, "config", "user.name", "Pi Graph Factory")
        (path / ".gitignore").write_text(DEFAULT_GITIGNORE, encoding="utf-8")
        git(path, "add", ".gitignore")
        git(path, "commit", "-m", "Initialize repository")
    if not (path / ".git").exists():
        raise FactoryError(f"not a Git repository: {path}")
    ensure_clean(path)
    return path


def validate_plan(plan: dict[str, Any], implementers: set[str]) -> None:
    required = {"summary", "tasks", "acceptance", "risks", "open_questions"}
    if not isinstance(plan, dict):
        raise FactoryError("plan must be a JSON object")
    if not required <= set(plan):
        raise FactoryError(f"plan is missing fields: {sorted(required - set(plan))}")
    if not isinstance(plan["summary"], str) or not plan["summary"].strip():
        raise FactoryError("plan summary must be a non-empty string")
    if not isinstance(plan["tasks"], list) or not plan["tasks"]:
        raise FactoryError("plan must contain at least one task")
    if not isinstance(plan["acceptance"], list) or not plan["acceptance"]:
        raise FactoryError("plan acceptance must contain non-empty commands")
    plan["acceptance"] = [
        validate_acceptance_command(command, "plan") for command in plan["acceptance"]
    ]
    if not isinstance(plan["risks"], list):
        raise FactoryError("plan risks must be an array")
    seen_ids: set[str] = set()
    ownership: list[tuple[str, str]] = []
    for task in plan["tasks"]:
        if not isinstance(task, dict) or not {"id", "owner", "files", "acceptance"} <= set(task):
            raise FactoryError("every task needs id, owner, files, and acceptance")
        if not isinstance(task["id"], str) or not TASK_ID.fullmatch(task["id"]):
            raise FactoryError(f"invalid task id: {task['id']!r}")
        if task["id"] in seen_ids:
            raise FactoryError(f"duplicate task id: {task['id']}")
        seen_ids.add(task["id"])
        if task["owner"] not in implementers:
            raise FactoryError(f"unknown task owner {task['owner']!r}")
        if not isinstance(task["files"], list) or not task["files"]:
            raise FactoryError(f"task {task['id']} must own at least one file pattern")
        task["files"] = [validate_repo_pattern(pattern) for pattern in task["files"]]
        if not isinstance(task["acceptance"], list) or not task["acceptance"]:
            raise FactoryError(f"task {task['id']} must contain non-empty acceptance commands")
        task["acceptance"] = [
            validate_acceptance_command(command, f"task {task['id']}")
            for command in task["acceptance"]
        ]
        for pattern in task["files"]:
            conflict = next(
                (
                    (other_pattern, other_owner)
                    for other_pattern, other_owner in ownership
                    if other_owner != task["owner"] and patterns_may_overlap(pattern, other_pattern)
                ),
                None,
            )
            if conflict:
                other_pattern, other_owner = conflict
                raise FactoryError(
                    f"conflicting file ownership; overlapping file ownership for "
                    f"{pattern} and {other_pattern}: "
                    f"{task['owner']} and {other_owner}"
                )
            ownership.append((pattern, task["owner"]))
    questions = plan["open_questions"]
    if not isinstance(questions, list):
        raise FactoryError("open_questions must be an array")
    question_ids: set[str] = set()
    for question in questions:
        if not isinstance(question, dict) or not {"id", "question", "blocking"} <= set(question):
            raise FactoryError("every open question needs id, question, and blocking")
        if (
            not isinstance(question["id"], str)
            or not TASK_ID.fullmatch(question["id"])
            or question["id"] in question_ids
        ):
            raise FactoryError(f"invalid or duplicate question id: {question['id']!r}")
        if not isinstance(question["question"], str) or not question["question"].strip():
            raise FactoryError("question text must be non-empty")
        if not isinstance(question["blocking"], bool):
            raise FactoryError("question blocking must be boolean")
        question_ids.add(question["id"])


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    config_path = Path(args.config).expanduser().resolve()
    config = load_config(config_path)
    repo = ensure_repo(Path(args.repo), args.new_repo)
    request = args.request
    if args.request_file:
        request = Path(args.request_file).read_text(encoding="utf-8")
    if not request or not request.strip():
        raise FactoryError("request must not be empty")
    base = git(repo, "rev-parse", "HEAD")
    identifier = args.id or f"factory-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run = Path(args.out).expanduser().resolve() if args.out else repo / ".factory" / "runs" / identifier
    if run.exists():
        raise FactoryError(f"run already exists: {run}")
    run.mkdir(parents=True)
    shutil.copy2(config_path, run / "factory.yaml")
    state = {
        "schema": "pi-graph-factory.run.v1", "id": identifier, "phase": "intake",
        "created_at": now(), "updated_at": now(), "sequence": 0,
        "repo": str(repo), "new_repo": args.new_repo, "base_commit": base,
        "target_branch": config["merge"]["target"], "request": request.strip(),
        "request_sha256": digest_bytes(request.strip().encode()),
        "config_sha256": digest_bytes((run / "factory.yaml").read_bytes()),
        "plan": None, "plan_sha256": None, "approved_plan_sha256": None,
        "answers": {}, "cycles": [], "lane_receipts": {}, "integration": None,
        "final_review": None, "merge": None,
        "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                  "total_tokens": 0, "cost_usd": 0.0, "unknown_calls": 0},
    }
    save_state(run, state, "trigger_received", {"request_sha256": state["request_sha256"]})
    return {"ok": True, "run": str(run), "phase": state["phase"], "base_commit": base}


def cmd_plan(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] not in {"intake", "clarification", "awaiting_plan_approval"}:
        raise FactoryError(f"cannot submit a plan during phase {state['phase']}")
    config = load_frozen_config(run, state)
    source = "file"
    planner_receipt = None
    planner_receipts: list[dict[str, Any]] = []
    plan_number = int(state.get("plan_revision", 0)) + 1
    if args.generate:
        source = "planner"
        planner_context = {
            "request": state["request"],
            "answers": state["answers"],
            "base_commit": state["base_commit"],
            "target_branch": state["target_branch"],
            "implementers": [
                {"id": item["id"], "scope": item["scope"]}
                for item in config["implementers"]
            ],
        }
        for attempt in range(1, 3):
            enforce_dispatch_limits(state, config["limits"], "plan")
            planner_receipt = invoke_agent(
                run, state, config["planner"], "plan", Path(state["repo"]), planner_context,
                config["limits"],
            )
            record_usage(state, planner_receipt)
            planner_receipts.append(planner_receipt)
            atomic_json(
                run / "receipts" / f"planner-{plan_number}-attempt-{attempt}.json",
                planner_receipt,
            )
            save_state(
                run,
                state,
                "planner_attempt_completed",
                {"revision": plan_number, "attempt": attempt,
                 "receipt_sha256": planner_receipt["receipt_sha256"]},
            )
            if planner_receipt["status"] != "passed" or not isinstance(
                planner_receipt["output"], dict
            ):
                validation_error = "planner did not return a typed plan object"
            else:
                plan = planner_receipt["output"]
                try:
                    validate_plan(plan, {item["id"] for item in config["implementers"]})
                    break
                except FactoryError as error:
                    validation_error = str(error)
            if attempt == 2:
                raise FactoryError(f"planner could not produce a valid plan: {validation_error}")
            planner_context = {
                **planner_context,
                "previous_invalid_plan": planner_receipt.get("output"),
                "controller_validation_error": validation_error,
                "repair_instruction": (
                    "Return a complete corrected plan. Change only what the controller error requires."
                ),
            }
    else:
        plan = json.loads(Path(args.file).read_text(encoding="utf-8"))
        validate_plan(plan, {item["id"] for item in config["implementers"]})
    unanswered = [item for item in plan["open_questions"]
                  if item.get("blocking") and item["id"] not in state["answers"]]
    state["plan"] = plan
    state["plan_sha256"] = digest_json(plan)
    state["approved_plan_sha256"] = None
    state["phase"] = "clarification" if unanswered else "awaiting_plan_approval"
    state["plan_revision"] = plan_number
    plan_path = run / "plans" / f"plan-{plan_number}.json"
    atomic_json(plan_path, plan)
    if planner_receipt is not None:
        receipt_path = run / "receipts" / f"planner-{plan_number}.json"
        atomic_json(receipt_path, planner_receipt)
        state["planner_receipt_sha256"] = digest_json(planner_receipt)
        state["planner_attempts"] = len(planner_receipts)
    save_state(run, state, "plan_submitted", {
        "plan_sha256": state["plan_sha256"],
        "blocking_questions": [x["id"] for x in unanswered],
        "source": source,
        "revision": plan_number,
    })
    return {"ok": True, "phase": state["phase"], "plan_sha256": state["plan_sha256"],
            "plan": str(plan_path), "source": source, "open_questions": unanswered}


def cmd_answer(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] != "clarification" or not state.get("plan"):
        raise FactoryError("answers are accepted only while clarification is active")
    questions = {item["id"]: item for item in state["plan"]["open_questions"]}
    if args.question not in questions:
        raise FactoryError(f"unknown question: {args.question}")
    state["answers"][args.question] = args.answer
    unanswered = [item for item in questions.values()
                  if item.get("blocking") and item["id"] not in state["answers"]]
    if not unanswered:
        state["phase"] = "intake"  # planner must incorporate answers into a revised plan
    save_state(run, state, "question_answered", {"question": args.question,
                                                  "remaining": [x["id"] for x in unanswered]})
    return {"ok": True, "phase": state["phase"], "remaining": unanswered,
            "next": "submit a revised plan incorporating all answers" if not unanswered else "answer remaining questions"}


def cmd_approve(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] != "awaiting_plan_approval":
        raise FactoryError(f"plan cannot be approved during phase {state['phase']}")
    if args.sha256 != state["plan_sha256"]:
        raise FactoryError("approval digest does not match the current plan")
    state["approved_plan_sha256"] = args.sha256
    state["approved_at"] = now()
    state["phase"] = "approved"
    save_state(run, state, "plan_approved", {"plan_sha256": args.sha256})
    return {"ok": True, "phase": "approved", "approved_plan_sha256": args.sha256}


def adapter_command() -> list[str]:
    override = os.environ.get("PI_GRAPH_FACTORY_ADAPTER")
    if override:
        return [override]
    return [sys.executable, str(ROOT / "scripts" / "agent_adapter.py")]


def validated_usage(receipt: dict[str, Any]) -> dict[str, int | float | None]:
    raw = receipt.get("usage")
    if not isinstance(raw, dict):
        raise FactoryError(f"{receipt.get('role', 'agent')} adapter usage must be an object")
    values: dict[str, int | float | None] = {}
    for key in ("input", "output", "total"):
        value = raw.get(key)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise FactoryError(
                f"{receipt.get('role', 'agent')} adapter returned invalid usage {key}: {value!r}"
            )
        values[key] = value
    cost = raw.get("cost")
    if cost is not None and (
        isinstance(cost, bool)
        or not isinstance(cost, (int, float))
        or not math.isfinite(cost)
        or cost < 0
    ):
        raise FactoryError(
            f"{receipt.get('role', 'agent')} adapter returned invalid usage cost: {cost!r}"
        )
    values["cost"] = cost
    return values


def record_usage(state: dict[str, Any], receipt: dict[str, Any]) -> None:
    values = validated_usage(receipt)
    usage = state.setdefault(
        "usage",
        {"calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
         "cost_usd": 0.0, "unknown_calls": 0},
    )
    usage["calls"] += 1
    usage["input_tokens"] += int(values["input"] or 0)
    usage["output_tokens"] += int(values["output"] or 0)
    usage["total_tokens"] += int(values["total"] or 0)
    usage["cost_usd"] += float(values["cost"] or 0)
    if values["total"] is None or values["cost"] is None:
        usage["unknown_calls"] += 1


def enforce_dispatch_limits(state: dict[str, Any], limits: dict[str, Any], role: str) -> None:
    usage = state.get("usage", {})
    if limits["require_usage"] and usage.get("unknown_calls", 0):
        raise FactoryError(
            f"cannot dispatch {role}: a prior agent did not report required token and cost usage"
        )
    if usage.get("total_tokens", 0) >= limits["max_total_tokens"]:
        raise FactoryError(
            f"cannot dispatch {role}: token dispatch limit reached "
            f"({usage['total_tokens']} >= {limits['max_total_tokens']})"
        )
    if usage.get("cost_usd", 0) >= limits["max_total_cost_usd"]:
        raise FactoryError(
            f"cannot dispatch {role}: cost dispatch limit reached "
            f"({usage['cost_usd']:.6f} >= {limits['max_total_cost_usd']:.6f})"
        )


def invoke_agent(run: Path, state: dict[str, Any], agent: dict[str, Any], role: str,
                 cwd: Path, context: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    context_path = run / "contexts" / f"{role.replace(':', '-')}.json"
    atomic_json(context_path, context)
    command = [*adapter_command(), "--role", role, "--harness", agent["harness"],
               "--model", agent["model"], "--thinking", agent["thinking"],
               "--instructions", agent["instructions"],
               "--context", str(context_path)]
    for skill in agent.get("skills", []):
        command.extend(["--skill", skill])
    if agent.get("tools"):
        command.extend(["--tools", ",".join(agent["tools"])])
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "WORKFLOW_DIR": str(ROOT)},
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=limits["agent_timeout_seconds"])
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        raise FactoryError(
            f"{role} adapter exceeded {limits['agent_timeout_seconds']}s timeout"
        ) from error
    if process.returncode:
        raise FactoryError(f"{role} adapter failed: {(stderr or stdout)[-2000:]}")
    try:
        payload = json.loads(stdout)
    except ValueError as error:
        raise FactoryError(f"{role} adapter returned invalid JSON") from error
    required = {"status", "harness", "model", "role", "output", "usage"}
    if not required <= set(payload):
        raise FactoryError(f"{role} adapter receipt missing {sorted(required - set(payload))}")
    if payload["harness"] != agent["harness"] or payload["model"] != agent["model"]:
        raise FactoryError(f"{role} adapter identity drift")
    usage = validated_usage(payload)
    if limits["require_usage"] and (usage["total"] is None or usage["cost"] is None):
        raise FactoryError(f"{role} adapter did not report required token and cost usage")
    payload["observed_at"] = now()
    payload["receipt_sha256"] = digest_json(payload)
    safe_role = role.replace(":", "-")
    atomic_json(
        run / "receipts" / f"agent-{safe_role}-{payload['receipt_sha256'][:12]}.json",
        payload,
    )
    return payload


def provision_lane(repo: Path, run: Path, run_id: str, owner: str, base: str) -> tuple[Path, str]:
    path = run / "worktrees" / owner
    branch = f"factory/{run_id}/{owner}"
    if path.exists():
        raise FactoryError(f"lane worktree already exists: {owner}")
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "-b", branch, str(path), base)
    return path, branch


def commit_lane(path: Path, owner: str) -> str:
    git(path, "add", "-A")
    if not git(path, "status", "--porcelain"):
        raise FactoryError(f"implementer {owner} produced no repository change")
    git(path, "commit", "-m", f"factory({owner}): implement approved task")
    return git(path, "rev-parse", "HEAD")


def execute_lane(
    run: Path,
    state: dict[str, Any],
    agent: dict[str, Any],
    owner: str,
    tasks: list[dict[str, Any]],
    workspace: Path,
    branch: str,
    limits: dict[str, Any],
) -> dict[str, Any]:
    receipt = invoke_agent(
        run,
        state,
        agent,
        f"implement:{owner}",
        workspace,
        {"request": state["request"], "plan": state["plan"], "tasks": tasks},
        limits,
    )
    output = receipt["output"]
    if (
        receipt["status"] != "passed"
        or not isinstance(output, dict)
        or output.get("status") != "pass"
        or not output.get("checks")
        or not isinstance(output.get("changed_files"), list)
    ):
        raise FactoryError(f"implementer {owner} did not return a passing receipt")
    git(workspace, "add", "-A")
    actual = staged_files(workspace)
    validate_lane_changes(owner, tasks, actual)
    claimed = sorted(output["changed_files"])
    if claimed != actual:
        raise FactoryError(
            f"implementer {owner} changed-file receipt does not match Git: "
            f"claimed={claimed}, actual={actual}"
        )
    acceptance = run_commands(
        workspace,
        acceptance_for_tasks(tasks),
        f"implementation owner {owner}",
    )
    receipt["verification"] = {"changed_files": actual, "acceptance": acceptance}
    commit = commit_lane(workspace, owner)
    return {"owner": owner, "branch": branch, "commit": commit, "receipt": receipt}


def integrate_lanes(repo: Path, run: Path, state: dict[str, Any], lane_commits: list[str]) -> dict[str, Any]:
    path = run / "worktrees" / "integration"
    branch = f"factory/{state['id']}/integration"
    git(repo, "worktree", "add", "-b", branch, str(path), state["base_commit"])
    for commit in lane_commits:
        git(path, "cherry-pick", commit)
    git(path, "diff", "--check", f"{state['base_commit']}..HEAD")
    changed = git(path, "diff", "--name-only", f"{state['base_commit']}..HEAD").splitlines()
    if not changed:
        raise FactoryError("integration contains no changed files")
    return {"path": str(path), "branch": branch, "commit": git(path, "rev-parse", "HEAD"),
            "changed_files": changed}


def evidence_path(root: Path, raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise FactoryError("evidence paths must be non-empty repository-relative strings")
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise FactoryError(f"evidence path escapes the integration repository: {raw!r}") from error
    return candidate


def file_receipt(root: Path, path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(root.resolve()).as_posix(), "bytes": path.stat().st_size,
            "sha256": digest_bytes(path.read_bytes())}


def capture_evidence(run: Path, state: dict[str, Any], config: dict[str, Any],
                     integration: Path, cycle: int) -> dict[str, Any]:
    approved = list(dict.fromkeys(state["plan"]["acceptance"]))
    configured = list(dict.fromkeys(config["evidence"].get("test_commands", [])))
    tests = run_commands(integration, approved, "integrated plan")
    tests.extend(run_commands(integration, configured, "configured evidence"))
    evidence_files = []
    for raw in [*config["evidence"]["screenshots"], config["evidence"].get("video")]:
        if not raw:
            continue
        path = evidence_path(integration, raw)
        if not path.is_file() or not path.stat().st_size:
            raise FactoryError(f"required evidence missing: {raw}")
        evidence_files.append(file_receipt(integration, path))
    if not tests or not all(item["passed"] for item in tests):
        raise FactoryError("one or more evidence test commands failed")
    source_commit = git(integration, "rev-parse", "HEAD")
    receipt = {"cycle": cycle, "captured_at": now(), "source_commit": source_commit,
               "approved_plan_sha256": state["approved_plan_sha256"],
               "files": evidence_files, "tests": tests}
    receipt["sha256"] = digest_json(receipt)
    atomic_json(run / "evidence" / f"cycle-{cycle}.json", receipt)
    return receipt


def review_output(receipt: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    output = receipt.get("output")
    if not isinstance(output, dict) or output.get("verdict") not in {"pass", "repair"}:
        raise FactoryError("reviewer output must contain verdict pass|repair")
    if not isinstance(output.get("issues"), list) or not isinstance(output.get("evidence"), list):
        raise FactoryError("reviewer output must contain issues and evidence arrays")
    if not output["evidence"]:
        raise FactoryError("reviewer supplied no evidence")
    if evidence["sha256"] not in output["evidence"]:
        raise FactoryError("reviewer did not cite the current evidence receipt")
    if output["verdict"] == "pass" and output["issues"]:
        raise FactoryError("reviewer cannot pass with unresolved issues")
    if output["verdict"] == "repair" and not output["issues"]:
        raise FactoryError("repair verdict requires issues")
    issue_ids: set[str] = set()
    for issue in output["issues"]:
        if not isinstance(issue, dict) or not {"id", "owner", "message"} <= set(issue):
            raise FactoryError("every review issue needs id, owner, and message")
        if not isinstance(issue["id"], str) or not issue["id"] or issue["id"] in issue_ids:
            raise FactoryError("review issue ids must be unique non-empty strings")
        if not isinstance(issue["message"], str) or not issue["message"].strip():
            raise FactoryError("review issue messages must be non-empty")
        issue_ids.add(issue["id"])
    return output


def run_repair(run: Path, state: dict[str, Any], config: dict[str, Any], integration: Path,
               cycle: int, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agents = {item["id"]: item for item in config["implementers"]}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        owner = issue.get("owner")
        if owner not in agents:
            raise FactoryError(f"review issue has unknown owner: {owner!r}")
        grouped.setdefault(owner, []).append(issue)
    receipts = []
    for owner, owned in grouped.items():
        enforce_dispatch_limits(state, config["limits"], f"repair:{cycle}:{owner}")
        tasks = [task for task in state["plan"]["tasks"] if task["owner"] == owner]
        receipt = invoke_agent(run, state, agents[owner], f"repair:{cycle}:{owner}", integration,
                               {"request": state["request"], "plan": state["plan"],
                                "issues": owned, "cycle": cycle},
                               config["limits"])
        record_usage(state, receipt)
        output = receipt["output"]
        if (
            receipt["status"] != "passed"
            or not isinstance(output, dict)
            or output.get("status") != "pass"
            or not output.get("checks")
        ):
            raise FactoryError(f"repair agent {owner} did not return passing checks")
        expected_issues = {issue["id"] for issue in owned}
        if set(output.get("addressed", [])) != expected_issues:
            raise FactoryError(f"repair agent {owner} did not address exactly its assigned issues")
        git(integration, "add", "-A")
        actual = staged_files(integration)
        validate_lane_changes(owner, tasks, actual)
        acceptance = run_commands(
            integration,
            acceptance_for_tasks(tasks),
            f"repair owner {owner}",
        )
        receipt["verification"] = {"changed_files": actual, "acceptance": acceptance}
        git(integration, "commit", "-m", f"factory: repair cycle {cycle} ({owner})")
        receipts.append(receipt)
    return receipts


def verify_merge_preconditions(repo: Path, state: dict[str, Any], evidence: dict[str, Any],
                               review: dict[str, Any], integration: Path) -> None:
    if state["approved_plan_sha256"] != state["plan_sha256"]:
        raise FactoryError("approved plan no longer matches current plan")
    if review.get("verdict") != "pass" or review.get("issues"):
        raise FactoryError("final review has not passed cleanly")
    current_commit = git(integration, "rev-parse", "HEAD")
    if evidence["source_commit"] != current_commit:
        raise FactoryError("evidence is stale relative to the integration commit")
    if evidence["approved_plan_sha256"] != state["approved_plan_sha256"]:
        raise FactoryError("evidence was not captured against the approved plan")
    if not all(item["passed"] for item in evidence["tests"]):
        raise FactoryError("evidence contains a failed test")
    if git(repo, "rev-parse", state["target_branch"]) != state["base_commit"]:
        raise FactoryError("target branch drifted after factory initialization")
    ensure_clean(repo)
    git(integration, "diff", "--check", f"{state['base_commit']}..HEAD")


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] != "approved" or state["approved_plan_sha256"] != state["plan_sha256"]:
        raise FactoryError("factory run requires the current plan to be explicitly approved")
    config = load_frozen_config(run, state)
    repo = Path(state["repo"])
    if git(repo, "rev-parse", "--show-toplevel") != str(repo.resolve()):
        raise FactoryError("run repository identity no longer matches its frozen target")
    if git(repo, "branch", "--show-current") != state["target_branch"]:
        raise FactoryError("target repository is not checked out on the approved merge branch")
    if git(repo, "rev-parse", "HEAD") != state["base_commit"]:
        raise FactoryError("repository HEAD drifted after plan approval")
    agents = {item["id"]: item for item in config["implementers"]}
    tasks_by_owner: dict[str, list[dict[str, Any]]] = {}
    for task in state["plan"]["tasks"]:
        tasks_by_owner.setdefault(task["owner"], []).append(task)
    enforce_dispatch_limits(state, config["limits"], "implementation batch")
    state["phase"] = "implementing"
    save_state(run, state, "implementation_started", {"owners": sorted(tasks_by_owner)})
    lane_specs = []
    for owner, tasks in tasks_by_owner.items():
        workspace, branch = provision_lane(repo, run, state["id"], owner, state["base_commit"])
        lane_specs.append((owner, tasks, workspace, branch))
    lane_commits_by_owner: dict[str, str] = {}
    first_failure: Exception | None = None
    with ThreadPoolExecutor(max_workers=len(lane_specs), thread_name_prefix="factory-lane") as pool:
        futures = {
            pool.submit(
                execute_lane,
                run,
                state,
                agents[owner],
                owner,
                tasks,
                workspace,
                branch,
                config["limits"],
            ): owner
            for owner, tasks, workspace, branch in lane_specs
        }
        for future in as_completed(futures):
            try:
                completed = future.result()
            except Exception as error:
                if first_failure is None:
                    first_failure = error
                continue
            owner = completed["owner"]
            lane_commits_by_owner[owner] = completed["commit"]
            state["lane_receipts"][owner] = {
                "branch": completed["branch"],
                "commit": completed["commit"],
                "receipt": completed["receipt"],
            }
            record_usage(state, completed["receipt"])
            save_state(run, state, "lane_completed", {"owner": owner, "commit": completed["commit"]})
    if first_failure is not None:
        raise first_failure
    enforce_dispatch_limits(state, config["limits"], "review:1")
    lane_commits = [lane_commits_by_owner[owner] for owner in tasks_by_owner]
    integration = integrate_lanes(repo, run, state, lane_commits)
    state["integration"] = integration
    state["phase"] = "reviewing"
    save_state(run, state, "integration_completed", {"commit": integration["commit"]})
    integration_path = Path(integration["path"])
    final_evidence = None
    final_review = None
    for cycle in range(1, config["review"]["max_cycles"] + 1):
        evidence = capture_evidence(run, state, config, integration_path, cycle)
        enforce_dispatch_limits(state, config["limits"], f"review:{cycle}")
        reviewer_receipt = invoke_agent(
            run, state, config["review"], f"review:{cycle}", integration_path,
            {"request": state["request"], "plan": state["plan"],
             "integration": state["integration"], "evidence": evidence, "cycle": cycle},
            config["limits"],
        )
        record_usage(state, reviewer_receipt)
        review = review_output(reviewer_receipt, evidence)
        cycle_record = {"cycle": cycle, "evidence": evidence, "review": review,
                        "review_receipt": reviewer_receipt, "repairs": []}
        state["cycles"].append(cycle_record)
        save_state(run, state, "review_completed", {"cycle": cycle, "verdict": review["verdict"]})
        if review["verdict"] == "pass":
            final_evidence, final_review = evidence, review
            break
        if cycle == config["review"]["max_cycles"]:
            state["phase"] = "human_required"
            state["final_review"] = review
            save_state(run, state, "repair_budget_exhausted", {"cycles": cycle})
            return {"ok": False, "phase": state["phase"], "run": str(run),
                    "cycles": cycle, "issues": review["issues"], "usage": state["usage"]}
        cycle_record["repairs"] = run_repair(run, state, config, integration_path,
                                              cycle, review["issues"])
        state["integration"]["commit"] = git(integration_path, "rev-parse", "HEAD")
        save_state(run, state, "repair_completed", {"cycle": cycle,
                                                     "commit": state["integration"]["commit"]})
    assert final_evidence is not None and final_review is not None
    verify_merge_preconditions(repo, state, final_evidence, final_review, integration_path)
    state["final_review"] = final_review
    state["final_evidence_sha256"] = final_evidence["sha256"]
    state["phase"] = "merge_ready"
    integration_commit = git(integration_path, "rev-parse", "HEAD")
    merge = {"status": "approved", "target": state["target_branch"],
             "commit": integration_commit, "approved_plan_sha256": state["approved_plan_sha256"],
             "evidence_sha256": final_evidence["sha256"]}
    if config["merge"]["apply"]:
        git(repo, "merge", "--ff-only", integration_commit)
        merge["status"] = "merged"
        state["phase"] = "merged"
    state["merge"] = merge
    save_state(run, state, "merge_authorized" if merge["status"] == "approved" else "merged", merge)
    atomic_json(run / "receipt.json", {"schema": "pi-graph-factory.receipt.v1",
                                        "run": state["id"], "phase": state["phase"],
                                        "plan_sha256": state["approved_plan_sha256"],
                                        "evidence_sha256": final_evidence["sha256"],
                                        "review": final_review, "merge": merge,
                                        "usage": state["usage"]})
    return {"ok": True, "phase": state["phase"], "run": str(run),
            "cycles": len(state["cycles"]), "merge": merge, "usage": state["usage"]}


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    state = load_state(Path(args.run).resolve())
    return {
        "ok": state["phase"] not in {"failed", "human_required"} and not state.get("last_error"),
        "state": state,
    }


def record_transition_failure(run: Path, error: BaseException) -> None:
    state = load_state(run)
    observed = {
        "calls": 0, "input_tokens": 0, "output_tokens": 0,
        "total_tokens": 0, "cost_usd": 0.0, "unknown_calls": 0,
    }
    for path in (run / "receipts").glob("agent-*.json"):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            holder = {"usage": observed}
            record_usage(holder, receipt)
        except (OSError, ValueError, FactoryError):
            observed["unknown_calls"] += 1
    state["usage"] = observed
    failure = {
        "at": now(),
        "phase": state["phase"],
        "type": type(error).__name__,
        "message": str(error),
    }
    state["last_error"] = failure
    save_state(run, state, "transition_failed", failure)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="factory")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--repo", required=True)
    init.add_argument("--config", default=str(ROOT / "factory.yaml"))
    request = init.add_mutually_exclusive_group(required=True)
    request.add_argument("--request")
    request.add_argument("--request-file")
    init.add_argument("--new-repo", action="store_true")
    init.add_argument("--id")
    init.add_argument("--out")
    plan = commands.add_parser("plan")
    plan.add_argument("--run", required=True)
    plan_source = plan.add_mutually_exclusive_group(required=True)
    plan_source.add_argument("--file")
    plan_source.add_argument("--generate", action="store_true")
    answer = commands.add_parser("answer")
    answer.add_argument("--run", required=True)
    answer.add_argument("--question", required=True)
    answer.add_argument("--answer", required=True)
    approve = commands.add_parser("approve")
    approve.add_argument("--run", required=True)
    approve.add_argument("--sha256", required=True)
    execute = commands.add_parser("run")
    execute.add_argument("--run", required=True)
    status = commands.add_parser("status")
    status.add_argument("--run", required=True)
    return root


COMMANDS = {"init": cmd_init, "plan": cmd_plan, "answer": cmd_answer,
            "approve": cmd_approve, "run": cmd_run, "status": cmd_status}


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in {"plan", "answer", "approve", "run"}:
            run = Path(args.run).resolve()
            with run_lock(run):
                try:
                    payload = COMMANDS[args.command](args)
                except (FactoryError, OSError, ValueError, json.JSONDecodeError) as error:
                    if args.command == "run":
                        record_transition_failure(run, error)
                    raise
        else:
            payload = COMMANDS[args.command](args)
    except (FactoryError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, separators=(",", ":")))
        return 2
    print(json.dumps(payload, separators=(",", ":")))
    return 0 if payload.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
