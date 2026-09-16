"""CLI-level checks: data are interpreted as commands, never copied as predictions."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'tools/replay_motion.py'
COLUMNS = ['stamp_ns', 'x_m', 'y_m', 'yaw_rad', 'vx_m_s', 'vy_m_s', 'wz_rad_s']


class ReplayTests(unittest.TestCase):
    def run_replay(self, rows):
        self.assertTrue(RUNNER.is_file(), 'Offline replay tool has not been implemented')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.csv'
            with path.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream)
                writer.writerow(COLUMNS)
                writer.writerows(rows)
            return subprocess.run([sys.executable, str(RUNNER), str(path)],
                                  capture_output=True, text=True, encoding='utf-8')

    def test_replay_integrates_input_and_agrees_with_analytic_truth(self):
        result = self.run_replay([[0, 0, 0, 0, .2, 0, 0],
                                  [500000000, .1, 0, 0, .2, 0, 0],
                                  [1000000000, .2, 0, 0, 0, 0, 0]])
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['samples'], 3)
        self.assertAlmostEqual(report['predicted_final']['x'], .2)
        self.assertTrue(report['passed'])

    def test_incorrect_truth_is_reported_not_reused_as_prediction(self):
        result = self.run_replay([[0, 0, 0, 0, .2, 0, 0],
                                  [500000000, .9, 0, 0, 0, 0, 0]])
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertAlmostEqual(report['max_position_error_m'], .8)
        self.assertAlmostEqual(report['predicted_final']['x'], .1)
        self.assertFalse(report['passed'])

    def test_bad_time_order_and_nonfinite_truth_are_input_errors(self):
        for rows in ([[0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]],
                     [[100, 0, 0, 0, 0, 0, 0], [50, 0, 0, 0, 0, 0, 0]],
                     [[0, 0, 0, 0, 0, 0, 0], [100, 'nan', 0, 0, 0, 0, 0]],
                     []):
            with self.subTest(rows=rows):
                result = self.run_replay(rows)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('Input error:', result.stderr)


if __name__ == '__main__':
    unittest.main()
