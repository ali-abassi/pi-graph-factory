from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.factory import (
    EvidenceFailure,
    FactoryError,
    capture_evidence,
    digest_bytes,
    load_config,
    review_output,
    validate_plan,
)


ROOT = Path(__file__).resolve().parents[1]


class FactoryCaptureFreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "capture@example.test"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Capture Fixture"],
            cwd=self.repo,
            check=True,
        )
        (self.repo / "app.txt").write_text("integrated current behavior\n", encoding="utf-8")
        evidence = self.repo / "evidence"
        evidence.mkdir()
        (evidence / "desktop.png").write_bytes(b"png")
        (evidence / "flow.webm").write_bytes(b"stale-before-integration")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "integrated"], cwd=self.repo, check=True)
        self.run = self.root / "run"
        self.run.mkdir()
        self.state = {
            "plan": {"acceptance": ["true"]},
            "approved_plan_sha256": "approved-plan",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def config(self, command: str) -> dict:
        return {
            "evidence": {
                "capture_commands": [command],
                "screenshots": ["evidence/desktop.png"],
                "video": "evidence/flow.webm",
                "test_commands": ["test -s app.txt"],
            }
        }

    def test_capture_command_refreshes_proof_after_integration(self) -> None:
        receipt = capture_evidence(
            self.run,
            self.state,
            self.config("cp app.txt evidence/flow.webm"),
            self.repo,
            1,
        )
        video = next(item for item in receipt["files"] if item["path"].endswith("flow.webm"))
        self.assertEqual(video["sha256"], digest_bytes((self.repo / "app.txt").read_bytes()))
        self.assertEqual(receipt["capture"][0]["command"], "cp app.txt evidence/flow.webm")
        self.assertTrue(receipt["capture"][0]["passed"])

    def test_failed_capture_command_stops_before_review(self) -> None:
        with self.assertRaisesRegex(FactoryError, "configured evidence capture"):
            capture_evidence(
                self.run,
                self.state,
                self.config("false"),
                self.repo,
                1,
            )

    def test_partial_failed_capture_is_restored_and_receipted(self) -> None:
        with self.assertRaises(EvidenceFailure) as raised:
            capture_evidence(
                self.run,
                self.state,
                self.config("printf partial > evidence/flow.webm; false"),
                self.repo,
                1,
            )
        evidence = raised.exception.evidence
        self.assertFalse(evidence["valid"])
        self.assertFalse(evidence["capture"][0]["passed"])
        self.assertEqual(
            subprocess.check_output(
                ["git", "-C", str(self.repo), "status", "--porcelain"], text=True
            ),
            "",
        )
        self.assertTrue((self.run / "evidence" / "cycle-1.json").is_file())

    def test_reviewer_cannot_pass_a_failed_capture_receipt(self) -> None:
        evidence = {
            "valid": False,
            "sha256": "failed-capture-receipt",
        }
        receipt = {
            "output": {
                "verdict": "pass",
                "issues": [],
                "evidence": ["failed-capture-receipt"],
            }
        }
        with self.assertRaisesRegex(FactoryError, "cannot pass when evidence capture is invalid"):
            review_output(receipt, evidence, {"summary": "legacy plan"})

    def test_plan_cannot_repeat_the_capture_command_as_acceptance(self) -> None:
        plan = {
            "summary": "Build and prove the app",
            "tasks": [
                {
                    "id": "build",
                    "owner": "product",
                    "files": ["app.txt"],
                    "acceptance": ["test -s app.txt"],
                }
            ],
            "acceptance": ["cp app.txt evidence/flow.webm"],
            "risks": [],
            "open_questions": [],
        }
        with self.assertRaisesRegex(FactoryError, "must not repeat configured evidence capture"):
            validate_plan(
                plan,
                {"product"},
                evidence_capture_commands={"cp app.txt evidence/flow.webm"},
            )

    def test_config_cannot_repeat_capture_as_an_evidence_test(self) -> None:
        value = yaml.safe_load((ROOT / "factory.yaml").read_text(encoding="utf-8"))
        value["evidence"]["test_commands"].append(
            value["evidence"]["capture_commands"][0]
        )
        path = self.root / "overlapping-evidence-commands.yaml"
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
        with self.assertRaisesRegex(FactoryError, "must not repeat state-changing"):
            load_config(path)

    def test_acceptance_mutation_stops_before_review(self) -> None:
        self.state["plan"]["acceptance"] = [
            "printf 'mutated after capture' > evidence/flow.webm"
        ]
        with self.assertRaisesRegex(FactoryError, "evidence acceptance mutated"):
            capture_evidence(
                self.run,
                self.state,
                self.config("cp app.txt evidence/flow.webm"),
                self.repo,
                1,
            )

    def test_ignored_evidence_is_not_accepted_as_commit_bound_proof(self) -> None:
        (self.repo / ".gitignore").write_text("ignored/\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "ignore generated proof"], cwd=self.repo, check=True)
        config = {
            "evidence": {
                "capture_commands": ["mkdir -p ignored && cp app.txt ignored/desktop.png"],
                "screenshots": ["ignored/desktop.png"],
                "video": None,
                "artifacts": [],
                "test_commands": ["test -s app.txt"],
            }
        }
        with self.assertRaisesRegex(FactoryError, "not tracked in the proof commit"):
            capture_evidence(self.run, self.state, config, self.repo, 1)


if __name__ == "__main__":
    unittest.main()
