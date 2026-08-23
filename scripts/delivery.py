#!/usr/bin/env python3
"""Execute an explicit deploy, health, and rollback contract."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

import yaml


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def command_receipt(
    cwd: Path,
    command: str,
    timeout_seconds: int | None,
    termination_grace_seconds: int,
) -> dict[str, Any]:
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
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
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
    return {
        "command": command,
        "passed": process.returncode == 0 and not timed_out,
        "exit_code": process.returncode,
        "output": (stdout + stderr)[-4000:],
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
    }


def run_until_failure(
    cwd: Path,
    commands: list[str],
    timeout_seconds: int | None,
    termination_grace_seconds: int,
) -> list[dict[str, Any]]:
    receipts = []
    for command in commands:
        receipt = command_receipt(
            cwd, command, timeout_seconds, termination_grace_seconds
        )
        receipts.append(receipt)
        if not receipt["passed"]:
            break
    return receipts


def git_value(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(cwd), *args], text=True, encoding="utf-8"
    ).strip()


def execute_delivery(
    cwd: Path,
    spec: dict[str, Any],
    *,
    command_timeout_seconds: int | None = None,
    termination_grace_seconds: int = 5,
) -> dict[str, Any]:
    before_commit = git_value(cwd, "rev-parse", "HEAD")
    before_status = git_value(cwd, "status", "--porcelain")
    if before_status:
        raise ValueError("delivery requires a clean target repository")

    deploy = run_until_failure(
        cwd,
        spec["deploy_commands"],
        command_timeout_seconds,
        termination_grace_seconds,
    )
    deploy_passed = bool(deploy) and all(item["passed"] for item in deploy)
    health = (
        run_until_failure(
            cwd,
            spec["health_commands"],
            command_timeout_seconds,
            termination_grace_seconds,
        )
        if deploy_passed
        else []
    )
    health_passed = bool(health) and all(item["passed"] for item in health)
    failure = None
    if not deploy_passed:
        failure = "deploy command failed"
    elif not health_passed:
        failure = "production health command failed"

    after_status = git_value(cwd, "status", "--porcelain")
    after_commit = git_value(cwd, "rev-parse", "HEAD")
    if after_commit != before_commit or after_status != before_status:
        failure = "delivery commands mutated the reviewed repository boundary"

    rollback = []
    status = "deployed"
    if failure is not None:
        rollback = run_until_failure(
            cwd,
            spec["rollback_commands"],
            command_timeout_seconds,
            termination_grace_seconds,
        )
        rolled_back = bool(rollback) and all(item["passed"] for item in rollback)
        rolled_back = rolled_back and (
            git_value(cwd, "rev-parse", "HEAD") == before_commit
            and git_value(cwd, "status", "--porcelain") == before_status
        )
        status = "rolled_back" if rolled_back else "failed"

    return {
        "status": status,
        "started_from_commit": before_commit,
        "completed_at": now(),
        "deploy": deploy,
        "health": health,
        "rollback": rollback,
        "failure": failure,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    delivery = config["delivery"]
    if not delivery.get("enabled"):
        raise SystemExit("delivery is disabled")
    limits = config.get("limits", {})
    result = execute_delivery(
        args.cwd.resolve(),
        delivery,
        command_timeout_seconds=limits.get("command_timeout_seconds"),
        termination_grace_seconds=limits.get("termination_grace_seconds", 5),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["status"] == "deployed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
