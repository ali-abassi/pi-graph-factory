#!/usr/bin/env python3
import argparse, json, subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--review", type=Path, required=True)
parser.add_argument("--target", required=True)
parser.add_argument("--apply", action="store_true")
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
review = json.loads(args.review.read_text())
if review.get("verdict") != "pass":
    raise SystemExit("merge refused: final review did not pass")
subprocess.run(["git", "diff", "--check"], check=True)
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
status = "approved"
if args.apply:
    subprocess.run(["git", "switch", args.target], check=True)
    subprocess.run(["git", "merge", "--ff-only", commit], check=True)
    status = "merged"
args.out.write_text(json.dumps({"status": status, "target": args.target, "commit": commit}) + "\n")
