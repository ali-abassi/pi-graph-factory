#!/usr/bin/env python3
"""Normalize Pi, Claude Code, and Codex into one factory receipt."""

from __future__ import annotations

import argparse
from collections import deque
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
COMPACT_STRING_BYTES = 4_096
CAPTURE_TAIL_BYTES = 2_000_000

CLAUDE_TOOL_NAMES = {
    "read": "Read",
    "edit": "Edit",
    "write": "Write",
    "bash": "Bash",
    "grep": "Grep",
    "find": "Glob",
    "ls": "Glob",
}


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def skill_prompt(paths: list[str]) -> str:
    """Inline trusted configured skills for harnesses without a skill flag."""

    blocks = []
    for raw in paths:
        path = resolve(raw)
        path = path / "SKILL.md" if path.is_dir() else path
        blocks.append(f"<skill path={raw!r}>\n{path.read_text(encoding='utf-8')}\n</skill>")
    return "\n".join(blocks)


def claude_command(
    model: str,
    prompt: str,
    tools: str = "",
    session_id: str | None = None,
) -> list[str]:
    """Build an unattended Claude command constrained to configured tools."""

    command = ["claude", "-p", "--model", model]
    allowed = []
    for raw in tools.split(","):
        name = CLAUDE_TOOL_NAMES.get(raw.strip().lower())
        if name and name not in allowed:
            allowed.append(name)
    if allowed:
        command.append("--allowedTools=" + ",".join(allowed))
    if session_id:
        command.extend(["--session-id", session_id])
    command.append(prompt)
    return command


def codex_command(model: str, prompt: str, final_response: Path) -> list[str]:
    """Build an unattended Codex command writable only inside its worktree."""

    return [
        "codex",
        "exec",
        "--model",
        model,
        # Current Codex makes this flag select the workspace-write sandbox;
        # passing --sandbox alongside it is a conflicting CLI contract.
        "--approve-for-me",
        "--json",
        "--output-last-message",
        str(final_response),
        prompt,
    ]


def persist_harness_blob(artifact_dir: Path, value: str) -> dict[str, object]:
    """Store one large UTF-8 value once and return its content-addressed reference."""

    encoded = value.encode("utf-8", errors="replace")
    digest = hashlib.sha256(encoded).hexdigest()
    relative = Path("harness.blobs") / f"{digest}.txt.gz"
    destination = artifact_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.parent.chmod(0o700)
    if not destination.exists():
        with gzip.open(destination, "wb", compresslevel=6) as target:
            target.write(encoded)
        destination.chmod(0o600)
    return {
        "$artifact": str(relative),
        "bytes": len(encoded),
        "sha256": digest,
        "encoding": "utf-8+gzip",
        "preview": value[:160] + " … " + value[-160:],
    }


def compact_harness_value(value: object, artifact_dir: Path) -> object:
    """Replace bulky transport fields with content-addressed artifact references."""

    if isinstance(value, str):
        encoded = value.encode("utf-8", errors="replace")
        if len(encoded) <= COMPACT_STRING_BYTES:
            return value
        return persist_harness_blob(artifact_dir, value)
    if isinstance(value, list):
        return [compact_harness_value(item, artifact_dir) for item in value]
    if isinstance(value, dict):
        return {
            key: compact_harness_value(item, artifact_dir)
            for key, item in value.items()
        }
    return value


def compact_harness_line(line: str, artifact_dir: Path) -> tuple[str, str | None]:
    """Return a readable event plus any settled Pi assistant event needed by the adapter."""

    try:
        event = json.loads(line)
    except ValueError:
        if len(line.encode("utf-8", errors="replace")) > COMPACT_STRING_BYTES:
            reference = persist_harness_blob(artifact_dir, line)
            return json.dumps(
                {"type": "raw_output", "content": reference},
                separators=(",", ":"),
                ensure_ascii=False,
            ) + "\n", None
        return line, None
    settled = None
    if (
        event.get("type") == "message_end"
        and isinstance(event.get("message"), dict)
        and event["message"].get("role") == "assistant"
    ):
        settled = line
    compact = compact_harness_value(event, artifact_dir)
    return json.dumps(compact, separators=(",", ":"), ensure_ascii=False) + "\n", settled


