#!/usr/bin/env python3
"""Read-only localhost dashboard over Pi Graph Factory run ledgers."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import os
import re
import sys
import webbrowser
from collections import defaultdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "dashboard" / "index.html"
LOOPBACK = "127.0.0.1"
SKIP_DIRECTORIES = {
    ".git",
    ".venv",
    "DerivedData",
    "graphify-out",
    "node_modules",
    "__pycache__",
}
ARTIFACT_GROUPS = {
    "Run ledger": ("state.json", "events.jsonl", "factory.yaml", "receipt.json"),
    "Intake": ("intake",),
    "Plans": ("plans",),
    "Contexts": ("contexts",),
    "Receipts": ("receipts",),
    "Logs": ("logs",),
    "Evidence": ("evidence", "worktrees/integration/evidence"),
    "Intelligence": ("intelligence",),
}
RUN_PATH = re.compile(r"(?:^|/)\.factory/runs/[^/]+$")
TEXT_SUFFIXES = {".jsonl", ".log", ".md", ".py", ".sh", ".swift", ".txt", ".yaml", ".yml"}


def iso_from_timestamp(value: float) -> str:
    return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat()


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {}, "top-level JSON value is not an object"
        return value, None
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, f"{type(error).__name__}: {error}"


def discover_run_paths(root: Path) -> list[Path]:
    """Find run directories without descending into their worktrees."""
    if (root / "state.json").is_file() and RUN_PATH.search(root.as_posix()):
        return [root]

    found: set[Path] = set()
    for current, directories, _files in os.walk(root, followlinks=False):
        current_path = Path(current)
        if ".factory" in directories:
            runs = current_path / ".factory" / "runs"
            if runs.is_dir():
                for candidate in runs.iterdir():
                    if candidate.is_dir() and (candidate / "state.json").is_file():
                        found.add(candidate.resolve())
            directories.remove(".factory")
        directories[:] = [
            name for name in directories if name not in SKIP_DIRECTORIES
        ]
    return sorted(found)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def artifact_id(path: Path) -> str:
    return hashlib.sha256(os.fsencode(str(path))).hexdigest()[:24]


def media_type(path: Path) -> str:
    if path.suffix.lower() == ".json":
        return "application/json"
    if path.suffix.lower() in TEXT_SUFFIXES:
        return "text/plain"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def artifact_groups(run: Path) -> tuple[list[dict[str, Any]], dict[str, Path]]:
    groups: list[dict[str, Any]] = []
    lookup: dict[str, Path] = {}
    resolved_run = run.resolve()

    for label, entries in ARTIFACT_GROUPS.items():
        files: set[Path] = set()
        for entry in entries:
            candidate = run / entry
            if candidate.is_file():
                files.add(candidate)
            elif candidate.is_dir():
                for path in candidate.rglob("*"):
                    if path.is_file() and not path.is_symlink():
                        files.add(path)

        items = []
        for path in sorted(files):
            try:
                resolved = path.resolve(strict=True)
                if not is_within(resolved, resolved_run):
                    continue
                metadata = resolved.stat()
            except OSError:
                continue
            identifier = artifact_id(resolved)
            lookup[identifier] = resolved
            items.append(
                {
                    "id": identifier,
                    "path": str(resolved.relative_to(resolved_run)),
                    "bytes": metadata.st_size,
                    "modified_at": iso_from_timestamp(metadata.st_mtime),
                    "media_type": media_type(resolved),
                }
            )
        if items:
            groups.append({"name": label, "items": items})
    return groups, lookup


def safe_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def receipt_usage(run: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records = []
    by_role: defaultdict[str, int] = defaultdict(int)
    for path in sorted((run / "receipts").glob("agent-*.json")):
        receipt, error = read_json(path)
        if error:
            continue
        usage = receipt.get("usage")
        if not isinstance(usage, dict):
            continue
        total = safe_number(usage.get("total"))
        role = receipt.get("role") if isinstance(receipt.get("role"), str) else "unknown"
        model = receipt.get("model") if isinstance(receipt.get("model"), str) else "unknown"
        if total is not None:
            by_role[role] += int(total)
        try:
            recorded_at = iso_from_timestamp(path.stat().st_mtime)
        except OSError:
            continue
        records.append(
            {
                "at": recorded_at,
                "role": role,
                "model": model,
                "input": safe_number(usage.get("input")),
                "output": safe_number(usage.get("output")),
                "total": total,
                "cost": safe_number(usage.get("cost")),
                "unknown": total is None or usage.get("cost") is None,
            }
        )
    return records, dict(sorted(by_role.items(), key=lambda item: (-item[1], item[0])))


def read_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events = []
    errors = []
    if not path.exists():
        return events, ["events.jsonl is missing"]
    try:
        with path.open(encoding="utf-8") as source:
            for number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("event is not an object")
                    events.append(value)
                except (json.JSONDecodeError, ValueError) as error:
                    message = f"events.jsonl line {number}: {error}"
                    errors.append(message)
                    events.append(
                        {
                            "sequence": number,
                            "event": "malformed_event",
                            "phase": "degraded",
                            "payload": {"error": message, "raw": line.rstrip("\n")},
                        }
                    )
    except (OSError, UnicodeError) as error:
        errors.append(f"cannot read events.jsonl: {type(error).__name__}: {error}")
    return events, errors


def text_from_issue(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("message", "error", "type"):
            if isinstance(value.get(key), str):
                return value[key]
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def blockers_from_state(state: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if state.get("last_error"):
        blockers.append(text_from_issue(state["last_error"]))
    pending = state.get("pending_lane_failures")
    if isinstance(pending, dict):
        blockers.extend(text_from_issue(value) for value in pending.values())
    review = state.get("final_review")
    cycles = state.get("cycles")
    if not isinstance(review, dict) and isinstance(cycles, list) and cycles:
        last_cycle = cycles[-1]
        if isinstance(last_cycle, dict):
            review = last_cycle.get("review")
    if isinstance(review, dict) and review.get("verdict") == "repair":
        issues = review.get("issues")
        if isinstance(issues, list):
            blockers.extend(text_from_issue(issue) for issue in issues)
    return list(dict.fromkeys(value for value in blockers if value.strip()))


def active_agents(run: Path) -> list[dict[str, Any]]:
    agents = []
    for path in sorted((run / "active").glob("*.json")):
        record, error = read_json(path)
        if error:
            agents.append({"role": path.stem, "alive": False, "error": error})
            continue
        alive = False
        pid = record.get("pid")
        if isinstance(pid, int) and not isinstance(pid, bool):
            try:
                os.kill(pid, 0)
                alive = True
            except PermissionError:
                alive = True
            except ProcessLookupError:
                pass
        agents.append(
            {
                "role": record.get("role", path.stem),
                "pid": pid,
                "alive": alive,
                "started_at": record.get("started_at"),
                "last_activity_at": record.get("last_activity_at"),
            }
        )
    return agents


def lanes_from_state(state: dict[str, Any], agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = (state.get("plan") or {}).get("tasks", [])
    owners: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("owner"), str):
                owners[task["owner"]].append(task)
    completed = state.get("lane_receipts") if isinstance(state.get("lane_receipts"), dict) else {}
    pending = (
        state.get("pending_lane_failures")
        if isinstance(state.get("pending_lane_failures"), dict)
        else {}
    )
    active_roles = {
        str(agent.get("role", ""))
        for agent in agents
        if agent.get("alive")
    }
    lanes = []
    for owner, owner_tasks in sorted(owners.items()):
        status = "checkpointed" if owner in completed else "waiting"
        if owner in pending:
            status = "failed"
        elif any(owner in role for role in active_roles):
            status = "active"
        dependencies = sorted(
            {
                dependency
                for task in owner_tasks
                for dependency in task.get("depends_on", [])
                if isinstance(dependency, str)
            }
        )
        lanes.append(
            {
                "owner": owner,
                "status": status,
                "task_count": len(owner_tasks),
                "depends_on": dependencies,
            }
        )
    return lanes


def operation_label(operation: Any) -> str | None:
    if not isinstance(operation, dict) or not operation:
        return None
    parts = [str(operation.get("kind", "operation"))]
    for key in ("owner", "cycle", "attempt"):
        if operation.get(key) is not None:
            parts.append(f"{key} {operation[key]}")
    return " · ".join(parts)


def serialize_run(run: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    state, state_error = read_json(run / "state.json")
    events, event_errors = read_events(run / "events.jsonl")
    artifacts, lookup = artifact_groups(run)
    agents = active_agents(run)
    repo_value = state.get("repo")
    repo = Path(repo_value).resolve() if isinstance(repo_value, str) else run.parents[2]
    identifier = state.get("id") if isinstance(state.get("id"), str) else run.name
    updated_at = state.get("updated_at")
    if not isinstance(updated_at, str):
        try:
            updated_at = iso_from_timestamp((run / "state.json").stat().st_mtime)
        except OSError:
            updated_at = None
    usage = state.get("usage") if isinstance(state.get("usage"), dict) else {}
    usage_records, usage_by_role = receipt_usage(run)
    degraded = ([f"state.json: {state_error}"] if state_error else []) + event_errors
    blockers = blockers_from_state(state)
    if state_error:
        blockers.insert(0, f"Run state is unreadable: {state_error}")
    cycles = state.get("cycles")
    run_key = hashlib.sha256(os.fsencode(str(run))).hexdigest()[:16]
    return (
        {
            "key": run_key,
            "id": identifier,
            "project": repo.name,
            "repo": str(repo),
            "run_path": str(run),
            "phase": state.get("phase", "degraded"),
            "operation": operation_label(state.get("operation")),
            "created_at": state.get("created_at"),
            "updated_at": updated_at,
            "next_command": (
                f"factory resume --run {run}"
                if state.get("phase") in {"implementing", "reviewing"}
                else None
            ),
            "usage": {
                "calls": safe_number(usage.get("calls")) or 0,
                "input_tokens": safe_number(usage.get("input_tokens")) or 0,
                "output_tokens": safe_number(usage.get("output_tokens")) or 0,
                "total_tokens": safe_number(usage.get("total_tokens")) or 0,
                "cost_usd": safe_number(usage.get("cost_usd")) or 0,
                "unknown_calls": safe_number(usage.get("unknown_calls")) or 0,
            },
            "usage_records": usage_records,
            "usage_by_role": usage_by_role,
            "blockers": blockers,
            "active_agents": agents,
            "lanes": lanes_from_state(state, agents),
            "completed_cycles": len(cycles) if isinstance(cycles, list) else 0,
            "events": events,
            "artifacts": artifacts,
            "degraded": degraded,
        },
        lookup,
    )


def build_snapshot(roots: list[Path]) -> tuple[dict[str, Any], dict[str, Path]]:
    runs = []
    artifacts: dict[str, Path] = {}
    discovery_errors = []
    for root in roots:
        if not root.is_dir():
            discovery_errors.append(f"Root does not exist or is not a directory: {root}")
            continue
        try:
            paths = discover_run_paths(root)
        except OSError as error:
            discovery_errors.append(f"Cannot scan {root}: {error}")
            continue
        for run_path in paths:
            item, run_artifacts = serialize_run(run_path)
            runs.append(item)
            artifacts.update(run_artifacts)
    runs.sort(key=lambda run: str(run.get("updated_at") or ""), reverse=True)

    projects: dict[str, dict[str, Any]] = {}
    for run in runs:
        repo = run["repo"]
        project = projects.setdefault(
            repo,
            {
                "name": run["project"],
                "repo": repo,
                "run_count": 0,
                "total_tokens": 0,
            },
        )
        project["run_count"] += 1
        project["total_tokens"] += int(run["usage"]["total_tokens"])

    return (
        {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "roots": [str(root) for root in roots],
            "projects": sorted(projects.values(), key=lambda item: item["name"].lower()),
            "runs": runs,
            "discovery_errors": discovery_errors,
        },
        artifacts,
    )


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], roots: list[Path]):
        self.roots = roots
        super().__init__(address, DashboardHandler)


class DashboardHandler(BaseHTTPRequestHandler):
    server: DashboardServer

    def log_message(self, format: str, *args: Any) -> None:
        print(f"dashboard: {self.address_string()} {format % args}", file=sys.stderr)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "media-src 'self'; connect-src 'self'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'",
        )
        super().end_headers()

    def valid_host(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]").lower()
        return host in {"127.0.0.1", "localhost", "::1"}

    def send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self.valid_host():
            self.send_error_json(HTTPStatus.FORBIDDEN, "invalid localhost Host header")
            return
        request = urlparse(self.path)
        if request.path == "/":
            try:
                body = INDEX.read_bytes()
            except OSError as error:
                self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if request.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if request.path == "/api/dashboard":
            snapshot, _artifacts = build_snapshot(self.server.roots)
            self.send_json(snapshot)
            return
        if request.path == "/api/artifact":
            identifier = parse_qs(request.query).get("id", [""])[0]
            _snapshot, artifacts = build_snapshot(self.server.roots)
            path = artifacts.get(identifier)
            if path is None:
                self.send_error_json(HTTPStatus.NOT_FOUND, "artifact is not in the run ledger")
                return
            self.send_artifact(path)
            return
        self.send_error_json(HTTPStatus.NOT_FOUND, "not found")

    def send_artifact(self, path: Path) -> None:
        try:
            size = path.stat().st_size
            source = path.open("rb")
        except OSError as error:
            self.send_error_json(HTTPStatus.NOT_FOUND, f"artifact unavailable: {error}")
            return

        start = 0
        end = max(0, size - 1)
        status = HTTPStatus.OK
        range_header = self.headers.get("Range")
        if range_header and size:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                source.close()
                self.send_error_json(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, "invalid range")
                return
            raw_start, raw_end = match.groups()
            if raw_start:
                start = int(raw_start)
                end = int(raw_end) if raw_end else end
            elif raw_end:
                length = min(int(raw_end), size)
                start = size - length
            if start > end or start >= size:
                source.close()
                self.send_error_json(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, "range outside artifact")
                return
            end = min(end, size - 1)
            status = HTTPStatus.PARTIAL_CONTENT

        length = max(0, end - start + 1) if size else 0
        self.send_response(status)
        self.send_header("Content-Type", media_type(path))
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", f'inline; filename="{path.name.replace(chr(34), "")}"')
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            source.seek(start)
            remaining = length
            while remaining:
                chunk = source.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)
        finally:
            source.close()


def create_server(roots: list[Path], port: int) -> DashboardServer:
    resolved = list(dict.fromkeys(root.expanduser().resolve() for root in roots))
    return DashboardServer((LOOPBACK, port), resolved)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Serve the read-only Pi Graph Factory dashboard on localhost."
    )
    command.add_argument(
        "--root",
        action="append",
        type=Path,
        default=[],
        help="Project, run, or parent directory to scan; repeat for multiple roots.",
    )
    command.add_argument("--port", type=int, default=7331)
    command.add_argument("--open", action="store_true", help="Open the dashboard in the default browser.")
    return command


def main() -> int:
    args = parser().parse_args()
    roots = args.root or [Path.cwd()]
    if not 0 <= args.port <= 65535:
        parser().error("--port must be between 0 and 65535")
    server = create_server(roots, args.port)
    url = f"http://{LOOPBACK}:{server.server_port}/"
    print(json.dumps({"url": url, "roots": [str(root) for root in server.roots]}), flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
