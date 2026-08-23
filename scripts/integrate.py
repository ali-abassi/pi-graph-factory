#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--run", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
receipts = sorted(args.run.glob("implement-*.md"))
values = [json.loads(path.read_text()) for path in receipts]
changed = sorted({item for value in values for item in value.get("changed_files", [])})
result = {"status": "pass" if changed else "fail", "lanes": [path.stem for path in receipts], "changed_files": changed}
args.out.write_text(json.dumps(result) + "\n")
raise SystemExit(0 if changed else 1)
