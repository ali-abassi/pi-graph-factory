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
FIXTURE = ROOT / "tests" / "fixture_adapter.py"


class FactoryLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.repo, check=True)
        (self.repo / ".gitignore").write_text(".factory/\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, check=True)
        self.config = self.root / "factory.yaml"
        value = yaml.safe_load((ROOT / "factory.yaml").read_text())
        value["implementers"] = [value["implementers"][0]]
        value["review"]["max_cycles"] = 5
        value["evidence"] = {
            "capture_commands": ["cp app.txt evidence/flow.webm"],
            "screenshots": ["evidence/desktop.png"],
            "video": "evidence/flow.webm",
            "test_commands": ["test -s app.txt", "test -f evidence/browser-receipt.json"],
        }
        value["merge"] = {"target": "main", "apply": True}
        self.config.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
        self.counter = self.root / "review-count"
        self.env = {**os.environ, "PI_GRAPH_FACTORY_ADAPTER": str(FIXTURE),
                    "PI_GRAPH_FACTORY_REVIEW_COUNTER": str(self.counter)}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, *args: str, expected: int = 0) -> dict:
        result = subprocess.run([sys.executable, str(FACTORY), *args], capture_output=True,
                                text=True, env=self.env, timeout=60, check=False)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def initialize(self, config: Path | None = None, run_id: str = "test-run") -> Path:
        payload = self.command("init", "--repo", str(self.repo), "--config", str(self.config),
                               "--request", "Create and prove a reviewed text application.",
                               "--id", run_id) if config is None else self.command(
                                   "init", "--repo", str(self.repo), "--config", str(config),
                                   "--request", "Create and prove a reviewed text application.",
                                   "--id", run_id)
        return Path(payload["run"])

    def write_plan(self, path: Path, questions: list[dict]) -> Path:
        plan = {
            "summary": "Create the text application",
            "tasks": [{"id": "build", "owner": "product",
                       "files": ["app.txt", "evidence/**"],
                       "acceptance": ["test -s app.txt"]}],
            "acceptance": ["test -s app.txt"], "risks": [], "open_questions": questions,
        }
        path.write_text(json.dumps(plan), encoding="utf-8")
        return path

    def test_full_trigger_clarification_approval_repair_evidence_and_merge(self) -> None:
        run = self.initialize()
        first = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "plan-1.json",
            [{"id": "tone", "question": "Which tone?", "blocking": True}],
        )))
        self.assertEqual(first["phase"], "clarification")
        premature = self.command("run", "--run", str(run), expected=2)
        self.assertIn("explicitly approved", premature["error"])
        answered = self.command("answer", "--run", str(run), "--question", "tone",
                                "--answer", "Direct")
        self.assertEqual(answered["phase"], "intake")
        revised = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "plan-2.json", [],
        )))
        wrong = self.command("approve", "--run", str(run), "--sha256", "0" * 64, expected=2)
        self.assertIn("does not match", wrong["error"])
        self.command("approve", "--run", str(run), "--sha256", revised["plan_sha256"])
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        self.assertEqual(completed["cycles"], 2)
        self.assertEqual((self.repo / "app.txt").read_text(), "implemented\nreviewed 1\n")
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(state["approved_plan_sha256"], state["plan_sha256"])
        self.assertEqual(state["final_review"]["verdict"], "pass")
        self.assertEqual(len(state["cycles"]), 2)
        self.assertNotEqual(state["cycles"][0]["evidence"]["source_commit"],
                            state["cycles"][1]["evidence"]["source_commit"])
        first_video = next(item for item in state["cycles"][0]["evidence"]["files"]
                           if item["path"] == "evidence/flow.webm")
        second_video = next(item for item in state["cycles"][1]["evidence"]["files"]
                            if item["path"] == "evidence/flow.webm")
        self.assertNotEqual(first_video["sha256"], second_video["sha256"])
        self.assertTrue(state["cycles"][1]["evidence"]["capture"][0]["passed"])
        receipt = json.loads((run / "receipt.json").read_text())
        self.assertEqual(receipt["merge"]["status"], "merged")
        self.assertEqual(receipt["evidence_sha256"], state["final_evidence_sha256"])

    def test_conflicting_file_ownership_is_rejected_before_approval(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        second = dict(config["implementers"][0])
        second["id"] = "second"
        config["implementers"].append(second)
        config_path = self.root / "two-lanes.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        run = self.initialize(config_path, "conflict-run")
        plan = {
            "summary": "conflict", "acceptance": ["true"], "risks": [], "open_questions": [],
            "tasks": [
                {"id": "one", "owner": "product", "files": ["app.txt"], "acceptance": ["true"]},
                {"id": "two", "owner": "second", "files": ["app.txt"], "acceptance": ["true"]},
            ],
        }
        path = self.root / "conflict.json"
        path.write_text(json.dumps(plan))
        payload = self.command("plan", "--run", str(run), "--file", str(path), expected=2)
        self.assertIn("conflicting file ownership", payload["error"])

    def test_frozen_contract_drift_is_rejected(self) -> None:
        run = self.initialize()
        (run / "factory.yaml").write_text((run / "factory.yaml").read_text() + "\n")
        payload = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "plan.json", [])), expected=2)
        self.assertIn("contract drifted", payload["error"])

    def test_configured_planner_generates_a_durable_typed_plan(self) -> None:
        run = self.initialize(run_id="generated-plan-run")
        planned = self.command("plan", "--run", str(run), "--generate")
        self.assertEqual(planned["phase"], "awaiting_plan_approval")
        self.assertEqual(planned["source"], "planner")
        plan_path = Path(planned["plan"])
        self.assertTrue(plan_path.is_file())
        self.assertEqual(json.loads(plan_path.read_text())["tasks"][0]["owner"], "product")
        self.assertEqual(json.loads(plan_path.read_text())["version"], 1)
        self.assertEqual(json.loads(plan_path.read_text())["success_criteria"][0]["id"], "SC-1")
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(state["plan_revision"], 1)
        self.assertTrue((run / "receipts" / "planner-1.json").is_file())
        self.assertEqual(subprocess.check_output(
            ["git", "-C", str(self.repo), "status", "--porcelain"], text=True,
        ), "")

    def test_new_repository_bootstrap_has_safe_ignore_defaults(self) -> None:
        target = self.root / "new-repository"
        initialized = self.command(
            "init", "--repo", str(target), "--new-repo", "--config", str(self.config),
            "--request", "Build a new application.", "--id", "new-repository-run",
        )
        self.assertEqual(initialized["phase"], "intake")
        ignored = (target / ".gitignore").read_text(encoding="utf-8")
        for entry in (".factory/", ".env", "__pycache__/", "*.py[cod]", "node_modules/"):
            self.assertIn(entry, ignored)
        self.assertEqual(
            subprocess.check_output(
                ["git", "-C", str(target), "status", "--porcelain"], text=True,
            ),
            "",
        )
        public_config = yaml.safe_load((ROOT / "factory.yaml").read_text(encoding="utf-8"))
        evidence_paths = [
            *public_config["evidence"]["screenshots"],
            public_config["evidence"]["video"],
            "evidence/factory/browser-receipt.json",
        ]
        for path in evidence_paths:
            ignored = subprocess.run(
                ["git", "-C", str(target), "check-ignore", "--no-index", "--", path],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(ignored.returncode, 1, f"public proof path is ignored: {path}")

    def test_five_failed_reviews_escalate_without_merge(self) -> None:
        run = self.initialize(run_id="exhausted-run")
        planned = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "exhausted-plan.json", [])))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_ALWAYS_REPAIR"] = "1"
        completed = self.command("run", "--run", str(run), expected=1)
        self.assertEqual(completed["phase"], "human_required")
        self.assertEqual(completed["cycles"], 5)
        self.assertEqual(git_head(self.repo), git_head(self.repo, "main"))

    def test_blocked_implementer_receipt_cannot_reach_integration(self) -> None:
        run = self.initialize(run_id="blocked-implementer-run")
        planned = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "blocked-plan.json", [])))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_IMPLEMENT_STATUS"] = "blocked"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("did not return a passing receipt", failed["error"])
        state = json.loads((run / "state.json").read_text())
        self.assertIsNone(state["integration"])
        self.assertIn("did not return a passing receipt", state["last_error"]["message"])

    def test_generated_runtime_artifact_cannot_reach_integration(self) -> None:
        run = self.initialize(run_id="generated-artifact-run")
        planned = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "generated-artifact-plan.json", [])))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_WRITE_PYC"] = "1"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("generated or secret-bearing artifacts", failed["error"])
        state = json.loads((run / "state.json").read_text())
        self.assertIsNone(state["integration"])
        self.assertEqual(git_head(self.repo), git_head(self.repo, "main"))

    def test_agent_timeout_stops_the_process_group_and_fails_closed(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["limits"]["agent_timeout_seconds"] = 1
        config_path = self.root / "timeout-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        run = self.initialize(config_path, "timeout-run")
        planned = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "timeout-plan.json", [])))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_ADAPTER_SLEEP"] = "2"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("exceeded 1s timeout", failed["error"])
        state = json.loads((run / "state.json").read_text())
        self.assertIsNone(state["integration"])
        self.assertIn("exceeded 1s timeout", state["last_error"]["message"])

    def test_token_limit_stops_dispatch_before_review(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["limits"]["max_total_tokens"] = 1
        config_path = self.root / "budget-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        run = self.initialize(config_path, "budget-run")
        planned = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "budget-plan.json", [])))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_USAGE_TOTAL"] = "2"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("token dispatch limit reached", failed["error"])
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(state["usage"]["total_tokens"], 2)
        self.assertFalse(self.counter.exists(), "reviewer must not start after budget exhaustion")

    def test_planner_usage_limit_stops_implementation_batch(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["limits"]["max_total_tokens"] = 1
        config_path = self.root / "planner-budget-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        run = self.initialize(config_path, "planner-budget-run")
        planned = self.command("plan", "--run", str(run), "--generate")
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("cannot dispatch implementation batch", failed["error"])
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(state["phase"], "approved")
        self.assertFalse((run / "worktrees").exists())

    def test_required_usage_rejects_unknown_provider_receipt(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["limits"]["require_usage"] = True
        config_path = self.root / "required-usage-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        run = self.initialize(config_path, "required-usage-run")
        planned = self.command("plan", "--run", str(run), "--file", str(self.write_plan(
            self.root / "required-usage-plan.json", [])))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_USAGE_UNKNOWN"] = "1"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("did not report required token and cost usage", failed["error"])
        state = json.loads((run / "state.json").read_text())
        self.assertIsNone(state["integration"])

    def test_plan_rejects_prose_where_executable_commands_are_required(self) -> None:
        run = self.initialize(run_id="prose-command-run")
        path = self.write_plan(self.root / "prose-plan.json", [])
        value = json.loads(path.read_text())
        value["acceptance"] = ["Run `python3 -m unittest`. "]
        path.write_text(json.dumps(value))
        failed = self.command("plan", "--run", str(run), "--file", str(path), expected=2)
        self.assertIn("raw shell command", failed["error"])

    def test_lane_acceptance_cannot_mutate_files_after_scope_validation(self) -> None:
        run = self.initialize(run_id="lane-acceptance-mutation-run")
        path = self.write_plan(self.root / "lane-acceptance-mutation.json", [])
        value = json.loads(path.read_text())
        value["tasks"][0]["acceptance"].append(
            "printf 'scope bypass' > reviewer-was-here.txt"
        )
        path.write_text(json.dumps(value))
        planned = self.command("plan", "--run", str(run), "--file", str(path))
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("acceptance for product mutated repository files", failed["error"])

    def test_reviewer_cannot_mutate_the_integration_it_is_judging(self) -> None:
        run = self.initialize(run_id="reviewer-mutation-run")
        planned = self.command(
            "plan",
            "--run",
            str(run),
            "--file",
            str(self.write_plan(self.root / "reviewer-mutation.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_REVIEW_MUTATION"] = "1"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("reviewer mutated the integration worktree", failed["error"])


def git_head(repo: Path, ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", ref], text=True).strip()


if __name__ == "__main__":
    unittest.main()
