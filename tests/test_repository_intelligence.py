from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.repository_intelligence import ensure_repository_intelligence


ROOT = Path(__file__).resolve().parents[1]
FAKE_GRAPHIFY = ROOT / "tests" / "fake_graphify.py"


class RepositoryIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "intelligence@example.test"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Repository Intelligence Fixture"],
            cwd=self.repo,
            check=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def commit(self, *names: str) -> None:
        subprocess.run(["git", "add", *names], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.repo, check=True)

    def ensure(self) -> dict:
        override = f"{sys.executable} {FAKE_GRAPHIFY}"
        with patch.dict(os.environ, {"PI_GRAPH_FACTORY_GRAPHIFY": override}):
            return ensure_repository_intelligence(
                self.repo,
                auto_install=False,
                timeout_seconds=30,
                termination_grace_seconds=1,
            )

    def test_code_repository_is_indexed_cached_and_refreshed_after_change(self) -> None:
        (self.repo / "app.py").write_text("print('first')\n", encoding="utf-8")
        self.commit("app.py")

        first = self.ensure()
        self.assertEqual(first["status"], "ready")
        self.assertTrue(first["refreshed"])
        self.assertEqual(first["nodes"], 1)
        self.assertTrue(Path(first["graph"]).is_file())
        self.assertEqual(
            subprocess.check_output(
                ["git", "-C", str(self.repo), "status", "--porcelain"], text=True,
            ),
            "",
        )

        cached = self.ensure()
        self.assertFalse(cached["refreshed"])
        self.assertEqual(cached["source_commit"], first["source_commit"])

        Path(cached["graph"]).write_text("not-json\n", encoding="utf-8")
        repaired = self.ensure()
        self.assertTrue(repaired["refreshed"])

        (self.repo / "app.py").write_text("print('second')\n", encoding="utf-8")
        self.commit("app.py")
        refreshed = self.ensure()
        self.assertTrue(refreshed["refreshed"])
        self.assertNotEqual(refreshed["source_commit"], first["source_commit"])

    def test_new_repository_without_code_defers_graph_until_code_exists(self) -> None:
        (self.repo / "VISION.md").write_text("# Vision\n", encoding="utf-8")
        (self.repo / "FEATURE_MAP.md").write_text("# Feature map\n", encoding="utf-8")
        self.commit("VISION.md", "FEATURE_MAP.md")

        receipt = self.ensure()
        self.assertEqual(receipt["status"], "deferred")
        self.assertIsNone(receipt["graph"])
        self.assertIn("no supported code", receipt["reason"])
        self.assertFalse((self.repo / "graphify-out" / "graph.json").exists())

        (self.repo / "app.py").write_text("print('ready')\n", encoding="utf-8")
        self.commit("app.py")
        ready = self.ensure()
        self.assertEqual(ready["status"], "ready")
        self.assertTrue(ready["refreshed"])


if __name__ == "__main__":
    unittest.main()
