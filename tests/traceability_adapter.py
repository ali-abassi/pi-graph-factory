#!/usr/bin/env python3
"""Deterministic adapter for the versioned success-criteria contract."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


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
    Path("app.txt").write_text("traceable implementation\n", encoding="utf-8")
    evidence = Path("evidence")
    evidence.mkdir(exist_ok=True)
    (evidence / "desktop.png").write_bytes(b"png")
    (evidence / "flow.webm").write_bytes(b"webm")
    output = {
        "status": "pass",
        "changed_files": ["app.txt", "evidence/desktop.png", "evidence/flow.webm"],
        "checks": [{"command": "test -s app.txt", "passed": True, "evidence": "nonempty"}],
        "summary": "implemented",
    }
elif args.role.startswith("review:"):
    mode = os.environ.get("PI_GRAPH_FACTORY_CRITERIA_MODE", "exact")
    criteria = [
        {"id": item["id"], "status": "pass", "evidence": f"verified {item['id']}"}
        for item in context["plan"]["success_criteria"]
    ]
    output = {
        "verdict": "pass",
        "issues": [],
        "evidence": [context["evidence"]["sha256"]],
        "criteria": criteria,
    }
    if mode == "omit":
        output.pop("criteria")
    elif mode == "missing":
        output["criteria"] = criteria[:-1]
else:
    raise SystemExit(f"unsupported traceability role: {args.role}")

print(json.dumps({
    "status": "passed",
    "harness": args.harness,
    "model": args.model,
    "role": args.role,
    "output": output,
    "usage": {"input": 1, "output": 1, "total": 2, "cost": 0},
}, separators=(",", ":")))
