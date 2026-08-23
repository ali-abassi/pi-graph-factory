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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

try:
    from delivery import execute_delivery
    from intake import INTAKE_MODES, IntakeError, resolve_intake
    from repository_intelligence import (
        IntelligenceError,
        ensure_repository_intelligence,
    )
except ModuleNotFoundError:  # imported as scripts.factory in the test/package path
    from scripts.delivery import execute_delivery
    from scripts.intake import INTAKE_MODES, IntakeError, resolve_intake
    from scripts.repository_intelligence import (
        IntelligenceError,
        ensure_repository_intelligence,
    )


ROOT = Path(__file__).resolve().parent.parent
FACTORY_SCHEMA = json.loads((ROOT / "schemas" / "factory.schema.json").read_text())
TERMINAL = {"human_required", "merge_ready", "merged", "delivered", "delivery_failed", "failed"}
GLOB_MAGIC = re.compile(r"[*?\[]")
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
GENERATED_DIRECTORIES = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "graphify-out",
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
graphify-out/
"""

PROJECT_DOCS = ("VISION.md", "FEATURE_MAP.md")
PROJECT_DOC_CONTEXT_LIMIT = 25_000
PLAN_RUBRIC_VERSION = "plan-quality-v1"
PLAN_JUDGE_DIMENSIONS = {
    "grounding": {"weight": 0.30, "critical": True},
    "coverage": {"weight": 0.25, "critical": False},
    "feasibility": {"weight": 0.20, "critical": True},
    "minimality": {"weight": 0.15, "critical": False},
    "alignment": {"weight": 0.10, "critical": False},
}


class FactoryError(RuntimeError):
    pass


class EvidenceFailure(FactoryError):
    def __init__(self, message: str, evidence: dict[str, Any]):
        super().__init__(message)
        self.evidence = evidence


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


def staged_change_digest(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--binary", "--full-index", "HEAD", "--"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise FactoryError(
            f"cannot fingerprint staged changes: {result.stderr.decode(errors='replace').strip()}"
        )
    return digest_bytes(result.stdout)


def worktree_changed_files(repo: Path) -> list[str]:
    tracked = set(git(repo, "diff", "--name-only").splitlines())
    tracked.update(git(repo, "diff", "--cached", "--name-only").splitlines())
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    tracked.update(value for value in untracked.split("\0") if value)
    return sorted(tracked)


def run_commands(
    cwd: Path,
    commands: list[str],
    label: str,
    *,
    raise_on_failure: bool = True,
    timeout_seconds: int | None = None,
    termination_grace_seconds: int = 5,
) -> list[dict[str, Any]]:
    receipts = []
    for command in commands:
        process = subprocess.Popen(
            ["bash", "-c", command],
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            receipt = {
                "command": command,
                "passed": process.returncode == 0,
                "exit_code": process.returncode,
                "output": (stdout + stderr)[-2000:],
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = process.communicate(timeout=termination_grace_seconds)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
            receipt = {
                "command": command,
                "passed": False,
                "exit_code": None,
                "output": (stdout + stderr)[-2000:],
                "timed_out": True,
                "timeout_seconds": timeout_seconds,
            }
        receipts.append(receipt)
        if not receipt["passed"] and raise_on_failure:
            detail = (
                f"exceeded {timeout_seconds}s timeout"
                if receipt["timed_out"]
                else f"exit {receipt['exit_code']}"
            )
            raise FactoryError(
                f"approved acceptance command failed for {label}: {command!r} "
                f"({detail}): {receipt['output'][-500:]}"
            )
        if not receipt["passed"]:
            break
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
    if not isinstance(value, dict):
        raise FactoryError("invalid factory contract: root must be an object")
    value.setdefault("delivery", {
        "enabled": False,
        "deploy_commands": [],
        "health_commands": [],
        "rollback_commands": [],
    })
    value.setdefault("intelligence", {
        "provider": "graphify",
        "required": True,
        "auto_install": True,
    })
    value["intelligence"].setdefault("enrichment", {"enabled": False})
    if "plan_review" not in value:
        reviewer = value.get("review", {})
        value["plan_review"] = {
            "harness": reviewer.get("harness", "pi"),
            "model": reviewer.get("model", value.get("model", "")),
            "thinking": reviewer.get("thinking", "high"),
            "instructions": "agents/plan_reviewer.md",
            "skills": [],
            "tools": ["read", "grep", "find", "ls"],
            "min_score": 8.5,
            "max_cycles": 3,
            "timeout_seconds": reviewer.get("timeout_seconds"),
        }
    value.setdefault("evidence", {}).setdefault("policy", "always")
    value.setdefault("limits", {}).setdefault("termination_grace_seconds", 5)
    value["limits"].setdefault("command_timeout_seconds", None)
    errors = sorted(Draft202012Validator(FACTORY_SCHEMA).iter_errors(value),
                    key=lambda error: [str(x) for x in error.absolute_path])
    if errors:
        raise FactoryError("invalid factory contract: " + "; ".join(
            f"{'.'.join(map(str, error.absolute_path))}: {error.message}" for error in errors))
    for field in ("capture_commands", "test_commands"):
        value["evidence"][field] = [
            validate_acceptance_command(command, f"evidence {field}")
            for command in value["evidence"].get(field, [])
        ]
    overlap = sorted(
        set(value["evidence"]["capture_commands"])
        & set(value["evidence"]["test_commands"])
    )
    if overlap:
        raise FactoryError(
            "evidence test_commands must not repeat state-changing capture_commands: "
            + ", ".join(repr(command) for command in overlap)
        )
    for field in ("deploy_commands", "health_commands", "rollback_commands"):
        value["delivery"][field] = [
            validate_acceptance_command(command, f"delivery {field}")
            for command in value["delivery"][field]
        ]
    if value["delivery"]["enabled"] and (
        not value["delivery"]["deploy_commands"]
        or not value["delivery"]["health_commands"]
    ):
        raise FactoryError(
            "enabled delivery requires non-empty deploy_commands and health_commands"
        )
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


def ensure_repo(path: Path, new_repo: bool, request: str = "") -> Path:
    path = path.expanduser().resolve()
    if not path.exists() and new_repo:
        path.mkdir(parents=True)
    if new_repo and path.is_dir() and not (path / ".git").exists():
        if any(path.iterdir()):
            raise FactoryError("new repository target exists and is not empty")
        git(path, "init", "-b", "main")
        git(path, "config", "user.email", "factory@example.invalid")
        git(path, "config", "user.name", "Pi Graph Factory")
        (path / ".gitignore").write_text(DEFAULT_GITIGNORE, encoding="utf-8")
        (path / "VISION.md").write_text(
            "# Vision\n\n## Mission\n\n"
            + request.strip()
            + "\n\n## Decision principles\n\n"
            "- Prefer the smallest complete solution.\n"
            "- Preserve working behavior unless the approved request changes it.\n"
            "- Prove user-visible outcomes before release.\n",
            encoding="utf-8",
        )
        (path / "FEATURE_MAP.md").write_text(
            "# Feature map\n\nNo implemented features yet. Update this map when the "
            "factory adds or materially changes a product capability.\n",
            encoding="utf-8",
        )
        git(path, "add", ".gitignore", *PROJECT_DOCS)
        git(path, "commit", "-m", "Initialize repository")
    if not (path / ".git").exists():
        raise FactoryError(f"not a Git repository: {path}")
    ensure_clean(path)
    return path


def read_project_memory(repo: Path) -> dict[str, Any]:
    documents = {}
    missing = []
    truncated = []
    for name in PROJECT_DOCS:
        path = repo / name
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            documents[name] = content[:PROJECT_DOC_CONTEXT_LIMIT]
            if len(content) > PROJECT_DOC_CONTEXT_LIMIT:
                truncated.append(name)
        else:
            missing.append(name)
    return {"documents": documents, "missing": missing, "truncated": truncated}


def prepare_repository_context(
    run: Path,
    state: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    repo = Path(state["repo"])
    policy = config["intelligence"]
    try:
        intelligence = ensure_repository_intelligence(
            repo,
            auto_install=policy["auto_install"],
            timeout_seconds=config["limits"]["command_timeout_seconds"],
            termination_grace_seconds=config["limits"]["termination_grace_seconds"],
            enrichment=policy["enrichment"],
        )
    except IntelligenceError as error:
        if policy["required"]:
            raise FactoryError(str(error)) from error
        intelligence = {
            "provider": "graphify",
            "status": "unavailable",
            "reason": str(error),
            "source_commit": state["base_commit"],
            "graph": None,
        }
    memory = read_project_memory(repo)
    atomic_json(run / "intelligence" / "graphify.json", intelligence)
    atomic_json(run / "intelligence" / "project-memory.json", memory)
    state["repository_intelligence"] = intelligence
    state["project_memory"] = {
        "files": sorted(memory["documents"]),
        "missing": memory["missing"],
        "truncated": memory["truncated"],
    }
    save_state(
        run,
        state,
        "repository_context_prepared",
        {
            "intelligence_status": intelligence["status"],
            "missing_project_docs": memory["missing"],
            "truncated_project_docs": memory["truncated"],
        },
    )
    return intelligence, memory


def durable_project_memory(run: Path) -> dict[str, Any]:
    path = run / "intelligence" / "project-memory.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_completed_repository_intelligence(
    run: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    repository: Path,
) -> None:
    try:
        receipt = ensure_repository_intelligence(
            repository,
            auto_install=config["intelligence"]["auto_install"],
            timeout_seconds=config["limits"]["command_timeout_seconds"],
            termination_grace_seconds=config["limits"]["termination_grace_seconds"],
            enrichment=config["intelligence"]["enrichment"],
        )
    except IntelligenceError as error:
        if config["intelligence"]["required"]:
            raise FactoryError(str(error)) from error
        receipt = {
            "provider": "graphify",
            "status": "unavailable",
            "reason": str(error),
            "graph": None,
        }
    atomic_json(run / "intelligence" / "post-implementation-graphify.json", receipt)
    state["post_implementation_intelligence"] = receipt
    save_state(
        run,
        state,
        "repository_intelligence_refreshed",
        {"status": receipt["status"], "graph": receipt.get("graph")},
    )


def validate_plan_judgment(
    receipt: dict[str, Any],
    minimum_score: float,
) -> dict[str, Any]:
    output = receipt.get("output")
    if receipt.get("status") != "passed" or not isinstance(output, dict):
        raise FactoryError("plan reviewer did not return a typed judgment")
    if output.get("rubric_version") != PLAN_RUBRIC_VERSION:
        raise FactoryError("plan reviewer used the wrong rubric version")
    dimensions = output.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != len(PLAN_JUDGE_DIMENSIONS) or {
        item.get("name") for item in dimensions if isinstance(item, dict)
    } != set(PLAN_JUDGE_DIMENSIONS):
        raise FactoryError("plan review must score every rubric dimension exactly once")
    scores = {}
    critical_failure = False
    for item in dimensions:
        name = item["name"]
        score = item.get("score")
        if score is None:
            if not PLAN_JUDGE_DIMENSIONS[name]["critical"]:
                raise FactoryError("only a critical plan dimension may use below-bar score")
            critical_failure = True
        elif (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or score < 7
            or score > 10
            or score * 2 != int(score * 2)
        ):
            raise FactoryError("plan review scores must use half-point anchors from 7 to 10")
        if not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
            raise FactoryError("every plan review dimension needs evidence")
        if not isinstance(item.get("reasoning"), str) or not item["reasoning"].strip():
            raise FactoryError("every plan review dimension needs reasoning")
        if not isinstance(item.get("gap_to_next"), str) or not item["gap_to_next"].strip():
            raise FactoryError("every plan review dimension needs a gap_to_next")
        scores[name] = score
    if bool(output.get("critical_failure")) != critical_failure:
        raise FactoryError("plan review critical_failure does not match dimension scores")
    computed_score = None
    if not critical_failure:
        weighted = sum(
            float(scores[name]) * spec["weight"]
            for name, spec in PLAN_JUDGE_DIMENSIONS.items()
        )
        computed_score = math.floor(weighted * 2 + 0.5) / 2
    if output.get("overall_score") != computed_score:
        raise FactoryError("plan review overall_score does not match weighted dimensions")
    expected_verdict = (
        "pass"
        if computed_score is not None and computed_score >= minimum_score
        else "revise"
    )
    if output.get("verdict") != expected_verdict:
        raise FactoryError("plan review verdict does not match the configured threshold")
    if (
        not isinstance(output.get("overall_reasoning"), str)
        or not output["overall_reasoning"].strip()
    ):
        raise FactoryError("plan review requires overall_reasoning")
    improvements = output.get("improvements")
    if not isinstance(improvements, list) or (expected_verdict == "revise" and not improvements):
        raise FactoryError("a failed plan review requires actionable improvements")
    for improvement in improvements:
        if (
            not isinstance(improvement, dict)
            or improvement.get("dimension") not in PLAN_JUDGE_DIMENSIONS
            or not isinstance(improvement.get("suggestion"), str)
            or not improvement["suggestion"].strip()
            or not isinstance(improvement.get("why_raises_score"), str)
            or not improvement["why_raises_score"].strip()
            or isinstance(improvement.get("current_anchor"), bool)
            or not isinstance(improvement.get("current_anchor"), (int, float))
            or isinstance(improvement.get("target_anchor"), bool)
            or not isinstance(improvement.get("target_anchor"), (int, float))
            or not math.isfinite(float(improvement["current_anchor"]))
            or not math.isfinite(float(improvement["target_anchor"]))
            or improvement["current_anchor"] * 2
            != int(improvement["current_anchor"] * 2)
            or improvement["target_anchor"] * 2
            != int(improvement["target_anchor"] * 2)
            or not 7 <= improvement["current_anchor"] < improvement["target_anchor"] <= 10
        ):
            raise FactoryError("plan review improvements must be specific and rubric-linked")
        dimension_score = scores[improvement["dimension"]]
        if dimension_score is not None and improvement["current_anchor"] != dimension_score:
            raise FactoryError("plan review improvement current_anchor must match its score")
    return output


def validate_plan(
    plan: dict[str, Any],
    implementers: set[str],
    *,
    require_versioned: bool = False,
    evidence_capture_commands: set[str] | None = None,
    evidence_policy: str = "always",
    required_project_docs: set[str] | None = None,
) -> None:
    required = {"summary", "tasks", "acceptance", "risks", "open_questions"}
    if not isinstance(plan, dict):
        raise FactoryError("plan must be a JSON object")
    version = plan.get("version")
    if require_versioned and version != 1:
        raise FactoryError("generated plans must use version 1 with success_criteria")
    if version is not None and version != 1:
        raise FactoryError(f"unsupported plan version: {version!r}")
    if version == 1:
        proof = plan.get("proof")
        if evidence_policy == "plan":
            if not isinstance(proof, dict) or not {"mode", "reason"} <= set(proof):
                raise FactoryError(
                    "version 1 plans require proof mode and reason when evidence policy is plan"
                )
            if proof["mode"] not in {"tests", "visual"}:
                raise FactoryError("plan proof mode must be tests|visual")
            if not isinstance(proof["reason"], str) or not proof["reason"].strip():
                raise FactoryError("plan proof reason must be non-empty")
            proof["reason"] = proof["reason"].strip()
        criteria = plan.get("success_criteria")
        if not isinstance(criteria, list) or not criteria:
            raise FactoryError("version 1 plans require non-empty success_criteria")
        if len(criteria) > 50:
            raise FactoryError("version 1 plans support at most 50 success criteria")
        criterion_ids: set[str] = set()
        for criterion in criteria:
            if not isinstance(criterion, dict) or not {"id", "description"} <= set(criterion):
                raise FactoryError("every success criterion needs id and description")
            criterion_id = criterion["id"]
            if (
                not isinstance(criterion_id, str)
                or not TASK_ID.fullmatch(criterion_id)
                or criterion_id in criterion_ids
            ):
                raise FactoryError(f"invalid or duplicate success criterion id: {criterion_id!r}")
            description = criterion["description"]
            if not isinstance(description, str) or not description.strip():
                raise FactoryError("success criterion descriptions must be non-empty")
            criterion["description"] = description.strip()
            criterion_ids.add(criterion_id)
        if require_versioned:
            research = plan.get("research")
            if not isinstance(research, list) or not research:
                raise FactoryError("generated plans require non-empty research findings")
            for finding in research:
                if (
                    not isinstance(finding, dict)
                    or not {"question", "finding", "evidence"} <= set(finding)
                    or not isinstance(finding["question"], str)
                    or not finding["question"].strip()
                    or not isinstance(finding["finding"], str)
                    or not finding["finding"].strip()
                    or not isinstance(finding["evidence"], list)
                    or not finding["evidence"]
                    or not all(isinstance(item, str) and item.strip() for item in finding["evidence"])
                ):
                    raise FactoryError(
                        "every generated-plan research finding needs question, finding, and evidence"
                    )
            assumptions = plan.get("assumptions")
            if not isinstance(assumptions, list) or not all(
                isinstance(item, str) and item.strip() for item in assumptions
            ):
                raise FactoryError("generated plan assumptions must be an array of strings")
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
    missing_docs = {
        document
        for document in (required_project_docs or set())
        if not any(
            matches_scope(document, task["files"])
            for task in plan["tasks"]
        )
    }
    if missing_docs:
        raise FactoryError(
            "generated plan must assign missing project memory files: "
            + ", ".join(sorted(missing_docs))
        )
    capture_overlap = sorted(
        (
            set(plan["acceptance"])
            | {
                command
                for task in plan["tasks"]
                for command in task["acceptance"]
            }
        )
        & (evidence_capture_commands or set())
    )
    if capture_overlap:
        raise FactoryError(
            "plan acceptance must not repeat configured evidence capture commands: "
            + ", ".join(repr(command) for command in capture_overlap)
        )
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
    try:
        request, intake, intake_ledger = resolve_intake(
            args.intake_mode,
            args.request,
            args.request_file,
            args.intake_ledger,
        )
    except IntakeError as error:
        raise FactoryError(str(error)) from error
    repo = ensure_repo(Path(args.repo), args.new_repo, intake["summary"])
    base = git(repo, "rev-parse", "HEAD")
    identifier = args.id or f"factory-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run = Path(args.out).expanduser().resolve() if args.out else repo / ".factory" / "runs" / identifier
    if run.exists():
        raise FactoryError(f"run already exists: {run}")
    run.mkdir(parents=True)
    shutil.copy2(config_path, run / "factory.yaml")
    intake_path = run / "intake" / intake["artifact"]
    intake_path.parent.mkdir(parents=True)
    intake_path.write_text(request + "\n", encoding="utf-8")
    intake["artifact_sha256"] = digest_bytes(intake_path.read_bytes())
    if intake_ledger is not None:
        ledger_path = run / "intake" / intake["ledger"]
        atomic_json(ledger_path, intake_ledger)
        intake["ledger_sha256"] = digest_bytes(ledger_path.read_bytes())
    state = {
        "schema": "pi-graph-factory.run.v1", "id": identifier, "phase": "intake",
        "created_at": now(), "updated_at": now(), "sequence": 0,
        "repo": str(repo), "new_repo": args.new_repo, "base_commit": base,
        "target_branch": config["merge"]["target"], "request": request.strip(),
        "request_sha256": digest_bytes(request.strip().encode()),
        "intake": intake,
        "config_sha256": digest_bytes((run / "factory.yaml").read_bytes()),
        "plan": None, "plan_sha256": None, "approved_plan_sha256": None,
        "answers": {}, "cycles": [], "lane_receipts": {}, "integration": None,
        "final_review": None, "merge": None,
        "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                  "total_tokens": 0, "cost_usd": 0.0, "unknown_calls": 0},
    }
    save_state(run, state, "trigger_received", {
        "request_sha256": state["request_sha256"],
        "intake": intake,
    })
    return {
        "ok": True,
        "run": str(run),
        "phase": state["phase"],
        "base_commit": base,
        "intake": intake,
    }


def cmd_plan(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] not in {"intake", "clarification", "awaiting_plan_approval"}:
        raise FactoryError(f"cannot submit a plan during phase {state['phase']}")
    config = load_frozen_config(run, state)
    source = "file"
    planner_receipt = None
    planner_receipts: list[dict[str, Any]] = []
    plan_judgment = None
    plan_number = int(state.get("plan_revision", 0)) + 1
    if args.generate:
        source = "planner"
        intelligence, memory = prepare_repository_context(run, state, config)
        planner_context = {
            "request": state["request"],
            "intake": state.get("intake", {"mode": "direct", "status": "ready"}),
            "answers": state["answers"],
            "base_commit": state["base_commit"],
            "target_branch": state["target_branch"],
            "implementers": [
                {"id": item["id"], "scope": item["scope"]}
                for item in config["implementers"]
            ],
            "evidence": config["evidence"],
            "repository_intelligence": intelligence,
            "project_memory": memory,
            "required_project_docs": memory["missing"],
        }
        for quality_cycle in range(1, config["plan_review"]["max_cycles"] + 1):
            planner_context["quality_cycle"] = quality_cycle
            planner_attempt_context = planner_context
            for attempt in range(1, 3):
                enforce_dispatch_limits(state, config["limits"], "plan")
                planner_receipt = invoke_agent(
                    run, state, config["planner"], "plan", Path(state["repo"]),
                    planner_attempt_context, config["limits"],
                )
                record_usage(state, planner_receipt)
                planner_receipts.append(planner_receipt)
                atomic_json(
                    run / "receipts" / (
                        f"planner-{plan_number}-cycle-{quality_cycle}-attempt-{attempt}.json"
                    ),
                    planner_receipt,
                )
                save_state(
                    run,
                    state,
                    "planner_attempt_completed",
                    {"revision": plan_number, "cycle": quality_cycle, "attempt": attempt,
                     "receipt_sha256": planner_receipt["receipt_sha256"]},
                )
                if planner_receipt["status"] != "passed" or not isinstance(
                    planner_receipt["output"], dict
                ):
                    validation_error = "planner did not return a typed plan object"
                else:
                    plan = planner_receipt["output"]
                    try:
                        validate_plan(
                            plan,
                            {item["id"] for item in config["implementers"]},
                            require_versioned=True,
                            evidence_capture_commands=set(
                                config["evidence"].get("capture_commands", [])
                            ),
                            evidence_policy=config["evidence"]["policy"],
                            required_project_docs=set(memory["missing"]),
                        )
                        break
                    except FactoryError as error:
                        validation_error = str(error)
                if attempt == 2:
                    raise FactoryError(
                        f"planner could not produce a valid plan: {validation_error}"
                    )
                planner_attempt_context = {
                    **planner_attempt_context,
                    "previous_invalid_plan": planner_receipt.get("output"),
                    "controller_validation_error": validation_error,
                    "repair_instruction": (
                        "Return a complete corrected plan. Change only what the "
                        "controller error requires."
                    ),
                }
            atomic_json(
                run / "plans" / f"plan-{plan_number}-cycle-{quality_cycle}.json",
                plan,
            )
            judge_context = {
                "request": state["request"],
                "intake": state.get("intake", {"mode": "direct", "status": "ready"}),
                "answers": state["answers"],
                "plan": plan,
                "repository_intelligence": intelligence,
                "project_memory": memory,
                "evidence_contract": config["evidence"],
                "minimum_score": config["plan_review"]["min_score"],
                "rubric_version": PLAN_RUBRIC_VERSION,
            }
            for judge_attempt in range(1, 3):
                enforce_dispatch_limits(
                    state, config["limits"], f"plan-review:{quality_cycle}"
                )
                judge_receipt = invoke_agent(
                    run,
                    state,
                    config["plan_review"],
                    f"plan-review:{quality_cycle}",
                    Path(state["repo"]),
                    judge_context,
                    config["limits"],
                )
                record_usage(state, judge_receipt)
                atomic_json(
                    run / "receipts" / (
                        f"plan-review-{plan_number}-cycle-{quality_cycle}-"
                        f"attempt-{judge_attempt}.json"
                    ),
                    judge_receipt,
                )
                try:
                    plan_judgment = validate_plan_judgment(
                        judge_receipt, config["plan_review"]["min_score"]
                    )
                    validation_error = None
                except FactoryError as error:
                    validation_error = str(error)
                save_state(
                    run,
                    state,
                    "plan_review_attempt_completed",
                    {"revision": plan_number, "cycle": quality_cycle,
                     "attempt": judge_attempt, "validation_error": validation_error},
                )
                if validation_error is None:
                    break
                if judge_attempt == 2:
                    raise FactoryError(
                        f"plan reviewer could not produce a valid judgment: {validation_error}"
                    )
                judge_context = {
                    **judge_context,
                    "previous_invalid_judgment": judge_receipt.get("output"),
                    "controller_validation_error": validation_error,
                    "repair_instruction": (
                        "Return a corrected judgment for the same plan and rubric."
                    ),
                }
            if plan_judgment["verdict"] == "pass":
                break
            save_state(
                run,
                state,
                "plan_revision_requested",
                {"revision": plan_number, "cycle": quality_cycle,
                 "score": plan_judgment["overall_score"],
                 "improvements": plan_judgment["improvements"]},
            )
            if quality_cycle == config["plan_review"]["max_cycles"]:
                raise FactoryError(
                    "plan did not reach the configured quality threshold after "
                    f"{quality_cycle} cycles"
                )
            planner_context = {
                **planner_context,
                "previous_plan": plan,
                "plan_review_feedback": plan_judgment["improvements"],
                "repair_instruction": (
                    "Revise the plan to close every rubric-linked gap. Ask a question "
                    "only if the repository, request, vision, and feature map cannot support "
                    "a defensible assumption."
                ),
            }
    else:
        plan = json.loads(Path(args.file).read_text(encoding="utf-8"))
        validate_plan(
            plan,
            {item["id"] for item in config["implementers"]},
            evidence_capture_commands=set(config["evidence"].get("capture_commands", [])),
            evidence_policy=config["evidence"]["policy"],
        )
    unanswered = [item for item in plan["open_questions"]
                  if item.get("blocking") and item["id"] not in state["answers"]]
    state["plan"] = plan
    state["plan_sha256"] = digest_json(plan)
    state["approved_plan_sha256"] = None
    state["phase"] = "clarification" if unanswered else "awaiting_plan_approval"
    state["plan_revision"] = plan_number
    state["plan_source"] = source
    plan_path = run / "plans" / f"plan-{plan_number}.json"
    atomic_json(plan_path, plan)
    if planner_receipt is not None:
        receipt_path = run / "receipts" / f"planner-{plan_number}.json"
        atomic_json(receipt_path, planner_receipt)
        state["planner_receipt_sha256"] = digest_json(planner_receipt)
        state["planner_attempts"] = len(planner_receipts)
        state["planning_cycles"] = quality_cycle
    state["plan_judgment"] = plan_judgment
    save_state(run, state, "plan_submitted", {
        "plan_sha256": state["plan_sha256"],
        "blocking_questions": [x["id"] for x in unanswered],
        "source": source,
        "revision": plan_number,
        "quality_score": plan_judgment.get("overall_score") if plan_judgment else None,
    })
    return {"ok": True, "phase": state["phase"], "plan_sha256": state["plan_sha256"],
            "plan": str(plan_path), "source": source, "open_questions": unanswered,
            "judgment": plan_judgment}


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
    if state.get("plan_source") == "planner" and (
        not state.get("plan_judgment")
        or state["plan_judgment"].get("verdict") != "pass"
    ):
        raise FactoryError("generated plan has no passing independent plan review")
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
    token_limit = limits.get("max_total_tokens")
    if token_limit is not None and usage.get("total_tokens", 0) >= token_limit:
        raise FactoryError(
            f"cannot dispatch {role}: token dispatch limit reached "
            f"({usage['total_tokens']} >= {token_limit})"
        )
    cost_limit = limits.get("max_total_cost_usd")
    if cost_limit is not None and usage.get("cost_usd", 0) >= cost_limit:
        raise FactoryError(
            f"cannot dispatch {role}: cost dispatch limit reached "
            f"({usage['cost_usd']:.6f} >= {cost_limit:.6f})"
        )


def invoke_agent(run: Path, state: dict[str, Any], agent: dict[str, Any], role: str,
                 cwd: Path, context: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    context_path = run / "contexts" / f"{role.replace(':', '-')}.json"
    atomic_json(context_path, context)
    command = [*adapter_command(), "--role", role, "--harness", agent["harness"],
               "--model", agent["model"], "--thinking", agent.get("thinking", "medium"),
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
    timeout = (
        agent["timeout_seconds"]
        if "timeout_seconds" in agent
        else limits.get("agent_timeout_seconds")
    )
    active_path = run / "active" / f"{role.replace(':', '-')}.json"
    atomic_json(
        active_path,
        {
            "role": role,
            "pid": process.pid,
            "process_group": process.pid,
            "started_at": now(),
            "cwd": str(cwd),
            "timeout_seconds": timeout,
        },
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=limits["termination_grace_seconds"])
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        raise FactoryError(
            f"{role} adapter exceeded {timeout}s timeout"
        ) from error
    finally:
        active_path.unlink(missing_ok=True)
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
    evidence_spec: dict[str, Any],
) -> dict[str, Any]:
    receipt = invoke_agent(
        run,
        state,
        agent,
        f"implement:{owner}",
        workspace,
        {"request": state["request"], "plan": state["plan"], "tasks": tasks,
         "evidence": evidence_spec,
         "repository_intelligence": state.get("repository_intelligence"),
         "project_memory": durable_project_memory(run)},
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
    before_acceptance = staged_change_digest(workspace)
    acceptance = run_commands(
        workspace,
        acceptance_for_tasks(tasks),
        f"implementation owner {owner}",
        timeout_seconds=limits["command_timeout_seconds"],
        termination_grace_seconds=limits["termination_grace_seconds"],
    )
    git(workspace, "add", "-A")
    after_acceptance_files = staged_files(workspace)
    if after_acceptance_files != actual or staged_change_digest(workspace) != before_acceptance:
        raise FactoryError(
            f"implementation acceptance for {owner} mutated repository files; "
            "acceptance commands must be read-only predicates"
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


def selected_proof(state: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    policy = config["evidence"].get("policy", "always")
    if policy == "always":
        return {"mode": "visual", "reason": "factory evidence policy requires visual proof"}
    if policy == "never":
        return {"mode": "tests", "reason": "factory evidence policy disables visual proof"}
    planned = state["plan"].get("proof") if isinstance(state.get("plan"), dict) else None
    if isinstance(planned, dict) and planned.get("mode") in {"tests", "visual"}:
        return {"mode": planned["mode"], "reason": planned["reason"]}
    return {
        "mode": "tests",
        "reason": "legacy plan without a visual-proof requirement",
    }


def restore_declared_capture_changes(integration: Path, changed: list[str]) -> None:
    tracked = []
    untracked = []
    for raw in changed:
        if git(integration, "ls-files", "--error-unmatch", "--", raw, check=False):
            tracked.append(raw)
        else:
            untracked.append(raw)
    if tracked:
        git(integration, "restore", "--staged", "--worktree", "--", *tracked)
    for raw in untracked:
        path = evidence_path(integration, raw)
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.exists():
            raise FactoryError(f"capture failure left a non-file artifact requiring inspection: {raw}")
    remaining = worktree_changed_files(integration)
    if remaining:
        raise FactoryError(
            "capture failure cleanup did not restore the integration boundary: "
            + ", ".join(remaining)
        )


def capture_evidence(run: Path, state: dict[str, Any], config: dict[str, Any],
                     integration: Path, cycle: int) -> dict[str, Any]:
    if worktree_changed_files(integration):
        raise FactoryError("integration worktree must be clean before evidence capture")
    proof = selected_proof(state, config)
    visual = proof["mode"] == "visual"
    declared = ([
        *config["evidence"]["screenshots"],
        config["evidence"].get("video"),
        *config["evidence"].get("artifacts", []),
    ] if visual else [])
    declared = [value for value in declared if value]
    limits = config.get("limits", {})
    command_timeout = limits.get("command_timeout_seconds")
    termination_grace = limits.get("termination_grace_seconds", 5)
    capture = run_commands(
        integration,
        list(dict.fromkeys(config["evidence"].get("capture_commands", []))) if visual else [],
        "configured evidence capture",
        raise_on_failure=False,
        timeout_seconds=command_timeout,
        termination_grace_seconds=termination_grace,
    )
    changed = worktree_changed_files(integration)
    unexpected = [value for value in changed if value not in declared]
    if unexpected:
        raise FactoryError(
            "evidence capture changed files outside declared artifacts: " + ", ".join(unexpected)
        )
    if capture and not all(item["passed"] for item in capture):
        restore_declared_capture_changes(integration, changed)
        source_commit = git(integration, "rev-parse", "HEAD")
        receipt = {
            "valid": False,
            "cycle": cycle,
            "captured_at": now(),
            "source_commit": source_commit,
            "approved_plan_sha256": state["approved_plan_sha256"],
            "proof": proof,
            "capture": capture,
            "files": [],
            "tests": [],
            "failure": "configured evidence capture failed before proof could be committed",
        }
        receipt["sha256"] = digest_json(receipt)
        atomic_json(run / "evidence" / f"cycle-{cycle}.json", receipt)
        raise EvidenceFailure("configured evidence capture failed; reviewer repair required", receipt)
    if changed:
        git(integration, "add", "--", *changed)
        git(integration, "commit", "-m", f"factory: capture evidence cycle {cycle}")
    approved = list(dict.fromkeys(state["plan"]["acceptance"]))
    configured = list(dict.fromkeys(config["evidence"].get("test_commands", [])))
    tests = run_commands(
        integration,
        approved,
        "integrated plan",
        timeout_seconds=command_timeout,
        termination_grace_seconds=termination_grace,
    )
    tests.extend(
        run_commands(
            integration,
            configured,
            "configured evidence",
            timeout_seconds=command_timeout,
            termination_grace_seconds=termination_grace,
        )
    )
    test_changes = worktree_changed_files(integration)
    if test_changes:
        raise FactoryError(
            "evidence acceptance mutated the committed review boundary; "
            "acceptance commands must be read-only predicates: " + ", ".join(test_changes)
        )
    evidence_files = []
    for raw in declared:
        if not raw:
            continue
        path = evidence_path(integration, raw)
        if not path.is_file() or not path.stat().st_size:
            raise FactoryError(f"required evidence missing: {raw}")
        try:
            git(integration, "ls-files", "--error-unmatch", "--", raw)
        except FactoryError as error:
            raise FactoryError(f"required evidence is not tracked in the proof commit: {raw}") from error
        evidence_files.append(file_receipt(integration, path))
    if not tests or not all(item["passed"] for item in tests):
        raise FactoryError("one or more evidence test commands failed")
    source_commit = git(integration, "rev-parse", "HEAD")
    receipt = {"valid": True, "cycle": cycle, "captured_at": now(), "source_commit": source_commit,
               "approved_plan_sha256": state["approved_plan_sha256"],
               "proof": proof, "capture": capture, "files": evidence_files, "tests": tests}
    receipt["sha256"] = digest_json(receipt)
    atomic_json(run / "evidence" / f"cycle-{cycle}.json", receipt)
    return receipt


def review_output(
    receipt: dict[str, Any], evidence: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
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
    if not evidence.get("valid", True) and output["verdict"] == "pass":
        raise FactoryError("reviewer cannot pass when evidence capture is invalid")
    if output["verdict"] == "repair" and not output["issues"]:
        raise FactoryError("repair verdict requires issues")
    failed_criteria: set[str] = set()
    approved_criterion_ids: set[str] = set()
    owner_patterns: dict[str, list[str]] = {}
    if plan.get("version") == 1:
        expected = [item["id"] for item in plan["success_criteria"]]
        criteria = output.get("criteria")
        if not isinstance(criteria, list):
            raise FactoryError("version 1 reviewer output must contain a criteria array")
        observed = [item.get("id") if isinstance(item, dict) else None for item in criteria]
        if observed != expected:
            raise FactoryError("reviewer criteria must exactly cover the approved criteria in order")
        approved_criterion_ids = set(expected)
        for item in criteria:
            if not {"id", "status", "evidence"} <= set(item):
                raise FactoryError("every reviewed criterion needs id, status, and evidence")
            if item["status"] not in {"pass", "fail"}:
                raise FactoryError("reviewed criterion status must be pass|fail")
            if not isinstance(item["evidence"], str) or not item["evidence"].strip():
                raise FactoryError("reviewed criterion evidence must be non-empty")
            if item["status"] == "fail":
                failed_criteria.add(item["id"])
        if output["verdict"] == "pass" and failed_criteria:
            raise FactoryError("reviewer cannot pass with failed success criteria")
        for task in plan["tasks"]:
            owner_patterns.setdefault(task["owner"], []).extend(task["files"])
    issue_ids: set[str] = set()
    cited_failed_criteria: set[str] = set()
    for issue in output["issues"]:
        if not isinstance(issue, dict) or not {"id", "owner", "message"} <= set(issue):
            raise FactoryError("every review issue needs id, owner, and message")
        if not isinstance(issue["id"], str) or not issue["id"] or issue["id"] in issue_ids:
            raise FactoryError("review issue ids must be unique non-empty strings")
        if not isinstance(issue["message"], str) or not issue["message"].strip():
            raise FactoryError("review issue messages must be non-empty")
        criterion_id = issue.get("criterion_id")
        if criterion_id is not None:
            if criterion_id not in approved_criterion_ids:
                raise FactoryError(f"review issue cites unknown success criterion: {criterion_id!r}")
            cited_failed_criteria.add(criterion_id)
        if plan.get("version") == 1:
            target_files = issue.get("target_files")
            if not isinstance(target_files, list) or not target_files:
                raise FactoryError("every version 1 review issue needs target_files")
            if not all(isinstance(target, str) for target in target_files):
                raise FactoryError(
                    "review issue target_files must be exact repository-relative paths"
                )
            if len(set(target_files)) != len(target_files):
                raise FactoryError("review issue target_files must be unique")
            for target in target_files:
                normalized = target.replace("\\", "/")
                if (
                    not normalized
                    or normalized != target
                    or normalized.startswith("/")
                    or GLOB_MAGIC.search(normalized)
                    or any(part in {"", ".", ".."} for part in normalized.split("/"))
                ):
                    raise FactoryError(
                        "review issue target_files must be exact repository-relative paths"
                    )
            owner = issue.get("owner")
            patterns = owner_patterns.get(owner)
            if not patterns:
                raise FactoryError(f"review issue has unknown owner: {owner!r}")
            outside = [target for target in target_files if not matches_scope(target, patterns)]
            if outside:
                raise FactoryError(
                    f"review issue target_files outside routed owner {owner} scope: "
                    + ", ".join(outside)
                )
        issue_ids.add(issue["id"])
    if failed_criteria - cited_failed_criteria:
        raise FactoryError("every failed success criterion requires a routed review issue")
    return output


def recover_committed_repairs(
    run: Path,
    state: dict[str, Any],
    integration: Path,
    limits: dict[str, Any],
    cycle: int,
    grouped: dict[str, list[dict[str, Any]]],
    cycle_record: dict[str, Any],
) -> list[dict[str, Any]]:
    """Rebuild repair checkpoints when Git committed before state was persisted."""
    receipts = list(cycle_record.get("repairs", []))
    completed = {
        receipt.get("verification", {}).get("owner")
        for receipt in receipts
        if isinstance(receipt, dict)
    }
    source_commit = cycle_record["evidence"]["source_commit"]
    raw = git(
        integration,
        "log",
        "--reverse",
        "--format=%H%x00%s",
        f"{source_commit}..HEAD",
    )
    committed: list[tuple[str, str]] = []
    pattern = re.compile(rf"^factory: repair cycle {cycle} \(([^)]+)\)$")
    for line in raw.splitlines() if raw else []:
        commit, separator, subject = line.partition("\0")
        match = pattern.fullmatch(subject) if separator else None
        if match is None or match.group(1) not in grouped:
            raise FactoryError(
                f"resume found an unrecognized commit after review cycle {cycle}: {subject!r}"
            )
        committed.append((commit, match.group(1)))
    expected_order = list(grouped)
    committed_order = [owner for _, owner in committed]
    if committed_order != expected_order[:len(committed_order)]:
        raise FactoryError(
            f"resume found out-of-order repair commits for cycle {cycle}: {committed_order}"
        )
    for commit, owner in committed:
        tasks = [task for task in state["plan"]["tasks"] if task["owner"] == owner]
        actual = sorted(
            git(
                integration,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                commit,
            ).splitlines()
        )
        validate_lane_changes(owner, tasks, actual)
        if owner in completed:
            continue
        candidates = sorted(
            (run / "receipts").glob(f"repair-{cycle}-{owner}-attempt-*.json"),
            reverse=True,
        )
        if not candidates:
            raise FactoryError(
                f"resume found committed repair work for {owner} without a durable receipt"
            )
        receipt = json.loads(candidates[0].read_text(encoding="utf-8"))
        output = receipt.get("output")
        expected_issues = {issue["id"] for issue in grouped[owner]}
        if (
            receipt.get("status") != "passed"
            or not isinstance(output, dict)
            or output.get("status") != "pass"
            or not output.get("checks")
            or set(output.get("addressed", [])) != expected_issues
        ):
            raise FactoryError(f"resume found an invalid repair receipt for {owner}")
        before = worktree_changed_files(integration)
        acceptance = run_commands(
            integration,
            acceptance_for_tasks(tasks),
            f"recovered repair owner {owner}",
            timeout_seconds=limits["command_timeout_seconds"],
            termination_grace_seconds=limits["termination_grace_seconds"],
        )
        if worktree_changed_files(integration) != before:
            raise FactoryError(
                f"recovered repair acceptance for {owner} mutated repository files"
            )
        receipt["verification"] = {
            "owner": owner,
            "changed_files": actual,
            "acceptance": acceptance,
            "commit": commit,
            "recovered": True,
        }
        receipts.append(receipt)
        completed.add(owner)
        cycle_record["repairs"] = receipts
        state["integration"]["commit"] = commit
        state.pop("operation", None)
        save_state(
            run,
            state,
            "repair_owner_recovered",
            {"cycle": cycle, "owner": owner, "commit": commit},
        )
    return receipts


def run_repair(run: Path, state: dict[str, Any], config: dict[str, Any], integration: Path,
               cycle: int, issues: list[dict[str, Any]],
               cycle_record: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    agents = {item["id"]: item for item in config["implementers"]}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        owner = issue.get("owner")
        if owner not in agents:
            raise FactoryError(f"review issue has unknown owner: {owner!r}")
        grouped.setdefault(owner, []).append(issue)
    receipts = (
        recover_committed_repairs(
            run, state, integration, config["limits"], cycle, grouped, cycle_record
        )
        if cycle_record is not None
        else []
    )
    completed_owners = {
        receipt.get("verification", {}).get("owner")
        for receipt in receipts
        if isinstance(receipt, dict)
    }
    for owner, owned in grouped.items():
        if owner in completed_owners:
            continue
        enforce_dispatch_limits(state, config["limits"], f"repair:{cycle}:{owner}")
        tasks = [task for task in state["plan"]["tasks"] if task["owner"] == owner]
        expected_issues = {issue["id"] for issue in owned}
        repair_context = {
            "request": state["request"],
            "plan": state["plan"],
            "issues": owned,
            "cycle": cycle,
            "repository_intelligence": state.get("repository_intelligence"),
            "project_memory": durable_project_memory(run),
        }
        receipt = None
        correction_files: list[str] | None = None
        correction_digest: str | None = None
        for attempt in range(1, 3):
            state["operation"] = {
                "kind": "repair",
                "cycle": cycle,
                "owner": owner,
                "attempt": attempt,
            }
            save_state(
                run,
                state,
                "repair_owner_started",
                {"cycle": cycle, "owner": owner, "attempt": attempt},
            )
            agent = agents[owner]
            role = f"repair:{cycle}:{owner}"
            if attempt == 2:
                agent = {**agent, "skills": [], "tools": ["read"]}
                role += ":protocol-correction"
            receipt = invoke_agent(
                run,
                state,
                agent,
                role,
                integration,
                repair_context,
                config["limits"],
            )
            record_usage(state, receipt)
            atomic_json(
                run / "receipts" / f"repair-{cycle}-{owner}-attempt-{attempt}.json",
                receipt,
            )
            output = receipt["output"]
            if (
                receipt["status"] != "passed"
                or not isinstance(output, dict)
                or output.get("status") != "pass"
                or not output.get("checks")
            ):
                raise FactoryError(f"repair agent {owner} did not return passing checks")
            addressed = output.get("addressed")
            validation_error = None
            if not isinstance(addressed, list) or set(addressed) != expected_issues:
                validation_error = (
                    f"repair agent {owner} did not address exactly its assigned issues"
                )
            save_state(
                run,
                state,
                "repair_protocol_attempt_completed",
                {
                    "cycle": cycle,
                    "owner": owner,
                    "attempt": attempt,
                    "validation_error": validation_error,
                },
            )
            if validation_error is None:
                break
            git(integration, "add", "-A")
            current_files = staged_files(integration)
            validate_lane_changes(owner, tasks, current_files)
            if attempt == 2:
                raise FactoryError(validation_error)
            correction_files = current_files
            correction_digest = staged_change_digest(integration)
            repair_context = {
                **repair_context,
                "previous_invalid_receipt": output,
                "controller_validation_error": validation_error,
                "repair_instruction": (
                    "Return a complete corrected receipt for work already performed. "
                    "Do not edit, create, delete, stage, or commit any file."
                ),
            }
        if receipt is None:
            raise FactoryError(f"repair agent {owner} ended without a typed receipt")
        git(integration, "add", "-A")
        actual = staged_files(integration)
        if correction_files is not None and (
            actual != correction_files or staged_change_digest(integration) != correction_digest
        ):
            raise FactoryError(
                f"repair receipt correction for {owner} mutated repository files"
            )
        validate_lane_changes(owner, tasks, actual)
        before_acceptance = staged_change_digest(integration)
        acceptance = run_commands(
            integration,
            acceptance_for_tasks(tasks),
            f"repair owner {owner}",
            timeout_seconds=config["limits"]["command_timeout_seconds"],
            termination_grace_seconds=config["limits"]["termination_grace_seconds"],
        )
        git(integration, "add", "-A")
        after_acceptance_files = staged_files(integration)
        if after_acceptance_files != actual or staged_change_digest(integration) != before_acceptance:
            raise FactoryError(
                f"repair acceptance for {owner} mutated repository files; "
                "acceptance commands must be read-only predicates"
            )
        receipt["verification"] = {
            "owner": owner,
            "changed_files": actual,
            "acceptance": acceptance,
        }
        git(integration, "commit", "-m", f"factory: repair cycle {cycle} ({owner})")
        receipts.append(receipt)
        if cycle_record is not None:
            cycle_record["repairs"] = receipts
            state["integration"]["commit"] = git(integration, "rev-parse", "HEAD")
            state.pop("operation", None)
            save_state(
                run,
                state,
                "repair_owner_completed",
                {"cycle": cycle, "owner": owner, "commit": state["integration"]["commit"]},
            )
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
    if not evidence.get("valid", True):
        raise FactoryError("final evidence capture is invalid")
    integration_changes = worktree_changed_files(integration)
    if integration_changes:
        raise FactoryError(
            "integration worktree changed after proof capture: " + ", ".join(integration_changes)
        )
    for item in evidence["files"]:
        path = evidence_path(integration, item["path"])
        try:
            git(integration, "ls-files", "--error-unmatch", "--", item["path"])
        except FactoryError as error:
            raise FactoryError(
                f"reviewed evidence is not tracked in the integration commit: {item['path']}"
            ) from error
        if not path.is_file() or digest_bytes(path.read_bytes()) != item["sha256"]:
            raise FactoryError(f"reviewed evidence hash no longer matches: {item['path']}")
    if git(repo, "rev-parse", state["target_branch"]) != state["base_commit"]:
        raise FactoryError("target branch drifted after factory initialization")
    ensure_clean(repo)
    git(integration, "diff", "--check", f"{state['base_commit']}..HEAD")


def validate_run_repository(state: dict[str, Any]) -> Path:
    repo = Path(state["repo"])
    if git(repo, "rev-parse", "--show-toplevel") != str(repo.resolve()):
        raise FactoryError("run repository identity no longer matches its frozen target")
    if git(repo, "branch", "--show-current") != state["target_branch"]:
        raise FactoryError("target repository is not checked out on the approved merge branch")
    if git(repo, "rev-parse", "HEAD") != state["base_commit"]:
        raise FactoryError("repository HEAD drifted after plan approval")
    return repo


def prepare_review_workspace_for_resume(
    run: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    integration: Path,
) -> None:
    expected_branch = f"factory/{state['id']}/integration"
    if not integration.exists():
        raise FactoryError("resume requires the existing integration worktree")
    if git(integration, "branch", "--show-current") != expected_branch:
        raise FactoryError("resume found an unexpected integration branch")
    changed = worktree_changed_files(integration)
    if not changed:
        return
    operation = state.get("operation") or {}
    if operation.get("kind") == "capture":
        proof = selected_proof(state, config)
        declared = (
            [
                *config["evidence"]["screenshots"],
                config["evidence"].get("video"),
                *config["evidence"].get("artifacts", []),
            ]
            if proof["mode"] == "visual"
            else []
        )
        declared = {path for path in declared if path}
        unexpected = [path for path in changed if path not in declared]
        if unexpected:
            raise FactoryError(
                "interrupted evidence capture changed undeclared files: "
                + ", ".join(unexpected)
            )
        restore_declared_capture_changes(integration, changed)
        state.pop("operation", None)
        save_state(
            run,
            state,
            "interrupted_capture_cleaned",
            {"changed_files": changed},
        )
        return
    if operation.get("kind") == "repair":
        owner = operation.get("owner")
        tasks = [
            task for task in state["plan"]["tasks"] if task["owner"] == owner
        ]
        if not tasks:
            raise FactoryError("interrupted repair references an unknown owner")
        validate_lane_changes(str(owner), tasks, changed)
        return
    raise FactoryError(
        "resume found ambiguous integration changes outside a checkpointed capture or repair"
    )


def recover_applied_merge(
    run: Path,
    state: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Recover the narrow crash window after a fast-forward but before state save."""
    if state["phase"] != "reviewing" or not config["merge"]["apply"]:
        return None
    repo = Path(state["repo"])
    if git(repo, "branch", "--show-current") != state["target_branch"]:
        raise FactoryError("target repository is not checked out on the approved merge branch")
    target_commit = git(repo, "rev-parse", "HEAD")
    if target_commit == state["base_commit"]:
        return None
    integration_record = state.get("integration") or {}
    integration_commit = integration_record.get("commit")
    if target_commit != integration_commit:
        raise FactoryError("target repository drifted to an unreviewed commit")
    if not state.get("cycles"):
        raise FactoryError("target moved before a durable review checkpoint existed")
    final_cycle = state["cycles"][-1]
    review = final_cycle.get("review") or {}
    evidence = final_cycle.get("evidence") or {}
    if review.get("verdict") != "pass" or review.get("issues"):
        raise FactoryError("target moved without a clean durable final review")
    if (
        not evidence.get("valid", True)
        or evidence.get("source_commit") != target_commit
        or evidence.get("approved_plan_sha256") != state["approved_plan_sha256"]
        or not evidence.get("tests")
        or not all(item.get("passed") for item in evidence["tests"])
    ):
        raise FactoryError("target moved without valid current-commit evidence")
    integration = Path(integration_record["path"])
    if not integration.exists() or git(integration, "rev-parse", "HEAD") != target_commit:
        raise FactoryError("reviewed integration worktree no longer matches the applied merge")
    if worktree_changed_files(integration):
        raise FactoryError("reviewed integration worktree changed after the applied merge")
    for item in evidence.get("files", []):
        path = evidence_path(integration, item["path"])
        if not path.is_file() or digest_bytes(path.read_bytes()) != item["sha256"]:
            raise FactoryError(f"reviewed evidence hash no longer matches: {item['path']}")
    ensure_clean(repo)
    git(integration, "diff", "--check", f"{state['base_commit']}..HEAD")
    merge = {
        "status": "merged",
        "target": state["target_branch"],
        "commit": target_commit,
        "approved_plan_sha256": state["approved_plan_sha256"],
        "evidence_sha256": evidence["sha256"],
        "recovered": True,
    }
    state["final_review"] = review
    state["final_evidence_sha256"] = evidence["sha256"]
    state["merge"] = merge
    state["phase"] = "delivery_ready" if config["delivery"]["enabled"] else "merged"
    state.pop("operation", None)
    save_state(run, state, "merge_recovered", merge)
    atomic_json(
        run / "receipt.json",
        {
            "schema": "pi-graph-factory.receipt.v1",
            "run": state["id"],
            "phase": state["phase"],
            "plan_sha256": state["approved_plan_sha256"],
            "evidence_sha256": evidence["sha256"],
            "review": review,
            "merge": merge,
            "usage": state["usage"],
        },
    )
    return {
        "ok": True,
        "phase": state["phase"],
        "run": str(run),
        "cycles": len(state["cycles"]),
        "merge": merge,
        "usage": state["usage"],
    }


