from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.repository_intelligence import IntelligenceError, ensure_repository_intelligence


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

    def ensure(self, enrichment: dict | None = None) -> dict:
        override = f"{sys.executable} {FAKE_GRAPHIFY}"
        with patch.dict(os.environ, {"PI_GRAPH_FACTORY_GRAPHIFY": override}):
            return ensure_repository_intelligence(
                self.repo,
                auto_install=False,
                timeout_seconds=30,
                termination_grace_seconds=1,
                enrichment=enrichment,
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

    @patch("scripts.repository_intelligence.pi_api_key", return_value="private-test-key")
    def test_semantic_enrichment_uses_configured_model_without_persisting_key(
        self, _key: object,
    ) -> None:
        (self.repo / "app.py").write_text("print('ready')\n", encoding="utf-8")
        (self.repo / "VISION.md").write_text("# Vision\n\nShip it.\n", encoding="utf-8")
        self.commit("app.py", "VISION.md")
        enrichment = {
            "enabled": True,
            "required": True,
            "backend": "deepseek",
            "model": "deepseek-ai/DeepSeek-V4-Flash-0731",
            "mode": "deep",
            "base_url": "https://inference.baseten.co/v1",
            "pi_auth_model": "baseten/deepseek-ai/DeepSeek-V4-Flash-0731",
        }

        receipt = self.ensure(enrichment)
        invocation = json.loads(
            (self.repo / "graphify-out" / "fake-invocation.json").read_text()
        )
        self.assertEqual(receipt["enrichment"]["status"], "ready")
        self.assertIn("--backend", invocation["args"])
        self.assertIn("deepseek", invocation["args"])
        self.assertIn("deepseek-ai/DeepSeek-V4-Flash-0731", invocation["args"])
        self.assertIn("deep", invocation["args"])
        self.assertNotIn("--code-only", invocation["args"])
        self.assertTrue(invocation["deepseek_key_present"])
        self.assertEqual(
            invocation["deepseek_base_url"], "https://inference.baseten.co/v1"
        )
        self.assertNotIn("private-test-key", json.dumps(receipt))
        self.assertIn("[REDACTED]", receipt["execution"]["output"])
        self.assertNotIn(
            "private-test-key",
            (self.repo / "graphify-out" / "factory-metadata.json").read_text(),
        )

        cached = self.ensure(enrichment)
        self.assertFalse(cached["refreshed"])

    @patch(
        "scripts.repository_intelligence.pi_api_key",
        side_effect=IntelligenceError("no configured credential"),
    )
    def test_optional_enrichment_falls_back_to_ast_and_retries_later(
        self, _key: object,
    ) -> None:
        (self.repo / "app.py").write_text("print('ready')\n", encoding="utf-8")
        self.commit("app.py")
        enrichment = {
            "enabled": True,
            "required": False,
            "backend": "deepseek",
            "model": "deepseek-v4-flash",
            "mode": "deep",
            "pi_auth_model": "baseten/deepseek-ai/DeepSeek-V4-Flash-0731",
        }

        receipt = self.ensure(enrichment)
        invocation = json.loads(
            (self.repo / "graphify-out" / "fake-invocation.json").read_text()
        )
        self.assertEqual(receipt["enrichment"]["status"], "unavailable")
        self.assertIn("--code-only", invocation["args"])
        metadata = json.loads(
            (self.repo / "graphify-out" / "factory-metadata.json").read_text()
        )
        self.assertIsNone(metadata["profile_sha256"])


if __name__ == "__main__":
    unittest.main()
