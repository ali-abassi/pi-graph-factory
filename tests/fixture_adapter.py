#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
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

transient_role = os.environ.get("PI_GRAPH_FACTORY_TRANSIENT_ROLE")
transient_marker_value = os.environ.get("PI_GRAPH_FACTORY_TRANSIENT_MARKER")
transient_harness = os.environ.get("PI_GRAPH_FACTORY_TRANSIENT_HARNESS")
if (
    transient_role == args.role
    and transient_marker_value
    and (not transient_harness or transient_harness == args.harness)
):
    transient_marker = Path(transient_marker_value)
    failures = int(transient_marker.read_text()) if transient_marker.exists() else 0
    failure_limit = int(os.environ.get("PI_GRAPH_FACTORY_TRANSIENT_FAILURES", "1"))
    if failures < failure_limit:
        transient_marker.write_text(str(failures + 1), encoding="utf-8")
        print("API Error: 529 Overloaded. This is a temporary server-side issue.", file=sys.stderr)
        raise SystemExit(1)

fatal_role = os.environ.get("PI_GRAPH_FACTORY_FATAL_ROLE")
fatal_marker_value = os.environ.get("PI_GRAPH_FACTORY_FATAL_MARKER")
if fatal_role == args.role and fatal_marker_value:
    fatal_marker = Path(fatal_marker_value)
    attempts = int(fatal_marker.read_text()) if fatal_marker.exists() else 0
    fatal_marker.write_text(str(attempts + 1), encoding="utf-8")
    print(
        "Authentication failed: 401 Unauthorized; API key=sk-ant-fixture-secret-1234567890.",
        file=sys.stderr,
    )
    raise SystemExit(1)

if args.role == "plan":
    required_docs = context.get("required_project_docs", [])
    output = {
        "version": 1,
        "summary": "Create the text application",
        "proof": {"mode": "visual", "reason": "exercise the browser evidence fixture"},
        "success_criteria": [
            {"id": "SC-1", "description": "The reviewed text artifact exists."}
        ],
        "research": [{
            "question": "What outcome and proof does this repository require?",
            "finding": "The project memory and request require a reviewed text artifact.",
            "evidence": ["VISION.md", "FEATURE_MAP.md"],
        }],
        "assumptions": [],
        "tasks": [{"id": "build", "owner": "product",
                   "files": ["app.txt", "evidence/**", *required_docs],
                   "acceptance": ["test -s app.txt"]}],
        "acceptance": ["test -s app.txt"],
        "risks": [],
        "open_questions": ([{
            "id": "human-context",
            "question": "Which irreversible product constraint cannot be inferred?",
            "blocking": True,
        }] if (
            os.environ.get("PI_GRAPH_FACTORY_BLOCKING_PLAN_QUESTION_ALWAYS") == "1"
            or (
                os.environ.get("PI_GRAPH_FACTORY_BLOCKING_PLAN_QUESTION") == "1"
                and not context.get("autonomy_feedback")
            )
        ) else []),
    }
    marker_value = os.environ.get("PI_GRAPH_FACTORY_INVALID_PLAN_MARKER")
    if marker_value and not Path(marker_value).exists():
        Path(marker_value).write_text("observed", encoding="utf-8")
        receipt_status = "invalid"
        output = {"error": "model response was not a JSON object", "raw_excerpt": "not json"}
elif args.role.startswith("plan-review:"):
    low_marker_value = os.environ.get("PI_GRAPH_FACTORY_LOW_PLAN_SCORE_ONCE")
    low = bool(low_marker_value and not Path(low_marker_value).exists())
    if low:
        Path(low_marker_value).write_text("observed", encoding="utf-8")
    score = 8.0 if low else 9.0
    output = {
        "rubric_version": "plan-quality-v1",
        "dimensions": [
            {
                "name": name,
                "score": score,
                "evidence": "The plan is grounded in the supplied request and repository context.",
                "reasoning": "It satisfies the named anchor with inspectable evidence.",
                "gap_to_next": "Add more explicit repository evidence." if low else "No material gap.",
            }
            for name in ("grounding", "coverage", "feasibility", "minimality", "alignment")
        ],
        "critical_failure": False,
        "overall_score": score,
        "overall_reasoning": "The plan clears the configured quality bar." if not low
        else "The plan needs more explicit grounding before approval.",
        "improvements": [] if not low else [{
            "dimension": "grounding",
            "current_anchor": 8.0,
            "target_anchor": 8.5,
            "suggestion": "Tie every implementation task to a named repository finding.",
            "why_raises_score": "It makes the plan independently traceable to repository evidence.",
        }],
        "verdict": "revise" if low else "pass",
    }
elif args.role.startswith("implement:"):
    Path("app.txt").write_text("implemented\n", encoding="utf-8")
    evidence = Path("evidence")
    evidence.mkdir(exist_ok=True)
    (evidence / "desktop.png").write_bytes(b"png-fixture")
    (evidence / "flow.webm").write_bytes(b"webm-fixture")
    (evidence / "browser-receipt.json").write_text('{"console_errors":[]}\n')
    changed_files = ["app.txt", "evidence/desktop.png", "evidence/flow.webm",
                     "evidence/browser-receipt.json"]
    assigned_files = {
        path
        for task in context.get("tasks", [])
        for path in task.get("files", [])
    }
    if "VISION.md" in assigned_files:
        Path("VISION.md").write_text("# Vision\n\nBuild reliable reviewed software.\n")
        changed_files.append("VISION.md")
    if "FEATURE_MAP.md" in assigned_files:
        Path("FEATURE_MAP.md").write_text("# Feature map\n\n- Reviewed text artifact\n")
        changed_files.append("FEATURE_MAP.md")
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
    versioned_plan = context["plan"].get("version") == 1
    if count == 0 or os.environ.get("PI_GRAPH_FACTORY_ALWAYS_REPAIR") == "1":
        issue = {"id": "FIX-1", "owner": "product",
                 "message": "mark implementation reviewed"}
        if versioned_plan:
            issue.update({"criterion_id": "SC-1", "target_files": ["app.txt"]})
        output = {"verdict": "repair", "issues": [issue],
                  "evidence": [context["evidence"]["sha256"]]}
        if versioned_plan:
            output["criteria"] = [{"id": "SC-1", "status": "fail",
                                   "evidence": "app.txt is not marked reviewed"}]
    else:
        output = {"verdict": "pass", "issues": [],
                  "evidence": [context["evidence"]["sha256"], "app.txt contains reviewed"]}
        if versioned_plan:
            output["criteria"] = [{"id": "SC-1", "status": "pass",
                                   "evidence": "app.txt contains reviewed"}]
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
