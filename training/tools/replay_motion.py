"""Recompute CSV commands with the ideal model, then compare to analytic truth."""
import argparse
import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros2_ws/src/nav_training'))
from nav_training.core import Pose2D, TimedModel, Twist2D


def compare(path: Path) -> dict:
    with path.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 2:
        raise ValueError('At least two timestamped rows are required')
    model = None
    first_ns = previous_ns = None
    max_position = max_yaw = 0.0
    for number, row in enumerate(rows, start=2):
        stamp_ns = int(row['stamp_ns'])
        truth = Pose2D(*(float(row[k]) for k in ('x_m', 'y_m', 'yaw_rad')))
        command = Twist2D(*(float(row[k]) for k in ('vx_m_s', 'vy_m_s', 'wz_rad_s')))
        if not all(math.isfinite(v) for v in (*asdict(truth).values(), *asdict(command).values())):
            raise ValueError(f'Nonfinite motion value on CSV row {number}')
        if previous_ns is not None and stamp_ns <= previous_ns:
            raise ValueError(f'Timestamps must strictly increase; CSV row {number}')
        if model is None:
            first_ns = stamp_ns
            model = TimedModel(pose=truth)
        # Subtract integer epoch before conversion, retaining subsecond precision.
        elapsed = (stamp_ns - first_ns) / 1_000_000_000
        model.set_command(command, elapsed)
        predicted = model.pose
        max_position = max(max_position, math.hypot(predicted.x-truth.x, predicted.y-truth.y))
        error = predicted.yaw-truth.yaw
        max_yaw = max(max_yaw, abs(math.atan2(math.sin(error), math.cos(error))))
        previous_ns = stamp_ns
    return {'provenance': 'ideal_model_recomputed_from_commands', 'samples': len(rows),
            'timeout_s': model.timeout, 'duration_s': elapsed,
            'predicted_final': asdict(model.pose),
            'max_position_error_m': max_position, 'max_yaw_error_rad': max_yaw,
            'passed': max_position < 1e-8 and max_yaw < 1e-8}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path, help='ground_truth.csv from synthetic-v1')
    args = parser.parse_args()
    try:
        report = compare(args.csv)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f'Input error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
