import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.dashboard import INDEX, build_snapshot, create_server


def write_max_fixture(root: Path) -> Path:
    """Create the locked maximum-content dashboard fixture."""
    repo = root / "monster-truck-mayhem"
    run_id = "monster-truck-ios-production-v2-with-a-deliberately-long-run-identifier"
    run = repo / ".factory" / "runs" / run_id
    for directory in ("receipts", "logs/review-5", "plans", "contexts", "evidence"):
        (run / directory).mkdir(parents=True, exist_ok=True)

    owners = ["design", *[f"implementation-{number:02d}" for number in range(1, 9)], "qa"]
    token_totals = [260_000, 215_000, 160_000, 140_000, 125_000, 110_000, 90_000, 75_000, 60_000, 49_391]
    tasks = [
        {
            "id": f"task-{index:02d}-with-a-long-but-inspectable-identifier",
            "owner": owner,
            "depends_on": [] if index == 1 else [f"task-{index - 1:02d}"],
        }
        for index, owner in enumerate(owners, start=1)
    ]
    blockers = [
        "Simulator proof is stale and must be recaptured at both approved viewport sizes.",
        "The acceptance test for restoring a suspended race still fails on the current commit.",
        "The release evidence receipt refers to an older repository commit.",
    ]
    state = {
        "schema": "pi-graph-factory.run.v1",
        "id": run_id,
        "repo": str(repo),
        "phase": "reviewing",
        "operation": {"kind": "repair", "owner": "design", "cycle": 5, "attempt": 2},
        "created_at": "2026-08-23T04:00:00+00:00",
        "updated_at": "2026-08-25T03:00:00+00:00",
        "usage": {
            "calls": 10,
            "input_tokens": 1_084_000,
            "output_tokens": 200_391,
            "total_tokens": 1_284_391,
            "cost_usd": 0.42,
            "unknown_calls": 2,
        },
        "plan": {"tasks": tasks},
        "lane_receipts": {owner: {"status": "passed"} for owner in owners[:5]},
        "pending_lane_failures": {"qa": {"message": blockers[1]}},
        "cycles": [{"review": {"verdict": "repair", "issues": [{"id": f"FIX-{index}", "message": message} for index, message in enumerate(blockers, start=1)]}} for _cycle in range(5)],
    }
    (run / "state.json").write_text(json.dumps(state), encoding="utf-8")

    beginning = datetime(2026, 8, 23, 4, tzinfo=timezone.utc)
    events = [
        {
            "sequence": sequence,
            "at": (beginning + timedelta(minutes=23 * sequence)).isoformat(),
            "event": ["trigger_received", "lane_started", "agent_progress", "verification_finished", "review_issue_recorded"][sequence % 5],
            "phase": "reviewing" if sequence > 90 else "implementing",
            "payload": {
                "owner": owners[sequence % len(owners)],
                "message": f"Complete preserved event payload {sequence}: " + "evidence remains inspectable; " * 8,
            },
        }
        for sequence in range(1, 121)
    ]
    (run / "events.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    (run / "factory.yaml").write_text("schema: 1\n", encoding="utf-8")
    (run / "plans" / "plan-5.json").write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
    (run / "contexts" / "vision-and-feature-context.md").write_text("# Vision\n\n" + "Production context.\n" * 80, encoding="utf-8")
    (run / "logs" / "review-5" / "stream.jsonl").write_text("\n".join(json.dumps({"event": "review_output", "index": index}) for index in range(240)) + "\n", encoding="utf-8")
    for index in range(32):
        (run / "evidence" / f"proof-{index:02d}-with-a-descriptive-name.txt").write_text(f"proof {index}\n", encoding="utf-8")

    for index, (owner, total) in enumerate(zip(owners, token_totals, strict=True)):
        receipt = {
            "role": owner,
            "model": "gpt-5.6-luna",
            "usage": {
                "input": total - 10_000,
                "output": 10_000,
                "total": total,
                "cost": None if index in {3, 8} else round(total / 1_000_000, 4),
            },
        }
        path = run / "receipts" / f"agent-{owner}-{index:02d}.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        recorded_at = beginning + timedelta(hours=index * 4)
        os.utime(path, (recorded_at.timestamp(), recorded_at.timestamp()))
    return run


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "monster-truck-mayhem"
        self.run = self.repo / ".factory" / "runs" / "hard-run-with-a-long-name"
        (self.run / "receipts").mkdir(parents=True)
        (self.run / "logs" / "review-1").mkdir(parents=True)
        (self.run / "plans").mkdir()
        (self.run / "active").mkdir()
        state = {
            "schema": "pi-graph-factory.run.v1",
            "id": "hard-run-with-a-long-name",
            "repo": str(self.repo),
            "phase": "reviewing",
            "operation": {"kind": "repair", "owner": "design", "cycle": 2},
            "created_at": "2026-08-25T01:00:00+00:00",
            "updated_at": "2026-08-25T03:00:00+00:00",
            "usage": {
                "calls": 2,
                "input_tokens": 800,
                "output_tokens": 200,
                "total_tokens": 1000,
                "cost_usd": 0.01,
                "unknown_calls": 1,
            },
            "plan": {
                "tasks": [
                    {"id": "ui", "owner": "design", "depends_on": []},
                    {"id": "qa", "owner": "qa", "depends_on": ["ui"]},
                ]
            },
            "lane_receipts": {"design": {"status": "passed"}},
            "pending_lane_failures": {},
            "cycles": [
                {
                    "review": {
                        "verdict": "repair",
                        "issues": [
                            {
                                "id": "FIX-1",
                                "message": "Simulator screenshot is stale and must be recaptured.",
                            }
                        ],
                    }
                }
            ],
        }
        (self.run / "state.json").write_text(json.dumps(state), encoding="utf-8")
        events = [
            {"sequence": 1, "at": "2026-08-25T01:00:00+00:00", "event": "trigger_received", "phase": "intake", "payload": {"request": "build it"}},
            {"sequence": 2, "at": "2026-08-25T03:00:00+00:00", "event": "repair_owner_started", "phase": "reviewing", "payload": {"owner": "design"}},
        ]
        (self.run / "events.jsonl").write_text(
            "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
        )
        (self.run / "factory.yaml").write_text("schema: 1\n", encoding="utf-8")
        (self.run / "plans" / "plan-1.json").write_text("{}\n", encoding="utf-8")
        (self.run / "logs" / "review-1" / "stream.jsonl").write_text(
            '{"event":"working"}\n', encoding="utf-8"
        )
        receipt = {
            "role": "review:1",
            "model": "gpt-5.6-luna",
            "usage": {"input": 800, "output": 200, "total": 1000, "cost": None},
        }
        receipt_path = self.run / "receipts" / "agent-review-1-abc.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        os.utime(receipt_path, (1_777_000_000, 1_777_000_000))

    def tearDown(self):
        self.temporary.cleanup()

    def test_snapshot_projects_controller_truth_and_complete_artifacts(self):
        snapshot, artifacts = build_snapshot([self.root])

        self.assertEqual(len(snapshot["projects"]), 1)
        self.assertEqual(len(snapshot["runs"]), 1)
        run = snapshot["runs"][0]
        self.assertEqual(run["phase"], "reviewing")
        self.assertEqual(run["operation"], "repair · owner design · cycle 2")
        self.assertEqual(run["blockers"], ["Simulator screenshot is stale and must be recaptured."])
        self.assertEqual(run["usage_by_role"], {"review:1": 1000})
        self.assertEqual(run["usage_records"][0]["model"], "gpt-5.6-luna")
        self.assertEqual([event["sequence"] for event in run["events"]], [1, 2])
        self.assertEqual([lane["status"] for lane in run["lanes"]], ["checkpointed", "waiting"])
        listed = {item["path"] for group in run["artifacts"] for item in group["items"]}
        self.assertIn("events.jsonl", listed)
        self.assertIn("logs/review-1/stream.jsonl", listed)
        self.assertEqual(len(artifacts), len(listed))

    def test_malformed_ledgers_stay_visible_as_degraded_runs(self):
        broken = self.repo / ".factory" / "runs" / "broken"
        broken.mkdir()
        (broken / "state.json").write_text("{nope", encoding="utf-8")
        (broken / "events.jsonl").write_text("not-json\n", encoding="utf-8")

        snapshot, _artifacts = build_snapshot([self.root])
        degraded = next(run for run in snapshot["runs"] if run["id"] == "broken")

        self.assertEqual(degraded["phase"], "degraded")
        self.assertIn("Run state is unreadable", degraded["blockers"][0])
        self.assertEqual(degraded["events"][0]["event"], "malformed_event")
        self.assertTrue(degraded["degraded"])

    def test_artifact_allowlist_excludes_unrelated_files_and_escaping_symlinks(self):
        secret = self.root / "private-secret.txt"
        secret.write_text("do not serve", encoding="utf-8")
        (self.run / "logs" / "review-1" / "escape.txt").symlink_to(secret)

        _snapshot, artifacts = build_snapshot([self.root])

        self.assertNotIn(secret.resolve(), artifacts.values())
        self.assertFalse(any(path.name == "escape.txt" for path in artifacts.values()))

    def test_http_api_range_requests_and_host_guard(self):
        server = create_server([self.root], 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(f"{base}/api/dashboard") as response:
                payload = json.load(response)
            self.assertEqual(payload["runs"][0]["id"], "hard-run-with-a-long-name")

            event_item = next(
                item
                for group in payload["runs"][0]["artifacts"]
                for item in group["items"]
                if item["path"] == "events.jsonl"
            )
            request = urllib.request.Request(
                f"{base}/api/artifact?id={event_item['id']}",
                headers={"Range": "bytes=0-4"},
            )
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(len(response.read()), 5)
                self.assertEqual(response.headers.get_content_type(), "text/plain")

            with self.assertRaises(urllib.error.HTTPError) as missing:
                urllib.request.urlopen(f"{base}/api/artifact?id=not-allowed")
            self.assertEqual(missing.exception.code, 404)
            missing.exception.close()

            hostile = urllib.request.Request(f"{base}/api/dashboard", headers={"Host": "evil.test"})
            with self.assertRaises(urllib.error.HTTPError) as forbidden:
                urllib.request.urlopen(hostile)
            self.assertEqual(forbidden.exception.code, 403)
            forbidden.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_interface_keeps_native_accessibility_and_reduced_motion_contracts(self):
        html = INDEX.read_text(encoding="utf-8")

        self.assertIn('<main id="workspace"', html)
        self.assertIn('aria-label="Projects and runs"', html)
        self.assertIn("focus-visible", html)
        self.assertIn("prefers-reduced-motion", html)
        self.assertIn("accessibleLabelForKey", html)
        self.assertIn('data-row="${row}"', html)
        self.assertIn("Use arrow keys to move", html)
        self.assertIn('button.addEventListener("focus"', html)
        self.assertNotIn("transition: all", html)
        self.assertNotIn('target="_blank"', html)

    def test_locked_maximum_fixture_has_exact_long_content_shape(self):
        maximum_root = self.root / "maximum-fixture"
        write_max_fixture(maximum_root)

        snapshot, _artifacts = build_snapshot([maximum_root])
        run = snapshot["runs"][0]

        self.assertEqual(
            run["id"],
            "monster-truck-ios-production-v2-with-a-deliberately-long-run-identifier",
        )
        self.assertEqual(len(run["events"]), 120)
        self.assertEqual(len(run["lanes"]), 10)
        self.assertEqual(run["usage"]["total_tokens"], 1_284_391)
        self.assertEqual(len(run["usage_records"]), 10)
        self.assertEqual(sum(run["usage_by_role"].values()), 1_284_391)
        self.assertGreaterEqual(len(run["blockers"]), 3)


if __name__ == "__main__":
    unittest.main()
