from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.factory import FactoryError, review_output


ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "scripts" / "factory.py"
ADAPTER = ROOT / "tests" / "traceability_adapter.py"
GRAPHIFY = ROOT / "tests" / "fake_graphify.py"


class FactoryTraceabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "traceability@example.test"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Traceability Fixture"],
            cwd=self.repo,
            check=True,
        )
        (self.repo / ".gitignore").write_text(".factory/\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, check=True)

        config = yaml.safe_load((ROOT / "factory.yaml").read_text(encoding="utf-8"))
        config["implementers"] = [config["implementers"][0]]
        config["evidence"] = {
            "screenshots": ["evidence/desktop.png"],
            "video": "evidence/flow.webm",
            "test_commands": ["test -s app.txt"],
        }
        config["merge"] = {"target": "main", "apply": False}
        self.config = self.root / "factory.yaml"
        self.config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        self.env = {
            **os.environ,
            "PI_GRAPH_FACTORY_ADAPTER": str(ADAPTER),
            "PI_GRAPH_FACTORY_GRAPHIFY": f"{sys.executable} {GRAPHIFY}",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(FACTORY), *args],
            text=True,
            capture_output=True,
            env=self.env,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def initialize(self, run_id: str) -> Path:
        initialized = self.cli(
            "init", "--repo", str(self.repo), "--config", str(self.config),
            "--request", "Build an application whose approved outcomes are traceable.",
            "--id", run_id,
        )
        return Path(initialized["run"])

    def plan_value(self, include_criteria: bool = True) -> dict:
        value = {
            "version": 1,
            "summary": "Build the traceable application",
            "proof": {"mode": "visual", "reason": "prove the user-facing application"},
            "tasks": [{
                "id": "build",
                "owner": "product",
                "files": ["app.txt", "evidence/**"],
                "acceptance": ["test -s app.txt"],
            }],
            "acceptance": ["test -s app.txt"],
            "risks": [],
            "open_questions": [],
        }
        if include_criteria:
            value["success_criteria"] = [
                {"id": "SC-1", "description": "The application artifact exists."},
                {"id": "SC-2", "description": "Current visual proof exists."},
            ]
        return value

    def submit(self, run: Path, value: dict, expected: int = 0) -> dict:
        path = self.root / f"{run.name}-plan.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return self.cli("plan", "--run", str(run), "--file", str(path), expected=expected)

    def approved(self, run_id: str) -> Path:
        run = self.initialize(run_id)
        planned = self.submit(run, self.plan_value())
        self.cli("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        return run

    def test_versioned_plan_requires_success_criteria(self) -> None:
        run = self.initialize("criteria-required")
        failed = self.submit(run, self.plan_value(include_criteria=False), expected=2)
        self.assertIn("success_criteria", failed["error"])

    def test_versioned_review_requires_criteria_array(self) -> None:
        run = self.approved("criteria-omitted")
        self.env["PI_GRAPH_FACTORY_CRITERIA_MODE"] = "omit"
        failed = self.cli("run", "--run", str(run), expected=2)
        self.assertIn("criteria", failed["error"])

    def test_versioned_review_requires_exact_criteria_coverage(self) -> None:
        run = self.approved("criteria-missing")
        self.env["PI_GRAPH_FACTORY_CRITERIA_MODE"] = "missing"
        failed = self.cli("run", "--run", str(run), expected=2)
        self.assertIn("exactly cover", failed["error"])

    def test_versioned_plan_with_exact_review_coverage_reaches_merge_ready(self) -> None:
        run = self.approved("criteria-exact")
        completed = self.cli("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merge_ready")
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [item["id"] for item in state["final_review"]["criteria"]],
            ["SC-1", "SC-2"],
        )

    def test_all_passing_criteria_cannot_request_advisory_repair(self) -> None:
        receipt = {
            "output": {
                "verdict": "repair",
                "issues": [{
                    "id": "FIX-1",
                    "owner": "product",
                    "criterion_id": "SC-1",
                    "target_files": ["app.txt"],
                    "message": "optional cleanup",
                }],
                "evidence": ["current-evidence"],
                "criteria": [
                    {"id": "SC-1", "status": "pass", "evidence": "artifact exists"},
                    {"id": "SC-2", "status": "pass", "evidence": "proof exists"},
                ],
            }
        }
        with self.assertRaisesRegex(FactoryError, "failed success criterion"):
            review_output(receipt, {"sha256": "current-evidence"}, self.plan_value())

    def test_repair_issue_must_cite_a_failed_criterion(self) -> None:
        receipt = {
            "output": {
                "verdict": "repair",
                "issues": [{
                    "id": "FIX-1",
                    "owner": "product",
                    "criterion_id": "SC-2",
                    "target_files": ["app.txt"],
                    "message": "wrongly routed repair",
                }],
                "evidence": ["current-evidence"],
                "criteria": [
                    {"id": "SC-1", "status": "fail", "evidence": "artifact missing"},
                    {"id": "SC-2", "status": "pass", "evidence": "proof exists"},
                ],
            }
        }
        with self.assertRaisesRegex(FactoryError, "must cite a failed"):
            review_output(receipt, {"sha256": "current-evidence"}, self.plan_value())

    def test_versioned_review_issue_requires_exact_target_files(self) -> None:
        plan = self.plan_value()
        receipt = {
            "output": {
                "verdict": "repair",
                "issues": [{
                    "id": "FIX-1",
                    "owner": "product",
                    "criterion_id": "SC-1",
                    "message": "app.txt is incomplete",
                }],
                "evidence": ["current-evidence"],
                "criteria": [
                    {"id": "SC-1", "status": "fail", "evidence": "app.txt is incomplete"},
                    {"id": "SC-2", "status": "pass", "evidence": "proof exists"},
                ],
            }
        }
        with self.assertRaisesRegex(FactoryError, "target_files"):
            review_output(receipt, {"sha256": "current-evidence"}, plan)
        receipt["output"]["issues"][0]["target_files"] = [{"path": "app.txt"}]
        with self.assertRaisesRegex(FactoryError, "exact repository-relative paths"):
            review_output(receipt, {"sha256": "current-evidence"}, plan)

    def test_versioned_review_issue_targets_must_belong_to_routed_owner(self) -> None:
        plan = {
            "version": 1,
            "summary": "Build a two-lane application",
            "success_criteria": [{"id": "SC-1", "description": "Validation agrees."}],
            "tasks": [
                {
                    "id": "backend",
                    "owner": "backend",
                    "files": ["deploy_gate.py"],
                    "acceptance": ["test -s deploy_gate.py"],
                },
                {
                    "id": "frontend",
                    "owner": "frontend",
                    "files": ["web/**"],
                    "acceptance": ["test -s web/app.js"],
                },
            ],
            "acceptance": ["test -s deploy_gate.py", "test -s web/app.js"],
            "risks": [],
            "open_questions": [],
        }
        receipt = {
            "output": {
                "verdict": "repair",
                "issues": [{
                    "id": "FIX-1",
                    "owner": "backend",
                    "criterion_id": "SC-1",
                    "target_files": ["web/app.js"],
                    "message": "Frontend validation accepts a version the backend rejects.",
                }],
                "evidence": ["current-evidence"],
                "criteria": [{
                    "id": "SC-1",
                    "status": "fail",
                    "evidence": "web/app.js and deploy_gate.py disagree",
                }],
            }
        }
        with self.assertRaisesRegex(FactoryError, "outside routed owner backend scope"):
            review_output(receipt, {"sha256": "current-evidence"}, plan)


if __name__ == "__main__":
    unittest.main()
