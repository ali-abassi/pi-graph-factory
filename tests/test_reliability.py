from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "scripts" / "factory.py"
ADAPTER = ROOT / "tests" / "concurrency_adapter.py"
GRAPHIFY = ROOT / "tests" / "fake_graphify.py"


class FactoryReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "reliability@example.test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Reliability Fixture"], cwd=self.repo, check=True)
        (self.repo / ".gitignore").write_text(".factory/\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, check=True)
        self.ready = self.root / "ready"
        self.env = {
            **os.environ,
            "PI_GRAPH_FACTORY_ADAPTER": str(ADAPTER),
            "PI_GRAPH_FACTORY_GRAPHIFY": f"{sys.executable} {GRAPHIFY}",
            "PI_GRAPH_FACTORY_READY_DIR": str(self.ready),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(FACTORY), *args], text=True, capture_output=True,
            env=self.env, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def approved_run(self, owners: list[str]) -> Path:
        config = yaml.safe_load((ROOT / "factory.yaml").read_text(encoding="utf-8"))
        base = config["implementers"][0]
        config["implementers"] = [
            {**base, "id": owner, "scope": owner} for owner in owners
        ]
        config["limits"]["termination_grace_seconds"] = 1
        config["evidence"] = {
            "screenshots": ["evidence/desktop.png"], "video": "evidence/flow.webm",
            "test_commands": ["test -f evidence/browser-receipt.json"],
        }
        config["merge"] = {"target": "main", "apply": True}
        config_path = self.root / "factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        initialized = self.cli(
            "init", "--repo", str(self.repo), "--config", str(config_path),
            "--request", "Reliability fixture", "--id", "reliability-run",
        )
        run = Path(initialized["run"])
        tasks = []
        for owner in owners:
            files = [f"{owner}.txt"]
            if owner == "product":
                files.append("evidence/**")
            tasks.append({"id": owner, "owner": owner, "files": files,
                          "acceptance": [f"test -s {owner}.txt"]})
        plan = {
            "summary": "Reliability plan", "tasks": tasks,
            "acceptance": [f"test -s {owner}.txt" for owner in owners],
            "risks": [], "open_questions": [],
        }
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        planned = self.cli("plan", "--run", str(run), "--file", str(plan_path))
        self.cli("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        return run

    def test_active_implementation_lanes_overlap(self) -> None:
        run = self.approved_run(["product", "design"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "2"
        completed = self.cli("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")

    def test_untracked_scope_escape_is_discarded_and_recorded(self) -> None:
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "escape"
        completed = self.cli("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        self.assertFalse((self.repo / "outside.txt").exists())
        state = json.loads((run / "state.json").read_text())
        correction = state["lane_receipts"]["product"]["receipt"]["scope_correction"]
        self.assertEqual(correction["discarded_files"], ["outside.txt"])
        self.assertTrue(
            next((run / "receipts").glob("scope-correction-product-*.json"), None)
        )
        events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
        lane = next(event for event in events if event["event"] == "lane_completed")
        self.assertEqual(
            lane["payload"]["discarded_untracked_scope_escapes"], ["outside.txt"]
        )

    def test_tracked_scope_escape_is_durable_and_fails_closed(self) -> None:
        (self.repo / "outside.txt").write_text("tracked baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "outside.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "track protected file"], cwd=self.repo, check=True)
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "escape"
        failed = self.cli("run", "--run", str(run), expected=2)
        self.assertIn("outside approved scope", failed["error"])
        status = self.cli("status", "--run", str(run), expected=1)
        self.assertFalse(status["ok"])
        self.assertIn("outside approved scope", status["state"]["last_error"]["message"])
        events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-1]["event"], "transition_failed")

    def test_unreported_untracked_scope_escape_is_discovered_and_discarded(self) -> None:
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "silent_escape"
        completed = self.cli("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        self.assertFalse((self.repo / "outside.txt").exists())
        state = json.loads((run / "state.json").read_text())
        correction = state["lane_receipts"]["product"]["receipt"]["scope_correction"]
        self.assertEqual(correction["discarded_files"], ["outside.txt"])
        self.assertNotIn("outside.txt", correction["reported_changed_files"])

    def test_linear_agent_commit_is_normalized_and_recorded(self) -> None:
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "commit"
        completed = self.cli("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        state = json.loads((run / "state.json").read_text())
        recovery = state["lane_receipts"]["product"]["receipt"][
            "agent_commit_recovery"
        ]
        self.assertEqual(len(recovery["agent_commits"]), 1)
        self.assertNotEqual(recovery["agent_head"], state["lane_receipts"]["product"]["commit"])
        self.assertTrue(
            next((run / "receipts").glob("agent-commit-recovery-product-*.json"), None)
        )
        events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
        lane = next(event for event in events if event["event"] == "lane_completed")
        self.assertEqual(lane["payload"]["normalized_agent_commits"], recovery["agent_commits"])

    def test_committed_tracked_scope_escape_still_fails_closed(self) -> None:
        (self.repo / "outside.txt").write_text("tracked baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "outside.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "track protected file"], cwd=self.repo, check=True)
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "commit_escape"
        failed = self.cli("run", "--run", str(run), expected=2)
        self.assertIn("outside approved scope", failed["error"])

    def test_amended_lane_baseline_fails_closed(self) -> None:
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "amend_baseline"
        failed = self.cli("run", "--run", str(run), expected=2)
        self.assertIn("rewrote or replaced its lane baseline", failed["error"])

    def test_second_writer_is_refused_by_run_lock(self) -> None:
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "hold"
        first = subprocess.Popen(
            [sys.executable, str(FACTORY), "run", "--run", str(run)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env,
        )
        deadline = time.monotonic() + 10
        while not (self.ready / "product").exists():
            if time.monotonic() >= deadline:
                first.kill()
                self.fail("first writer did not reach the hold point")
            time.sleep(0.02)
        try:
            refused = self.cli("run", "--run", str(run), expected=2)
        finally:
            (self.ready / "release").write_text("release\n", encoding="utf-8")
            stdout, stderr = first.communicate(timeout=20)
        self.assertIn("already active", refused["error"])
        self.assertEqual(first.returncode, 0, stdout + stderr)
        self.assertEqual(json.loads(stdout)["phase"], "merged")

    def test_abrupt_controller_death_can_terminate_and_resume_its_lane(self) -> None:
        run = self.approved_run(["product"])
        self.env["PI_GRAPH_FACTORY_EXPECTED_LANES"] = "1"
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "hold"
        first = subprocess.Popen(
            [sys.executable, str(FACTORY), "run", "--run", str(run)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )
        deadline = time.monotonic() + 10
        while not (self.ready / "product").exists() or not list((run / "active").glob("*.json")):
            if time.monotonic() >= deadline:
                first.kill()
                self.fail("factory did not reach the interruptible lane checkpoint")
            time.sleep(0.02)
        first.kill()
        first.communicate(timeout=5)
        inspected = self.cli("inspect", "--run", str(run))
        self.assertEqual(inspected["phase"], "implementing")
        self.assertTrue(inspected["resumable"])
        self.assertTrue(any(item["alive"] for item in inspected["active_agents"]))
        self.env["PI_GRAPH_FACTORY_RELIABILITY_MODE"] = "barrier"
        resumed = self.cli("resume", "--run", str(run), "--terminate-active")
        self.assertEqual(resumed["phase"], "merged")
        self.assertFalse(list((run / "active").glob("*.json")))


if __name__ == "__main__":
    unittest.main()
