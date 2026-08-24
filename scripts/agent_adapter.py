#!/usr/bin/env python3
"""Normalize Pi, Claude Code, and Codex into one factory receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

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


def claude_command(model: str, prompt: str, tools: str = "") -> list[str]:
    """Build an unattended Claude command constrained to configured tools."""

    command = ["claude", "-p", "--model", model]
    allowed = []
    for raw in tools.split(","):
        name = CLAUDE_TOOL_NAMES.get(raw.strip().lower())
        if name and name not in allowed:
            allowed.append(name)
    if allowed:
        command.append("--allowedTools=" + ",".join(allowed))
    command.append(prompt)
    return command


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
        for opening in ("```json", "```JSON", "```"):
            if not stripped.startswith(opening):
                continue
            candidate = stripped[len(opening):].lstrip()
            if candidate.endswith("```"):
                candidate = candidate[:-3].rstrip()
            try:
                return "passed", json.loads(candidate)
            except ValueError:
                break
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
    if args.harness == "pi":
        command = ["pi", "-p", "--mode", "json", "--no-session", "--model", args.model,
                   "--thinking", args.thinking, "--no-extensions", "--no-skills"]
        for skill in args.skill:
            command.extend(["--skill", str(resolve(skill))])
        if args.tools:
            command.extend(["--tools", args.tools])
        command.append(prompt)
    elif args.harness == "claude-code":
        command = claude_command(args.model, prompt, args.tools)
    else:
        command = ["codex", "exec", "--model", args.model, prompt]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        print((result.stderr or result.stdout)[-2000:], file=sys.stderr)
        return result.returncode
    usage = {"input": None, "output": None, "total": None, "cost": None}
    raw = result.stdout.strip()
    if args.harness == "pi":
        raw, usage = pi_output(raw)
    status, output = decode_output(raw)
    receipt = {"status": status, "harness": args.harness, "model": args.model,
               "role": args.role, "output": output, "usage": usage,
               "skills": args.skill,
               "raw_sha256": hashlib.sha256(raw.encode()).hexdigest()}
    print(json.dumps(receipt, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
