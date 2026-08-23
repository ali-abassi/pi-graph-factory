#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--role", required=True)
parser.add_argument("--harness", required=True)
parser.add_argument("--model", required=True)
parser.add_argument("--instructions", required=True)
parser.add_argument("--context", type=Path, required=True)
parser.add_argument("--skill", action="append", default=[])
parser.add_argument("--tools", default="")
args = parser.parse_args()
context = json.loads(args.context.read_text())

if args.role.startswith("implement:"):
    Path("app.txt").write_text("implemented\n", encoding="utf-8")
    evidence = Path("evidence")
    evidence.mkdir(exist_ok=True)
    (evidence / "desktop.png").write_bytes(b"png-fixture")
    (evidence / "flow.webm").write_bytes(b"webm-fixture")
    (evidence / "browser-receipt.json").write_text('{"console_errors":[]}\n')
    output = {"status": "pass", "changed_files": ["app.txt", "evidence/desktop.png",
              "evidence/flow.webm", "evidence/browser-receipt.json"],
              "checks": ["test -s app.txt"], "summary": "implemented fixture"}
elif args.role.startswith("repair:"):
    with Path("app.txt").open("a", encoding="utf-8") as target:
        target.write(f"reviewed {args.role.split(':')[1]}\n")
    output = {"status": "pass", "addressed": ["FIX-1"],
              "checks": ["grep -q reviewed app.txt"]}
elif args.role.startswith("review:"):
    counter = Path(os.environ["PI_GRAPH_FACTORY_REVIEW_COUNTER"])
    count = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(count + 1))
    if count == 0 or os.environ.get("PI_GRAPH_FACTORY_ALWAYS_REPAIR") == "1":
        output = {"verdict": "repair", "issues": [{"id": "FIX-1", "owner": "product",
                  "message": "mark implementation reviewed"}],
                  "evidence": [context["evidence"]["sha256"]]}
    else:
        output = {"verdict": "pass", "issues": [],
                  "evidence": [context["evidence"]["sha256"], "app.txt contains reviewed"]}
else:
    raise SystemExit(f"unsupported fixture role: {args.role}")

receipt = {"status": "passed", "harness": args.harness, "model": args.model,
           "role": args.role, "output": output,
           "usage": {"input": 1, "output": 1, "total": 2, "cost": 0}}
print(json.dumps(receipt, separators=(",", ":")))
