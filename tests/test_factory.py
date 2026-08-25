from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from compile_factory import SCHEMA, compile_factory  # noqa: E402
from factory import (  # noqa: E402
    PROJECT_DOC_CONTEXT_LIMIT,
    FactoryError,
    enforce_dispatch_limits,
    is_unsafe_repository_artifact,
    metric_score_from_receipts,
    run_optimization_search,
    run_repair,
    run_commands_before_deadline,
    read_project_memory,
    task_dependency_waves,
    validate_plan,
    validate_plan_judgment,
    validate_controller_optimization_receipt,
    validate_optimization_candidate,
    validate_prompt_evaluation,
    validated_usage,
)


class FactoryCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = yaml.safe_load((ROOT / "factory.yaml").read_text())

    def test_contract_is_valid_and_reviews_are_unlimited(self) -> None:
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(self.factory)), [])
        self.assertLessEqual(len(self.factory["implementers"]), 10)
        self.assertIsNone(self.factory["review"]["max_cycles"])
        self.assertEqual(self.factory["review"]["projection_cycles"], 5)
        roles = [self.factory["planner"], self.factory["plan_review"],
                 *self.factory["implementers"], self.factory["review"]]
        for role in roles:
            self.assertTrue((ROOT / role["instructions"]).is_file())
            for skill in role.get("skills", []):
                self.assertTrue((ROOT / skill / "SKILL.md").is_file(), skill)

    def test_copywriting_is_a_routable_specialist_without_a_second_lifecycle(self) -> None:
        implementers = {item["id"]: item for item in self.factory["implementers"]}
        self.assertEqual(
            set(implementers),
            {"product", "design", "visual-assets", "copy", "prompt", "optimization"},
        )
        for owner in ("product", "design", "copy"):
            self.assertIn("skills/evil-genius-copywriter", implementers[owner]["skills"])
        self.assertEqual(implementers["copy"]["instructions"], "agents/copywriter.md")
        self.assertIn("skills/prompt-engineering", implementers["product"]["skills"])
        self.assertIn("skills/prompt-engineering", implementers["prompt"]["skills"])
        self.assertIn("skills/improvement", implementers["optimization"]["skills"])
        self.assertIn("skills/autoagent", implementers["optimization"]["skills"])
        self.assertIn("skills/evil-genius-copywriter", self.factory["review"]["skills"])
        self.assertIn("skills/prompt-engineering", self.factory["review"]["skills"])
        self.assertIn("skills/improvement", self.factory["review"]["skills"])
        self.assertIn("skills/taste", self.factory["planner"]["skills"])
        self.assertIn("skills/visual-research", self.factory["planner"]["skills"])
        self.assertIn("skills/decision-making", self.factory["planner"]["skills"])
        self.assertIn("skills/deep-thinking", self.factory["plan_review"]["skills"])
        self.assertIn("skills/image-generation", implementers["visual-assets"]["skills"])
        self.assertEqual(implementers["visual-assets"]["harness"], "codex")

        workflow = compile_factory(self.factory)
        steps = {step["id"]: step for step in workflow["steps"]}
        self.assertEqual(steps["implement-copy"]["needs"], ["plan-review"])
        self.assertEqual(steps["implement-prompt"]["needs"], ["plan-review"])
        self.assertEqual(steps["implement-optimization"]["needs"], ["plan-review"])
        self.assertEqual(
            steps["integrate"]["needs"],
            [
                "implement-product",
                "implement-design",
                "implement-visual-assets",
                "implement-copy",
                "implement-prompt",
                "implement-optimization",
            ],
        )

        plan = {
            "version": 1,
            "summary": "Write the verified repository description.",
            "proof": {"mode": "tests", "reason": "repository metadata draft"},
            "research": [{
                "question": "What can the repository claim?",
                "finding": "The README documents the supported workflow.",
                "evidence": ["README.md"],
            }],
            "assumptions": [],
            "success_criteria": [{
                "id": "SC-COPY",
                "description": "The description states a supported capability without hype.",
            }],
            "tasks": [{
                "id": "write-copy",
                "owner": "copy",
                "files": ["docs/repository-description.txt"],
                "acceptance": ["test -s docs/repository-description.txt"],
            }],
            "acceptance": ["test -s docs/repository-description.txt"],
            "risks": [],
            "open_questions": [],
        }
        validate_plan(
            plan,
            set(implementers),
            require_versioned=True,
            evidence_policy="plan",
        )

    def test_visual_plans_require_research_direction_assets_and_real_proof(self) -> None:
        implementers = {item["id"] for item in self.factory["implementers"]}
        plan = {
            "version": 1,
            "summary": "Build one polished game loop with original generated art.",
            "proof": {"mode": "visual", "reason": "The result is interactive and visual."},
            "research": [{
                "question": "What makes the target loop legible?",
                "finding": "Three inspected listings prioritize the vehicle and immediate action.",
                "evidence": ["https://apps.apple.com/example"],
            }],
            "assumptions": [],
            "success_criteria": [{
                "id": "SC-LOOP",
                "description": "The player can complete one polished driving loop.",
            }],
            "tasks": [
                {
                    "id": "build-ui",
                    "owner": "design",
                    "files": ["GameUI/**"],
                    "acceptance": ["test -f GameUI/GameView.swift"],
                },
                {
                    "id": "make-art",
                    "owner": "visual-assets",
                    "files": ["Assets/**"],
                    "acceptance": ["test -f Assets/truck.png"],
                },
            ],
            "visual_contract": {
                "kind": "new_product",
                "audience": "Players who want a quick tactile monster-truck session.",
                "references": [
                    {"source": f"https://apps.apple.com/example-{index}",
                     "observed": "The core action is visible in the first gameplay frame.",
                     "adopt": "Lead with readable vehicle scale and terrain contrast.",
                     "avoid": "Do not copy branded vehicles or level composition."}
                    for index in range(3)
                ],
                "alternatives": [
                    {"name": "toy-diorama", "premise": "Tactile tabletop spectacle.",
                     "tradeoffs": ["Readable but less realistic."]},
                    {"name": "stadium-impact", "premise": "High-energy arena action.",
                     "tradeoffs": ["Exciting but visually denser."]},
                ],
                "selected_direction": "Toy-diorama for immediate mobile readability.",
                "principles": ["Readable silhouette", "Tactile terrain", "Immediate feedback"],
                "screens": [{"id": "drive", "purpose": "Play the core loop.",
                             "states": ["ready", "driving", "crashed"]}],
                "assets": [{"id": "truck", "owner": "visual-assets",
                            "files": ["Assets/truck.png"], "source": "generated",
                            "brief": "Original side-view truck with transparent background."}],
                "originality": "Use only general genre patterns and original vehicle art.",
                "quality_bar": ["No clipped controls", "Truck is visually dominant",
                                "Crash feedback is visible"],
                "verification": {"surface": "iOS Simulator", "driver": "scripts/verify-ios.sh",
                                 "evidence": ["evidence/drive.png", "evidence/drive.mp4"],
                                 "feature_coverage": ["SC-LOOP"]},
            },
            "acceptance": ["test -f GameUI/GameView.swift", "test -f Assets/truck.png"],
            "risks": [],
            "open_questions": [],
        }
        validate_plan(plan, implementers, require_versioned=True, evidence_policy="plan")

        missing = copy.deepcopy(plan)
        missing.pop("visual_contract")
        with self.assertRaisesRegex(FactoryError, "require a visual_contract"):
            validate_plan(missing, implementers, require_versioned=True, evidence_policy="plan")

        under_researched = copy.deepcopy(plan)
        under_researched["visual_contract"]["references"] = [
            under_researched["visual_contract"]["references"][0]
        ]
        with self.assertRaisesRegex(FactoryError, "at least 3 references"):
            validate_plan(
                under_researched, implementers, require_versioned=True, evidence_policy="plan"
            )

        wrong_asset_owner = copy.deepcopy(plan)
        wrong_asset_owner["visual_contract"]["assets"][0]["owner"] = "design"
        wrong_asset_owner["visual_contract"]["assets"][0]["files"] = ["GameUI/truck.png"]
        with self.assertRaisesRegex(FactoryError, "must be owned by visual-assets"):
            validate_plan(
                wrong_asset_owner, implementers, require_versioned=True,
                evidence_policy="plan",
            )

    def test_project_memory_retains_75000_characters_and_marks_overflow(self) -> None:
        self.assertEqual(PROJECT_DOC_CONTEXT_LIMIT, 75_000)
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            for name in ("VISION.md", "FEATURE_MAP.md", "TASTE.md"):
                (repo / name).write_text("x" * (PROJECT_DOC_CONTEXT_LIMIT + 1))
            memory = read_project_memory(repo)
        self.assertEqual(memory["missing"], [])
        self.assertEqual(set(memory["truncated"]), {"VISION.md", "FEATURE_MAP.md", "TASTE.md"})
        self.assertTrue(all(
            len(content) == PROJECT_DOC_CONTEXT_LIMIT
            for content in memory["documents"].values()
        ))

    def test_plan_cannot_use_controller_owned_delivery_as_acceptance(self) -> None:
        plan = {
            "summary": "Build and locally deploy one command.",
            "tasks": [{
                "id": "build",
                "owner": "product",
                "files": ["tool.py"],
                "acceptance": ["python3 -m unittest discover -s tests -v"],
            }],
            "acceptance": ["python3 /tmp/deployed-tool --help"],
            "risks": [],
            "open_questions": [],
        }
        with self.assertRaisesRegex(FactoryError, "controller-owned delivery"):
            validate_plan(
                plan,
                {"product"},
                delivery_commands={"python3 /tmp/deployed-tool --help"},
            )

    def test_prompt_owner_requires_an_executable_runtime_contract(self) -> None:
        implementers = {item["id"] for item in self.factory["implementers"]}
        command = "python3 -m unittest tests.test_prompt_contract -v"
        plan = {
            "version": 1,
            "summary": "Harden a production agent prompt.",
            "proof": {"mode": "tests", "reason": "prompt contract evaluation"},
            "research": [{
                "question": "Where is the prompt consumed?",
                "finding": "The runtime validates a typed decision object.",
                "evidence": ["prompts/system.md", "src/runtime.py"],
            }],
            "assumptions": [],
            "success_criteria": [{
                "id": "SC-PROMPT",
                "description": "The prompt fails safely across declared cases.",
            }],
            "tasks": [{
                "id": "harden-prompt",
                "owner": "prompt",
                "files": ["prompts/**"],
                "acceptance": [command],
            }],
            "prompt_contract": {
                "runtime": "decision-agent-v2",
                "objective": "Return a grounded routing decision.",
                "authoritative_context": ["signed policy supplied by the host"],
                "untrusted_inputs": ["user request", "retrieved documents", "tool output"],
                "output_schema": "schemas/decision.schema.json",
                "abstention": "Return status=insufficient_evidence with missing fields.",
                "host_enforcement": ["validate schema", "enforce tool allowlist"],
                "evaluation_commands": [command],
                "cases": [
                    {"id": kind.replace("_", "-"), "kind": kind, "assertion": f"verify {kind}"}
                    for kind in (
                        "happy_path",
                        "missing_input",
                        "malformed_input",
                        "prompt_injection",
                        "tool_failure",
                        "abstention",
                    )
                ],
            },
            "acceptance": [command],
            "risks": [],
            "open_questions": [],
        }
        validate_plan(plan, implementers, require_versioned=True, evidence_policy="plan")

        prose_runtime = copy.deepcopy(plan)
        prose_runtime["prompt_contract"]["runtime"] = (
            "Offline Python template renderer in tests/test_prompt_contract.py"
        )
        with self.assertRaisesRegex(FactoryError, "stable machine identifier"):
            validate_plan(
                prose_runtime,
                implementers,
                require_versioned=True,
                evidence_policy="plan",
            )

        missing = copy.deepcopy(plan)
        missing.pop("prompt_contract")
        with self.assertRaisesRegex(FactoryError, "requires a prompt_contract"):
            validate_plan(missing, implementers, require_versioned=True, evidence_policy="plan")

        no_injection = copy.deepcopy(plan)
        no_injection["prompt_contract"]["cases"] = [
            case for case in no_injection["prompt_contract"]["cases"]
            if case["kind"] != "prompt_injection"
        ]
        with self.assertRaisesRegex(FactoryError, "lacks required case kinds"):
            validate_plan(no_injection, implementers, require_versioned=True, evidence_policy="plan")

        untested = copy.deepcopy(plan)
        untested["tasks"][0]["acceptance"] = ["true"]
        untested["acceptance"] = ["true"]
        with self.assertRaisesRegex(FactoryError, "must be assigned to prompt-task acceptance"):
            validate_plan(untested, implementers, require_versioned=True, evidence_policy="plan")

        no_op = copy.deepcopy(plan)
        no_op["prompt_contract"]["evaluation_commands"] = ["true"]
        no_op["tasks"][0]["acceptance"] = ["true"]
        no_op["acceptance"] = ["true"]
        with self.assertRaisesRegex(FactoryError, "cannot be no-op"):
            validate_plan(no_op, implementers, require_versioned=True, evidence_policy="plan")

        typed = {
            "schema": "pi-graph-factory.prompt-evaluation.v1",
            "runtime": plan["prompt_contract"]["runtime"],
            "cases": [
                {
                    "id": case["id"],
                    "kind": case["kind"],
                    "passed": True,
                    "evidence": f"observed {case['kind']}",
                }
                for case in plan["prompt_contract"]["cases"]
            ],
        }
        validated = validate_prompt_evaluation(
            [{"command": command, "output": json.dumps(typed), "passed": True}],
            plan["prompt_contract"],
        )
        self.assertEqual(len(validated["cases"]), 6)
        validated = validate_prompt_evaluation(
            [{
                "command": command,
                "stdout": json.dumps(typed) + "\n",
                "stderr": "Ran 6 tests\nOK\n",
                "output": json.dumps(typed) + "\nRan 6 tests\nOK\n",
                "passed": True,
            }],
            plan["prompt_contract"],
        )
        self.assertEqual(validated["runtime"], plan["prompt_contract"]["runtime"])
        with self.assertRaisesRegex(FactoryError, "no typed receipt"):
            validate_prompt_evaluation(
                [{"command": command, "output": "", "passed": True}],
                plan["prompt_contract"],
            )

    def test_optimization_requires_a_frozen_controller_owned_contract(self) -> None:
        implementers = {item["id"] for item in self.factory["implementers"]}

        def optimization_plan() -> dict:
            return {
                "version": 1,
                "summary": "Improve the coding-agent harness against a frozen evaluation.",
                "proof": {"mode": "tests", "reason": "score and preservation gates"},
                "research": [{
                    "question": "What may the optimizer change?",
                    "finding": "The harness is separate from evaluator cases.",
                    "evidence": ["agent/", "eval/"],
                }],
                "assumptions": [],
                "success_criteria": [{
                    "id": "SC-OPT",
                    "description": "A promoted harness clears the declared gain and gates.",
                }],
                "tasks": [{
                    "id": "optimize-harness",
                    "owner": "optimization",
                    "files": ["agent/**"],
                    "acceptance": ["python3 -m unittest discover -s tests -v"],
                }],
                "optimization": {
                    "objective": "Increase passed evaluation tasks without regressions.",
                    "evaluation_version": "eval-v1",
                    "mutable_files": ["agent/**"],
                    "forbidden_files": ["eval/**", "tests/**"],
                    "metric": {
                        "name": "passed_tasks",
                        "direction": "maximize",
                        "minimum_gain": 1,
                    },
                    "target_score": None,
                    "development_commands": [
                        "python3 scripts/score.py --format pi-graph-factory.metric.v1"
                    ],
                    "preservation_commands": ["python3 -m compileall -q agent"],
                    "promotion_commands": ["python3 -m unittest discover -s holdout -v"],
                    "max_candidates": 5,
                    "max_consecutive_non_keeps": 3,
                    "max_seconds": 28800,
                    "stop_conditions": [
                        "candidate budget exhausted",
                        "plateau",
                        "wall time exhausted",
                        "invalid evaluation",
                    ],
                },
                "acceptance": [
                    "python3 -m compileall -q agent",
                ],
                "risks": ["development score may not generalize"],
                "open_questions": [],
            }

        valid = optimization_plan()
        validate_plan(valid, implementers, require_versioned=True, evidence_policy="plan")
        fingerprint = "sha256:" + "a" * 64
        receipt = {
            "optimization": {
                "schema": "pi-graph-factory.optimization-receipt.v1",
                "evaluation_version": "eval-v1",
                "baseline_score": 12,
                "final_score": 14,
                "gain": 2,
                "decision": "promoted",
                "protected_fingerprint": fingerprint,
                "artifact_fingerprint": fingerprint,
                "candidates": [{
                    "id": "c1",
                    "hypothesis": "A typed verification tool reduces silent completion.",
                    "score": 14,
                    "status": "keep",
                    "gates_passed": True,
                }],
                "promotion": [{"command": "holdout", "passed": True}],
                "elapsed_seconds": 120.5,
            }
        }
        validate_controller_optimization_receipt(receipt, valid["optimization"])

        missing = optimization_plan()
        missing.pop("optimization")
        with self.assertRaisesRegex(FactoryError, "requires an optimization contract"):
            validate_plan(missing, implementers, require_versioned=True, evidence_policy="plan")

        overlap = optimization_plan()
        overlap["optimization"]["forbidden_files"] = ["agent/eval/**"]
        with self.assertRaisesRegex(FactoryError, "must not overlap"):
            validate_plan(overlap, implementers, require_versioned=True, evidence_policy="plan")

        mutable_evaluator = optimization_plan()
        mutable_evaluator["tasks"].append({
            "id": "rewrite-evaluator",
            "owner": "product",
            "files": ["eval/**"],
            "acceptance": ["python3 -m unittest discover -s eval -v"],
        })
        with self.assertRaisesRegex(FactoryError, "forbidden_files must not overlap"):
            validate_plan(
                mutable_evaluator,
                implementers,
                require_versioned=True,
                evidence_policy="plan",
            )

        unobserved = optimization_plan()
        unobserved["acceptance"].remove("python3 -m compileall -q agent")
        unobserved["acceptance"].append("true")
        with self.assertRaisesRegex(FactoryError, "must also be top-level acceptance"):
            validate_plan(
                unobserved, implementers, require_versioned=True, evidence_policy="plan"
            )

        repeated_promotion = optimization_plan()
        repeated_promotion["acceptance"].append(
            "python3 -m unittest discover -s holdout -v"
        )
        with self.assertRaisesRegex(FactoryError, "controller-owned"):
            validate_plan(
                repeated_promotion, implementers, require_versioned=True, evidence_policy="plan"
            )

        over_budget = optimization_plan()
        over_budget["optimization"]["max_candidates"] = 11
        with self.assertRaisesRegex(FactoryError, "between 1 and 10"):
            validate_plan(
                over_budget, implementers, require_versioned=True, evidence_policy="plan"
            )

        no_time_bound = optimization_plan()
        no_time_bound["optimization"]["max_seconds"] = 0
        with self.assertRaisesRegex(FactoryError, "max_seconds must be a positive integer"):
            validate_plan(
                no_time_bound, implementers, require_versioned=True, evidence_policy="plan"
            )

        weak = copy.deepcopy(receipt)
        weak["optimization"]["final_score"] = 12.5
        weak["optimization"]["gain"] = 0.5
        with self.assertRaisesRegex(FactoryError, "minimum gain"):
            validate_controller_optimization_receipt(weak, valid["optimization"])

        stale = copy.deepcopy(receipt)
        stale["optimization"]["promotion"][0]["passed"] = False
        with self.assertRaisesRegex(FactoryError, "promotion did not pass"):
            validate_controller_optimization_receipt(stale, valid["optimization"])

        too_slow = copy.deepcopy(receipt)
        too_slow["optimization"]["elapsed_seconds"] = 28800.1
        with self.assertRaisesRegex(FactoryError, "exceeded max_seconds"):
            validate_controller_optimization_receipt(too_slow, valid["optimization"])

        score = metric_score_from_receipts(
            [{"output": "trace\n{\"schema\":\"pi-graph-factory.metric.v1\","
                        "\"evaluation_version\":\"eval-v1\",\"score\":14}\n"}],
            valid["optimization"],
        )
        self.assertEqual(score, 14)
        with self.assertRaisesRegex(FactoryError, "controller owns scores"):
            validate_optimization_candidate(
                {"optimization": {
                    "candidate_id": "c1",
                    "hypothesis": "general change",
                    "score": 999,
                }},
                "c1",
            )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FactoryError, "wall-time budget"):
                run_commands_before_deadline(
                    Path(directory),
                    ["sleep 0.1", "sleep 0.1"],
                    "bounded evaluation",
                    deadline=time.monotonic() + 0.15,
                    command_timeout_seconds=1,
                )

    def test_optimization_controller_scores_and_promotes_an_isolated_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            run = root / "run"
            workspace = run / "worktrees" / "optimization"
            (repo / "agent").mkdir(parents=True)
            (repo / "eval").mkdir()
            (repo / "agent" / "value.txt").write_text("1\n", encoding="utf-8")
            (repo / "eval" / "score.py").write_text(
                "import json, pathlib\n"
                "score = int(pathlib.Path('agent/value.txt').read_text().strip())\n"
                "print(json.dumps({'schema':'pi-graph-factory.metric.v1',"
                "'evaluation_version':'eval-v1','score':score}))\n",
                encoding="utf-8",
            )
            (repo / "eval" / "gate.py").write_text(
                "import pathlib, sys\n"
                "sys.exit(0 if int(pathlib.Path('agent/value.txt').read_text()) > 0 else 1)\n",
                encoding="utf-8",
            )
            (repo / "eval" / "promote.py").write_text(
                "import pathlib, sys\n"
                "sys.exit(0 if int(pathlib.Path('agent/value.txt').read_text()) >= 2 else 1)\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Factory Test"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "factory@example.invalid"],
                check=True,
            )
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)
            run.mkdir()
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "-qb", "factory/test/optimization",
                 str(workspace), "HEAD"],
                check=True,
            )
            task = {
                "id": "optimize-value",
                "owner": "optimization",
                "files": ["agent/**"],
                "acceptance": ["python3 eval/gate.py"],
            }
            contract = {
                "objective": "increase the fixture score",
                "evaluation_version": "eval-v1",
                "mutable_files": ["agent/**"],
                "forbidden_files": ["eval/**"],
                "metric": {"name": "value", "direction": "maximize", "minimum_gain": 1},
                "target_score": 2,
                "development_commands": ["python3 eval/score.py"],
                "preservation_commands": ["python3 eval/gate.py"],
                "promotion_commands": ["python3 eval/promote.py"],
                "max_candidates": 1,
                "max_consecutive_non_keeps": 1,
                "max_seconds": 60,
                "stop_conditions": [
                    "target achieved",
                    "candidate budget exhausted",
                    "plateau",
                    "wall time exhausted",
                    "invalid evaluation",
                ],
            }
            state = {
                "repo": str(repo),
                "request": "improve the fixture",
                "plan": {"tasks": [task], "optimization": contract},
                "repository_intelligence": None,
            }
            agent = {"harness": "pi", "model": "fixture", "thinking": "low"}
            limits = {
                "command_timeout_seconds": 10,
                "termination_grace_seconds": 1,
                "require_usage": False,
            }

            def candidate(*args, **kwargs):
                cwd = args[4]
                context = args[5]
                candidate_id = context["optimization_iteration"]["candidate_id"]
                (cwd / "agent" / "value.txt").write_text("2\n", encoding="utf-8")
                return {
                    "status": "passed",
                    "harness": "pi",
                    "model": "fixture",
                    "role": f"implement:optimization:{candidate_id}",
                    "output": {
                        "status": "pass",
                        "changed_files": ["agent/value.txt"],
                        "checks": [{"command": "local", "passed": True}],
                        "summary": "increase one fixture mechanism",
                        "optimization": {
                            "candidate_id": candidate_id,
                            "hypothesis": "raising the value raises the frozen metric",
                        },
                    },
                    "usage": {"input": 1, "output": 1, "total": 2, "cost": 0.0},
                }

            with patch("factory.invoke_agent", side_effect=candidate):
                receipt = run_optimization_search(
                    run,
                    state,
                    agent,
                    [task],
                    workspace,
                    limits,
                    {},
                )

            result = receipt["output"]["optimization"]
            self.assertEqual(result["baseline_score"], 1)
            self.assertEqual(result["final_score"], 2)
            self.assertEqual(result["candidates"][0]["status"], "keep")
            self.assertEqual(len(result["promotion"]), 1)
            self.assertEqual((workspace / "agent" / "value.txt").read_text(), "2\n")
            staged = subprocess.run(
                ["git", "-C", str(workspace), "diff", "--cached", "--name-only"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.splitlines()
            self.assertEqual(staged, ["agent/value.txt"])
            with self.assertRaisesRegex(FactoryError, "attempt already exists"):
                run_optimization_search(
                    run,
                    state,
                    agent,
                    [task],
                    workspace,
                    limits,
                    {},
                )
            with self.assertRaisesRegex(FactoryError, "cannot reuse consumed promotion"):
                run_repair(
                    run,
                    state,
                    {"implementers": [{"id": "optimization"}], "limits": limits},
                    workspace,
                    1,
                    [{"id": "OPT-REPAIR", "owner": "optimization"}],
                )

    def test_compiler_projects_guarded_review_window_and_controller_continuation(self) -> None:
        workflow = compile_factory(self.factory)
        steps = {step["id"]: step for step in workflow["steps"]}
        ids = list(steps)
        self.assertEqual(len([item for item in ids if item.startswith("review-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("repair-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("capture-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("merge-")]), 5)
        agent_steps = [steps["plan"], steps["plan-review"], *[steps[item] for item in ids
                                       if item.startswith(("implement-", "review-", "repair-"))]]
        self.assertTrue(agent_steps)
        expected_timeouts = {
            "plan": self.factory["planner"]["timeout_seconds"],
            "plan-review": self.factory["plan_review"]["timeout_seconds"],
            **{
                f"implement-{agent['id']}": agent["timeout_seconds"]
                for agent in self.factory["implementers"]
            },
            **{
                f"review-{cycle}": self.factory["review"]["timeout_seconds"]
                for cycle in range(1, 6)
            },
            **{
                f"repair-{cycle}": self.factory["implementers"][0]["timeout_seconds"]
                for cycle in range(1, 6)
            },
        }
        self.assertTrue(agent_steps)
        for step in agent_steps:
            expected = expected_timeouts[step["id"]]
            if expected is None:
                self.assertNotIn("timeout", step)
            else:
                self.assertEqual(step["timeout"], expected)
        for step_id in ["integrate", "controller-review-continues", *[
            f"capture-{cycle}" for cycle in range(1, 6)
        ], *[f"merge-{cycle}" for cycle in range(1, 6)], "repository-intelligence"]:
            self.assertEqual(
                steps[step_id]["timeout"],
                self.factory["limits"]["command_timeout_seconds"],
            )
        for cycle in range(1, 6):
            merge = steps[f"merge-{cycle}"]
            self.assertEqual(merge["needs"], [f"review-{cycle}"])
            self.assertEqual(merge["when"], {"op": "equals", "path": "/verdict", "value": "pass"})
        self.assertNotIn("human-required", steps)
        self.assertEqual(steps["controller-review-continues"]["needs"], ["repair-5"])
        self.assertEqual(steps["capture-2"]["needs"], ["repair-1"])
        self.assertEqual(steps["plan"]["needs"], ["repository-intelligence"])
        self.assertEqual(steps["implement-product"]["needs"], ["plan-review"])
        self.assertNotIn("retries", steps["plan-review"])

    def test_contract_rejects_excess_implementers_fallbacks_or_projection(self) -> None:
        too_many = dict(self.factory)
        too_many["implementers"] = self.factory["implementers"] * 6
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(too_many)))
        too_long = yaml.safe_load((ROOT / "factory.yaml").read_text())
        too_long["review"]["max_cycles"] = 6
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(too_long)), [])
        too_long["review"]["projection_cycles"] = 21
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(too_long)))
        too_many_fallbacks = yaml.safe_load((ROOT / "factory.yaml").read_text())
        design = next(
            item for item in too_many_fallbacks["implementers"] if item["id"] == "design"
        )
        design["fallbacks"] *= 3
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(too_many_fallbacks)))

    def test_role_timeout_can_be_disabled_and_subscription_limits_are_optional(self) -> None:
        value = yaml.safe_load((ROOT / "factory.yaml").read_text())
        value["planner"]["timeout_seconds"] = None
        workflow = compile_factory(value)
        plan = next(step for step in workflow["steps"] if step["id"] == "plan")
        self.assertNotIn("timeout", plan)
        enforce_dispatch_limits(
            {"usage": {"total_tokens": 10**9, "cost_usd": 10**9, "unknown_calls": 0}},
            value["limits"],
            "subscription-backed agent",
        )

    def test_enabled_delivery_adds_guarded_post_merge_nodes(self) -> None:
        value = yaml.safe_load((ROOT / "factory.yaml").read_text())
        value["merge"]["apply"] = True
        value["delivery"] = {
            "enabled": True,
            "deploy_commands": ["true"],
            "health_commands": ["true"],
            "rollback_commands": ["true"],
        }
        workflow = compile_factory(value)
        steps = {step["id"]: step for step in workflow["steps"]}
        deliveries = [step for step in steps.values() if step["id"].startswith("deliver-")]
        self.assertEqual(len(deliveries), 5)
        for cycle, delivery in enumerate(deliveries, start=1):
            self.assertEqual(delivery["needs"], [f"merge-{cycle}"])
            self.assertEqual(
                delivery["when"],
                {"op": "equals", "path": "/status", "value": "merged"},
            )

    def test_generated_and_secret_bearing_artifacts_are_classified_conservatively(self) -> None:
        for path in (
            "tests/__pycache__/test_app.cpython-314.pyc",
            "MonsterTruckMayhemDomain/.build/debug/GameTests.xctest",
            "DerivedData/Build/app",
            "node_modules/tool/index.js",
            ".env",
            "config/.env.production",
            ".DS_Store",
        ):
            self.assertTrue(is_unsafe_repository_artifact(path), path)
        for path in (".env.example", ".env.sample", ".env.template", "src/app.py"):
            self.assertFalse(is_unsafe_repository_artifact(path), path)

    def test_task_dependencies_compile_into_deterministic_owner_waves(self) -> None:
        tasks = [
            {"id": "domain", "owner": "product", "depends_on": []},
            {"id": "art", "owner": "visual-assets", "depends_on": []},
            {"id": "docs", "owner": "copy", "depends_on": []},
            {
                "id": "ui",
                "owner": "design",
                "depends_on": ["domain", "art"],
            },
        ]

        self.assertEqual(
            task_dependency_waves(tasks),
            [["product", "visual-assets", "copy"], ["design"]],
        )

    def test_task_dependency_owner_cycle_fails_closed(self) -> None:
        tasks = [
            {"id": "domain", "owner": "product", "depends_on": ["ui"]},
            {"id": "ui", "owner": "design", "depends_on": ["domain"]},
        ]

        with self.assertRaisesRegex(FactoryError, "owner cycle"):
            task_dependency_waves(tasks)

    def test_usage_rejects_non_finite_or_non_integer_values(self) -> None:
        valid = {"role": "test", "usage": {"input": 1, "output": 2, "total": 3,
                                             "cost": 0.01}}
        self.assertEqual(validated_usage(valid)["total"], 3)
        with self.assertRaises(FactoryError):
            validated_usage({"role": "test", "usage": {"total": 3.5, "cost": 0}})
        with self.assertRaises(FactoryError):
            validated_usage({"role": "test", "usage": {"total": 3, "cost": float("nan")}})

    def test_generated_plan_must_assign_missing_project_memory(self) -> None:
        plan = {
            "version": 1,
            "summary": "Implement the request",
            "proof": {"mode": "tests", "reason": "backend-only change"},
            "research": [{
                "question": "Where should the change live?",
                "finding": "The application module owns it.",
                "evidence": ["src/app.py"],
            }],
            "assumptions": [],
            "success_criteria": [{"id": "SC-1", "description": "The behavior works."}],
            "tasks": [{
                "id": "build", "owner": "product", "files": ["src/**"],
                "acceptance": ["python3 -m unittest"],
            }],
            "acceptance": ["python3 -m unittest"],
            "risks": [],
            "open_questions": [],
        }
        with self.assertRaisesRegex(FactoryError, "missing project memory"):
            validate_plan(
                plan,
                {"product"},
                require_versioned=True,
                required_project_docs={"VISION.md", "FEATURE_MAP.md"},
            )

    def test_plan_judge_score_is_recomputed_instead_of_trusted(self) -> None:
        receipt = {
            "status": "passed",
            "output": {
                "rubric_version": "plan-quality-v1",
                "dimensions": [{
                    "name": name,
                    "score": 9,
                    "evidence": "inspectable context",
                    "reasoning": "the named anchor is met",
                    "gap_to_next": "no material gap",
                } for name in (
                    "grounding", "coverage", "feasibility", "minimality", "alignment"
                )],
                "critical_failure": False,
                "overall_score": 10,
                "overall_reasoning": "forged total",
                "improvements": [],
                "verdict": "pass",
            },
        }
        with self.assertRaisesRegex(FactoryError, "weighted dimensions"):
            validate_plan_judgment(receipt, 8.5)
        receipt["output"]["dimensions"][0]["score"] = float("nan")
        with self.assertRaisesRegex(FactoryError, "half-point anchors"):
            validate_plan_judgment(receipt, 8.5)

    def test_plan_judge_cannot_average_away_a_critical_dimension_below_bar(self) -> None:
        scores = {
            "grounding": 9,
            "coverage": 9,
            "feasibility": 8,
            "minimality": 9,
            "alignment": 9,
        }
        receipt = {
            "status": "passed",
            "output": {
                "rubric_version": "plan-quality-v1",
                "dimensions": [
                    {
                        "name": name,
                        "score": score,
                        "evidence": "inspectable context",
                        "reasoning": "the named anchor is met",
                        "gap_to_next": "raise the critical dimension to the release bar",
                    }
                    for name, score in scores.items()
                ],
                "critical_failure": False,
                "overall_score": 9.0,
                "overall_reasoning": "The weighted score clears the bar.",
                "improvements": [
                    {
                        "suggestion": "Make the execution contract mechanically complete.",
                        "dimension": "feasibility",
                        "current_anchor": 8,
                        "target_anchor": 8.5,
                        "why_raises_score": "The critical execution risk would be closed.",
                    }
                ],
                "verdict": "revise",
            },
        }

        judgment = validate_plan_judgment(receipt, 8.5)
        self.assertEqual(judgment["verdict"], "revise")


if __name__ == "__main__":
    unittest.main()
