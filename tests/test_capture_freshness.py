from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.factory import FactoryError, capture_evidence, digest_bytes


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


if __name__ == "__main__":
    unittest.main()
