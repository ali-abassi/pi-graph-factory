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
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
spec = yaml.safe_load(args.config.read_text())
evidence = spec["evidence"]
tests = []
for command in evidence.get("test_commands", []):
    completed = subprocess.run(["bash", "-c", command], text=True, capture_output=True, check=False)
    tests.append({"command": command, "passed": completed.returncode == 0,
                  "output": (completed.stdout + completed.stderr)[-1000:]})
screens = [path for path in evidence["screenshots"] if Path(path).is_file() and Path(path).stat().st_size]
video = evidence.get("video") or ""
video_ok = not video or (Path(video).is_file() and Path(video).stat().st_size > 0)
status = "pass" if len(screens) == len(evidence["screenshots"]) and video_ok and all(x["passed"] for x in tests) else "fail"
args.out.write_text(json.dumps({"status": status, "screenshots": screens, "video": video, "tests": tests}) + "\n")
raise SystemExit(0 if status == "pass" else 1)
