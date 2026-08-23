#!/usr/bin/env python3
"""Materialize the bounded-loop human escalation receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--cycles", type=int, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()

review = json.loads(args.review.read_text(encoding="utf-8"))
issues = review.get("issues")
if review.get("verdict") != "repair" or not isinstance(issues, list) or not issues:
    raise SystemExit("human escalation requires an unresolved repair verdict")

args.out.write_text(
    json.dumps({"status": "human_required", "cycles": args.cycles, "issues": issues}) + "\n",
    encoding="utf-8",
)
