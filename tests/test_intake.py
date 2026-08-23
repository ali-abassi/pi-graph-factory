from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "scripts" / "factory.py"


INTERACTIVE_BRIEF = """# Goal Brief: Example

## Objective
Build the example.
## Definition Of Done
- It works.
## Planning Posture
- Evidence policy: proportional.
## Achievability Check
- Status: Ready With Assumptions.
## Pass/Fail Checklist
| Requirement | Pass Condition | Evidence |
| --- | --- | --- |
| Example | Works | Test |
## Deliverables
- Example
## Task Graph
| Task | Depends On | Can Run In Parallel? | Owner | Output |
| --- | --- | --- | --- | --- |
| Build | None | No | product | Example |
## Orchestration Plan
- One lane.
## Validation
- Run tests.
## Stop Conditions
- Stop on missing authority.
## Ready-To-Run Goal Prompt
Build and test the example.
"""


AUTO_BRIEF = """# Self-Grilled Brief: Example

## Intent Read
Build the example.
## Status
Ready With Assumptions
## Resolved Direction
One focused example.
## Self-Grill Ledger
The material decision is recorded in the ledger.
## Taste Direction
Native and restrained.
## Experience Architecture
One complete path with failure handling.
## Product And Technical Architecture
One local application boundary.
## Execution Contract
Build and test the example.
## Assumptions
- The default is reversible.
## Human-Only Decisions
- None.
## Ready-To-Run Prompt
Build and test the example.
"""


def auto_ledger() -> dict:
    areas = ["intent", "audience", "scope", "experience", "taste", "architecture",
             "validation"]
    return {
        "schema_version": 1,
        "goal": "Build the example.",
        "intent_read": "A small complete example with observable proof.",
        "ready_status": "ready_with_assumptions",
        "coverage": [
            {"area": area, "status": "assumed" if area == "audience" else "resolved",
             "reason": f"{area} is bounded for the first version."}
            for area in areas
        ],
        "questions": [{
            "id": "scope-001",
            "area": "scope",
            "question": "What is the smallest complete scope?",
            "answer": "One working example with tests.",
            "answer_type": "default",
            "basis": "It is coherent and reversible.",
            "confidence": "medium",
            "reversibility": "easy",
            "implications": ["Exclude speculative extensions."],
            "status": "resolved",
            "would_overturn": "A broader explicit requirement.",
        }],
        "decision_summary": {
            "point_of_view": "Complete beats broad.",
            "primary_user": "A first-time operator.",
            "core_outcome": "Run one proven example.",
            "signature_move": "One obvious path.",
            "architecture": "One local application boundary.",
            "non_goals": ["Speculative extensions"],
            "quality_floor": ["Tests pass"],
        },
        "human_decisions": [],
    }


class FactoryIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.test"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Fixture"], cwd=self.repo, check=True
        )
        (self.repo / ".gitignore").write_text(".factory/\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(FACTORY), *args],
            capture_output=True,
            text=True,
            env=os.environ,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_direct_intake_remains_backward_compatible_and_durable(self) -> None:
        payload = self.command(
            "init", "--repo", str(self.repo), "--request", "Fix the export bug.",
            "--id", "direct-run",
        )
        run = Path(payload["run"])
        self.assertEqual(payload["intake"]["mode"], "direct")
        self.assertEqual((run / "intake" / "request.md").read_text(), "Fix the export bug.\n")

    def test_interactive_intake_requires_and_preserves_a_ready_goal_brief(self) -> None:
        brief = self.root / "goal-brief.md"
        brief.write_text(INTERACTIVE_BRIEF, encoding="utf-8")
        payload = self.command(
            "init", "--repo", str(self.repo), "--request-file", str(brief),
            "--intake-mode", "interactive", "--id", "interactive-run",
        )
        run = Path(payload["run"])
        self.assertEqual(payload["intake"]["status"], "ready_with_assumptions")
        self.assertEqual((run / "intake" / "goal-brief.md").read_text().strip(),
                         INTERACTIVE_BRIEF.strip())

    def test_auto_intake_preserves_a_validated_brief_and_decision_ledger(self) -> None:
        brief = self.root / "self-grilled-brief.md"
        ledger = self.root / "self-grill.json"
        brief.write_text(AUTO_BRIEF, encoding="utf-8")
        ledger.write_text(json.dumps(auto_ledger()), encoding="utf-8")
        payload = self.command(
            "init", "--repo", str(self.repo), "--request-file", str(brief),
            "--intake-mode", "auto", "--intake-ledger", str(ledger),
            "--id", "auto-run",
        )
        run = Path(payload["run"])
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(state["intake"]["mode"], "auto")
        self.assertEqual(state["intake"]["status"], "ready_with_assumptions")
        self.assertEqual(
            json.loads((run / "intake" / "self-grill.json").read_text())["goal"],
            "Build the example.",
        )

    def test_auto_intake_refuses_unresolved_human_only_decisions(self) -> None:
        brief = self.root / "self-grilled-brief.md"
        ledger = self.root / "self-grill.json"
        value = auto_ledger()
        value["ready_status"] = "human_decision_required"
        value["human_decisions"] = ["platform-001"]
        brief.write_text(AUTO_BRIEF, encoding="utf-8")
        ledger.write_text(json.dumps(value), encoding="utf-8")
        payload = self.command(
            "init", "--repo", str(self.repo), "--request-file", str(brief),
            "--intake-mode", "auto", "--intake-ledger", str(ledger),
            "--id", "blocked-auto-run", expected=2,
        )
        self.assertIn("unresolved human-only decisions", payload["error"])
        self.assertFalse((self.repo / ".factory" / "runs" / "blocked-auto-run").exists())

    def test_auto_new_repo_seeds_vision_from_the_resolved_outcome(self) -> None:
        brief = self.root / "self-grilled-brief.md"
        ledger = self.root / "self-grill.json"
        target = self.root / "new-repo"
        brief.write_text(AUTO_BRIEF, encoding="utf-8")
        ledger.write_text(json.dumps(auto_ledger()), encoding="utf-8")
        self.command(
            "init", "--repo", str(target), "--new-repo", "--request-file", str(brief),
            "--intake-mode", "auto", "--intake-ledger", str(ledger),
            "--id", "auto-new-run",
        )
        vision = (target / "VISION.md").read_text()
        self.assertIn("Run one proven example.", vision)
        self.assertNotIn("Self-Grill Ledger", vision)


if __name__ == "__main__":
    unittest.main()
