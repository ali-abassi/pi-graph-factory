#!/usr/bin/env python3
"""Compile a bounded software-factory contract into Pi Graph Core YAML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schemas" / "factory.schema.json").read_text())


def gate_json(assertion: str) -> str:
    return f'python3 -c "import json,os; x=json.load(open(os.environ[\'OUT\'])); {assertion}"'


def harness_command(agent: dict[str, Any], role: str, extra: str = "") -> str:
    skills = " ".join(f"--skill {json.dumps(item)}" for item in agent.get("skills", []))
    tools = ",".join(agent.get("tools", []))
    return (
        'python3 "$WORKFLOW_DIR/scripts/run_harness.py" '
        f'--harness {agent["harness"]} --model {json.dumps(agent["model"])} '
        f'--instructions {json.dumps(agent["instructions"])} --role {json.dumps(role)} '
        + (f'--thinking {agent.get("thinking", "medium")} ' if agent.get("thinking") else "")
        + (f'--tools {json.dumps(tools)} ' if tools else "")
        + skills + " " + extra
    ).strip()


def compile_factory(spec: dict[str, Any]) -> dict[str, Any]:
    errors = list(Draft202012Validator(SCHEMA).iter_errors(spec))
    if errors:
        details = "; ".join(f"{'.'.join(map(str, error.absolute_path))}: {error.message}" for error in errors)
        raise ValueError(details)

    steps: list[dict[str, Any]] = [{
        "id": "plan", "needs": [],
        "cmd": harness_command(spec["planner"], "planner", '--input "$INPUT"'),
        "schema": {"summary": "string", "tasks": "array", "acceptance": "array", "risks": "array"},
        "gate": gate_json("assert x['tasks'] and x['acceptance']"),
        "retries": 1,
    }]
    implementer_ids = []
    for lane in spec["implementers"]:
        sid = f"implement-{lane['id']}"
        implementer_ids.append(sid)
        steps.append({
            "id": sid, "needs": ["plan"],
            "cmd": harness_command(
                lane, f"implementer:{lane['id']}",
                f'--plan "$RUN/plan.md" --scope {json.dumps(lane["scope"])} --workspace {json.dumps(lane["id"])}',
            ),
            "schema": {"status": {"type": "string", "enum": ["pass"]},
                       "changed_files": "array", "checks": "array", "summary": "string"},
            "gate": gate_json("assert x['status']=='pass' and x['changed_files'] and x['checks']"),
            "retries": 1,
        })

    steps.append({
        "id": "integrate", "needs": implementer_ids,
        "cmd": 'python3 "$WORKFLOW_DIR/scripts/integrate.py" --run "$RUN" --out "$OUT"',
        "schema": {"status": {"type": "string", "enum": ["pass"]},
                   "lanes": "array", "changed_files": "array"},
        "gate": gate_json("assert x['status']=='pass' and x['changed_files']"),
    })
    previous = "integrate"
    reviewer = spec["review"]
    for cycle in range(1, reviewer["max_cycles"] + 1):
        capture = f"capture-{cycle}"
        review = f"review-{cycle}"
        repair = f"repair-{cycle}"
        steps.append({
            "id": capture, "needs": [previous],
            "cmd": (
                'python3 "$WORKFLOW_DIR/scripts/capture_evidence.py" '
                f'--cycle {cycle} --config "$WORKFLOW_DIR/factory.yaml" --out "$OUT"'
            ),
            "schema": {"status": {"type": "string", "enum": ["pass"]},
                       "screenshots": "array", "video": "string", "tests": "array"},
            "gate": gate_json("assert x['status']=='pass' and x['tests']"),
        })
        steps.append({
            "id": review, "needs": [capture],
            "cmd": harness_command(
                reviewer, f"reviewer:cycle-{cycle}",
                f'--plan "$RUN/plan.md" --evidence "$RUN/{capture}.md" --cycle {cycle}',
            ),
            "schema": {"verdict": {"type": "string", "enum": ["pass", "repair"]},
                       "issues": "array", "evidence": "array"},
            "gate": gate_json("assert x['verdict'] in ('pass','repair') and x['evidence']"),
        })
        steps.append({
            "id": repair, "needs": [review], "from": review,
            "when": {"op": "equals", "path": "/verdict", "value": "repair"},
            "cmd": harness_command(
                spec["implementers"][0], f"repairer:cycle-{cycle}",
                f'--review "$RUN/{review}.md" --cycle {cycle} --workspace repair-{cycle}',
            ),
            "schema": {"status": {"type": "string", "enum": ["pass"]},
                       "addressed": "array", "checks": "array"},
            "gate": gate_json("assert x['status']=='pass' and x['addressed'] and x['checks']"),
        })
        previous = repair

    final_review = f"review-{reviewer['max_cycles']}"
    steps.append({
        "id": "merge", "needs": [previous, final_review], "from": final_review,
        "when": {"op": "equals", "path": "/verdict", "value": "pass"},
        "cmd": (
            'python3 "$WORKFLOW_DIR/scripts/merge_guard.py" '
            f'--review "$RUN/{final_review}.md" --target {json.dumps(spec["merge"]["target"])} '
            + ("--apply " if spec["merge"]["apply"] else "") + '--out "$OUT"'
        ),
        "schema": {"status": {"type": "string", "enum": ["approved", "merged"]},
                   "target": "string", "commit": "string"},
        "gate": gate_json("assert x['status'] in ('approved','merged') and x['commit']"),
    })
    return {
        "version": 1, "workflow": spec["factory"], "workers": min(10, len(implementer_ids)),
        "input": {"required": True, "description": "One software change request"},
        "steps": steps,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("factory", type=Path)
    parser.add_argument("--out", type=Path, default=Path("steps.yaml"))
    args = parser.parse_args()
    spec = yaml.safe_load(args.factory.read_text(encoding="utf-8"))
    workflow = compile_factory(spec)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
