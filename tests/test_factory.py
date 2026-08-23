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


class FactoryCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = yaml.safe_load((ROOT / "factory.yaml").read_text())

    def test_contract_is_valid_and_bounded(self) -> None:
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(self.factory)), [])
        self.assertLessEqual(len(self.factory["implementers"]), 10)
        self.assertEqual(self.factory["review"]["max_cycles"], 5)

    def test_compiler_emits_ten_review_repair_nodes_and_guarded_merge(self) -> None:
        workflow = compile_factory(self.factory)
        ids = [step["id"] for step in workflow["steps"]]
        self.assertEqual(len([item for item in ids if item.startswith("review-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("repair-")]), 5)
        self.assertEqual(len([item for item in ids if item.startswith("capture-")]), 5)
        merge = workflow["steps"][-1]
        self.assertEqual(merge["id"], "merge")
        self.assertEqual(merge["when"], {"op": "equals", "path": "/verdict", "value": "pass"})

    def test_contract_rejects_more_than_ten_implementers_or_five_cycles(self) -> None:
        too_many = dict(self.factory)
        too_many["implementers"] = self.factory["implementers"] * 6
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(too_many)))
        too_long = yaml.safe_load((ROOT / "factory.yaml").read_text())
        too_long["review"]["max_cycles"] = 6
        self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(too_long)))


if __name__ == "__main__":
    unittest.main()
