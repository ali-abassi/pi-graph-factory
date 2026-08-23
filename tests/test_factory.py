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
from factory import FactoryError, is_unsafe_repository_artifact, validated_usage  # noqa: E402


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
        self.assertTrue(all(item["timeout"] == self.factory["limits"]["agent_timeout_seconds"]
                            for item in agent_steps))
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
