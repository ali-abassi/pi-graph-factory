#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


args = sys.argv[1:]
if not args or args[0] != "extract":
    raise SystemExit("fake Graphify supports only extract")
repo = Path(args[1]).resolve()
out = repo / "graphify-out"
out.mkdir(parents=True, exist_ok=True)
(out / "graph.json").write_text(
    json.dumps({
        "nodes": [{"id": "fixture", "label": "Fixture application"}],
        "edges": [],
        "hyperedges": [],
    }) + "\n",
    encoding="utf-8",
)
print(f"indexed {repo}")
