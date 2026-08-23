from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from compile_factory import SCHEMA, compile_factory  # noqa: E402
from factory import (  # noqa: E402
    FactoryError,
    enforce_dispatch_limits,
    is_unsafe_repository_artifact,
    validate_plan,
    validate_plan_judgment,
    validated_usage,
)


class FactoryCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = yaml.safe_load((ROOT / "factory.yaml").read_text())

    def test_contract_is_valid_and_bounded(self) -> None:
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(self.factory)), [])
        self.assertLessEqual(len(self.factory["implementers"]), 10)
        self.assertEqual(self.factory["review"]["max_cycles"], 5)

    def test_copywriting_is_a_routable_specialist_without_a_second_lifecycle(self) -> None:
        implementers = {item["id"]: item for item in self.factory["implementers"]}
        self.assertEqual(set(implementers), {"product", "design", "copy"})
        for owner in ("product", "design", "copy"):
            self.assertIn("skills/evil-genius-copywriter", implementers[owner]["skills"])
        self.assertEqual(implementers["copy"]["instructions"], "agents/copywriter.md")
        self.assertIn("skills/evil-genius-copywriter", self.factory["review"]["skills"])

        workflow = compile_factory(self.factory)
        steps = {step["id"]: step for step in workflow["steps"]}
        self.assertEqual(steps["implement-copy"]["needs"], ["plan-review"])
        self.assertEqual(
            steps["integrate"]["needs"],
            ["implement-product", "implement-design", "implement-copy"],
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

    def test_compiler_gives_every_review_a_guarded_terminal_exit(self) -> None:
        workflow = compile_factory(self.factory)
        steps = {step["id"]: step for step in workflow["steps"]}
        ids = list(steps)
        self.assertEqual(len([item for item in ids if item.startswith("review-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("repair-")]), 4)
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
                for cycle in range(1, 5)
            },
        }
        self.assertTrue(agent_steps)
        for step in agent_steps:
            self.assertEqual(step["timeout"], expected_timeouts[step["id"]])
        for step_id in ["integrate", "human-required", *[
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
        self.assertEqual(
            steps["human-required"]["when"],
            {"op": "equals", "path": "/verdict", "value": "repair"},
        )
        self.assertEqual(steps["capture-2"]["needs"], ["repair-1"])
        self.assertEqual(steps["plan"]["needs"], ["repository-intelligence"])
        self.assertEqual(steps["implement-product"]["needs"], ["plan-review"])
        self.assertNotIn("retries", steps["plan-review"])

    def test_contract_rejects_more_than_ten_implementers_or_five_cycles(self) -> None:
        too_many = dict(self.factory)
        too_many["implementers"] = self.factory["implementers"] * 6
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(too_many)))
        too_long = yaml.safe_load((ROOT / "factory.yaml").read_text())
        too_long["review"]["max_cycles"] = 6
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(too_long)))

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
            "node_modules/tool/index.js",
            ".env",
            "config/.env.production",
            ".DS_Store",
        ):
            self.assertTrue(is_unsafe_repository_artifact(path), path)
        for path in (".env.example", ".env.sample", ".env.template", "src/app.py"):
            self.assertFalse(is_unsafe_repository_artifact(path), path)

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


if __name__ == "__main__":
    unittest.main()
