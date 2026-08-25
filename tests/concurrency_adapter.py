#!/usr/bin/env python3
"""Barrier-backed adapter that proves implementation lanes overlap in time."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
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
context = json.loads(args.context.read_text(encoding="utf-8"))
mode = os.environ.get("PI_GRAPH_FACTORY_RELIABILITY_MODE", "barrier")

if args.role.startswith("implement:"):
    owner = args.role.split(":", 1)[1]
    ready = Path(os.environ["PI_GRAPH_FACTORY_READY_DIR"])
    ready.mkdir(parents=True, exist_ok=True)
    (ready / owner).write_text("ready\n", encoding="utf-8")
    dependency_mode = os.environ.get("PI_GRAPH_FACTORY_DEPENDENCY_MODE") == "1"
    if dependency_mode and owner == "design":
        if not Path("product.txt").is_file():
            raise SystemExit("downstream design lane cannot see committed product output")
    expected = 1 if dependency_mode else int(os.environ.get("PI_GRAPH_FACTORY_EXPECTED_LANES", "1"))
    deadline = time.monotonic() + 5
    while len([path for path in ready.iterdir() if path.name != "release"]) < expected:
        if time.monotonic() >= deadline:
            raise SystemExit("implementation lanes did not overlap")
        time.sleep(0.02)
    if mode == "hold":
        while not (ready / "release").exists():
            if time.monotonic() >= deadline:
                raise SystemExit("hold was not released")
            time.sleep(0.02)
    target = Path(f"{owner}.txt")
    target.write_text(f"implemented by {owner}\n", encoding="utf-8")
    changed = [target.as_posix()]
    if owner == "product":
        evidence = Path("evidence")
        evidence.mkdir(exist_ok=True)
        (evidence / "desktop.png").write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        ))
        (evidence / "flow.webm").write_bytes(b"\x1aE\xdf\xa3\x00reliability")
        (evidence / "browser-receipt.json").write_text('{"console_errors":[]}\n', encoding="utf-8")
        changed.extend(["evidence/desktop.png", "evidence/flow.webm", "evidence/browser-receipt.json"])
    if mode in {"escape", "silent_escape", "commit_escape"}:
        Path("outside.txt").write_text("escape\n", encoding="utf-8")
    if mode in {"escape", "commit_escape"}:
        changed.append("outside.txt")
    if mode in {"commit", "commit_escape"}:
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(
            ["git", "commit", "-qm", f"agent commit by {owner}"], check=True
        )
    if mode == "amend_baseline":
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(
            ["git", "commit", "--amend", "-qm", f"amended by {owner}"], check=True
        )
    output = {"status": "pass", "changed_files": sorted(changed),
              "checks": ["barrier passed"], "summary": owner}
elif args.role.startswith("review:"):
    output = {"verdict": "pass", "issues": [], "evidence": [context["evidence"]["sha256"]]}
else:
    raise SystemExit(f"unsupported reliability role: {args.role}")

print(json.dumps({
    "status": "passed", "harness": args.harness, "model": args.model,
    "role": args.role, "output": output,
    "usage": {"input": 1, "output": 1, "total": 2, "cost": 0},
}, separators=(",", ":")))
