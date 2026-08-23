#!/usr/bin/env python3
"""Validate evidence produced by project-owned capture commands.

This prototype does not invent browser automation. Projects provide screenshot,
video, and test commands; this adapter verifies the declared files and receipts.
"""
import argparse
import json
import subprocess
from pathlib import Path

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--cycle", type=int, required=True)
parser.add_argument("--config", type=Path, required=True)
parser.add_argument("--plan", type=Path)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
spec = yaml.safe_load(args.config.read_text())
evidence = spec["evidence"]
policy = evidence.get("policy", "always")
plan = json.loads(args.plan.read_text()) if args.plan and args.plan.is_file() else {}
planned_proof = plan.get("proof") if isinstance(plan, dict) else None
if policy == "always":
    proof = {"mode": "visual", "reason": "factory evidence policy requires visual proof"}
elif policy == "never":
    proof = {"mode": "tests", "reason": "factory evidence policy disables visual proof"}
elif isinstance(planned_proof, dict) and planned_proof.get("mode") in {"tests", "visual"}:
    proof = planned_proof
else:
    proof = {"mode": "tests", "reason": "legacy plan without a visual-proof requirement"}
visual = proof["mode"] == "visual"
capture = []
for command in evidence.get("capture_commands", []) if visual else []:
    completed = subprocess.run(["bash", "-c", command], text=True, capture_output=True, check=False)
    capture.append({"command": command, "passed": completed.returncode == 0,
                    "output": (completed.stdout + completed.stderr)[-1000:]})
tests = []
for command in evidence.get("test_commands", []):
    completed = subprocess.run(["bash", "-c", command], text=True, capture_output=True, check=False)
    tests.append({"command": command, "passed": completed.returncode == 0,
                  "output": (completed.stdout + completed.stderr)[-1000:]})
expected_screens = evidence["screenshots"] if visual else []
screens = [path for path in expected_screens if Path(path).is_file() and Path(path).stat().st_size]
video = (evidence.get("video") or "") if visual else ""
video_ok = not video or (Path(video).is_file() and Path(video).stat().st_size > 0)
expected_artifacts = evidence.get("artifacts", []) if visual else []
artifacts = [path for path in expected_artifacts
             if Path(path).is_file() and Path(path).stat().st_size]
status = "pass" if (len(screens) == len(expected_screens) and video_ok
                    and len(artifacts) == len(expected_artifacts)
                    and all(x["passed"] for x in capture) and all(x["passed"] for x in tests)) else "fail"
args.out.write_text(json.dumps({"status": status, "proof": proof, "capture": capture, "screenshots": screens,
                                "video": video, "artifacts": artifacts, "tests": tests}) + "\n")
raise SystemExit(0 if status == "pass" else 1)