def tasks_by_owner(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in state["plan"]["tasks"]:
        grouped.setdefault(task["owner"], []).append(task)
    return grouped


def ensure_lane_workspace(repo: Path, run: Path, state: dict[str, Any], owner: str) -> tuple[Path, str]:
    workspace = run / "worktrees" / owner
    branch = f"factory/{state['id']}/{owner}"
    if workspace.exists():
        if git(workspace, "branch", "--show-current") != branch:
            raise FactoryError(f"resume found unexpected branch in {owner} worktree")
        return workspace, branch
    if git(repo, "rev-parse", "--verify", branch, check=False):
        workspace.parent.mkdir(parents=True, exist_ok=True)
        git(repo, "worktree", "add", str(workspace), branch)
        return workspace, branch
    return provision_lane(repo, run, state["id"], owner, state["base_commit"])


def latest_agent_receipt(run: Path, role: str) -> dict[str, Any] | None:
    matches = []
    for path in (run / "receipts").glob("agent-*.json"):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if receipt.get("role") == role:
            matches.append((path.stat().st_mtime_ns, receipt))
    return max(matches, default=(0, None), key=lambda item: item[0])[1]


def recover_committed_lane(
    run: Path,
    state: dict[str, Any],
    owner: str,
    tasks: list[dict[str, Any]],
    workspace: Path,
    branch: str,
    limits: dict[str, Any],
) -> dict[str, Any] | None:
    if worktree_changed_files(workspace):
        return None
    head = git(workspace, "rev-parse", "HEAD")
    if head == state["base_commit"]:
        return None
    if git(workspace, "log", "-1", "--format=%s") != f"factory({owner}): implement approved task":
        raise FactoryError(f"resume found an unrecognized commit in {owner} lane")
    actual = sorted(
        git(workspace, "diff", "--name-only", f"{state['base_commit']}..{head}").splitlines()
    )
    validate_lane_changes(owner, tasks, actual)
    receipt = latest_agent_receipt(run, f"implement:{owner}")
    if receipt is None:
        raise FactoryError(f"resume found committed {owner} work without its durable agent receipt")
    output = receipt.get("output")
    if (
        receipt.get("status") != "passed"
        or not isinstance(output, dict)
        or output.get("status") != "pass"
        or sorted(output.get("changed_files", [])) != actual
    ):
        raise FactoryError(f"resume found an invalid durable receipt for committed lane {owner}")
    acceptance = run_commands(
        workspace,
        acceptance_for_tasks(tasks),
        f"recovered owner {owner}",
        timeout_seconds=limits["command_timeout_seconds"],
        termination_grace_seconds=limits["termination_grace_seconds"],
    )
    if worktree_changed_files(workspace):
        raise FactoryError(f"recovered acceptance for {owner} mutated repository files")
    receipt["verification"] = {
        "owner": owner,
        "changed_files": actual,
        "acceptance": acceptance,
        "recovered": True,
    }
    return {"owner": owner, "branch": branch, "commit": head, "receipt": receipt}


def continue_implementation(
    run: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    repo: Path,
) -> Path:
    agents = {item["id"]: item for item in config["implementers"]}
    grouped = tasks_by_owner(state)
    if state["phase"] == "approved":
        enforce_dispatch_limits(state, config["limits"], "implementation batch")
        state["phase"] = "implementing"
        save_state(run, state, "implementation_started", {"owners": sorted(grouped)})
    lane_specs = []
    lane_commits_by_owner: dict[str, str] = {}
    for owner, tasks in grouped.items():
        completed = state["lane_receipts"].get(owner)
        if completed:
            commit = completed.get("commit")
            if not commit or git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}", check=False) != commit:
                raise FactoryError(f"resume cannot resolve completed lane commit for {owner}")
            lane_commits_by_owner[owner] = commit
            continue
        workspace, branch = ensure_lane_workspace(repo, run, state, owner)
        recovered = recover_committed_lane(
            run, state, owner, tasks, workspace, branch, config["limits"]
        )
        if recovered is not None:
            state["lane_receipts"][owner] = {
                "branch": branch,
                "commit": recovered["commit"],
                "receipt": recovered["receipt"],
            }
            lane_commits_by_owner[owner] = recovered["commit"]
            save_state(
                run,
                state,
                "lane_recovered",
                {"owner": owner, "commit": recovered["commit"]},
            )
            continue
        lane_specs.append((owner, tasks, workspace, branch))
    first_failure: Exception | None = None
    if lane_specs:
        enforce_dispatch_limits(state, config["limits"], "implementation batch")
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
                    config["evidence"],
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
                save_state(
                    run,
                    state,
                    "lane_completed",
                    {"owner": owner, "commit": completed["commit"]},
                )
    if first_failure is not None:
        raise first_failure
    enforce_dispatch_limits(state, config["limits"], "review:1")
    lane_commits = [lane_commits_by_owner[owner] for owner in grouped]
    integration_path = run / "worktrees" / "integration"
    integration_branch = f"factory/{state['id']}/integration"
    if state.get("integration"):
        integration = state["integration"]
        integration_path = Path(integration["path"])
    elif integration_path.exists() or git(
        repo, "rev-parse", "--verify", integration_branch, check=False
    ):
        if not integration_path.exists():
            git(repo, "worktree", "add", str(integration_path), integration_branch)
        if git(integration_path, "branch", "--show-current") != integration_branch:
            raise FactoryError("resume found an unexpected integration branch")
        if worktree_changed_files(integration_path):
            raise FactoryError("resume found ambiguous uncommitted integration changes")
        for commit in lane_commits:
            ancestor = subprocess.run(
                ["git", "-C", str(integration_path), "merge-base", "--is-ancestor", commit, "HEAD"],
                check=False,
            )
            if ancestor.returncode:
                git(integration_path, "cherry-pick", commit)
        changed = git(
            integration_path, "diff", "--name-only", f"{state['base_commit']}..HEAD"
        ).splitlines()
        integration = {
            "path": str(integration_path),
            "branch": integration_branch,
            "commit": git(integration_path, "rev-parse", "HEAD"),
            "changed_files": changed,
        }
    else:
        integration = integrate_lanes(repo, run, state, lane_commits)
    state["integration"] = integration
    state["phase"] = "reviewing"
    save_state(run, state, "integration_completed", {"commit": integration["commit"]})
    return Path(integration["path"])


