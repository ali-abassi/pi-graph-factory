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


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


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
    if args.harness == "pi":
        command = ["pi", "-p", "--mode", "json", "--no-session", "--model", args.model,
                   "--thinking", args.thinking, "--no-extensions", "--no-skills"]
        for skill in args.skill:
            command.extend(["--skill", str(resolve(skill))])
        if args.tools:
            command.extend(["--tools", args.tools])
        command.append(prompt)
    elif args.harness == "claude-code":
        command = ["claude", "-p", "--model", args.model, prompt]
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
    try:
        output = json.loads(raw)
    except ValueError:
        print(f"{args.harness} did not return the required JSON object", file=sys.stderr)
        return 2
    receipt = {"status": "passed", "harness": args.harness, "model": args.model,
               "role": args.role, "output": output, "usage": usage,
               "raw_sha256": hashlib.sha256(raw.encode()).hexdigest()}
    print(json.dumps(receipt, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
