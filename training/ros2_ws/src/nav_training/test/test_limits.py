"""Real numeric input boundary tests; these run without ROS."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nav_training.limits import bound_planar_command, bounded_number


class CommandLimitsTests(unittest.TestCase):
    def test_keeps_valid_body_velocity_and_zero(self):
        self.assertEqual(bound_planar_command((0.2, -0.1, 0, 0, 0, -0.3)),
                         (0.2, -0.1, -0.3))
        self.assertEqual(bound_planar_command((0, 0, 0, 0, 0, 0)), (0, 0, 0))

    def test_clips_linear_norm_without_changing_direction(self):
        vx, vy, wz = bound_planar_command((3, 4, 0, 0, 0, -5))
        self.assertAlmostEqual(vx, 0.3)
        self.assertAlmostEqual(vy, 0.4)
        self.assertEqual(wz, -1.0)

    def test_large_finite_components_still_preserve_direction(self):
        vx, vy, wz = bound_planar_command((1e308, 1e308, 0, 0, 0, 0))
        self.assertAlmostEqual(math.hypot(vx, vy), 0.5)
        self.assertAlmostEqual(vx, vy)
        self.assertEqual(wz, 0)

    def test_custom_limits_apply(self):
        self.assertEqual(bound_planar_command((2, 0, 0, 0, 0, 3), 0.25, 0.75),
                         (0.25, 0, 0.75))

    def test_nonfinite_or_nonplanar_command_is_rejected(self):
        for index in range(6):
            for bad in (math.nan, math.inf, -math.inf):
                command = [0.0] * 6
                command[index] = bad
                with self.subTest(index=index, value=bad), self.assertRaises(ValueError):
                    bound_planar_command(command)
        for index in (2, 3, 4):
            command = [0.0] * 6
            command[index] = 0.1
            with self.subTest(axis=index), self.assertRaises(ValueError):
                bound_planar_command(command)

    def test_invalid_limits_and_wrong_shape_are_rejected(self):
        for bad in (0, -1, math.nan, math.inf):
            with self.subTest(limit=bad), self.assertRaises(ValueError):
                bound_planar_command((0,) * 6, bad, 1)
        with self.assertRaises(ValueError):
            bound_planar_command((0,) * 5)

    def test_parameter_range_rejects_bad_rate_and_keeps_endpoints(self):
        for bad in (-1, 0, math.nan, math.inf, 201):
            with self.subTest(rate=bad), self.assertRaises(ValueError):
                bounded_number(bad, 'rate_hz', 0.1, 200)
        self.assertEqual(bounded_number(0.1, 'rate_hz', 0.1, 200), 0.1)
        self.assertEqual(bounded_number(200, 'rate_hz', 0.1, 200), 200)


if __name__ == '__main__':
    unittest.main()
