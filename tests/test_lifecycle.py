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
GRAPHIFY = ROOT / "tests" / "fake_graphify.py"


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
        (self.repo / "VISION.md").write_text(
            "# Vision\n\nBuild a reliable reviewed text application.\n", encoding="utf-8"
        )
        (self.repo / "FEATURE_MAP.md").write_text(
            "# Feature map\n\n- Reviewed text artifact\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", ".gitignore", "VISION.md", "FEATURE_MAP.md"],
            cwd=self.repo,
            check=True,
        )
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
        self.env = {
            **os.environ,
            "PI_GRAPH_FACTORY_ADAPTER": str(FIXTURE),
            "PI_GRAPH_FACTORY_GRAPHIFY": f"{sys.executable} {GRAPHIFY}",
            "PI_GRAPH_FACTORY_REVIEW_COUNTER": str(self.counter),
        }

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
        self.assertIn("configured authority", premature["error"])
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

    def test_capture_failure_is_reviewed_repaired_and_recaptured(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["evidence"]["capture_commands"] = [
            "grep -q reviewed app.txt && cp app.txt evidence/flow.webm"
        ]
        config_path = self.root / "capture-repair-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        run = self.initialize(config_path, "capture-repair-run")
        planned = self.command(
            "plan",
            "--run",
            str(run),
            "--file",
            str(self.write_plan(self.root / "capture-repair-plan.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        state = json.loads((run / "state.json").read_text())
        self.assertFalse(state["cycles"][0]["evidence"]["valid"])
        self.assertEqual(state["cycles"][0]["evidence"]["files"], [])
        self.assertTrue(state["cycles"][1]["evidence"]["valid"])
        self.assertTrue(state["cycles"][1]["evidence"]["files"])
        self.assertEqual(state["cycles"][0]["review"]["verdict"], "repair")
        self.assertEqual(state["cycles"][1]["review"]["verdict"], "pass")

    def test_malformed_repair_receipt_gets_one_read_only_correction(self) -> None:
        run = self.initialize(run_id="repair-protocol-correction-run")
        planned = self.command(
            "plan",
            "--run",
            str(run),
            "--file",
            str(self.write_plan(self.root / "repair-protocol-plan.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        marker = self.root / "invalid-repair-observed"
        self.env["PI_GRAPH_FACTORY_INVALID_REPAIR_MARKER"] = str(marker)
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        self.assertEqual((self.repo / "app.txt").read_text(encoding="utf-8"),
                         "implemented\nreviewed 1\n")
        self.assertTrue((run / "receipts" / "repair-1-product-attempt-1.json").is_file())
        self.assertTrue((run / "receipts" / "repair-1-product-attempt-2.json").is_file())

    def test_repair_receipt_correction_cannot_mutate_the_worktree(self) -> None:
        run = self.initialize(run_id="repair-protocol-mutation-run")
        planned = self.command(
            "plan",
            "--run",
            str(run),
            "--file",
            str(self.write_plan(self.root / "repair-protocol-mutation.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_INVALID_REPAIR_MARKER"] = str(
            self.root / "invalid-repair-mutation-observed"
        )
        self.env["PI_GRAPH_FACTORY_REPAIR_CORRECTION_MUTATION"] = "1"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("receipt correction for product mutated", failed["error"])

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
        self.assertEqual(planned["phase"], "approved")
        self.assertEqual(planned["source"], "planner")
        self.assertEqual(planned["approval"]["authority"], "plan-review")
        plan_path = Path(planned["plan"])
        self.assertTrue(plan_path.is_file())
        self.assertEqual(json.loads(plan_path.read_text())["tasks"][0]["owner"], "product")
        self.assertEqual(json.loads(plan_path.read_text())["version"], 1)
        self.assertEqual(json.loads(plan_path.read_text())["success_criteria"][0]["id"], "SC-1")
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(state["plan_revision"], 1)
        self.assertEqual(state["planning_cycles"], 1)
        self.assertEqual(state["plan_judgment"]["overall_score"], 9.0)
        self.assertEqual(state["plan_judgment"]["verdict"], "pass")
        self.assertEqual(state["approved_plan_sha256"], state["plan_sha256"])
        self.assertEqual(state["plan_approval"]["authority"], "plan-review")
        self.assertTrue((run / "receipts" / "planner-1.json").is_file())
        self.assertTrue((run / "receipts" / "plan-review-1-cycle-1-attempt-1.json").is_file())
        self.assertEqual(subprocess.check_output(
            ["git", "-C", str(self.repo), "status", "--porcelain"], text=True,
        ), "")

    def test_start_runs_from_request_through_guarded_merge_without_human_approval(self) -> None:
        completed = self.command(
            "start",
            "--repo", str(self.repo),
            "--config", str(self.config),
            "--request", "Create and prove a reviewed text application.",
            "--id", "autonomous-start-run",
        )
        self.assertEqual(completed["phase"], "merged")
        self.assertEqual(completed["planning"]["approval"]["authority"], "plan-review")
        run = Path(completed["run"])
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["approved_plan_sha256"], state["plan_sha256"])
        events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
        self.assertIn("plan_auto_approved", [event["event"] for event in events])
        self.assertEqual((self.repo / "app.txt").read_text(encoding="utf-8"),
                         "implemented\nreviewed 1\n")

    def test_advance_drives_an_initialized_run_without_manual_stage_commands(self) -> None:
        run = self.initialize(run_id="autonomous-advance-run")
        completed = self.command("advance", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        self.assertEqual(completed["planning"]["approval"]["authority"], "plan-review")

    def test_start_resolves_planner_questions_without_a_human_checkpoint(self) -> None:
        self.env["PI_GRAPH_FACTORY_BLOCKING_PLAN_QUESTION"] = "1"
        completed = self.command(
            "start",
            "--repo", str(self.repo),
            "--config", str(self.config),
            "--request", "Create and prove a reviewed text application.",
            "--id", "autonomous-question-run",
        )
        self.assertEqual(completed["phase"], "merged")
        self.assertEqual(completed["planning"]["open_questions"], [])
        state = json.loads(
            (Path(completed["run"]) / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["planning_cycles"], 2)
        events = [
            json.loads(line)
            for line in (Path(completed["run"]) / "events.jsonl").read_text().splitlines()
        ]
        revisions = [event for event in events if event["event"] == "plan_revision_requested"]
        self.assertEqual(revisions[0]["payload"]["blocking_questions"], ["human-context"])

    def test_missing_legacy_approval_policy_defaults_to_autonomous(self) -> None:
        config = yaml.safe_load(self.config.read_text(encoding="utf-8"))
        config.pop("approval")
        config_path = self.root / "legacy-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        completed = self.command(
            "start",
            "--repo", str(self.repo),
            "--config", str(config_path),
            "--request", "Create and prove a reviewed text application.",
            "--id", "legacy-autonomous-run",
        )
        self.assertEqual(completed["phase"], "merged")
        self.assertEqual(completed["planning"]["approval"]["authority"], "plan-review")

    def test_unresolved_planner_question_fails_closed_without_waiting_for_a_human(self) -> None:
        self.env["PI_GRAPH_FACTORY_BLOCKING_PLAN_QUESTION_ALWAYS"] = "1"
        failed = self.command(
            "start",
            "--repo", str(self.repo),
            "--config", str(self.config),
            "--request", "Create and prove a reviewed text application.",
            "--id", "unresolved-autonomous-question-run",
            expected=2,
        )
        self.assertIn("autonomous quality contract", failed["error"])
        run = self.repo / ".factory" / "runs" / "unresolved-autonomous-question-run"
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "intake")
        self.assertNotEqual(state["phase"], "clarification")

    def test_human_approval_mode_remains_available(self) -> None:
        config = yaml.safe_load(self.config.read_text(encoding="utf-8"))
        config["approval"] = {"mode": "human"}
        config_path = self.root / "human-approval-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        waiting = self.command(
            "start",
            "--repo", str(self.repo),
            "--config", str(config_path),
            "--request", "Create and prove a reviewed text application.",
            "--id", "human-approval-run",
        )
        self.assertEqual(waiting["phase"], "awaiting_plan_approval")
        self.assertTrue(waiting["needs_human"])
        self.assertIn("human plan approval", waiting["reason"])

    def test_malformed_planner_output_gets_one_bounded_retry(self) -> None:
        run = self.initialize(run_id="planner-protocol-retry-run")
        marker = self.root / "invalid-plan-observed"
        self.env["PI_GRAPH_FACTORY_INVALID_PLAN_MARKER"] = str(marker)
        planned = self.command("plan", "--run", str(run), "--generate")
        self.assertEqual(planned["phase"], "approved")
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["planner_attempts"], 2)
        self.assertTrue(
            (run / "receipts" / "planner-1-cycle-1-attempt-1.json").is_file()
        )
        self.assertTrue(
            (run / "receipts" / "planner-1-cycle-1-attempt-2.json").is_file()
        )

    def test_low_plan_score_is_revised_until_it_clears_the_quality_gate(self) -> None:
        run = self.initialize(run_id="plan-quality-loop-run")
        marker = self.root / "low-plan-score-observed"
        self.env["PI_GRAPH_FACTORY_LOW_PLAN_SCORE_ONCE"] = str(marker)
        planned = self.command("plan", "--run", str(run), "--generate")
        self.assertEqual(planned["judgment"]["overall_score"], 9.0)
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["planning_cycles"], 2)
        self.assertTrue((run / "plans" / "plan-1-cycle-1.json").is_file())
        self.assertTrue((run / "plans" / "plan-1-cycle-2.json").is_file())
        events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
        self.assertIn("plan_revision_requested", [event["event"] for event in events])

    def test_generated_plan_restores_missing_project_memory(self) -> None:
        subprocess.run(
            ["git", "rm", "-q", "VISION.md", "FEATURE_MAP.md"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-qm", "remove project memory"],
            cwd=self.repo,
            check=True,
        )
        run = self.initialize(run_id="missing-project-memory-run")
        planned = self.command("plan", "--run", str(run), "--generate")
        planned_value = json.loads(Path(planned["plan"]).read_text(encoding="utf-8"))
        assigned = set(planned_value["tasks"][0]["files"])
        self.assertTrue({"VISION.md", "FEATURE_MAP.md"} <= assigned)
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        self.assertTrue((self.repo / "VISION.md").is_file())
        self.assertTrue((self.repo / "FEATURE_MAP.md").is_file())

    def test_failed_review_protocol_resumes_from_integration(self) -> None:
        run = self.initialize(run_id="review-resume-run")
        planned = self.command(
            "plan",
            "--run",
            str(run),
            "--file",
            str(self.write_plan(self.root / "review-resume-plan.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_INVALID_REVIEW_ALWAYS"] = "1"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("reviewer could not produce valid output", failed["error"])
        self.env.pop("PI_GRAPH_FACTORY_INVALID_REVIEW_ALWAYS")
        inspected = self.command("inspect", "--run", str(run))
        self.assertTrue(inspected["resumable"])
        self.assertEqual(inspected["phase"], "reviewing")
        completed = self.command("resume", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")

    def test_committed_repair_is_recovered_without_rerunning_the_owner(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["merge"]["apply"] = False
        config_path = self.root / "repair-recovery-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        run = self.initialize(config_path, "repair-recovery-run")
        planned = self.command(
            "plan", "--run", str(run), "--file",
            str(self.write_plan(self.root / "repair-recovery-plan.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merge_ready")

        state_path = run / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        integration = Path(state["integration"]["path"])
        repair_commit = subprocess.check_output(
            [
                "git", "-C", str(integration), "log", "--format=%H", "--grep",
                "^factory: repair cycle 1 (product)$",
            ],
            text=True,
        ).strip()
        subprocess.run(
            ["git", "-C", str(integration), "reset", "--hard", repair_commit],
            check=True,
            capture_output=True,
        )
        first_cycle = state["cycles"][0]
        first_cycle["repairs"] = []
        state["cycles"] = [first_cycle]
        state["phase"] = "reviewing"
        state["integration"]["commit"] = first_cycle["evidence"]["source_commit"]
        state["final_review"] = None
        state["merge"] = None
        state.pop("final_evidence_sha256", None)
        state.pop("last_error", None)
        state_path.write_text(json.dumps(state), encoding="utf-8")

        resumed = self.command("resume", "--run", str(run))
        self.assertEqual(resumed["phase"], "merge_ready")
        recovered = json.loads(state_path.read_text(encoding="utf-8"))["cycles"][0]["repairs"][0]
        self.assertTrue(recovered["verification"]["recovered"])
        events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
        self.assertIn("repair_owner_recovered", [event["event"] for event in events])

    def test_applied_merge_is_recovered_from_reviewed_commit(self) -> None:
        run = self.initialize(run_id="merge-recovery-run")
        planned = self.command(
            "plan", "--run", str(run), "--file",
            str(self.write_plan(self.root / "merge-recovery-plan.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")

        state_path = run / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["phase"] = "reviewing"
        state["operation"] = {"kind": "merge"}
        state["final_review"] = None
        state["merge"] = None
        state.pop("final_evidence_sha256", None)
        state.pop("last_error", None)
        state_path.write_text(json.dumps(state), encoding="utf-8")

        resumed = self.command("resume", "--run", str(run))
        self.assertEqual(resumed["phase"], "merged")
        self.assertTrue(resumed["merge"]["recovered"])
        receipt = json.loads((run / "receipt.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["merge"]["recovered"])

    def test_delivery_is_explicit_and_health_gated(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["delivery"] = {
            "enabled": True,
            "deploy_commands": ["true"],
            "health_commands": ["true"],
            "rollback_commands": ["true"],
        }
        config_path = self.root / "delivery-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        run = self.initialize(config_path, "delivery-run")
        planned = self.command(
            "plan", "--run", str(run), "--file",
            str(self.write_plan(self.root / "delivery-plan.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "delivery_ready")
        delivered = self.command("deliver", "--run", str(run))
        self.assertEqual(delivered["phase"], "delivered")
        self.assertEqual(delivered["delivery"]["status"], "deployed")

    def test_failed_delivery_runs_rollback_and_stays_failed(self) -> None:
        config = yaml.safe_load(self.config.read_text())
        config["delivery"] = {
            "enabled": True,
            "deploy_commands": ["true"],
            "health_commands": ["false"],
            "rollback_commands": ["true"],
        }
        config_path = self.root / "rollback-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        run = self.initialize(config_path, "rollback-run")
        planned = self.command(
            "plan", "--run", str(run), "--file",
            str(self.write_plan(self.root / "rollback-plan.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.command("run", "--run", str(run))
        failed = self.command("deliver", "--run", str(run), expected=1)
        self.assertEqual(failed["phase"], "delivery_failed")
        self.assertEqual(failed["delivery"]["status"], "rolled_back")

    def test_new_repository_bootstrap_has_safe_ignore_defaults(self) -> None:
        target = self.root / "new-repository"
        target.mkdir()
        initialized = self.command(
            "init", "--repo", str(target), "--new-repo", "--config", str(self.config),
            "--request", "Build a new application.", "--id", "new-repository-run",
        )
        self.assertEqual(initialized["phase"], "intake")
        ignored = (target / ".gitignore").read_text(encoding="utf-8")
        for entry in (
            ".factory/", ".env", "__pycache__/", "*.py[cod]", "node_modules/",
            "graphify-out/",
        ):
            self.assertIn(entry, ignored)
        self.assertIn("Build a new application.", (target / "VISION.md").read_text())
        self.assertTrue((target / "FEATURE_MAP.md").is_file())
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
        config["implementers"][0]["timeout_seconds"] = 1
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
        # Planner and independent plan judge each report two fixture tokens.
        # Let planning finish, then prove the implementation batch cannot start.
        config["limits"]["max_total_tokens"] = 3
        config_path = self.root / "planner-budget-factory.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
        run = self.initialize(config_path, "planner-budget-run")
        self.command("plan", "--run", str(run), "--generate")
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

    def test_malformed_reviewer_output_gets_one_bounded_retry(self) -> None:
        run = self.initialize(run_id="reviewer-validation-retry-run")
        planned = self.command(
            "plan",
            "--run",
            str(run),
            "--file",
            str(self.write_plan(self.root / "reviewer-validation-retry.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_INVALID_REVIEW_ONCE"] = "1"
        completed = self.command("run", "--run", str(run))
        self.assertEqual(completed["phase"], "merged")
        retries = [
            json.loads(line)["payload"]
            for line in (run / "events.jsonl").read_text().splitlines()
            if json.loads(line)["event"] == "reviewer_attempt_completed"
        ]
        self.assertIsNotNone(retries[0]["validation_error"])
        self.assertIsNone(retries[1]["validation_error"])
        self.assertTrue((run / "receipts" / "reviewer-1-attempt-1.json").is_file())
        self.assertTrue((run / "receipts" / "reviewer-1-attempt-2.json").is_file())

    def test_two_malformed_reviewer_outputs_fail_closed(self) -> None:
        run = self.initialize(run_id="reviewer-validation-exhausted-run")
        planned = self.command(
            "plan",
            "--run",
            str(run),
            "--file",
            str(self.write_plan(self.root / "reviewer-validation-exhausted.json", [])),
        )
        self.command("approve", "--run", str(run), "--sha256", planned["plan_sha256"])
        self.env["PI_GRAPH_FACTORY_INVALID_REVIEW_ALWAYS"] = "1"
        failed = self.command("run", "--run", str(run), expected=2)
        self.assertIn("reviewer could not produce valid output", failed["error"])
        self.assertTrue((run / "receipts" / "reviewer-1-attempt-1.json").is_file())
        self.assertTrue((run / "receipts" / "reviewer-1-attempt-2.json").is_file())
        self.assertFalse((run / "receipts" / "reviewer-1-attempt-3.json").exists())


def git_head(repo: Path, ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", ref], text=True).strip()


if __name__ == "__main__":
    unittest.main()
