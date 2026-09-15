"""Create small, analytic teaching assets; never overwrite an existing output."""
from __future__ import annotations

import argparse
import csv
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys

import numpy as np
from rosbags.interfaces import (
    Qos, QosDurability, QosHistory, QosLiveliness, QosReliability, QosTime,
)
from rosbags.rosbag2 import Writer
from rosbags.typesys import Stores, get_typestore


START_NS = 100_000_000_000
STEP_NS = 100_000_000
SAMPLES = 51
DURATION_S = 5.0
SCENARIOS = {
    "stationary": (0.0, 0.0, 0.0),
    "forward": (0.2, 0.0, 0.0),
    "lateral": (0.0, 0.1, 0.0),
    "rotation": (0.0, 0.0, 0.2),
}
TOPICS = {
    "/nav_training/cmd_vel": ("geometry_msgs/msg/Twist", SAMPLES),
    "/nav_training/odom": ("nav_msgs/msg/Odometry", SAMPLES),
    "/nav_training/tf": ("tf2_msgs/msg/TFMessage", SAMPLES),
    "/nav_training/tf_static": ("tf2_msgs/msg/TFMessage", 1),
}
CSV_FIELDS = ("stamp_ns", "elapsed_s", "x_m", "y_m", "yaw_rad", "vx_m_s", "vy_m_s", "wz_rad_s")


def write_text(path: Path, text: str) -> None:
    # Explicit LF avoids platform-dependent CSV/JSON/map bytes.
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def samples(command: tuple[float, float, float]) -> list[dict]:
    """Direct closed-form truth, independent of the training motion integrator."""
    vx, vy, wz = command
    rows = []
    for index in range(SAMPLES):
        elapsed = index / 10
        # Each fixture uses translation OR rotation, starting from zero pose.
        active = command if index < SAMPLES - 1 else (0.0, 0.0, 0.0)
        rows.append(dict(zip(CSV_FIELDS, (
            START_NS + index * STEP_NS, elapsed,
            vx * elapsed, vy * elapsed, wz * elapsed, *active,
        ))))
    return rows


def qos(static: bool = False, depth: int = 10) -> Qos:
    return Qos(
        history=QosHistory.KEEP_LAST, depth=1 if static else depth,
        reliability=QosReliability.RELIABLE,
        durability=QosDurability.TRANSIENT_LOCAL if static else QosDurability.VOLATILE,
        deadline=QosTime(0, 0), lifespan=QosTime(0, 0),
        liveliness=QosLiveliness.AUTOMATIC, liveliness_lease_duration=QosTime(0, 0),
        avoid_ros_namespace_conventions=False,
    )


