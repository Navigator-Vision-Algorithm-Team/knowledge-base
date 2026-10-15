"""Teaching A*: Python 3.10+, standard library, no ROS or robot connection."""

import argparse
from collections import deque
from copy import deepcopy
import heapq
from importlib.util import module_from_spec, spec_from_file_location
from itertools import count
import json
from pathlib import Path
import sys


def valid_input(grid, start, goal):
    """Accept only nonempty rectangular binary grids and free integer endpoints."""
    if not isinstance(grid, (list, tuple)) or not grid:
        return False
    if not all(isinstance(row, (list, tuple)) and row for row in grid):
        return False
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        return False
    if any(type(cell) is not int or cell not in (0, 1) for row in grid for cell in row):
        return False
    for point in (start, goal):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return False
        if any(type(value) is not int for value in point):
            return False
        x, y = point
        if not (0 <= x < width and 0 <= y < len(grid)) or grid[y][x] != 0:
            return False
    return True


def heuristic(node, goal):
    """Manhattan lower bound in the same units as four-neighbor unit cost."""
    return abs(node[0] - goal[0]) + abs(node[1] - goal[1])


def reconstruct_path(parent, goal):
    path = [goal]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    return [list(point) for point in reversed(path)]


def plan(grid, start, goal):
    """Return status/path/cost/expanded; coordinates are (x, y), y runs down.

    expanded counts unique cells processed, including the goal. Invalid input
    is rejected before search; no_path is a valid completed search result.
    """
    if not valid_input(grid, start, goal):
        return dict(status="invalid", path=[], cost=None, expanded=0)
    start, goal = tuple(start), tuple(goal)
    order = count()
    frontier = [(heuristic(start, goal), 0, next(order), start)]
    g_score = {start: 0}
    parent = {}
    closed = set()
    while frontier:
        _, g, _, current = heapq.heappop(frontier)
        if current in closed or g != g_score[current]:
            continue  # Older heap entries are not new expansions.
        closed.add(current)
        if current == goal:
            return dict(status="ok", path=reconstruct_path(parent, goal),
                        cost=g, expanded=len(closed))
        x, y = current
        for neighbor in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            nx, ny = neighbor
            if not (0 <= nx < len(grid[0]) and 0 <= ny < len(grid)):
                continue
            if grid[ny][nx] == 1 or neighbor in closed:
                continue
            candidate = g + 1
            if candidate < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = candidate
                parent[neighbor] = current
                heapq.heappush(frontier, (candidate + heuristic(neighbor, goal),
                                         candidate, next(order), neighbor))
    return dict(status="no_path", path=[], cost=None, expanded=len(closed))


def bfs_cost(grid, start, goal):
    """Independent shortest distance for checker; it never calls A* helpers."""
    queue = deque([(tuple(start), 0)])
    seen = {tuple(start)}
    while queue:
        (x, y), distance = queue.popleft()
        if (x, y) == tuple(goal):
            return distance
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if (0 <= nx < len(grid[0]) and 0 <= ny < len(grid)
                    and grid[ny][nx] == 0 and (nx, ny) not in seen):
                seen.add((nx, ny))
                queue.append(((nx, ny), distance + 1))
    return None


def small_cases():
    """All 128 obstacle masks for 3x3, with opposite corner endpoints free."""
    cells = [(x, y) for y in range(3) for x in range(3)
             if (x, y) not in ((0, 0), (2, 2))]
    for mask in range(128):
        grid = [[0] * 3 for _ in range(3)]
        for bit, (x, y) in enumerate(cells):
            grid[y][x] = (mask >> bit) & 1
        cost = bfs_cost(grid, [0, 0], [2, 2])
        yield dict(name=f"small_{mask:03d}", grid=grid, start=[0, 0], goal=[2, 2],
                   expected_status="ok" if cost is not None else "no_path",
                   expected_cost=cost)


