#!/usr/bin/env python3
"""Build or refresh the target repository's deterministic Graphify code map."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any


CODE_SUFFIXES = {
    ".bash", ".c", ".cc", ".cpp", ".cs", ".css", ".dart", ".elixir", ".ex",
    ".exs", ".go", ".groovy", ".h", ".hpp", ".html", ".java", ".js", ".jsx",
    ".kt", ".kts", ".less", ".lua", ".m", ".mm", ".php", ".pl", ".pm", ".proto",
    ".ps1", ".py", ".r", ".rb", ".rs", ".sass", ".scala", ".scss", ".sh", ".sol",
    ".sql", ".svelte", ".swift", ".ts", ".tsx", ".vue", ".zig",
}
AUTO_INSTALL_PACKAGE = "graphifyy==0.9.48"


class IntelligenceError(RuntimeError):
    pass


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise IntelligenceError((completed.stderr or completed.stdout).strip())
    return completed.stdout.strip()


def add_local_exclude(repo: Path) -> None:
    common = Path(git(repo, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = repo / common
    path = common.resolve() / "info" / "exclude"
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if "graphify-out/" not in current.splitlines():
        path.write_text(current.rstrip() + "\ngraphify-out/\n", encoding="utf-8")


def has_code(repo: Path) -> bool:
    tracked = git(repo, "ls-files", "-z").split("\0")
    return any(Path(path).suffix.lower() in CODE_SUFFIXES for path in tracked if path)


def graphify_command(repo: Path, auto_install: bool) -> list[str]:
    override = os.environ.get("PI_GRAPH_FACTORY_GRAPHIFY")
    if override:
        return shlex.split(override)
    executable = shutil.which("graphify")
    if executable:
        return [executable]
    recorded_python = repo / "graphify-out" / ".graphify_python"
    if recorded_python.is_file():
        interpreter = recorded_python.read_text(encoding="utf-8").strip()
        if interpreter and Path(interpreter).is_file():
            return [interpreter, "-m", "graphify"]
    if importlib.util.find_spec("graphify") is not None:
        return [sys.executable, "-m", "graphify"]
    uv = shutil.which("uv")
    if auto_install and uv:
        return [uv, "tool", "run", "--from", AUTO_INSTALL_PACKAGE, "graphify"]
    raise IntelligenceError(
        "Graphify is required for repository planning; install graphifyy or enable "
        "intelligence.auto_install with uv available"
    )


def inspect_graph(graph: Path) -> tuple[int, int]:
    try:
        payload = json.loads(graph.read_text(encoding="utf-8"))
        node_count = len(payload["nodes"])
        edge_count = len(payload.get("edges", payload.get("links", [])))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise IntelligenceError(f"Graphify produced an invalid graph: {error}") from error
    if node_count == 0:
        raise IntelligenceError("Graphify produced an empty graph for a code repository")
    return node_count, edge_count


def ready_receipt(
    graph: Path,
    commit: str,
    base: list[str],
    *,
    refreshed: bool,
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    node_count, edge_count = inspect_graph(graph)
    receipt = {
        "provider": "graphify",
        "status": "ready",
        "source_commit": commit,
        "graph": str(graph),
        "nodes": node_count,
        "edges": edge_count,
        "refreshed": refreshed,
        "query_command": shlex.join([
            *base, "query", "<question>", "--graph", str(graph), "--budget", "2000"
        ]),
    }
    if execution is not None:
        receipt["execution"] = execution
    return receipt


def run_process(
    command: list[str],
    cwd: Path,
    timeout_seconds: int | None,
    termination_grace_seconds: int,
) -> dict[str, Any]:
    process = subprocess.Popen(
        command,
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
        "timed_out": timed_out,
        "output": (stdout + stderr)[-4000:],
    }


def ensure_repository_intelligence(
    repo: Path,
    *,
    auto_install: bool,
    timeout_seconds: int | None,
    termination_grace_seconds: int,
) -> dict[str, Any]:
    repo = repo.resolve()
    add_local_exclude(repo)
    commit = git(repo, "rev-parse", "HEAD")
    if not has_code(repo):
        return {
            "provider": "graphify",
            "status": "deferred",
            "reason": "repository has no supported code yet",
            "source_commit": commit,
            "graph": None,
        }
    base = graphify_command(repo, auto_install)
    graph = repo / "graphify-out" / "graph.json"
    metadata = repo / "graphify-out" / "factory-metadata.json"
    try:
        previous = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        previous = {}
    if previous.get("source_commit") == commit and graph.is_file():
        try:
            return ready_receipt(graph, commit, base, refreshed=False)
        except IntelligenceError:
            pass
    command = [
        *base,
        "extract",
        str(repo),
        "--code-only",
        "--no-cluster",
        "--out",
        str(repo),
    ]
    execution = run_process(command, repo, timeout_seconds, termination_grace_seconds)
    if not execution["passed"]:
        raise IntelligenceError(
            "Graphify repository extraction failed: " + execution["output"][-1000:]
        )
    receipt = ready_receipt(graph, commit, base, refreshed=True, execution=execution)
    metadata.write_text(
        json.dumps({"provider": "graphify", "source_commit": commit}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--auto-install", action="store_true")
    parser.add_argument("--optional", action="store_true")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--termination-grace", type=int, default=30)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = ensure_repository_intelligence(
            args.repo,
            auto_install=args.auto_install,
            timeout_seconds=args.timeout,
            termination_grace_seconds=args.termination_grace,
        )
    except IntelligenceError as error:
        if not args.optional:
            print(json.dumps({"ok": False, "error": str(error)}, separators=(",", ":")))
            return 2
        receipt = {
            "provider": "graphify",
            "status": "unavailable",
            "reason": str(error),
            "source_commit": git(args.repo.resolve(), "rev-parse", "HEAD"),
            "graph": None,
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **receipt}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
