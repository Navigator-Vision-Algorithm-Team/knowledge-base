"""Behavior checks for the synthetic geometry, estimator, SVG and CLI contract."""
from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "make_comparison_figures.py"
INPUT = HERE / "comparison_inputs.json"


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        # Before implementation this gives an assertion failure, not an import error.
        self.assertTrue(SCRIPT.is_file(), "comparison generator has not been implemented")
        spec = importlib.util.spec_from_file_location("comparison_figures", SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.inputs = json.loads(INPUT.read_text(encoding="utf-8"))

    def test_five_degree_rotation_preserves_range_and_has_known_error(self):
        point = self.module.transform_point((1.0, 0.0), (0.2, 0.0), 5.0)
        self.assertAlmostEqual(point[0], 1.1961946980917455, places=12)
        self.assertAlmostEqual(point[1], 0.08715574274765817, places=12)
        self.assertAlmostEqual(math.hypot(point[0] - 0.2, point[1]), 1.0, places=12)
        self.assertAlmostEqual(math.hypot(point[0] - 1.2, point[1]), 0.087238774730672, places=12)

    def test_image_row_is_flipped_before_map_cell_center(self):
        # Image (14,8), H=16 => grid row 7 => (-1+14.5*.25, -1+7.5*.25).
        self.assertEqual(self.module.map_cell_center(14, 8, 16, 0.25, (-1.0, -1.0, 0.0)), (2.625, 0.875))
        self.assertEqual(self.module.map_cell_center(14, 8, 16, 0.25, (-0.5, -1.0, 0.0)), (3.125, 0.875))
        rotated = self.module.map_cell_center(0, 0, 1, 1.0, (0.0, 0.0, math.pi / 2))
        self.assertAlmostEqual(rotated[0], -0.5, places=12)
        self.assertAlmostEqual(rotated[1], 0.5, places=12)

    def test_kalman_one_step_matches_hand_calculation(self):
        # F=[[1,1],[0,1]], P0=I, Q=0, R=1 => K=[2/3,1/3].
        config = {"initial_velocity_m_s": 0.0, "initial_position_variance_m2": 1.0,
                  "initial_velocity_variance_m2_s2": 1.0, "measurement_variance_m2": 1.0,
                  "acceleration_variance_m2_s4": 0.0}
        result = self.module.kalman_velocity([0.0, 1.0], 1.0, config)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 1.0 / 3.0, places=12)

    def test_velocity_uses_metres_and_seconds_with_same_scoring_window(self):
        report = self.module.build_report(self.inputs)
        data = report["velocity"]
        self.assertEqual(len(data["times_s"]), 41)
        self.assertAlmostEqual(data["times_s"][-1], 4.0)
        self.assertAlmostEqual(data["measured_positions_m"][1], 0.014)
        self.assertAlmostEqual(data["difference_velocity_m_s"][0], 0.06)
        self.assertEqual(data["metrics"]["scored_samples"], 40)
        self.assertEqual(data["metrics"]["scoring_window"], "k=1..40; initialization k=0 excluded from both")
        self.assertLess(data["metrics"]["kalman_rmse_m_s"], data["metrics"]["difference_rmse_m_s"])

    def test_truth_is_not_an_input_to_kalman_estimator(self):
        data = self.module.build_report(self.inputs)["velocity"]
        estimated = self.module.kalman_velocity(data["measured_positions_m"], data["dt_s"], self.inputs["velocity"]["kalman"])
        self.assertEqual(estimated, data["kalman_velocity_m_s"])
        # A constant translated measurement must give the same velocity estimate.
        shifted = self.module.kalman_velocity([p + 10.0 for p in data["measured_positions_m"]], data["dt_s"], self.inputs["velocity"]["kalman"])
        for left, right in zip(estimated, shifted):
            self.assertAlmostEqual(left, right, places=11)

    def test_report_profiles_the_fixed_geometry_without_missing_values(self):
        report = self.module.build_report(self.inputs)
        self.assertEqual(report["profile"]["tf_point_count"], 10)
        self.assertEqual(report["profile"]["map_size_cells"], [20, 16])
        self.assertEqual(report["profile"]["occupied_cells"], 75)
        self.assertEqual(report["profile"]["position_samples"], 41)
        self.assertEqual(report["profile"]["missing_values"], 0)
        self.assertAlmostEqual(report["map"]["marked_displacement_m"], 0.5)
        self.assertAlmostEqual(report["tf"]["one_metre_point_error_m"], 0.087238774730672, places=12)

    def test_geometry_axes_keep_equal_scale_for_one_metre(self):
        svg = self.module.SVG("test")
        axes = self.module.Axes(svg, 80, 80, 300, 300, (0, 4, 0, 2), "x (m)", "y (m)", equal=True)
        origin = axes.point(0, 0)
        along_x = axes.point(1, 0)
        along_y = axes.point(0, 1)
        self.assertAlmostEqual(along_x[0] - origin[0], origin[1] - along_y[1])

    def test_edited_inputs_do_not_leave_default_numbers_in_figure_labels(self):
        edited = copy.deepcopy(self.inputs)
        edited["tf"]["yaw_error_deg"] = 10.0
        edited["map"]["origin_shift_m"] = [1.0, 0.0]
        edited["velocity"]["true_velocity_m_s"] = 0.4
        edited["velocity"]["dt_s"] = 0.2
        edited["velocity"]["position_noise_m"] = edited["velocity"]["position_noise_m"][:21]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "figures"
            self.module.generate(edited, out)
            def labels(name):
                return " ".join(ET.parse(out / name).getroot().itertext())
            self.assertIn("10 deg = 0.174533 rad", labels("tf-yaw-comparison.svg"))
            self.assertIn("shift = 1.00 m", labels("map-origin-comparison.svg"))
            self.assertIn("Truth (0.4 m/s)", labels("velocity-noise-comparison.svg"))
            self.assertIn("k = 1..20", labels("velocity-noise-comparison.svg"))

    def test_invalid_inputs_are_rejected_before_writing_outputs(self):
        mutations = [
            ("nonfinite", lambda p: p["tf"].update(yaw_error_deg=float("nan"))),
            ("zero dt", lambda p: p["velocity"].update(dt_s=0)),
            ("short sequence", lambda p: p["velocity"].update(position_noise_m=[0.0])),
            ("negative R", lambda p: p["velocity"]["kalman"].update(measurement_variance_m2=-1)),
            ("ragged map", lambda p: p["map"]["rows_north_first"].__setitem__(1, "10")),
            ("bad occupancy", lambda p: p["map"]["rows_north_first"].__setitem__(1, "x" * 20)),
            ("bad cell", lambda p: p["map"].update(marked_image_cell=[20, 8])),
            ("zero resolution", lambda p: p["map"].update(resolution_m=0)),
            ("boolean number", lambda p: p["velocity"].update(dt_s=True)),
            ("not synthetic", lambda p: p.update(synthetic=False)),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                bad = copy.deepcopy(self.inputs)
                mutate(bad)
                output = Path(temp) / "output"
                with self.assertRaises(ValueError):
                    self.module.generate(bad, output)
                self.assertFalse(output.exists())

    def test_generated_outputs_are_finite_parseable_and_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_out, second_out = Path(first) / "figures", Path(second) / "figures"
            report = self.module.generate(self.inputs, first_out)
            self.module.generate(self.inputs, second_out)
            names = {"tf-yaw-comparison.svg", "map-origin-comparison.svg", "velocity-noise-comparison.svg", "comparison_report.json"}
            self.assertEqual({p.name for p in first_out.iterdir()}, names)
            for name in names:
                self.assertEqual((first_out / name).read_bytes(), (second_out / name).read_bytes())
                if name.endswith(".svg"):
                    root = ET.parse(first_out / name).getroot()
                    self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                    text = " ".join(root.itertext())
                    self.assertIn("Synthetic", text)
                    self.assertIn("(m", text)
                    self.assertTrue(root.findall(".//{http://www.w3.org/2000/svg}polyline") or root.findall(".//{http://www.w3.org/2000/svg}polygon"))
            decoded = json.loads((first_out / "comparison_report.json").read_text(encoding="utf-8"))
            self.assertEqual(decoded, report)
            def check_finite(value):
                if isinstance(value, dict):
                    for child in value.values():
                        check_finite(child)
                elif isinstance(value, list):
                    for child in value:
                        check_finite(child)
                elif isinstance(value, float):
                    self.assertTrue(math.isfinite(value))
            check_finite(report)

    def test_cli_accepts_an_independent_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "my-figures"
            run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--input", str(INPUT), "--output-dir", str(out)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue((out / "comparison_report.json").is_file())
            self.assertIn("Synthetic", run.stdout)

    def test_existing_directory_is_rejected_without_changing_any_bytes(self):
        for empty in (True, False):
            with self.subTest(empty=empty), tempfile.TemporaryDirectory() as temp:
                out = Path(temp) / "existing"
                out.mkdir()
                if not empty:
                    (out / "tf-yaw-comparison.svg").write_bytes(b"student notes: preserve me")
                before = {p.name: p.read_bytes() for p in out.iterdir()}
                with self.assertRaises(FileExistsError):
                    self.module.generate(self.inputs, out)
                self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, before)

    def test_cli_requires_explicit_output_directory(self):
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 2)
        self.assertIn("--output-dir", run.stderr)
        self.assertIn("required", run.stderr)

    def test_cli_rejects_existing_output_directory_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--output-dir", temp], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, 2)
            self.assertIn("error:", run.stderr)
            self.assertNotIn("Traceback", run.stderr)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_cli_bad_json_has_actionable_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "bad.json"
            bad.write_text("{", encoding="utf-8")
            run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--input", str(bad), "--output-dir", str(Path(temp) / "out")], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, 2)
            self.assertIn("error:", run.stderr)
            self.assertNotIn("Traceback", run.stderr)


if __name__ == "__main__":
    unittest.main()
