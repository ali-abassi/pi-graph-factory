from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "scripts" / "factory.py"
ADAPTER = ROOT / "tests" / "benchmark_adapter.py"
GRAPHIFY = ROOT / "tests" / "fake_graphify.py"


class FactoryBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "benchmark@example.test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Factory Benchmark"], cwd=self.repo, check=True)
        (self.repo / ".gitignore").write_text(".factory/\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, check=True)
        self.env = {
            **os.environ,
            "PI_GRAPH_FACTORY_ADAPTER": str(ADAPTER),
            "PI_GRAPH_FACTORY_GRAPHIFY": f"{sys.executable} {GRAPHIFY}",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(FACTORY), *args],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def config(self, owners: list[str]) -> Path:
        source = yaml.safe_load((ROOT / "factory.yaml").read_text(encoding="utf-8"))
        base = source["implementers"][0]
        source["implementers"] = [
            {**base, "id": owner, "scope": f"Approved {owner} files"}
            for owner in owners
        ]
        source["evidence"] = {
            "screenshots": ["evidence/desktop.png"],
            "video": "evidence/flow.webm",
            "test_commands": ["git diff --check", "test -f evidence/browser-receipt.json"],
        }
        source["merge"] = {"target": "main", "apply": True}
        path = self.root / f"factory-{'-'.join(owners)}.yaml"
        path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
        return path

    def execute(
        self,
        owners: list[str],
        tasks: list[dict],
        acceptance: list[str],
        *,
        expected: int = 0,
    ) -> tuple[Path, dict]:
        initialized = self.command(
            "init", "--repo", str(self.repo), "--config", str(self.config(owners)),
            "--request", "Implement the approved benchmark request.", "--id", "benchmark-run",
        )
        run = Path(initialized["run"])
        plan = {
            "summary": "Approved benchmark plan",
            "tasks": tasks,
            "acceptance": acceptance,
            "risks": [],
            "open_questions": [],
        }
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        planned = self.command("plan", "--run", str(run), "--file", str(plan_path))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        return run, self.command("run", "--run", str(run), expected=expected)

    @staticmethod
    def task(task_id: str, owner: str, files: list[str], acceptance: list[str]) -> dict:
        return {"id": task_id, "owner": owner, "files": files, "acceptance": acceptance}

    def test_simple_single_owner_change_passes_first_review(self) -> None:
        _, result = self.execute(
            ["product"],
            [self.task("fix", "product", ["product.txt", "evidence/**"], ["test -s product.txt"])],
            ["test -s product.txt"],
        )
        self.assertEqual((result["phase"], result["cycles"]), ("merged", 1))

    def test_medium_two_lane_change_repairs_only_named_owner(self) -> None:
        self.env["PI_GRAPH_FACTORY_REVIEW_OWNERS"] = "design"
        _, result = self.execute(
            ["product", "design"],
            [
                self.task("api", "product", ["api.txt", "evidence/**"], ["test -s api.txt"]),
                self.task("ui", "design", ["ui.txt"], ["test -s ui.txt"]),
            ],
            ["test -s api.txt", "test -s ui.txt"],
        )
        self.assertEqual((result["phase"], result["cycles"]), ("merged", 2))
        self.assertIn("repaired in cycle 1", (self.repo / "ui.txt").read_text(encoding="utf-8"))
        self.assertNotIn("repaired", (self.repo / "api.txt").read_text(encoding="utf-8"))

    def test_complex_three_lane_change_survives_two_directed_repairs(self) -> None:
        self.env["PI_GRAPH_FACTORY_REVIEW_OWNERS"] = "design,docs"
        _, result = self.execute(
            ["product", "design", "docs"],
            [
                self.task("core", "product", ["core.txt", "evidence/**"], ["test -s core.txt"]),
                self.task("interface", "design", ["ui.txt"], ["test -s ui.txt"]),
                self.task("guide", "docs", ["guide.txt"], ["test -s guide.txt"]),
            ],
            ["test -s core.txt", "test -s ui.txt", "test -s guide.txt"],
        )
        self.assertEqual((result["phase"], result["cycles"]), ("merged", 3))
        self.assertIn("repaired in cycle 1", (self.repo / "ui.txt").read_text(encoding="utf-8"))
        self.assertIn("repaired in cycle 2", (self.repo / "guide.txt").read_text(encoding="utf-8"))

    def test_untracked_implementation_scope_escape_is_discarded(self) -> None:
        self.env["PI_GRAPH_FACTORY_ESCAPE_OWNER"] = "product"
        _, result = self.execute(
            ["product"],
            [self.task("fix", "product", ["product.txt", "evidence/**"], ["test -s product.txt"])],
            ["test -s product.txt"],
        )
        self.assertEqual(result["phase"], "merged")
        self.assertFalse((self.repo / "outside-approved-scope.txt").exists())
        run = Path(result["run"])
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(
            state["lane_receipts"]["product"]["receipt"]["scope_correction"][
                "discarded_files"
            ],
            ["outside-approved-scope.txt"],
        )

    def test_overlapping_ownership_is_refused_before_approval(self) -> None:
        initialized = self.command(
            "init", "--repo", str(self.repo), "--config", str(self.config(["product", "design"])),
            "--request", "Reject ambiguous ownership.", "--id", "benchmark-run",
        )
        plan = {
            "summary": "Ambiguous plan",
            "tasks": [
                self.task("all-src", "product", ["src/**"], ["true"]),
                self.task("api", "design", ["src/api/**"], ["true"]),
            ],
            "acceptance": ["true"], "risks": [], "open_questions": [],
        }
        path = self.root / "overlap.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(FACTORY), "plan", "--run", initialized["run"], "--file", str(path)],
            capture_output=True, text=True, env=self.env, timeout=60, check=False,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("overlapping file ownership", result.stdout)

    def test_approved_task_acceptance_is_executed(self) -> None:
        _, result = self.execute(
            ["product"],
            [self.task("fix", "product", ["product.txt", "evidence/**"], ["false"])],
            ["test -s product.txt"],
            expected=2,
        )
        self.assertIn("approved acceptance command failed", result["error"])

    def test_reviewer_must_cite_current_evidence_receipt(self) -> None:
        self.env["PI_GRAPH_FACTORY_FORGE_EVIDENCE"] = "1"
        _, result = self.execute(
            ["product"],
            [self.task("fix", "product", ["product.txt", "evidence/**"], ["test -s product.txt"])],
            ["test -s product.txt"],
            expected=2,
        )
        self.assertIn("current evidence receipt", result["error"])


if __name__ == "__main__":
    unittest.main()