def continue_review(
    run: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    repo: Path,
    integration_path: Path,
) -> dict[str, Any]:
    final_evidence = None
    final_review = None
    start_cycle = 1
    if state["cycles"]:
        last_cycle = state["cycles"][-1]
        cycle = last_cycle["cycle"]
        if last_cycle["review"]["verdict"] == "pass":
            final_evidence = last_cycle["evidence"]
            final_review = last_cycle["review"]
        elif cycle == config["review"]["max_cycles"]:
            state["phase"] = "human_required"
            state["final_review"] = last_cycle["review"]
            save_state(run, state, "repair_budget_exhausted", {"cycles": cycle})
            return {"ok": False, "phase": state["phase"], "run": str(run),
                    "cycles": cycle, "issues": last_cycle["review"]["issues"],
                    "usage": state["usage"]}
        else:
            last_cycle["repairs"] = run_repair(
                run,
                state,
                config,
                integration_path,
                cycle,
                last_cycle["review"]["issues"],
                last_cycle,
            )
            state["integration"]["commit"] = git(integration_path, "rev-parse", "HEAD")
            save_state(
                run,
                state,
                "repair_completed",
                {"cycle": cycle, "commit": state["integration"]["commit"]},
            )
            start_cycle = cycle + 1
    for cycle in range(start_cycle, config["review"]["max_cycles"] + 1):
        if final_evidence is not None:
            break
        state["operation"] = {"kind": "capture", "cycle": cycle}
        save_state(run, state, "evidence_capture_started", {"cycle": cycle})
        try:
            evidence = capture_evidence(run, state, config, integration_path, cycle)
        except EvidenceFailure as failure:
            evidence = failure.evidence
        state["integration"]["commit"] = evidence["source_commit"]
        review_context = {
            "request": state["request"],
            "plan": state["plan"],
            "integration": state["integration"],
            "evidence": evidence,
            "cycle": cycle,
            "project_memory": durable_project_memory(run),
        }
        reviewer_receipt = None
        review = None
        for attempt in range(1, 3):
            enforce_dispatch_limits(state, config["limits"], f"review:{cycle}:attempt:{attempt}")
            state["operation"] = {
                "kind": "review",
                "cycle": cycle,
                "attempt": attempt,
            }
            save_state(
                run,
                state,
                "reviewer_started",
                {"cycle": cycle, "attempt": attempt},
            )
            reviewer_receipt = invoke_agent(
                run,
                state,
                config["review"],
                f"review:{cycle}",
                integration_path,
                review_context,
                config["limits"],
            )
            record_usage(state, reviewer_receipt)
            reviewer_changes = worktree_changed_files(integration_path)
            if reviewer_changes:
                raise FactoryError(
                    "reviewer mutated the integration worktree: " + ", ".join(reviewer_changes)
                )
            atomic_json(
                run / "receipts" / f"reviewer-{cycle}-attempt-{attempt}.json",
                reviewer_receipt,
            )
            try:
                review = review_output(reviewer_receipt, evidence, state["plan"])
                validation_error = None
            except FactoryError as error:
                validation_error = str(error)
            save_state(
                run,
                state,
                "reviewer_attempt_completed",
                {"cycle": cycle, "attempt": attempt, "validation_error": validation_error},
            )
            if validation_error is None:
                break
            if attempt == 2:
                raise FactoryError(
                    f"reviewer could not produce valid output: {validation_error}"
                )
            review_context = {
                **review_context,
                "previous_invalid_review": reviewer_receipt.get("output"),
                "controller_validation_error": validation_error,
                "repair_instruction": (
                    "Return a complete corrected review for the same evidence. "
                    "Change only what the controller error requires."
                ),
            }
        if reviewer_receipt is None or review is None:
            raise FactoryError("reviewer validation ended without a typed result")
        cycle_record = {"cycle": cycle, "evidence": evidence, "review": review,
                        "review_receipt": reviewer_receipt, "repairs": []}
        state["cycles"].append(cycle_record)
        state.pop("operation", None)
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
        cycle_record["repairs"] = run_repair(
            run, state, config, integration_path, cycle, review["issues"], cycle_record
        )
        state["integration"]["commit"] = git(integration_path, "rev-parse", "HEAD")
        save_state(run, state, "repair_completed", {"cycle": cycle,
                                                     "commit": state["integration"]["commit"]})
    if final_evidence is None or final_review is None:
        raise FactoryError("review loop ended without a final evidence-backed verdict")
    refresh_completed_repository_intelligence(
        run, state, config, integration_path
    )
    state["operation"] = {"kind": "merge"}
    save_state(
        run,
        state,
        "merge_started",
        {"commit": git(integration_path, "rev-parse", "HEAD")},
    )
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
        state["phase"] = "delivery_ready" if config["delivery"]["enabled"] else "merged"
    state["merge"] = merge
    state.pop("operation", None)
    save_state(run, state, "merge_authorized" if merge["status"] == "approved" else "merged", merge)
    atomic_json(run / "receipt.json", {"schema": "pi-graph-factory.receipt.v1",
                                        "run": state["id"], "phase": state["phase"],
                                        "plan_sha256": state["approved_plan_sha256"],
                                        "evidence_sha256": final_evidence["sha256"],
                                        "review": final_review, "merge": merge,
                                        "usage": state["usage"]})
    return {"ok": True, "phase": state["phase"], "run": str(run),
            "cycles": len(state["cycles"]), "merge": merge, "usage": state["usage"]}


