"""Behavior checks for the offline patrol protocol; no ROS imports or mocks."""
import importlib.util
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

ASSETS = Path(__file__).resolve().parent
REFERENCE = ASSETS / "patrol_reference.py"


class PatrolBehaviorTests(unittest.TestCase):
    def setUp(self):
        # An absent implementation is a RED assertion, not an import error.
        self.assertTrue(REFERENCE.is_file(), "offline patrol behavior is not implemented")
        spec = importlib.util.spec_from_file_location("patrol_reference", REFERENCE)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)

    def start(self, **options):
        model = self.api.Patrol([(0.2, 0.0), (0.2, 0.2)], **options)
        model.tick(0.0, odom_stamp=0.0, obstacle_stamp=0.0, obstacle_distance=2.0)
        return model

    def test_normal_reaches_ordered_points_at_hand_calculated_times(self):
        model = self.start()
        for i in range(1, 21):
            now = i / 10
            event = model.tick(now, odom_stamp=now, obstacle_stamp=now, obstacle_distance=2.0)
        self.assertEqual(event["state"], "SUCCEEDED")
        self.assertEqual(event["velocity"], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(event["pose"][0], 0.2)
        self.assertAlmostEqual(event["pose"][1], 0.2)
        self.assertEqual([row["index"] for row in model.waypoint_logs], [0, 1])
        self.assertEqual([row["time"] for row in model.waypoint_logs], [1.0, 2.0])
        self.assertEqual(model.result["reached_points"], 2)
        self.assertAlmostEqual(model.result["total_time"], 2.0)

    def test_wait_stops_immediately_then_resumes_only_above_clear_threshold(self):
        model = self.start()
        model.tick(0.1, odom_stamp=0.1, obstacle_stamp=0.1, obstacle_distance=0.4)
        stopped_pose = model.pose[:]
        for now, distance in [(0.2, 0.6), (0.3, 0.8)]:
            event = model.tick(now, odom_stamp=now, obstacle_stamp=now, obstacle_distance=distance)
            self.assertEqual(event["state"], "WAITING")
            self.assertEqual(event["velocity"], [0.0, 0.0, 0.0])
            self.assertEqual(event["pose"], stopped_pose)
        event = model.tick(0.4, odom_stamp=0.4, obstacle_stamp=0.4, obstacle_distance=0.81)
        self.assertEqual(event["state"], "MOVING")
        event = model.tick(0.5, odom_stamp=0.5, obstacle_stamp=0.5, obstacle_distance=0.5)
        self.assertEqual(event["state"], "MOVING")
        self.assertGreater(event["pose"][0], stopped_pose[0])

    def test_cancel_is_terminal_and_never_moves_after_later_fresh_input(self):
        model = self.start()
        event = model.tick(0.1, odom_stamp=0.1, obstacle_stamp=0.1,
                           obstacle_distance=2.0, cancel=True)
        self.assertEqual(event["state"], "CANCELED")
        frozen = event["pose"][:]
        result = model.result.copy()
        for now in [0.2, 0.3, 1.0]:
            event = model.tick(now, odom_stamp=now, obstacle_stamp=now, obstacle_distance=2.0)
            self.assertEqual(event["pose"], frozen)
            self.assertEqual(event["velocity"], [0.0, 0.0, 0.0])
            self.assertEqual(event["state"], "CANCELED")
            self.assertEqual(model.result, result)
        self.assertEqual(model.waypoint_logs, [])

    def test_timeout_clips_old_motion_at_half_second_even_for_late_tick(self):
        model = self.api.Patrol([(1.0, 0.0)])
        model.tick(0.0, odom_stamp=0.0, obstacle_stamp=0.0, obstacle_distance=2.0)
        event = model.tick(0.8)
        self.assertEqual(event["state"], "ABORTED")
        self.assertAlmostEqual(event["pose"][0], 0.1)  # 0.2 m/s * 0.5 s
        self.assertEqual(event["velocity"], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(model.result["total_time"], 0.5)
        self.assertEqual(model.result["reason"], "input_timeout")
        later = model.tick(0.9, odom_stamp=0.9, obstacle_stamp=0.9, obstacle_distance=2.0)
        self.assertEqual(later["pose"], event["pose"])
        self.assertEqual(later["state"], "ABORTED")

    def test_either_input_can_expire_and_exact_timeout_is_expired(self):
        for missing in ["odom_stamp", "obstacle_stamp"]:
            with self.subTest(missing=missing):
                model = self.start()
                for i in range(1, 6):
                    now = i / 10
                    observation = {"odom_stamp": now, "obstacle_stamp": now}
                    del observation[missing]
                    if "obstacle_stamp" in observation:
                        observation["obstacle_distance"] = 2.0
                    event = model.tick(now, **observation)
                self.assertEqual(event["state"], "ABORTED")
                self.assertAlmostEqual(event["pose"][0], 0.1)
                self.assertEqual(event["velocity"], [0.0, 0.0, 0.0])

    def test_fresh_packet_cannot_revive_a_missed_timeout(self):
        model = self.start()
        event = model.tick(0.8, odom_stamp=0.8, obstacle_stamp=0.8, obstacle_distance=2.0)
        self.assertEqual(event["state"], "ABORTED")
        self.assertAlmostEqual(event["pose"][0], 0.1)

    def test_missing_initial_inputs_aborts_without_motion(self):
        model = self.api.Patrol([(1.0, 0.0)])
        event = model.tick(0.0)
        self.assertEqual(event["state"], "ABORTED")
        self.assertEqual(event["pose"], [0.0, 0.0, 0.0])

    def test_speed_limit_applies_to_diagonal_norm(self):
        model = self.api.Patrol([(1.0, 1.0)], max_speed=0.2)
        event = model.tick(0.0, odom_stamp=0.0, obstacle_stamp=0.0, obstacle_distance=2.0)
        vx, vy, wz = event["velocity"]
        self.assertAlmostEqual(math.hypot(vx, vy), 0.2)
        self.assertEqual(wz, 0.0)
        event = model.tick(0.1, odom_stamp=0.1, obstacle_stamp=0.1, obstacle_distance=2.0)
        self.assertAlmostEqual(math.hypot(*event["pose"][:2]), 0.02)

    def test_short_leg_does_not_overshoot_and_success_stays_frozen(self):
        model = self.api.Patrol([(0.005, 0.0)])
        first = model.tick(0.0, odom_stamp=0.0, obstacle_stamp=0.0, obstacle_distance=2.0)
        self.assertAlmostEqual(first["velocity"][0], 0.05)
        event = model.tick(0.1, odom_stamp=0.1, obstacle_stamp=0.1, obstacle_distance=2.0)
        self.assertEqual(event["state"], "SUCCEEDED")
        self.assertAlmostEqual(event["pose"][0], 0.005)
        later = model.tick(0.2, odom_stamp=0.2, obstacle_stamp=0.2, obstacle_distance=2.0)
        self.assertEqual(later["pose"], event["pose"])

    def test_invalid_goal_and_parameters_are_rejected(self):
        bad_goals = [[], [(math.nan, 0)], [(0, math.inf)], [(0,)], "bad", [(True, 0)]]
        for points in bad_goals:
            with self.subTest(points=points), self.assertRaises(ValueError):
                self.api.Patrol(points)
        for options in [{"dt": 0}, {"dt": math.inf}, {"max_speed": -1},
                        {"input_timeout": 0}, {"stop_distance": 0.8, "clear_distance": 0.5}]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.api.Patrol([(1, 0)], **options)

    def test_bad_event_does_not_change_pose_or_state(self):
        bad = [(0.0, {}), (-0.1, {}), (math.nan, {}), (math.inf, {}),
               (0.1, {"obstacle_distance": -1}), (0.1, {"obstacle_distance": math.nan}),
               (0.1, {"odom_stamp": 0.2}), (0.1, {"odom_stamp": -0.1}),
               (0.1, {"cancel": "yes"})]
        for now, options in bad:
            with self.subTest(now=now, options=options):
                model = self.start()
                pose, state = model.pose[:], model.state
                with self.assertRaises(ValueError):
                    model.tick(now, **options)
                self.assertEqual(model.pose, pose)
                self.assertEqual(model.state, state)

    def test_obstacle_receipt_and_value_must_be_one_sample(self):
        for options in [{"obstacle_stamp": 0.1}, {"obstacle_distance": 0.4}]:
            with self.subTest(options=options):
                model = self.start()
                pose = model.pose[:]
                with self.assertRaises(ValueError):
                    model.tick(0.1, **options)
                self.assertEqual(model.pose, pose)
                self.assertEqual(model.obstacle_stamp, 0.0)
                self.assertEqual(model.obstacle_distance, 2.0)

    def test_large_finite_coordinates_do_not_overflow_velocity(self):
        model = self.api.Patrol([(1e308, 1e308)], max_speed=1e308)
        event = model.tick(0.0, odom_stamp=0.0, obstacle_stamp=0.0, obstacle_distance=2.0)
        self.assertTrue(all(math.isfinite(value) for value in event["velocity"]))
        self.assertLessEqual(math.hypot(*event["velocity"][:2]), 1e308)

    def test_contract_rejects_nonfinite_result_and_excessive_velocity(self):
        valid = self.api.run_scenario("normal")
        expected = {"state": "SUCCEEDED", "total_time": 2.0, "reached_points": 2,
                    "pose": [0.2, 0.2, 0.0], "waypoint_times": [1.0, 2.0]}
        invalid = copy.deepcopy(valid)
        invalid["result"]["total_time"] = math.nan
        self.assertFalse(self.api.check_contract(invalid, expected)["passed"])
        invalid = copy.deepcopy(valid)
        invalid["events"][0]["velocity"] = [0.3, 0.0, 0.0]
        self.assertFalse(self.api.check_contract(invalid, expected)["passed"])

    def test_unrepresentable_waypoint_segments_are_rejected_before_motion(self):
        for points in [[(1.7e308, 1.7e308)], [(1e308, 0.0), (-1e308, 0.0)]]:
            with self.subTest(points=points), self.assertRaises(ValueError):
                self.api.Patrol(points)

    def test_contract_rejects_missing_or_malformed_pose_and_velocity(self):
        valid = self.api.run_scenario("normal")
        expected = {"state": "SUCCEEDED", "total_time": 2.0, "reached_points": 2,
                    "pose": [0.2, 0.2, 0.0], "waypoint_times": [1.0, 2.0]}
        for field in ["pose", "velocity"]:
            for value in [[], [0.0, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, "0", 0.0]]:
                with self.subTest(field=field, value=value):
                    invalid = copy.deepcopy(valid)
                    for event in invalid["events"]:
                        event[field] = value
                    self.assertFalse(self.api.check_contract(invalid, expected)["passed"])

    def test_fixed_cases_match_independent_contract_and_are_deterministic(self):
        for name, state, end, position, count in [
            ("normal", "SUCCEEDED", 2.0, [0.2, 0.2, 0.0], 2),
            ("obstacle", "SUCCEEDED", 2.7, [0.2, 0.2, 0.0], 2),
            ("cancel", "CANCELED", 0.5, [0.1, 0.0, 0.0], 0),
            ("timeout", "ABORTED", 0.9, [0.18, 0.0, 0.0], 0),
        ]:
            with self.subTest(name=name):
                report = self.api.run_scenario(name)
                self.assertEqual(report, self.api.run_scenario(name))
                self.assertTrue(report["contract"]["passed"])
                self.assertEqual(report["result"]["state"], state)
                self.assertAlmostEqual(report["result"]["total_time"], end)
                self.assertEqual(report["result"]["reached_points"], count)
                for got, want in zip(report["events"][-1]["pose"], position):
                    self.assertAlmostEqual(got, want)
                terminal = [e for e in report["events"] if e["state"] == state]
                for event in terminal:
                    self.assertEqual(event["velocity"], [0.0, 0.0, 0.0])
                    self.assertEqual(event["pose"], terminal[0]["pose"])

    def test_cli_json_reports_feedback_logs_and_contract(self):
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(REFERENCE),
                              "--scenario", "obstacle", "--json"],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["result"]["state"], "SUCCEEDED")
        self.assertEqual(len(report["waypoint_logs"]), 2)
        self.assertEqual(report["events"][5]["state"], "WAITING")
        self.assertAlmostEqual(report["events"][5]["feedback"]["distance_to_goal"], 0.1)
        self.assertTrue(report["contract"]["passed"])


if __name__ == "__main__":
    unittest.main()