def write_scenario(directory: Path, rows: list[dict], store) -> None:
    directory.mkdir()
    with (directory / "ground_truth.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value if key == "stamp_ns" else f"{value:.10f}" for key, value in row.items()})

    def message(name: str, *args):
        return store.types[name](*args)

    def vector(x: float = 0.0, y: float = 0.0, z: float = 0.0):
        return message("geometry_msgs/msg/Vector3", x, y, z)

    def orientation(yaw: float):
        return message("geometry_msgs/msg/Quaternion", 0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2))

    def header(stamp_ns: int, frame: str):
        sec, nanosec = divmod(stamp_ns, 1_000_000_000)
        return message("std_msgs/msg/Header", message("builtin_interfaces/msg/Time", sec, nanosec), frame)

    def transform(stamp_ns: int, parent: str, child: str, translation, rotation):
        stamped = message("geometry_msgs/msg/TransformStamped", header(stamp_ns, parent), child,
                          message("geometry_msgs/msg/Transform", translation, rotation))
        return message("tf2_msgs/msg/TFMessage", [stamped])

    # Humble metadata_io reads offered_qos_profiles as a YAML string (v8).
    # Do not switch to v9's sequence encoding without a Humble runtime check.
    with Writer(directory / "bag", version=8) as bag:
        connections = {
            topic: bag.add_connection(topic, msgtype, typestore=store,
                                      offered_qos_profiles=[qos(topic.endswith("tf_static"), 100 if topic.endswith("/tf") else 10)])
            for topic, (msgtype, _) in TOPICS.items()
        }

        def emit(topic: str, stamp_ns: int, value) -> None:
            bag.write(connections[topic], stamp_ns, store.serialize_cdr(value, TOPICS[topic][0]))

        emit("/nav_training/tf_static", START_NS,
             transform(START_NS, "training_base", "training_lidar", vector(0.2, 0.0, 0.1), orientation(0.0)))
        for row in rows:
            stamp_ns = row["stamp_ns"]
            rotation = orientation(row["yaw_rad"])
            command = message("geometry_msgs/msg/Twist", vector(row["vx_m_s"], row["vy_m_s"]), vector(z=row["wz_rad_s"]))
            position = message("geometry_msgs/msg/Point", row["x_m"], row["y_m"], 0.0)
            pose = message("geometry_msgs/msg/Pose", position, rotation)
            odom = message("nav_msgs/msg/Odometry", header(stamp_ns, "training_odom"), "training_base",
                           message("geometry_msgs/msg/PoseWithCovariance", pose, np.zeros(36, dtype=np.float64)),
                           message("geometry_msgs/msg/TwistWithCovariance", command, np.zeros(36, dtype=np.float64)))
            emit("/nav_training/cmd_vel", stamp_ns, command)
            emit("/nav_training/odom", stamp_ns, odom)
            emit("/nav_training/tf", stamp_ns,
                 transform(stamp_ns, "training_odom", "training_base", vector(row["x_m"], row["y_m"]), rotation))
    # rosbags uses native platform newlines for this external metadata file.
    metadata = directory / "bag" / "metadata.yaml"
    write_text(metadata, "\n".join(line.rstrip() for line in metadata.read_text(encoding="utf-8").splitlines()) + "\n")


def write_map(directory: Path) -> None:
    directory.mkdir()
    width, height, resolution = 20, 16, 0.25
    pixels = [[0 if col in (0, width - 1) or row in (0, height - 1)
               or (col == 14 and 4 <= row <= 10) else 254
               for col in range(width)] for row in range(height)]
    write_text(directory / "teaching_map.pgm", "P2\n# Synthetic occupancy grid; first image row is north.\n20 16\n255\n" +
               "\n".join(" ".join(map(str, row)) for row in pixels) + "\n")
    write_text(directory / "teaching_map.yaml", "image: teaching_map.pgm\nmode: trinary\nresolution: 0.25\norigin: [-1.0, -1.0, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")
    points = [(-1.0 + (col + 0.5) * resolution, -1.0 + (height - 1 - row + 0.5) * resolution, 0.0)
              for row in range(height) for col in range(width) if pixels[row][col] == 0]
    write_text(directory / "teaching_map.pcd", (
        "# Synthetic occupied-cell centers, frame training_odom, meters.\n"
        "VERSION .7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n"
        f"WIDTH {len(points)}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS {len(points)}\nDATA ascii\n" +
        "".join(f"{x:.3f} {y:.3f} {z:.3f}\n" for x, y, z in points)))


def write_time_anomalies(directory: Path) -> None:
    directory.mkdir()
    timestamps = (100_000_000_000, 100_100_000_000, 100_100_000_000,
                  100_050_000_000, 100_450_000_000, 100_550_000_000)
    write_text(directory / "timestamps.csv", "row_index,stamp_ns\n" +
               "".join(f"{index},{stamp}\n" for index, stamp in enumerate(timestamps)))
    write_json(directory / "expected.json", {
        "row_index_base": 0, "nominal_step_ns": STEP_NS, "gap_rule": "delta_ns > 200000000",
        "events": [{"row_index": 2, "kind": "duplicate"}, {"row_index": 3, "kind": "rollback"},
                   {"row_index": 4, "kind": "gap"}],
        "scope": "CSV arrival-order exercise only; never silently sort these timestamps.",
    })