def active_agent_records(run: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted((run / "active").glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            pid = int(record["pid"])
            os.kill(pid, 0)
            record["alive"] = True
        except ProcessLookupError:
            record["alive"] = False
        except (OSError, ValueError, KeyError):
            record = {"path": str(path), "alive": False, "invalid": True}
        record["path"] = str(path)
        records.append(record)
    return records


def reconcile_active_agents(run: Path, terminate: bool, grace_seconds: int) -> None:
    for record in active_agent_records(run):
        path = Path(record["path"])
        if not record.get("alive"):
            path.unlink(missing_ok=True)
            continue
        if not terminate:
            raise FactoryError(
                f"factory-owned adapter is still active for {record.get('role')}; "
                "retry resume with --terminate-active after inspection"
            )
        pid = int(record["pid"])
        role = str(record.get("role", ""))
        command = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "command="], text=True, encoding="utf-8"
        ).strip()
        if os.getpgid(pid) != int(record.get("process_group", -1)) or "--role" not in command or role not in command:
            raise FactoryError(f"refusing to terminate unverified process {pid} for {role}")
        os.killpg(pid, signal.SIGTERM)
        deadline = time.monotonic() + grace_seconds
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            os.killpg(pid, signal.SIGKILL)
        path.unlink(missing_ok=True)


