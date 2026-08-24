#!/usr/bin/env python3
"""Experimental normalized adapter for Pi, Claude Code, and Codex."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

try:
    from agent_adapter import claude_command, skill_prompt
except ModuleNotFoundError:
    from scripts.agent_adapter import claude_command, skill_prompt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", choices=["pi", "claude-code", "codex"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--instructions", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--thinking", default="medium")
    parser.add_argument("--tools", default="")
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--intelligence", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--scope", default="")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--cycle", type=int, default=0)
    args = parser.parse_args()
    workflow_dir = Path(os.environ.get("WORKFLOW_DIR", ".")).resolve()
    if not args.instructions.is_absolute():
        args.instructions = workflow_dir / args.instructions
    args.skill = [str(path if path.is_absolute() else workflow_dir / path) for path in map(Path, args.skill)]
    context = []
    for label in ("input", "intelligence", "plan", "review", "evidence"):
        path = getattr(args, label)
        if path and path.is_file():
            context.append(f"<{label}>\n{path.read_text(encoding='utf-8')}\n</{label}>")
    prompt = args.instructions.read_text(encoding="utf-8") + "\n\n" + "\n".join(context)
    prompt += f"\n\nRole: {args.role}\nScope: {args.scope}\nCycle: {args.cycle}\n"
    if args.harness != "pi" and args.skill:
        prompt += "\n<configured_skills>\n" + skill_prompt(args.skill) + "\n</configured_skills>"
    if os.environ.get("PI_GRAPH_FACTORY_FAKE"):
        print(os.environ.get("PI_GRAPH_FACTORY_FAKE_OUTPUT", '{"status":"pass"}'))
        return 0
    if args.harness == "pi":
        command = ["pi", "-p", "--mode", "json", "--no-session", "--model", args.model,
                   "--thinking", args.thinking, "--no-skills"]
        for skill in args.skill:
            command.extend(["--skill", skill])
        if args.tools:
            command.extend(["--tools", args.tools])
        command.append(prompt)
    elif args.harness == "claude-code":
        command = claude_command(args.model, prompt, args.tools)
    else:
        command = ["codex", "exec", "--model", args.model, prompt]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        print(result.stderr[-2000:], file=os.sys.stderr)
        return result.returncode
    output = result.stdout.strip()
    if args.harness == "pi":
        messages = []
        for line in output.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "message_end" and event.get("message", {}).get("role") == "assistant":
                messages.append(event["message"])
        if not messages:
            print("Pi produced no final assistant message", file=os.sys.stderr)
            return 1
        output = "".join(
            item.get("text", "") for item in messages[-1].get("content", [])
            if item.get("type") == "text"
        ).strip()
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
