"""Analytic motion expectations; no ROS installation or hardware needed."""
import importlib
import math
from pathlib import Path
import sys
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / 'ros2_ws/src/nav_training'
sys.path.insert(0, str(PACKAGE))


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((PACKAGE / 'nav_training/core.py').is_file(),
                        'The motion implementation has not been added yet')
        self.core = importlib.import_module('nav_training.core')

    def assertPose(self, actual, x, y, yaw):
        self.assertAlmostEqual(actual.x, x, places=9)
        self.assertAlmostEqual(actual.y, y, places=9)
        self.assertAlmostEqual(actual.yaw, yaw, places=9)

    def test_body_axes_and_rotated_heading(self):
        c = self.core
        for start, velocity, want in (
            (c.Pose2D(), c.Twist2D(.2, 0, 0), (1, 0, 0)),
            (c.Pose2D(), c.Twist2D(0, .2, 0), (0, 1, 0)),
            (c.Pose2D(0, 0, math.pi / 2), c.Twist2D(.2, 0, 0),
             (0, 1, math.pi / 2)),
            (c.Pose2D(2, 3, 0), c.Twist2D(0, 0, .2), (2, 3, 1)),
        ):
            with self.subTest(want=want):
                self.assertPose(c.integrate_body(start, velocity, 5), *want)

    def test_arc_and_lateral_arc_match_quarter_circle(self):
        c = self.core
        self.assertPose(c.integrate_body(c.Pose2D(), c.Twist2D(1, 0, 1),
                                        math.pi / 2), 1, 1, math.pi / 2)
        self.assertPose(c.integrate_body(c.Pose2D(), c.Twist2D(0, 1, 1),
                                        math.pi / 2), -1, 1, math.pi / 2)

    def test_near_zero_rotation_and_zero_duration(self):
        c = self.core
        self.assertPose(c.integrate_body(c.Pose2D(), c.Twist2D(.2, 0, 1e-14), 5),
                        1, 0, 5e-14)
        self.assertPose(c.integrate_body(c.Pose2D(1, 2, 3), c.Twist2D(1, 2, 3), 0),
                        1, 2, 3)

    def test_invalid_values_are_rejected_before_state_changes(self):
        c = self.core
        for dt in (-1, math.nan, math.inf):
            with self.subTest(dt=dt), self.assertRaises(ValueError):
                c.integrate_body(c.Pose2D(), c.Twist2D(), dt)
        for bad in (math.nan, math.inf, -math.inf):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                c.integrate_body(c.Pose2D(bad, 0, 0), c.Twist2D(), 1)
            with self.assertRaises(ValueError):
                c.integrate_body(c.Pose2D(), c.Twist2D(0, bad, 0), 1)
        for timeout in (0, -1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                c.TimedModel(timeout=timeout)
        model = c.TimedModel()
        model.set_command(c.Twist2D(.2, 0, 0), 10)
        with self.assertRaises(ValueError):
            model.set_command(c.Twist2D(math.nan, 0, 0), 10.1)
        self.assertEqual(model.stamp, 10)
        with self.assertRaises(ValueError):
            model.step(math.inf)
        self.assertEqual(model.stamp, 10)

    def test_first_stamp_and_no_command_do_not_move(self):
        c = self.core
        model = c.TimedModel()
        self.assertIsNone(model.stamp)
        self.assertPose(model.step(1000), 0, 0, 0)
        self.assertPose(model.step(1005), 0, 0, 0)
        self.assertEqual(model.active_twist(1005), c.Twist2D())

    def test_expiry_clips_interval_instead_of_losing_or_extending_motion(self):
        c = self.core
        model = c.TimedModel(timeout=.5)
        model.set_command(c.Twist2D(.2, 0, 0), 10)
        self.assertPose(model.step(10.2), .04, 0, 0)
        self.assertPose(model.step(12), .1, 0, 0)
        self.assertEqual(model.active_twist(10.5), c.Twist2D())
        self.assertPose(model.step(13), .1, 0, 0)

    def test_new_command_integrates_previous_then_zero_stays_zero(self):
        c = self.core
        model = c.TimedModel(timeout=1)
        model.set_command(c.Twist2D(.2, 0, 0), 0)
        model.set_command(c.Twist2D(0, .4, 0), .5)
        self.assertPose(model.step(1), .1, .2, 0)
        model.set_command(c.Twist2D(), 1)
        self.assertPose(model.step(2), .1, .2, 0)

    def test_clock_rollback_preserves_pose_clears_velocity_and_can_restart(self):
        c = self.core
        model = c.TimedModel(timeout=1)
        model.set_command(c.Twist2D(.2, 0, 0), 10)
        model.step(10.5)
        self.assertPose(model.step(1), .1, 0, 0)
        self.assertEqual(model.clock_resets, 1)
        self.assertEqual(model.active_twist(1), c.Twist2D())
        self.assertPose(model.step(1.5), .1, 0, 0)
        model.set_command(c.Twist2D(0, .2, 0), 2)
        self.assertPose(model.step(2.5), .1, .1, 0)

    def test_repeated_stamp_does_not_integrate_twice(self):
        c = self.core
        model = c.TimedModel(timeout=1)
        model.set_command(c.Twist2D(.2, 0, 0), 0)
        self.assertPose(model.step(.5), .1, 0, 0)
        self.assertPose(model.step(.5), .1, 0, 0)


if __name__ == '__main__':
    unittest.main()