def continue_factory(run: Path, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if state["approved_plan_sha256"] != state["plan_sha256"]:
        raise FactoryError("factory run requires the current plan to be explicitly approved")
    recovered_merge = recover_applied_merge(run, state, config)
    if recovered_merge is not None:
        return recovered_merge
    repo = validate_run_repository(state)
    if state["phase"] in {"approved", "implementing"}:
        integration_path = continue_implementation(run, state, config, repo)
    elif state["phase"] == "reviewing" and state.get("integration"):
        integration_path = Path(state["integration"]["path"])
        prepare_review_workspace_for_resume(run, state, config, integration_path)
    else:
        raise FactoryError(f"factory cannot continue during phase {state['phase']}")
    return continue_review(run, state, config, repo, integration_path)


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] != "approved":
        raise FactoryError("factory run requires the current plan to be explicitly approved")
    return continue_factory(run, state, load_frozen_config(run, state))


def cmd_resume(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] not in {"implementing", "reviewing"}:
        raise FactoryError(f"factory run is not resumable during phase {state['phase']}")
    config = load_frozen_config(run, state)
    reconcile_active_agents(
        run,
        terminate=args.terminate_active,
        grace_seconds=config["limits"]["termination_grace_seconds"],
    )
    state["usage"] = observed_usage(run)
    state.pop("last_error", None)
    save_state(run, state, "resume_started", {"phase": state["phase"]})
    return continue_factory(run, state, config)


