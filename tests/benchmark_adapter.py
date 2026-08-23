#!/usr/bin/env python3
"""Deterministic agent harness for simple, medium, and complex factory cases."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path


def literal_files(tasks: list[dict], owner: str) -> list[str]:
    values = []
    for task in tasks:
        if task["owner"] != owner:
            continue
        for raw in task["files"]:
            if not any(char in raw for char in "*?["):
                values.append(raw)
    return values


def write_evidence() -> list[str]:
    paths = [
        "evidence/desktop.png",
        "evidence/flow.webm",
        "evidence/browser-receipt.json",
    ]
    Path(paths[0]).parent.mkdir(parents=True, exist_ok=True)
    Path(paths[0]).write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    ))
    Path(paths[1]).write_bytes(b"\x1aE\xdf\xa3\x00fixture-webm")
    Path(paths[2]).write_text('{"console_errors":[],"network_errors":[]}\n', encoding="utf-8")
    return paths


parser = argparse.ArgumentParser()
parser.add_argument("--role", required=True)
parser.add_argument("--harness", required=True)
parser.add_argument("--model", required=True)
parser.add_argument("--thinking", required=True)
parser.add_argument("--instructions", required=True)
parser.add_argument("--context", type=Path, required=True)
parser.add_argument("--skill", action="append", default=[])
parser.add_argument("--tools", default="")
args = parser.parse_args()
context = json.loads(args.context.read_text(encoding="utf-8"))

if args.role.startswith("implement:"):
    owner = args.role.split(":", 1)[1]
    changed = []
    for raw in literal_files(context["tasks"], owner):
        path = Path(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"implemented by {owner}\n", encoding="utf-8")
        changed.append(raw)
    if owner == "product":
        changed.extend(write_evidence())
    if os.environ.get("PI_GRAPH_FACTORY_ESCAPE_OWNER") == owner:
        Path("outside-approved-scope.txt").write_text("escaped\n", encoding="utf-8")
        changed.append("outside-approved-scope.txt")
    output = {
        "status": "pass",
        "changed_files": sorted(changed),
        "checks": ["fixture implementation completed"],
        "summary": f"implemented {owner}",
    }
elif args.role.startswith("repair:"):
    owner = args.role.rsplit(":", 1)[1]
    targets = literal_files(context["plan"]["tasks"], owner)
    if not targets:
        raise SystemExit(f"no literal repair target for {owner}")
    with Path(targets[0]).open("a", encoding="utf-8") as output_file:
        output_file.write(f"repaired in cycle {context['cycle']}\n")
    output = {
        "status": "pass",
        "addressed": [issue["id"] for issue in context["issues"]],
        "checks": [f"repaired {targets[0]}"],
    }
elif args.role.startswith("review:"):
    cycle = int(args.role.split(":", 1)[1])
    owners = [value for value in os.environ.get("PI_GRAPH_FACTORY_REVIEW_OWNERS", "").split(",") if value]
    evidence_sha = context["evidence"]["sha256"]
    citations = ["forged-evidence"] if os.environ.get("PI_GRAPH_FACTORY_FORGE_EVIDENCE") else [evidence_sha]
    if cycle <= len(owners):
        owner = owners[cycle - 1]
        output = {
            "verdict": "repair",
            "issues": [{"id": f"FIX-{cycle}", "owner": owner, "message": f"repair {owner}"}],
            "evidence": citations,
        }
    else:
        output = {"verdict": "pass", "issues": [], "evidence": citations}
else:
    raise SystemExit(f"unsupported benchmark role: {args.role}")

receipt = {
    "status": "passed",
    "harness": args.harness,
    "model": args.model,
    "role": args.role,
    "output": output,
    "usage": {"input": 1, "output": 1, "total": 2, "cost": 0},
}
print(json.dumps(receipt, separators=(",", ":")))