def run_streaming(command: list[str], artifact_dir: Path | None) -> subprocess.CompletedProcess:
    """Run a harness while making its raw streams durable before it exits."""

    if artifact_dir is None:
        return subprocess.run(command, text=True, capture_output=True, check=False)
    streams = {
        "stdout": artifact_dir / "harness.stdout",
        "stderr": artifact_dir / "harness.stderr",
    }
    for path in streams.values():
        path.touch()
        path.chmod(0o600)
    process = subprocess.Popen(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    captured: dict[str, deque[str]] = {"stdout": deque(), "stderr": deque()}
    captured_bytes = {"stdout": 0, "stderr": 0}
    settled_stdout: list[str | None] = [None]

    def capture_tail(name: str, value: str) -> None:
        captured[name].append(value)
        captured_bytes[name] += len(value.encode("utf-8", errors="replace"))
        while captured[name] and captured_bytes[name] > CAPTURE_TAIL_BYTES:
            removed = captured[name].popleft()
            captured_bytes[name] -= len(removed.encode("utf-8", errors="replace"))

    def drain(name: str, pipe: object) -> None:
        with streams[name].open("a", encoding="utf-8") as destination:
            for line in pipe:  # type: ignore[union-attr]
                if name == "stdout":
                    compact, settled = compact_harness_line(line, artifact_dir)
                    if settled is not None:
                        settled_stdout[0] = settled
                    capture_tail(name, line)
                    destination.write(compact)
                else:
                    capture_tail(name, line)
                    compact, _ = compact_harness_line(line, artifact_dir)
                    destination.write(compact)
                destination.flush()

    threads = [
        threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()
    returncode = process.wait()
    for thread in threads:
        thread.join()
    if process.stdout is not None:
        process.stdout.close()
    if process.stderr is not None:
        process.stderr.close()
    return subprocess.CompletedProcess(
        command,
        returncode,
        settled_stdout[0] or "".join(captured["stdout"]),
        "".join(captured["stderr"]),
    )


def claude_transcript(session_id: str) -> Path | None:
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return None
    matches = list(root.glob(f"*/{session_id}.jsonl"))
    return matches[0] if len(matches) == 1 else None


def claude_usage(path: Path) -> tuple[dict, dict]:
    """Aggregate one usage record per Claude message id, never per JSONL row."""

    seen = set()
    details = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "unique_messages": 0,
    }
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") if event.get("type") == "assistant" else None
        if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
            continue
        identity = message.get("id")
        if not isinstance(identity, str) or identity in seen:
            continue
        seen.add(identity)
        usage = message["usage"]
        for field in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        ):
            value = usage.get(field, 0)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                details[field] += value
    details["unique_messages"] = len(seen)
    input_tokens = (
        details["input_tokens"]
        + details["cache_creation_input_tokens"]
        + details["cache_read_input_tokens"]
    )
    output_tokens = details["output_tokens"]
    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens,
        "cost": None,
    }, details


