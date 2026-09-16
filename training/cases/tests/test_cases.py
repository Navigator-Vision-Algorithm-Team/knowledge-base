"""Behavioral regression for the two explicit, non-ROS teaching models."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_case import CacheModel, run_topic, run_stale

CASES = Path(__file__).resolve().parents[1]


class TopicCaseTests(unittest.TestCase):
    def test_same_visible_publisher_does_not_mean_delivery(self):
        data = json.loads((CASES / "inputs/topic-mismatch.json").read_text())
        broken = run_topic(data, "broken")
        fixed = run_topic(data, "fixed")
        self.assertEqual(broken[1]["publisher"], "/nav_training/sequence")
        self.assertEqual(fixed[1]["publisher"], "/nav_training/sequence")
        self.assertEqual(broken[1]["received"], 0)
        self.assertEqual(fixed[1]["received"], 5)
        self.assertEqual([r["sequence"] for r in fixed[0] if r["delivered"]], [1, 2, 3, 4, 5])

    def test_relative_repair_follows_changed_namespace(self):
        data = {"namespace": "/second_team", "publisher": "sequence",
                "subscriber_broken": "/sequence", "subscriber_fixed": "sequence",
                "sequence": [7, 8]}
        self.assertEqual(run_topic(data, "fixed")[1]["received"], 2)
        self.assertEqual(run_topic(data, "broken")[1]["received"], 0)


class CacheCaseTests(unittest.TestCase):
    def test_zero_clears_cache_before_any_later_sync(self):
        for mode, expected in (("broken", 2), ("fixed", 0)):
            data = json.loads((CASES / "inputs/stale-command.json").read_text())
            rows, report = run_stale(data, mode)
            self.assertEqual(report["stale_reissues"], expected)
            self.assertEqual(rows[3]["output"], [0.0, 0.0, 0.0])
            if mode == "fixed":
                self.assertIsNone(rows[4]["output"])
                self.assertIsNone(rows[5]["output"])
            self.assertEqual(rows[-1]["output"], [0.0, 0.1, 0.0])

    def test_near_zero_uses_original_epsilon_rule(self):
        model = CacheModel("fixed", 0.0, 0.0)
        model.step({"at": 0, "event": "local_plan"})
        model.step({"at": 0.1, "event": "command", "twist": [0.2, 0, 0]})
        model.step({"at": 0.2, "event": "command", "twist": [0.000001, 0, 0]})
        self.assertIsNone(model.step({"at": 0.3, "event": "sync", "yaw": 0}))

    def test_spin_and_rotation_are_separate_from_cache_fix(self):
        model = CacheModel("fixed", 1.5707963267948966, 0.5)
        output = model.step({"at": 0, "event": "command", "twist": [0.2, 0, 0]})
        self.assertAlmostEqual(output[0], 0.0)
        self.assertAlmostEqual(output[1], -0.2)
        self.assertEqual(output[2], 0.5)
        self.assertEqual(model.step({"at": 1, "event": "command", "twist": [0, 0, 0]}), [0, 0, 0.5])
        self.assertIsNone(model.step({"at": 2, "event": "spin", "value": 0}))

    def test_controller_timeout_is_not_a_command_watchdog(self):
        model = CacheModel("fixed", 0, 0)
        model.step({"at": 0, "event": "local_plan"})
        self.assertIsNone(model.step({"at": 0.5, "event": "command", "twist": [0.2, 0, 0]}))
        self.assertEqual(model.step({"at": 9, "event": "sync", "yaw": 0}), [0.2, 0, 0])
        self.assertEqual(model.step({"at": 10, "event": "command", "twist": [0, 0.1, 0]}), [0, 0.1, 0])

    def test_epsilon_boundary_is_nonzero_and_zero_cancels_rotation_cache(self):
        model = CacheModel("fixed", 0, 0)
        model.step({"at": 0, "event": "local_plan"})
        model.step({"at": 0.1, "event": "command", "twist": [0, 0, 0.00001]})
        self.assertEqual(model.step({"at": 0.2, "event": "sync", "yaw": 0}), [0, 0, 0.00001])
        model.step({"at": 0.3, "event": "command", "twist": [0, 0, 0]})
        self.assertIsNone(model.step({"at": 0.4, "event": "sync", "yaw": 0}))

    def test_bad_event_times_and_nonfinite_commands_are_rejected(self):
        model = CacheModel("fixed", 0, 0)
        model.step({"at": 1, "event": "local_plan"})
        with self.assertRaises(ValueError):
            model.step({"at": 0, "event": "sync", "yaw": 0})
        with self.assertRaises(ValueError):
            model.step({"at": 2, "event": "command", "twist": [float("nan"), 0, 0]})


class CommandLineTests(unittest.TestCase):
    def test_cli_writes_evidence_and_gate_rejects_fault(self):
        with tempfile.TemporaryDirectory() as directory:
            for case in ("topic-mismatch", "stale-command"):
                for mode, code in (("broken", 1), ("fixed", 0)):
                    target = Path(directory) / (case + "-" + mode)
                    result = subprocess.run([sys.executable, "-X", "utf8", str(CASES / "run_case.py"),
                        case, "--mode", mode, "--input", str(CASES / "inputs" / (case + ".json")),
                        "--out-dir", str(target), "--check-contract"], capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(result.returncode, code, result.stderr)
                    report = json.loads((target / "report.json").read_text())
                    self.assertEqual(report["contract_passed"], mode == "fixed")
                    self.assertTrue((target / "events.jsonl").read_text().strip())

    def test_cli_preserves_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "证据"
            args = [sys.executable, "-X", "utf8", str(CASES / "run_case.py"), "topic-mismatch",
                    "--mode", "fixed", "--out-dir", str(target)]
            first = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(first.returncode, 0, first.stderr)
            report = (target / "report.json").read_bytes()
            second = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(second.returncode, 2)
            self.assertIn("证据", second.stderr)
            self.assertEqual((target / "report.json").read_bytes(), report)


if __name__ == "__main__":
    unittest.main()
