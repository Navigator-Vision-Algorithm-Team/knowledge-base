"""A* student scaffold: fill heuristic, search, reconstruct_path; stdlib only.

grid[y][x], top-left (0,0), y increases down; 0 free / 1 blocked.
Keep the public plan(grid,start,goal) API when moving to your own repository.
"""

import heapq
from itertools import count
import json
import sys


def valid_input(grid, start, goal):
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
    """TODO 1: Manhattan lower bound; return an integer number of steps."""
    raise NotImplementedError("TODO 1: implement heuristic(node, goal)")


def reconstruct_path(parent, goal):
    """TODO 3: follow parent from goal, reverse, return [[x,y], ...]."""
    raise NotImplementedError("TODO 3: implement reconstruct_path(parent, goal)")


def search(grid, start, goal):
    """TODO 2: finish the A* loop; return status/path/cost/expanded."""
    order = count()
    frontier = [(heuristic(start, goal), 0, next(order), start)]
    g_score = {start: 0}
    parent = {}
    closed = set()
    # Heap entries: (f, g, insertion_order, (x,y)). Pop the lowest first.
    # Skip old entries; count only distinct cells actually processed.
    # Stop when the goal is popped, then call reconstruct_path(parent, goal).
    # Neighbors: (x+1,y), (x,y+1), (x-1,y), (x,y-1).
    # Each legal move has candidate_g = g + 1. Update parent/g_score only
    # if this candidate is cheaper; push candidate_g + heuristic into heap.
    # When frontier empties, return no_path, [], None, len(closed).
    raise NotImplementedError("TODO 2: implement the search loop")


def plan(grid, start, goal):
    if not valid_input(grid, start, goal):
        return dict(status="invalid", path=[], cost=None, expanded=0)
    return search(grid, tuple(start), tuple(goal))


if __name__ == "__main__":
    try:
        # Small detour from the worksheet: the correct cost is six steps.
        result = plan([[0, 1, 0], [0, 1, 0], [0, 0, 0]], [0, 0], [2, 0])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except NotImplementedError as error:
        print(f"unfinished: {error}", file=sys.stderr)
        raise SystemExit(1)