def file_metadata(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def preserve_harness_artifacts(
    artifact_dir: Path | None,
    stdout: str,
    stderr: str,
    session_id: str | None,
) -> tuple[dict, tuple[dict, dict] | None]:
    """Keep compact harness events, referenced payloads, and declared lane proof."""

    if artifact_dir is None:
        transcript = claude_transcript(session_id) if session_id else None
        return {}, claude_usage(transcript) if transcript else None
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.chmod(0o700)
    stdout_path = artifact_dir / "harness.stdout"
    stderr_path = artifact_dir / "harness.stderr"
    if not stdout_path.exists():
        stdout_path.write_text(stdout, encoding="utf-8")
    if not stderr_path.exists():
        stderr_path.write_text(stderr, encoding="utf-8")
    stdout_path.chmod(0o600)
    stderr_path.chmod(0o600)
    files = [file_metadata(stdout_path), file_metadata(stderr_path)]
    blob_directory = artifact_dir / "harness.blobs"
    if blob_directory.is_dir():
        files.extend(file_metadata(path) for path in sorted(blob_directory.glob("*.gz")))
    visual_smoke_directory = artifact_dir / "visual-smoke"
    if visual_smoke_directory.is_dir():
        for path in sorted(visual_smoke_directory.rglob("*")):
            if path.is_file() and not path.is_symlink():
                path.chmod(0o600)
                files.append(file_metadata(path))
    session_path = artifact_dir / "session.json"
    if session_path.is_file():
        files.append(file_metadata(session_path))
    final_response = artifact_dir / "final-response.txt"
    if final_response.is_file():
        final_response.chmod(0o600)
        files.append(file_metadata(final_response))
    transcript_usage = None
    source = claude_transcript(session_id) if session_id else None
    if source:
        transcript_path = artifact_dir / "transcript.jsonl"
        shutil.copy2(source, transcript_path)
        transcript_path.chmod(0o600)
        files.append(file_metadata(transcript_path))
        transcript_usage = claude_usage(transcript_path)
    manifest = {
        "schema": "pi-graph-factory.agent-artifacts.v1",
        "directory": str(artifact_dir),
        "session_id": session_id,
        "files": files,
    }
    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_path.chmod(0o600)
    manifest["manifest"] = file_metadata(manifest_path)
    return manifest, transcript_usage


def pi_output(stream: str) -> tuple[str, dict]:
    final = None
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "message_end" and event.get("message", {}).get("role") == "assistant":
            final = event["message"]
    if not final or final.get("stopReason") != "stop":
        raise ValueError("Pi produced no settled final assistant response")
    text = "".join(item.get("text", "") for item in final.get("content", [])
                   if item.get("type") == "text").strip()
    usage = final.get("usage", {})
    return text, {"input": usage.get("input"), "output": usage.get("output"),
                  "total": usage.get("totalTokens"),
                  "cost": (usage.get("cost") or {}).get("total")}


def decode_output(raw: str) -> tuple[str, object]:
    """Keep malformed model output typed so bounded controller retries can run."""

    try:
        return "passed", json.loads(raw)
    except ValueError:
        stripped = raw.strip()
        if stripped.count("```") == 2:
            opening = stripped.index("```")
            closing = stripped.index("```", opening + 3)
            candidate = stripped[opening + 3:closing].strip()
            if candidate[:4].lower() == "json":
                candidate = candidate[4:].lstrip()
            try:
                return "passed", json.loads(candidate)
            except ValueError:
                pass
        return "invalid", {
            "error": "model response was not a JSON object",
            "raw_excerpt": raw[-4000:],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True)
    parser.add_argument("--harness", choices=["pi", "claude-code", "codex"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--thinking", required=True)
    parser.add_argument("--instructions", required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--tools", default="")
    args = parser.parse_args()
    context = json.loads(args.context.read_text(encoding="utf-8"))
    instructions = resolve(args.instructions).read_text(encoding="utf-8")
    prompt = instructions + "\n\n<context>\n" + json.dumps(context, indent=2) + "\n</context>"
    if args.harness != "pi" and args.skill:
        prompt += "\n\n<configured_skills>\n" + skill_prompt(args.skill) + "\n</configured_skills>"
    claude_session_id = str(uuid.uuid4()) if args.harness == "claude-code" else None
    artifact_value = os.environ.get("PI_GRAPH_FACTORY_AGENT_ARTIFACT_DIR")
    artifact_dir = Path(artifact_value) if artifact_value else None
    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir.chmod(0o700)
        session_path = artifact_dir / "session.json"
        session_path.write_text(
            json.dumps(
                {
                    "schema": "pi-graph-factory.agent-session.v1",
                    "harness": args.harness,
                    "model": args.model,
                    "role": args.role,
                    "session_id": claude_session_id,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        session_path.chmod(0o600)
    if args.harness == "pi":
        command = ["pi", "-p", "--mode", "json", "--no-session", "--model", args.model,
                   "--thinking", args.thinking, "--no-extensions", "--no-skills"]
        for skill in args.skill:
            command.extend(["--skill", str(resolve(skill))])
        if args.tools:
            command.extend(["--tools", args.tools])
        command.append(prompt)
    elif args.harness == "claude-code":
        command = claude_command(
            args.model,
            prompt,
            args.tools,
            session_id=claude_session_id,
        )
    else:
        if artifact_dir is not None:
            final_response = artifact_dir / "final-response.txt"
        else:
            temporary_response = tempfile.NamedTemporaryFile(
                prefix="pi-graph-factory-", suffix=".txt", delete=False
            )
            temporary_response.close()
            final_response = Path(temporary_response.name)
        command = codex_command(args.model, prompt, final_response)
    result = run_streaming(command, artifact_dir)
    artifacts, transcript_usage = preserve_harness_artifacts(
        artifact_dir,
        result.stdout,
        result.stderr,
        claude_session_id,
    )
    if result.returncode:
        if args.harness == "codex" and artifact_dir is None:
            final_response.unlink(missing_ok=True)
        print((result.stderr or result.stdout)[-2000:], file=sys.stderr)
        return result.returncode
    usage = {"input": None, "output": None, "total": None, "cost": None}
    raw = result.stdout.strip()
    if args.harness == "pi":
        raw, usage = pi_output(raw)
    elif transcript_usage is not None:
        usage, details = transcript_usage
        artifacts["usage"] = details
    elif args.harness == "codex":
        if not final_response.is_file():
            raise ValueError("Codex produced no final response file")
        raw = final_response.read_text(encoding="utf-8").strip()
        if artifact_dir is None:
            final_response.unlink(missing_ok=True)
    status, output = decode_output(raw)
    receipt = {"status": status, "harness": args.harness, "model": args.model,
               "role": args.role, "output": output, "usage": usage,
               "skills": args.skill,
               "artifacts": artifacts,
               "raw_sha256": hashlib.sha256(raw.encode()).hexdigest()}
    print(json.dumps(receipt, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