def generate(output: Path) -> dict:
    if version("rosbags") != "0.10.11":
        raise ValueError("Use training/requirements-data.txt: this format is verified with rosbags 0.10.11")
    # mkdir is exclusive, including pre-existing empty directories and symlinks.
    # On an interrupted generation the partial directory is kept for inspection.
    output.mkdir(parents=True, exist_ok=False)
    store = get_typestore(Stores.ROS2_HUMBLE)
    for name, command in SCENARIOS.items():
        write_scenario(output / name, samples(command), store)
    write_map(output / "map")
    write_time_anomalies(output / "time_anomalies")
    files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file():
            raw = path.read_bytes()
            files[path.relative_to(output).as_posix()] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    manifest = {
        "dataset_id": "synthetic-v1", "format_version": 1,
        "generator": {"path": "training/tools/generate_data.py", "rosbags_version": "0.10.11",
                      "typestore": "ROS2_HUMBLE", "bag_metadata_version": 8, "storage": "sqlite3", "serialization": "cdr"},
        "provenance": {
            "kind": "synthetic_analytic", "valid_pointlio_input": False,
            "source": "Closed-form motion from zero pose plus hand-constructed occupancy grid; no external recording.",
            "source_baseline": "Navigation-2027@183a4109b0de2030bb8970a54654937c8b039ba9 (teaching context only)",
            "sensor_noise": False, "imu": False, "raw_lidar": False,
            "limitations": "Ideal holonomic motion, no slip, latency, noise, obstacles or estimation. Covariances are zero synthetic placeholders; never fusion tuning evidence.",
        },
        "time": {"start_ns": START_NS, "step_ns": STEP_NS, "samples": SAMPLES, "duration_s": DURATION_S,
                 "epoch": "arbitrary simulation epoch, not UTC wall time", "final_sample": "zero command at elapsed=5 s"},
        "units": {"stamp_ns": "nanoseconds", "elapsed_s": "seconds", "position": "meters", "yaw": "radians",
                  "linear_velocity": "meters/second", "angular_velocity": "radians/second"},
        "frames": {"pose_parent": "training_odom", "body": "training_base", "lidar": "training_lidar",
                   "static_translation_m": [0.2, 0.0, 0.1], "static_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                   "axes": "right-handed, body +x forward, +y left, +z up; positive yaw counterclockwise"},
        "scenarios": {name: {"command_before_stop": dict(zip(("vx_m_s", "vy_m_s", "wz_rad_s"), command)),
                              "expected_final": dict(zip(("x_m", "y_m", "yaw_rad"), (v * DURATION_S for v in command))),
                              "samples": SAMPLES, "bag_messages": 154}
                      for name, command in SCENARIOS.items()},
        "topics": {name: {"type": value[0], "messages_per_bag": value[1],
                          "durability": "transient_local" if name.endswith("tf_static") else "volatile"}
                   for name, value in TOPICS.items()},
        "map": {"width_cells": 20, "height_cells": 16, "resolution_m": 0.25, "origin": [-1.0, -1.0, 0.0],
                "frame": "training_odom", "occupied_cells": 75, "pcd_points": 75,
                "pcd_meaning": "one point at each occupied cell center, z=0; no lidar scan or 3D environment"},
        "files": files,
    }
    write_json(output / "manifest.json", manifest)
    return {"dataset_id": manifest["dataset_id"], "scenarios": len(SCENARIOS), "bag_messages": 616,
            "hashed_assets": len(files), "asset_bytes": sum(item["bytes"] for item in files.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory; existing paths are rejected")
    args = parser.parse_args()
    try:
        result = generate(args.output.expanduser().absolute())
    except FileExistsError:
        print("Output already exists; choose a new directory. Existing data was not overwritten.", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Generation failed: {exc}. Any partial output is retained for inspection.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
