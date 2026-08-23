from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.delivery import execute_delivery


class FactoryDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "delivery@example.test"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Delivery Fixture"],
            cwd=self.repo,
            check=True,
        )
        (self.repo / "app.txt").write_text("ready\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "ready"], cwd=self.repo, check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_success_requires_deploy_and_health(self) -> None:
        result = execute_delivery(
            self.repo,
            {"deploy_commands": ["true"], "health_commands": ["true"],
             "rollback_commands": ["false"]},
        )
        self.assertEqual(result["status"], "deployed")
        self.assertTrue(result["deploy"][0]["passed"])
        self.assertTrue(result["health"][0]["passed"])
        self.assertEqual(result["rollback"], [])

    def test_health_failure_runs_configured_rollback(self) -> None:
        result = execute_delivery(
            self.repo,
            {"deploy_commands": ["true"], "health_commands": ["false"],
             "rollback_commands": ["true"]},
        )
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["failure"], "production health command failed")
        self.assertTrue(result["rollback"][0]["passed"])

    def test_delivery_timeout_terminates_command_and_runs_rollback(self) -> None:
        result = execute_delivery(
            self.repo,
            {"deploy_commands": ["sleep 2"], "health_commands": ["true"],
             "rollback_commands": ["true"]},
            command_timeout_seconds=1,
            termination_grace_seconds=1,
        )
        self.assertEqual(result["status"], "rolled_back")
        self.assertTrue(result["deploy"][0]["timed_out"])
        self.assertEqual(result["health"], [])
        self.assertTrue(result["rollback"][0]["passed"])


if __name__ == "__main__":
    unittest.main()
