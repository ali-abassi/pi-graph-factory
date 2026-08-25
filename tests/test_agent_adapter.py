from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.agent_adapter import (
    claude_command,
    claude_usage,
    codex_command,
    decode_output,
    run_streaming,
    skill_prompt,
)


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

    def test_prose_around_inline_json_remains_invalid(self) -> None:
        status, _ = decode_output('Here is the result: {"verdict":"pass"}')
        self.assertEqual(status, "invalid")

    def test_prose_around_one_json_fence_is_normalized(self) -> None:
        status, output = decode_output(
            'All checks pass.\n\n```json\n{"verdict":"pass"}\n```'
        )
        self.assertEqual(status, "passed")
        self.assertEqual(output, {"verdict": "pass"})

    def test_multiple_fenced_objects_remain_ambiguous_and_invalid(self) -> None:
        status, _ = decode_output(
            '```json\n{"verdict":"pass"}\n```\n```json\n{"verdict":"fail"}\n```'
        )
        self.assertEqual(status, "invalid")

    def test_configured_skill_can_be_inlined_for_non_pi_harnesses(self) -> None:
        prompt = skill_prompt(["skills/ponytail"])
        self.assertIn("factory-ponytail", prompt)
        self.assertIn("standard library", prompt)

    def test_claude_command_preapproves_only_the_configured_tools(self) -> None:
        command = claude_command(
            "claude-sonnet-4-6",
            "Implement the approved UI scope.",
            "read,edit,write,bash",
        )

        self.assertEqual(
            command,
            [
                "claude",
                "-p",
                "--model",
                "claude-sonnet-4-6",
                "--allowedTools=Read,Edit,Write,Bash",
                "Implement the approved UI scope.",
            ],
        )

    def test_claude_command_can_bind_a_durable_session_id(self) -> None:
        command = claude_command(
            "claude-sonnet-4-6",
            "Return the receipt.",
            "read",
            session_id="00000000-0000-4000-8000-000000000000",
        )

        self.assertIn("--session-id", command)
        self.assertIn("00000000-0000-4000-8000-000000000000", command)

    def test_codex_command_is_writable_only_inside_the_worktree(self) -> None:
        command = codex_command(
            "gpt-5.6-luna",
            "Generate the approved assets.",
            Path("/tmp/final-response.txt"),
        )

        self.assertIn("--sandbox", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
        self.assertIn("--approve-for-me", command)
        self.assertIn("--json", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_harness_streams_are_persisted_before_process_completion(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            artifacts = Path(raw)
            result = run_streaming(
                [sys.executable, "-c", "print('one', flush=True); print('two', flush=True)"],
                artifacts,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual((artifacts / "harness.stdout").read_text(), "one\ntwo\n")
            self.assertEqual((artifacts / "harness.stderr").read_text(), "")

    def test_claude_usage_deduplicates_repeated_jsonl_message_records(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "transcript.jsonl"
            first = {
                "type": "assistant",
                "message": {
                    "id": "msg-1",
                    "usage": {
                        "input_tokens": 1,
                        "output_tokens": 2,
                        "cache_creation_input_tokens": 3,
                        "cache_read_input_tokens": 4,
                    },
                },
            }
            second = {
                "type": "assistant",
                "message": {
                    "id": "msg-2",
                    "usage": {
                        "input_tokens": 5,
                        "output_tokens": 6,
                        "cache_creation_input_tokens": 7,
                        "cache_read_input_tokens": 8,
                    },
                },
            }
            path.write_text(
                "\n".join(json.dumps(item) for item in (first, first, second)) + "\n",
                encoding="utf-8",
            )

            usage, details = claude_usage(path)

        self.assertEqual(details["unique_messages"], 2)
        self.assertEqual(details["output_tokens"], 8)
        self.assertEqual(usage, {"input": 28, "output": 8, "total": 36, "cost": None})


if __name__ == "__main__":
    unittest.main()
