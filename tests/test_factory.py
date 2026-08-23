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
    validated_usage,
)


class FactoryCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = yaml.safe_load((ROOT / "factory.yaml").read_text())

    def test_contract_is_valid_and_bounded(self) -> None:
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(self.factory)), [])
        self.assertLessEqual(len(self.factory["implementers"]), 10)
        self.assertEqual(self.factory["review"]["max_cycles"], 5)

    def test_compiler_gives_every_review_a_guarded_terminal_exit(self) -> None:
        workflow = compile_factory(self.factory)
        steps = {step["id"]: step for step in workflow["steps"]}
        ids = list(steps)
        self.assertEqual(len([item for item in ids if item.startswith("review-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("repair-")]), 4)
        self.assertEqual(len([item for item in ids if item.startswith("capture-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("merge-")]), 5)
        agent_steps = [steps["plan"], *[steps[item] for item in ids
                                       if item.startswith(("implement-", "review-", "repair-"))]]
        self.assertTrue(agent_steps)
        expected_timeouts = {
            "plan": self.factory["planner"]["timeout_seconds"],
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
        ], *[f"merge-{cycle}" for cycle in range(1, 6)]]:
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


if __name__ == "__main__":
    unittest.main()
