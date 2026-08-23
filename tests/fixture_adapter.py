#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
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
context = json.loads(args.context.read_text())
time.sleep(float(os.environ.get("PI_GRAPH_FACTORY_ADAPTER_SLEEP", "0")))
receipt_status = "passed"

if args.role == "plan":
    output = {
        "version": 1,
        "summary": "Create the text application",
        "success_criteria": [
            {"id": "SC-1", "description": "The reviewed text artifact exists."}
        ],
        "tasks": [{"id": "build", "owner": "product",
                   "files": ["app.txt", "evidence/**"],
                   "acceptance": ["test -s app.txt"]}],
        "acceptance": ["test -s app.txt"],
        "risks": [],
        "open_questions": [],
    }
    marker_value = os.environ.get("PI_GRAPH_FACTORY_INVALID_PLAN_MARKER")
    if marker_value and not Path(marker_value).exists():
        Path(marker_value).write_text("observed", encoding="utf-8")
        receipt_status = "invalid"
        output = {"error": "model response was not a JSON object", "raw_excerpt": "not json"}
elif args.role.startswith("implement:"):
    Path("app.txt").write_text("implemented\n", encoding="utf-8")
    evidence = Path("evidence")
    evidence.mkdir(exist_ok=True)
    (evidence / "desktop.png").write_bytes(b"png-fixture")
    (evidence / "flow.webm").write_bytes(b"webm-fixture")
    (evidence / "browser-receipt.json").write_text('{"console_errors":[]}\n')
    changed_files = ["app.txt", "evidence/desktop.png", "evidence/flow.webm",
                     "evidence/browser-receipt.json"]
    if os.environ.get("PI_GRAPH_FACTORY_WRITE_PYC") == "1":
        generated = evidence / "__pycache__" / "capture.cpython-314.pyc"
        generated.parent.mkdir()
        generated.write_bytes(b"compiled-fixture")
        changed_files.append("evidence/__pycache__/capture.cpython-314.pyc")
    output = {"status": os.environ.get("PI_GRAPH_FACTORY_IMPLEMENT_STATUS", "pass"),
              "changed_files": changed_files,
              "checks": ["test -s app.txt"], "summary": "implemented fixture"}
elif args.role.startswith("repair:"):
    if "controller_validation_error" not in context:
        with Path("app.txt").open("a", encoding="utf-8") as target:
            target.write(f"reviewed {args.role.split(':')[1]}\n")
    elif os.environ.get("PI_GRAPH_FACTORY_REPAIR_CORRECTION_MUTATION") == "1":
        with Path("app.txt").open("a", encoding="utf-8") as target:
            target.write("protocol correction mutation\n")
    output = {"status": os.environ.get("PI_GRAPH_FACTORY_REPAIR_STATUS", "pass"),
              "addressed": ["FIX-1"],
              "checks": ["grep -q reviewed app.txt"]}
    marker_value = os.environ.get("PI_GRAPH_FACTORY_INVALID_REPAIR_MARKER")
    if marker_value and not Path(marker_value).exists():
        Path(marker_value).write_text("observed", encoding="utf-8")
        output.pop("addressed")
elif args.role.startswith("review:"):
    if os.environ.get("PI_GRAPH_FACTORY_REVIEW_MUTATION") == "1":
        Path("reviewer-was-here.txt").write_text("reviewers must be read-only\n")
    counter = Path(os.environ["PI_GRAPH_FACTORY_REVIEW_COUNTER"])
    count = int(counter.read_text()) if counter.exists() else 0
    invalid_marker = Path(f"{counter}.invalid-review-once")
    invalid_always = os.environ.get("PI_GRAPH_FACTORY_INVALID_REVIEW_ALWAYS") == "1"
    invalid_once = invalid_always or (
        os.environ.get("PI_GRAPH_FACTORY_INVALID_REVIEW_ONCE") == "1"
        and not invalid_marker.exists()
    )
    if invalid_once and not invalid_always:
        invalid_marker.write_text("observed")
    else:
        counter.write_text(str(count + 1))
    if count == 0 or os.environ.get("PI_GRAPH_FACTORY_ALWAYS_REPAIR") == "1":
        output = {"verdict": "repair", "issues": [{"id": "FIX-1", "owner": "product",
                  "message": "mark implementation reviewed"}],
                  "evidence": [context["evidence"]["sha256"]]}
    else:
        output = {"verdict": "pass", "issues": [],
                  "evidence": [context["evidence"]["sha256"], "app.txt contains reviewed"]}
    if invalid_once:
        output["evidence"] = ["truncated-evidence-receipt"]
else:
    raise SystemExit(f"unsupported fixture role: {args.role}")

receipt = {"status": receipt_status, "harness": args.harness, "model": args.model,
           "role": args.role, "output": output,
           "usage": {"input": 1, "output": 1,
                     "total": (None if os.environ.get("PI_GRAPH_FACTORY_USAGE_UNKNOWN") == "1"
                               else int(os.environ.get("PI_GRAPH_FACTORY_USAGE_TOTAL", "2"))),
                     "cost": (None if os.environ.get("PI_GRAPH_FACTORY_USAGE_UNKNOWN") == "1"
                              else float(os.environ.get("PI_GRAPH_FACTORY_USAGE_COST", "0")))}}
print(json.dumps(receipt, separators=(",", ":")))
