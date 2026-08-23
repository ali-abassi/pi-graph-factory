from __future__ import annotations

import unittest

from scripts.agent_adapter import decode_output


class AgentAdapterTests(unittest.TestCase):
    def test_malformed_model_text_becomes_a_typed_invalid_receipt_payload(self) -> None:
        status, output = decode_output("Here is the plan, but not as JSON.")
        self.assertEqual(status, "invalid")
        self.assertEqual(output["error"], "model response was not a JSON object")
        self.assertIn("not as JSON", output["raw_excerpt"])

    def test_json_model_text_remains_a_passing_object(self) -> None:
        status, output = decode_output('{"verdict":"pass"}')
        self.assertEqual(status, "passed")
        self.assertEqual(output, {"verdict": "pass"})

    def test_single_json_code_fence_is_normalized(self) -> None:
        status, output = decode_output('```json\n{"verdict":"pass"}\n```')
        self.assertEqual(status, "passed")
        self.assertEqual(output, {"verdict": "pass"})

    def test_prose_around_json_remains_invalid(self) -> None:
        status, _ = decode_output('Here is the result: {"verdict":"pass"}')
        self.assertEqual(status, "invalid")


if __name__ == "__main__":
    unittest.main()