def cmd_inspect(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    lanes = {}
    for owner in tasks_by_owner(state) if state.get("plan") else []:
        workspace = run / "worktrees" / owner
        lanes[owner] = {
            "checkpointed": owner in state.get("lane_receipts", {}),
            "worktree": str(workspace),
            "exists": workspace.exists(),
            "changed_files": worktree_changed_files(workspace) if workspace.exists() else [],
        }
    resumable = state["phase"] in {"implementing", "reviewing"}
    return {
        "ok": True,
        "run": str(run),
        "phase": state["phase"],
        "operation": state.get("operation"),
        "resumable": resumable,
        "next_command": f"factory resume --run {run}" if resumable else None,
        "last_error": state.get("last_error"),
        "active_agents": active_agent_records(run),
        "lanes": lanes,
        "integration": state.get("integration"),
        "completed_cycles": len(state.get("cycles", [])),
        "artifacts": {
            "state": str(run / "state.json"),
            "events": str(run / "events.jsonl"),
            "intake": [str(path) for path in sorted((run / "intake").glob("*"))],
            "plans": [str(path) for path in sorted((run / "plans").glob("*.json"))],
            "contexts": [str(path) for path in sorted((run / "contexts").glob("*.json"))],
            "receipts": [str(path) for path in sorted((run / "receipts").glob("*.json"))],
            "evidence": [str(path) for path in sorted((run / "evidence").glob("*.json"))],
            "intelligence": [
                str(path) for path in sorted((run / "intelligence").glob("*.json"))
            ],
        },
    }


def cmd_deliver(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] not in {"delivery_ready", "delivery_failed"}:
        raise FactoryError(f"delivery cannot run during phase {state['phase']}")
    config = load_frozen_config(run, state)
    if not config["delivery"]["enabled"]:
        raise FactoryError("delivery is disabled in the frozen factory contract")
    if not state.get("merge") or state["merge"].get("status") != "merged":
        raise FactoryError("delivery requires an applied guarded merge")
    repo = Path(state["repo"])
    if git(repo, "rev-parse", "HEAD") != state["merge"]["commit"]:
        raise FactoryError("target repository drifted after guarded merge")
    ensure_clean(repo)
    result = execute_delivery(
        repo,
        config["delivery"],
        command_timeout_seconds=config["limits"]["command_timeout_seconds"],
        termination_grace_seconds=config["limits"]["termination_grace_seconds"],
    )
    state["delivery"] = result
    if result["status"] == "deployed":
        state["phase"] = "delivered"
        state.pop("last_error", None)
        event = "delivery_completed"
    else:
        state["phase"] = "delivery_failed"
        state["last_error"] = {
            "at": now(),
            "phase": "delivery",
            "type": "DeliveryFailure",
            "message": result["failure"],
        }
        event = "delivery_failed"
    atomic_json(run / "delivery.json", result)
    receipt_path = run / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["phase"] = state["phase"]
    receipt["delivery"] = result
    atomic_json(receipt_path, receipt)
    save_state(run, state, event, result)
    return {"ok": result["status"] == "deployed", "phase": state["phase"],
            "run": str(run), "delivery": result}


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    state = load_state(Path(args.run).resolve())
    return {
        "ok": state["phase"] not in {"failed", "human_required"} and not state.get("last_error"),
        "state": state,
    }


def observed_usage(run: Path) -> dict[str, Any]:
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
    return observed


def record_transition_failure(run: Path, error: BaseException) -> None:
    state = load_state(run)
    state["usage"] = observed_usage(run)
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
    init.add_argument("--intake-mode", choices=INTAKE_MODES, default="direct")
    init.add_argument("--intake-ledger")
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
    resume = commands.add_parser("resume")
    resume.add_argument("--run", required=True)
    resume.add_argument("--terminate-active", action="store_true")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--run", required=True)
    deliver = commands.add_parser("deliver")
    deliver.add_argument("--run", required=True)
    status = commands.add_parser("status")
    status.add_argument("--run", required=True)
    return root


COMMANDS = {"init": cmd_init, "plan": cmd_plan, "answer": cmd_answer,
            "approve": cmd_approve, "run": cmd_run, "resume": cmd_resume,
            "inspect": cmd_inspect, "deliver": cmd_deliver, "status": cmd_status}


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in {"plan", "answer", "approve", "run", "resume", "deliver"}:
            run = Path(args.run).resolve()
            with run_lock(run):
                try:
                    payload = COMMANDS[args.command](args)
                except (FactoryError, OSError, ValueError, json.JSONDecodeError) as error:
                    if args.command in {"run", "resume", "deliver"}:
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