def check_result(result, case):
    """Validate actual path geometry, endpoints and optimal cost, not its picture."""
    if not isinstance(result, dict):
        raise ValueError("plan must return a dict")
    if not {"status", "path", "cost", "expanded"} <= result.keys():
        raise ValueError("missing status/path/cost/expanded")
    if result["status"] != case["expected_status"]:
        raise ValueError(f"expected status {case['expected_status']}, got {result['status']}")
    expanded = result["expanded"]
    if type(expanded) is not int or expanded < 0:
        raise ValueError("expanded must be a nonnegative integer")
    if result["status"] != "ok":
        if result["path"] != [] or result["cost"] is not None:
            raise ValueError("invalid/no_path requires path=[] and cost=None")
        if result["status"] == "invalid" and expanded != 0:
            raise ValueError("invalid input must not enter search")
        if result["status"] == "no_path":
            free_cells = sum(cell == 0 for row in case["grid"] for cell in row)
            if not 1 <= expanded <= free_cells:
                raise ValueError("no_path expanded must count unique processed free cells")
        return
    path = result["path"]
    if not isinstance(path, (list, tuple)) or not path:
        raise ValueError("ok requires a nonempty ordered path")
    points = []
    for point in path:
        if (not isinstance(point, (list, tuple)) or len(point) != 2
                or any(type(value) is not int for value in point)):
            raise ValueError("path coordinates must be integer (x,y) pairs")
        x, y = point
        grid = case["grid"]
        if not (0 <= x < len(grid[0]) and 0 <= y < len(grid)) or grid[y][x] != 0:
            raise ValueError("path leaves the grid or crosses an occupied cell")
        points.append(tuple(point))
    if points[0] != tuple(case["start"]) or points[-1] != tuple(case["goal"]):
        raise ValueError("path endpoints do not match start and goal")
    if any(abs(x - nx) + abs(y - ny) != 1
           for (x, y), (nx, ny) in zip(points, points[1:])):
        raise ValueError("each path step must be one four-neighbor move")
    if type(result["cost"]) is not int or result["cost"] != len(points) - 1:
        raise ValueError("cost must equal the number of unit-cost path steps")
    if result["cost"] != case["expected_cost"]:
        raise ValueError(f"nonoptimal cost: expected {case['expected_cost']}, got {result['cost']}")
    free_cells = sum(cell == 0 for row in case["grid"] for cell in row)
    if not (1 <= expanded <= free_cells):
        raise ValueError("expanded must count unique processed free cells, including goal")


def check_planner(planner, fixed):
    report = dict(passed=True, fixed_cases=len(fixed), small_maps=128, failures=[])
    for case in [*fixed, *small_cases()]:
        try:
            grid = deepcopy(case["grid"])
            result = planner(grid, case["start"][:], case["goal"][:])
            check_result(result, case)
            if grid != case["grid"]:
                raise ValueError("plan changed its input grid")
        except Exception as error:
            report["failures"].append(dict(case=case["name"],
                                           error=f"{type(error).__name__}: {error}"))
    report["passed"] = not report["failures"]
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--case", help="run one fixed case (default: detour)")
    choice.add_argument("--all", action="store_true", help="check the reference on all inputs")
    choice.add_argument("--check", type=Path, metavar="STUDENT.py", help="check a module's plan function")
    args = parser.parse_args(argv)
    fixed = json.loads(Path(__file__).with_name("astar_cases.json").read_text(encoding="utf-8"))["cases"]
    if args.check is not None:
        try:
            student_path = args.check.resolve()
            if not student_path.is_file() or student_path.suffix != ".py":
                raise ValueError("--check requires an existing .py file")
            # Prevent import from writing __pycache__ next to the student's file.
            sys.dont_write_bytecode = True
            spec = spec_from_file_location("astar_student", student_path)
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            if not callable(getattr(module, "plan", None)):
                raise ValueError("student module must expose plan(grid,start,goal)")
        except Exception as error:
            print(f"input error: {type(error).__name__}: {error}", file=sys.stderr)
            return 2
        report = check_planner(module.plan, fixed)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["passed"] else 1
    if args.all:
        report = check_planner(plan, fixed)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["passed"] else 1
    name = args.case or "detour"
    case = next((case for case in fixed if case["name"] == name), None)
    if case is None:
        parser.error(f"unknown case {name!r}; choose: {', '.join(case['name'] for case in fixed)}")
    result = plan(case["grid"], case["start"], case["goal"])
    print(json.dumps(dict(case=name, **result), ensure_ascii=False, indent=2))
    return 2 if result["status"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
