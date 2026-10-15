"""Offline A* contract tests; run with Python 3.10+ and no extra packages."""

from collections import deque
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ASSETS = Path(__file__).resolve().parent
REFERENCE = ASSETS / "astar_reference.py"


def independent_distance(grid, start, goal):
    """BFS oracle: no A* helpers, priority queue, or heuristic are reused."""
    queue = deque([(tuple(start), 0)])
    visited = {tuple(start)}
    while queue:
        (x, y), distance = queue.popleft()
        if (x, y) == tuple(goal):
            return distance
        for nx, ny in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if (0 <= ny < len(grid) and 0 <= nx < len(grid[0])
                    and grid[ny][nx] == 0 and (nx, ny) not in visited):
                visited.add((nx, ny))
                queue.append(((nx, ny), distance + 1))
    return None


class AstarWorkshopTests(unittest.TestCase):
    def reference(self):
        # Before implementation this reports a deliberate assertion failure,
        # rather than an accidental import error.
        self.assertTrue(REFERENCE.exists(), "reference plan/CLI not implemented yet")
        spec = spec_from_file_location("astar_reference_under_test", REFERENCE)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(REFERENCE), *map(str, arguments)],
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )

    def assert_path(self, result, grid, start, goal, cost):
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cost"], cost)
        points = [tuple(point) for point in result["path"]]
        self.assertEqual(points[0], tuple(start))
        self.assertEqual(points[-1], tuple(goal))
        self.assertEqual(len(points) - 1, cost)
        for x, y in points:
            self.assertTrue(0 <= y < len(grid) and 0 <= x < len(grid[0]))
            self.assertEqual(grid[y][x], 0)
        for (x, y), (nx, ny) in zip(points, points[1:]):
            self.assertEqual(abs(x - nx) + abs(y - ny), 1)
        self.assertIs(type(result["expanded"]), int)
        self.assertGreaterEqual(result["expanded"], 1)

    # Bugs caught: crossing a wall, wrong [row][column] convention, bad backtrace.
    def test_detour_has_legal_six_step_path_in_row_down_grid(self):
        grid = [[0, 1, 0], [0, 1, 0], [0, 0, 0]]
        self.assert_path(self.reference().plan(grid, [0, 0], [2, 0]),
                         grid, [0, 0], [2, 0], 6)

    # Bug caught: an unreachable goal returns an invented path or loops forever.
    def test_no_path_is_normal_result_with_no_cost(self):
        result = self.reference().plan([[0, 1, 0], [0, 1, 0]], [0, 0], [2, 0])
        self.assertEqual(result["status"], "no_path")
        self.assertEqual(result["path"], [])
        self.assertIsNone(result["cost"])
        self.assertEqual(result["expanded"], 2)

    # Bugs caught: negative indices wrap, blocked endpoints are accepted,
    # empty/ragged/non-binary grids or non-integer points are silently used.
    def test_bad_inputs_are_invalid_before_search(self):
        planner = self.reference().plan
        bad = [
            ([], [0, 0], [0, 0]),
            ([[]], [0, 0], [0, 0]),
            ([[0], [0, 0]], [0, 0], [0, 1]),
            ([[0, -1]], [0, 0], [1, 0]),
            ([[0, 0]], [-1, 0], [1, 0]),
            ([[0, 0]], [0, 0], [2, 0]),
            ([[1, 0]], [0, 0], [1, 0]),
            ([[0, 1]], [0, 0], [1, 0]),
            ([[1]], [0, 0], [0, 0]),
            ([[0]], [0.0, 0], [0, 0]),
            ([[0]], [True, 0], [0, 0]),
        ]
        for grid, start, goal in bad:
            with self.subTest(grid=grid, start=start, goal=goal):
                self.assertEqual(planner(grid, start, goal), {
                    "status": "invalid", "path": [], "cost": None, "expanded": 0,
                })

    # Bug caught: start == goal gets an empty path or extra step.
    def test_same_free_endpoint_is_one_point_zero_cost(self):
        self.assertEqual(self.reference().plan([[0]], [0, 0], [0, 0]), {
            "status": "ok", "path": [[0, 0]], "cost": 0, "expanded": 1,
        })

    # Bug caught: x/y confusion or diagonal shortcuts in a narrow route.
    def test_narrow_channel_is_sixteen_steps(self):
        grid = [[0, 0, 0, 0, 0], [1, 1, 1, 1, 0], [0, 0, 0, 0, 0],
                [0, 1, 1, 1, 1], [0, 0, 0, 0, 0]]
        self.assert_path(self.reference().plan(grid, [0, 0], [4, 4]),
                         grid, [0, 0], [4, 4], 16)

    # Bug caught: changed g-update/termination loses optimality in some layout.
    def test_all_small_obstacle_layouts_match_independent_bfs(self):
        planner = self.reference().plan
        interior = [(x, y) for y in range(3) for x in range(3)
                    if (x, y) not in ((0, 0), (2, 2))]
        for mask in range(128):
            grid = [[0] * 3 for _ in range(3)]
            for bit, (x, y) in enumerate(interior):
                grid[y][x] = (mask >> bit) & 1
            expected = independent_distance(grid, [0, 0], [2, 2])
            result = planner(grid, [0, 0], [2, 2])
            with self.subTest(mask=mask):
                if expected is None:
                    self.assertEqual(result["status"], "no_path")
                    self.assertEqual(result["path"], [])
                    self.assertIsNone(result["cost"])
                else:
                    self.assert_path(result, grid, [0, 0], [2, 2], expected)
                self.assertLessEqual(result["expanded"], 9)

    # Bugs caught: input mutation makes successive planning calls depend on order.
    def test_repeatable_planning_preserves_input(self):
        planner = self.reference().plan
        grid = [[0, 0, 0], [0, 1, 0]]
        before = [row[:] for row in grid]
        first = planner(grid, [0, 0], [2, 1])
        self.assertEqual(planner(grid, [0, 0], [2, 1]), first)
        self.assertEqual(grid, before)

    # Bug caught: provided cases and their literal expected answers disagree.
    def test_fixed_case_file_matches_literal_contract(self):
        reference = self.reference()
        cases = json.loads((ASSETS / "astar_cases.json").read_text(encoding="utf-8"))["cases"]
        self.assertTrue({"detour", "no_path", "out_of_bounds", "occupied", "same", "narrow"}
                        <= {case["name"] for case in cases})
        for case in cases:
            with self.subTest(case=case["name"]):
                result = reference.plan(case["grid"], case["start"], case["goal"])
                self.assertEqual(result["status"], case["expected_status"])
                self.assertEqual(result["cost"], case["expected_cost"])

    # Bugs caught: CLI crashes, fails to emit reusable JSON, or hides input errors.
    def test_cli_case_and_all_have_clear_exit_codes(self):
        run = self.cli("--case", "detour")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["cost"], 6)
        self.assertEqual(self.cli("--case", "no_path").returncode, 0)
        invalid = self.cli("--case", "empty")
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(json.loads(invalid.stdout)["status"], "invalid")
        self.assertEqual(self.cli("--case", "not_a_case").returncode, 2)
        all_cases = self.cli("--all")
        self.assertEqual(all_cases.returncode, 0, all_cases.stderr)
        self.assertTrue(json.loads(all_cases.stdout)["passed"])

    # Bug caught: checker compares only status/cost and accepts teleportation.
    def test_checker_rejects_wrong_path_even_with_optimal_claimed_cost(self):
        self.reference()
        with tempfile.TemporaryDirectory() as directory:
            student = Path(directory) / "bad_path.py"
            student.write_text(
                "def plan(grid, start, goal):\n"
                "    return dict(status='ok', path=[start, goal], cost=6, expanded=1)\n",
                encoding="utf-8",
            )
            run = self.cli("--check", student)
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            self.assertFalse(json.loads(run.stdout)["passed"])

    # Bug caught: checker accepts a real valid route with falsified cost.
    def test_checker_rejects_wrong_cost_on_correct_path(self):
        self.reference()
        with tempfile.TemporaryDirectory() as directory:
            student = Path(directory) / "bad_cost.py"
            student.write_text(
                "def plan(grid, start, goal):\n"
                "    return dict(status='ok', path=[[0,0],[0,1],[0,2],"
                "[1,2],[2,2],[2,1],[2,0]], cost=5, expanded=7)\n",
                encoding="utf-8",
            )
            run = self.cli("--check", student)
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            self.assertFalse(json.loads(run.stdout)["passed"])

    # Bug caught: TODO starter is mistaken for a completed student or reference.
    def test_unfinished_starter_exits_nonzero_and_checker_reports_failure(self):
        self.reference()
        run = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(ASSETS / "astar_starter.py")],
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(run.returncode, 1)
        self.assertIn("TODO", run.stderr)
        checked = self.cli("--check", ASSETS / "astar_starter.py")
        self.assertEqual(checked.returncode, 1)
        self.assertFalse(json.loads(checked.stdout)["passed"])

    # Bug caught: loader/checker cannot accept a conforming module path.
    def test_checker_accepts_reference_and_rejects_missing_student(self):
        self.reference()
        checked = self.cli("--check", REFERENCE)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        report = json.loads(checked.stdout)
        self.assertTrue(report["passed"])
        self.assertEqual(report["small_maps"], 128)
        self.assertEqual(self.cli("--check", ASSETS / "absent_student.py").returncode, 2)

    # Bug caught: an unreachable result invents more unique expansions than cells.
    def test_checker_rejects_impossible_no_path_expansion_count(self):
        case = dict(grid=[[0, 1, 0], [0, 1, 0]], start=[0, 0], goal=[2, 0],
                    expected_status="no_path", expected_cost=None)
        result = dict(status="no_path", path=[], cost=None, expanded=99)
        with self.assertRaises(ValueError):
            self.reference().check_result(result, case)


if __name__ == "__main__":
    unittest.main()
