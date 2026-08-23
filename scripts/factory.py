#!/usr/bin/env python3
"""Durable trigger-to-merge controller for Pi Graph Factory."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
FACTORY_SCHEMA = json.loads((ROOT / "schemas" / "factory.schema.json").read_text())
TERMINAL = {"human_required", "merge_ready", "merged", "failed"}


class FactoryError(RuntimeError):
    pass


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
    result = subprocess.run(["git", "-C", str(repo), *args], text=True,
                            capture_output=True, check=False)
    if check and result.returncode:
        raise FactoryError(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


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
        (path / ".gitignore").write_text(".factory/\n", encoding="utf-8")
        git(path, "add", ".gitignore")
        git(path, "commit", "-m", "Initialize repository")
    if not (path / ".git").exists():
        raise FactoryError(f"not a Git repository: {path}")
    ensure_clean(path)
    return path


def validate_plan(plan: dict[str, Any], implementers: set[str]) -> None:
    required = {"summary", "tasks", "acceptance", "risks", "open_questions"}
    if not required <= set(plan):
        raise FactoryError(f"plan is missing fields: {sorted(required - set(plan))}")
    if not isinstance(plan["tasks"], list) or not plan["tasks"]:
        raise FactoryError("plan must contain at least one task")
    seen_ids: set[str] = set()
    ownership: dict[str, str] = {}
    for task in plan["tasks"]:
        if not {"id", "owner", "files", "acceptance"} <= set(task):
            raise FactoryError("every task needs id, owner, files, and acceptance")
        if task["id"] in seen_ids:
            raise FactoryError(f"duplicate task id: {task['id']}")
        seen_ids.add(task["id"])
        if task["owner"] not in implementers:
            raise FactoryError(f"unknown task owner {task['owner']!r}")
        for pattern in task["files"]:
            if pattern in ownership and ownership[pattern] != task["owner"]:
                raise FactoryError(
                    f"conflicting file ownership for {pattern}: {ownership[pattern]} and {task['owner']}")
            ownership[pattern] = task["owner"]
    questions = plan["open_questions"]
    if not isinstance(questions, list):
        raise FactoryError("open_questions must be an array")
    for question in questions:
        if not {"id", "question", "blocking"} <= set(question):
            raise FactoryError("every open question needs id, question, and blocking")


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
    identifier = args.id or f"factory-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
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
    }
    save_state(run, state, "trigger_received", {"request_sha256": state["request_sha256"]})
    return {"ok": True, "run": str(run), "phase": state["phase"], "base_commit": base}


def cmd_plan(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run).resolve()
    state = load_state(run)
    if state["phase"] not in {"intake", "clarification", "awaiting_plan_approval"}:
        raise FactoryError(f"cannot submit a plan during phase {state['phase']}")
    plan = json.loads(Path(args.file).read_text(encoding="utf-8"))
    config = load_frozen_config(run, state)
    validate_plan(plan, {item["id"] for item in config["implementers"]})
    unanswered = [item for item in plan["open_questions"]
                  if item.get("blocking") and item["id"] not in state["answers"]]
    state["plan"] = plan
    state["plan_sha256"] = digest_json(plan)
    state["approved_plan_sha256"] = None
    state["phase"] = "clarification" if unanswered else "awaiting_plan_approval"
    save_state(run, state, "plan_submitted", {
        "plan_sha256": state["plan_sha256"], "blocking_questions": [x["id"] for x in unanswered]})
    return {"ok": True, "phase": state["phase"], "plan_sha256": state["plan_sha256"],
            "open_questions": unanswered}


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


def invoke_agent(run: Path, state: dict[str, Any], agent: dict[str, Any], role: str,
                 cwd: Path, context: dict[str, Any]) -> dict[str, Any]:
    context_path = run / "contexts" / f"{role.replace(':', '-')}.json"
    atomic_json(context_path, context)
    command = [*adapter_command(), "--role", role, "--harness", agent["harness"],
               "--model", agent["model"], "--instructions", agent["instructions"],
               "--context", str(context_path)]
    for skill in agent.get("skills", []):
        command.extend(["--skill", skill])
    if agent.get("tools"):
        command.extend(["--tools", ",".join(agent["tools"])])
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False,
                            env={**os.environ, "WORKFLOW_DIR": str(ROOT)})
    if result.returncode:
        raise FactoryError(f"{role} adapter failed: {(result.stderr or result.stdout)[-2000:]}")
    try:
        payload = json.loads(result.stdout)
    except ValueError as error:
        raise FactoryError(f"{role} adapter returned invalid JSON") from error
    required = {"status", "harness", "model", "role", "output", "usage"}
    if not required <= set(payload):
        raise FactoryError(f"{role} adapter receipt missing {sorted(required - set(payload))}")
    if payload["harness"] != agent["harness"] or payload["model"] != agent["model"]:
        raise FactoryError(f"{role} adapter identity drift")
    payload["receipt_sha256"] = digest_json(payload)
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


def file_receipt(path: Path) -> dict[str, Any]:
    return {"path": str(path), "bytes": path.stat().st_size,
            "sha256": digest_bytes(path.read_bytes())}


def capture_evidence(run: Path, state: dict[str, Any], config: dict[str, Any],
                     integration: Path, cycle: int) -> dict[str, Any]:
    tests = []
    for command in config["evidence"].get("test_commands", []):
        result = subprocess.run(["bash", "-c", command], cwd=integration, text=True,
                                capture_output=True, check=False)
        tests.append({"command": command, "passed": result.returncode == 0,
                      "output": (result.stdout + result.stderr)[-2000:]})
    evidence_files = []
    for raw in [*config["evidence"]["screenshots"], config["evidence"].get("video")]:
        if not raw:
            continue
        path = integration / raw
        if not path.is_file() or not path.stat().st_size:
            raise FactoryError(f"required evidence missing: {raw}")
        evidence_files.append(file_receipt(path))
    if not tests or not all(item["passed"] for item in tests):
        raise FactoryError("one or more evidence test commands failed")
    source_commit = git(integration, "rev-parse", "HEAD")
    receipt = {"cycle": cycle, "captured_at": now(), "source_commit": source_commit,
               "approved_plan_sha256": state["approved_plan_sha256"],
               "files": evidence_files, "tests": tests}
    receipt["sha256"] = digest_json(receipt)
    atomic_json(run / "evidence" / f"cycle-{cycle}.json", receipt)
    return receipt


def review_output(receipt: dict[str, Any]) -> dict[str, Any]:
    output = receipt.get("output")
    if not isinstance(output, dict) or output.get("verdict") not in {"pass", "repair"}:
        raise FactoryError("reviewer output must contain verdict pass|repair")
    if not isinstance(output.get("issues"), list) or not isinstance(output.get("evidence"), list):
        raise FactoryError("reviewer output must contain issues and evidence arrays")
    if not output["evidence"]:
        raise FactoryError("reviewer supplied no evidence")
    if output["verdict"] == "pass" and output["issues"]:
        raise FactoryError("reviewer cannot pass with unresolved issues")
    if output["verdict"] == "repair" and not output["issues"]:
        raise FactoryError("repair verdict requires issues")
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
        receipt = invoke_agent(run, state, agents[owner], f"repair:{cycle}:{owner}", integration,
                               {"request": state["request"], "plan": state["plan"],
                                "issues": owned, "cycle": cycle})
        output = receipt["output"]
        if receipt["status"] != "passed" or not isinstance(output, dict) or not output.get("checks"):
            raise FactoryError(f"repair agent {owner} did not return passing checks")
        receipts.append(receipt)
    git(integration, "add", "-A")
    if git(integration, "status", "--porcelain"):
        git(integration, "commit", "-m", f"factory: repair cycle {cycle}")
    else:
        raise FactoryError("repair cycle produced no repository change")
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
    state["phase"] = "implementing"
    save_state(run, state, "implementation_started", {"owners": sorted(tasks_by_owner)})
    lane_commits = []
    for owner, tasks in tasks_by_owner.items():
        workspace, branch = provision_lane(repo, run, state["id"], owner, state["base_commit"])
        receipt = invoke_agent(run, state, agents[owner], f"implement:{owner}", workspace,
                               {"request": state["request"], "plan": state["plan"], "tasks": tasks})
        output = receipt["output"]
        if receipt["status"] != "passed" or not isinstance(output, dict) or not output.get("checks"):
            raise FactoryError(f"implementer {owner} did not return a passing receipt")
        commit = commit_lane(workspace, owner)
        lane_commits.append(commit)
        state["lane_receipts"][owner] = {"branch": branch, "commit": commit, "receipt": receipt}
        save_state(run, state, "lane_completed", {"owner": owner, "commit": commit})
    integration = integrate_lanes(repo, run, state, lane_commits)
    state["integration"] = integration
    state["phase"] = "reviewing"
    save_state(run, state, "integration_completed", {"commit": integration["commit"]})
    integration_path = Path(integration["path"])
    final_evidence = None
    final_review = None
    for cycle in range(1, config["review"]["max_cycles"] + 1):
        evidence = capture_evidence(run, state, config, integration_path, cycle)
        reviewer_receipt = invoke_agent(
            run, state, config["review"], f"review:{cycle}", integration_path,
            {"request": state["request"], "plan": state["plan"],
             "integration": state["integration"], "evidence": evidence, "cycle": cycle})
        review = review_output(reviewer_receipt)
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
                    "cycles": cycle, "issues": review["issues"]}
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
                                        "review": final_review, "merge": merge})
    return {"ok": True, "phase": state["phase"], "run": str(run),
            "cycles": len(state["cycles"]), "merge": merge}


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    state = load_state(Path(args.run).resolve())
    return {"ok": state["phase"] not in {"failed", "human_required"}, "state": state}


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
    plan.add_argument("--file", required=True)
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
        payload = COMMANDS[args.command](args)
    except (FactoryError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, separators=(",", ":")))
        return 2
    print(json.dumps(payload, separators=(",", ":")))
    return 0 if payload.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
