#!/usr/bin/env python3
"""Build or refresh the target repository's deterministic Graphify code map."""

from __future__ import annotations

import argparse
import hashlib
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
SEMANTIC_AUTO_INSTALL_PACKAGE = "graphifyy[openai]==0.9.48"
GRAPHIFY_KEY_ENV = {
    "claude": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "openai": "OPENAI_API_KEY",
}
GRAPHIFY_BASE_URL_ENV = {
    "claude": "ANTHROPIC_BASE_URL",
    "deepseek": "DEEPSEEK_BASE_URL",
    "gemini": "GEMINI_BASE_URL",
    "kimi": "KIMI_BASE_URL",
    "openai": "OPENAI_BASE_URL",
}


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


def find_uv() -> str | None:
    executable = shutil.which("uv")
    if executable:
        return executable
    sibling = Path(sys.executable).with_name("uv")
    return str(sibling) if sibling.is_file() else None


def graphify_command(repo: Path, auto_install: bool, semantic: bool = False) -> list[str]:
    override = os.environ.get("PI_GRAPH_FACTORY_GRAPHIFY")
    if override:
        return shlex.split(override)
    uv = find_uv()
    if semantic and auto_install and uv:
        return [uv, "tool", "run", "--from", SEMANTIC_AUTO_INSTALL_PACKAGE, "graphify"]
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
    enrichment: dict[str, Any],
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
        "enrichment": enrichment,
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
    environment: dict[str, str] | None = None,
    redact_values: list[str] | None = None,
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
        env=environment,
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
    output = stdout + stderr
    for value in redact_values or []:
        if value:
            output = output.replace(value, "[REDACTED]")
    return {
        "command": command,
        "passed": process.returncode == 0 and not timed_out,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "output": output[-4000:],
    }


def enrichment_profile(value: dict[str, Any] | None) -> dict[str, Any]:
    value = value or {}
    if not value.get("enabled", False):
        return {"enabled": False, "status": "disabled"}
    return {
        "enabled": True,
        "status": "ready",
        "required": bool(value.get("required", True)),
        "backend": value.get("backend", "deepseek"),
        "model": value.get("model", "deepseek-v4-flash"),
        "mode": value.get("mode", "deep"),
        "base_url": value.get("base_url"),
        "pi_auth_model": value.get("pi_auth_model"),
    }


def profile_digest(profile: dict[str, Any]) -> str:
    payload = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def pi_api_key(model: str) -> str:
    pi = shutil.which("pi")
    if not pi:
        raise IntelligenceError("Graphify enrichment auth requires Pi on PATH")
    completed = subprocess.run(
        [pi, "auth", "print-api-key", "--model", model],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    key = completed.stdout.strip()
    if completed.returncode or not key:
        detail = completed.stderr.strip() or "Pi returned no credential"
        raise IntelligenceError(f"cannot obtain Graphify enrichment credential: {detail}")
    return key


def enriched_command(
    base: list[str],
    repo: Path,
    profile: dict[str, Any],
) -> tuple[list[str], dict[str, str], list[str]]:
    command = [*base, "extract", str(repo)]
    environment = os.environ.copy()
    if not profile["enabled"]:
        return (
            [*command, "--code-only", "--no-cluster", "--out", str(repo)],
            environment,
            [],
        )

    backend = profile["backend"]
    model = profile["model"]
    if not isinstance(backend, str) or not backend:
        raise IntelligenceError("Graphify enrichment backend must not be empty")
    if not isinstance(model, str) or not model:
        raise IntelligenceError("Graphify enrichment model must not be empty")
    command.extend(["--backend", backend, "--model", model])
    if profile["mode"] == "deep":
        command.extend(["--mode", "deep"])
    elif profile["mode"] != "standard":
        raise IntelligenceError("Graphify enrichment mode must be standard or deep")

    auth_model = profile.get("pi_auth_model")
    if auth_model:
        if not isinstance(auth_model, str):
            raise IntelligenceError("Graphify enrichment pi_auth_model must be a string")
        key_env = GRAPHIFY_KEY_ENV.get(backend)
        if not key_env:
            raise IntelligenceError(
                f"Pi credential bridging is not supported for Graphify backend {backend!r}"
            )
        environment[key_env] = pi_api_key(auth_model)
    base_url = profile.get("base_url")
    if base_url:
        if not isinstance(base_url, str):
            raise IntelligenceError("Graphify enrichment base_url must be a string")
        base_env = GRAPHIFY_BASE_URL_ENV.get(backend)
        if not base_env:
            raise IntelligenceError(
                f"custom base URLs are not supported for Graphify backend {backend!r}"
            )
        environment[base_env] = base_url
    command.extend(["--out", str(repo)])
    secret = environment.get(GRAPHIFY_KEY_ENV.get(backend, ""), "")
    return command, environment, [secret] if secret else []


def ensure_repository_intelligence(
    repo: Path,
    *,
    auto_install: bool,
    timeout_seconds: int | None,
    termination_grace_seconds: int,
    enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    add_local_exclude(repo)
    commit = git(repo, "rev-parse", "HEAD")
    profile = enrichment_profile(enrichment)
    profile_sha256 = profile_digest(profile)
    if not has_code(repo):
        return {
            "provider": "graphify",
            "status": "deferred",
            "reason": "repository has no supported code yet",
            "source_commit": commit,
            "graph": None,
            "enrichment": {**profile, "status": "deferred"},
        }
    base = graphify_command(repo, auto_install, semantic=profile["enabled"])
    graph = repo / "graphify-out" / "graph.json"
    metadata = repo / "graphify-out" / "factory-metadata.json"
    try:
        previous = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        previous = {}
    if (
        previous.get("source_commit") == commit
        and previous.get("profile_sha256") == profile_sha256
        and graph.is_file()
    ):
        try:
            return ready_receipt(
                graph, commit, base, refreshed=False, enrichment=profile
            )
        except IntelligenceError:
            pass
    try:
        command, environment, redactions = enriched_command(base, repo, profile)
    except IntelligenceError as error:
        if profile.get("required", False):
            raise
        profile = {**profile, "status": "unavailable", "reason": str(error)}
        command, environment, redactions = enriched_command(
            base, repo, {"enabled": False, "status": "disabled"}
        )
    execution = run_process(
        command,
        repo,
        timeout_seconds,
        termination_grace_seconds,
        environment,
        redactions,
    )
    if not execution["passed"] and profile["enabled"] and not profile.get("required", True):
        failure = execution["output"][-1000:]
        profile = {
            **profile,
            "status": "unavailable",
            "reason": "semantic extraction failed; used AST-only fallback: " + failure,
        }
        command, environment, redactions = enriched_command(
            base, repo, {"enabled": False, "status": "disabled"}
        )
        execution = run_process(
            command,
            repo,
            timeout_seconds,
            termination_grace_seconds,
            environment,
            redactions,
        )
    if not execution["passed"]:
        raise IntelligenceError(
            "Graphify repository extraction failed: " + execution["output"][-1000:]
        )
    receipt = ready_receipt(
        graph,
        commit,
        base,
        refreshed=True,
        enrichment=profile,
        execution=execution,
    )
    metadata.write_text(
        json.dumps(
            {
                "provider": "graphify",
                "source_commit": commit,
                "profile_sha256": (
                    profile_sha256 if profile.get("status") != "unavailable" else None
                ),
            },
            sort_keys=True,
        ) + "\n",
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
