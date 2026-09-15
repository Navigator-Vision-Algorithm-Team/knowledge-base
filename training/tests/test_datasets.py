"""Black-box checks of the committed and regenerated synthetic teaching assets."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from rosbags.highlevel import AnyReader
from rosbags.interfaces import QosDurability
from rosbags.typesys import Stores, get_typestore
from ruamel.yaml import YAML


TRAINING = Path(__file__).resolve().parents[1]
GENERATOR = TRAINING / "tools" / "generate_data.py"
COMMITTED = TRAINING / "datasets" / "synthetic-v1"
SCENARIOS = ("stationary", "forward", "lateral", "rotation")
START_NS = 100_000_000_000
TOPICS = {
    "/nav_training/cmd_vel": ("geometry_msgs/msg/Twist", 51),
    "/nav_training/odom": ("nav_msgs/msg/Odometry", 51),
    "/nav_training/tf": ("tf2_msgs/msg/TFMessage", 51),
    "/nav_training/tf_static": ("tf2_msgs/msg/TFMessage", 1),
}


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="nav-training-data-test-")
        cls.output = Path(cls.temp.name) / "first"
        cls.result = subprocess.run(
            [sys.executable, "-X", "utf8", str(GENERATOR), "--output", str(cls.output)],
            capture_output=True, text=True, encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def dataset(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        return self.output

    def test_generator_creates_new_output_and_never_overwrites(self):
        output = self.dataset()
        sentinel = output / "student-notes.txt"
        sentinel.write_text("preserve me", encoding="utf-8")
        before = (output / "manifest.json").read_bytes()
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(GENERATOR), "--output", str(output)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me")
        self.assertEqual((output / "manifest.json").read_bytes(), before)
        sentinel.unlink()

    def test_analytic_trajectories_have_independent_expected_endpoints(self):
        output = self.dataset()
        endpoints = {
            "stationary": (0.0, 0.0, 0.0),
            "forward": (1.0, 0.0, 0.0),
            "lateral": (0.0, 0.5, 0.0),
            "rotation": (0.0, 0.0, 1.0),
        }
        for name, endpoint in endpoints.items():
            with self.subTest(name=name):
                with (output / name / "ground_truth.csv").open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(len(rows), 51)
                self.assertEqual([int(r["stamp_ns"]) for r in rows], list(range(START_NS, START_NS + 5_000_000_001, 100_000_000)))
                for column, expected in zip(("x_m", "y_m", "yaw_rad"), endpoint):
                    self.assertAlmostEqual(float(rows[-1][column]), expected, places=10)
                    self.assertAlmostEqual(float(rows[25][column]), expected / 2, places=10)
                for column in ("vx_m_s", "vy_m_s", "wz_rad_s"):
                    self.assertEqual(float(rows[-1][column]), 0.0)

    def test_map_pgm_pixels_and_pcd_cell_centers_share_yaml_geometry(self):
        mapdir = self.dataset() / "map"
        metadata = YAML(typ="safe").load((mapdir / "teaching_map.yaml").read_text())
        self.assertEqual(metadata["resolution"], 0.25)
        self.assertEqual(metadata["origin"], [-1.0, -1.0, 0.0])
        tokens = []
        for line in (mapdir / metadata["image"]).read_text().splitlines():
            tokens.extend(line.partition("#")[0].split())
        self.assertEqual(tokens[:4], ["P2", "20", "16", "255"])
        pixels = list(map(int, tokens[4:]))
        self.assertEqual(len(pixels), 320)
        self.assertEqual(set(pixels), {0, 254})
        lines = (mapdir / "teaching_map.pcd").read_text().splitlines()
        points = [tuple(map(float, line.split())) for line in lines[lines.index("DATA ascii") + 1:]]
        expected = set()
        for row in range(16):
            for col in range(20):
                if pixels[row * 20 + col] == 0:
                    expected.add((-1.0 + (col + 0.5) * 0.25, -1.0 + (15 - row + 0.5) * 0.25, 0.0))
        self.assertEqual(set(points), expected)
        self.assertEqual(len(points), len(expected))
        self.assertIn((-0.875, -0.875, 0.0), expected)
        self.assertIn((3.875, 2.875, 0.0), expected)
        self.assertNotIn((0.125, 0.125, 0.0), expected)

    def test_independent_reader_deserializes_counts_types_and_timing(self):
        output = self.dataset()
        for name in SCENARIOS:
            with self.subTest(name=name), AnyReader([output / name / "bag"], default_typestore=get_typestore(Stores.ROS2_HUMBLE)) as reader:
                self.assertEqual({c.topic: (c.msgtype, c.msgcount) for c in reader.connections}, TOPICS)
                seen = {topic: [] for topic in TOPICS}
                for connection, stamp, raw in reader.messages():
                    self.assertEqual(bytes(raw[:4]), b"\x00\x01\x00\x00")
                    message = reader.deserialize(raw, connection.msgtype)
                    seen[connection.topic].append((stamp, message))
                    header = getattr(message, "header", None)
                    if header is not None:
                        self.assertEqual(header.stamp.sec * 1_000_000_000 + header.stamp.nanosec, stamp)
                        self.assertEqual(header.frame_id, "training_odom")
                for topic, (_, count) in TOPICS.items():
                    self.assertEqual(len(seen[topic]), count)
                    self.assertEqual(seen[topic][0][0], START_NS)
                    if count > 1:
                        self.assertEqual([stamp for stamp, _ in seen[topic]], list(range(START_NS, START_NS + 5_000_000_001, 100_000_000)))
                expected_command = {
                    "stationary": (0.0, 0.0, 0.0), "forward": (0.2, 0.0, 0.0),
                    "lateral": (0.0, 0.1, 0.0), "rotation": (0.0, 0.0, 0.2),
                }[name]
                for index, (_, command) in enumerate(seen["/nav_training/cmd_vel"]):
                    self.assertEqual((command.linear.x, command.linear.y, command.angular.z),
                                     expected_command if index < 50 else (0.0, 0.0, 0.0))
                    self.assertEqual((command.linear.z, command.angular.x, command.angular.y), (0.0, 0.0, 0.0))
                last = seen["/nav_training/odom"][-1][1]
                self.assertEqual(last.child_frame_id, "training_base")
                self.assertAlmostEqual(last.pose.pose.position.x, 1.0 if name == "forward" else 0.0)
                self.assertAlmostEqual(last.pose.pose.position.y, 0.5 if name == "lateral" else 0.0)
                import math
                self.assertAlmostEqual(last.pose.pose.orientation.z, math.sin(0.5) if name == "rotation" else 0.0)
                self.assertAlmostEqual(last.pose.pose.orientation.w, math.cos(0.5) if name == "rotation" else 1.0)
                self.assertEqual(last.twist.twist.linear.x, 0.0)
                self.assertEqual(last.twist.twist.linear.y, 0.0)
                self.assertEqual(last.twist.twist.angular.z, 0.0)

    def test_tf_geometry_and_static_durability_are_preserved_in_bags(self):
        output = self.dataset()
        for name in SCENARIOS:
            with self.subTest(name=name), AnyReader([output / name / "bag"], default_typestore=get_typestore(Stores.ROS2_HUMBLE)) as reader:
                static_connection = next(c for c in reader.connections if c.topic == "/nav_training/tf_static")
                self.assertEqual(static_connection.ext.offered_qos_profiles[0].durability, QosDurability.TRANSIENT_LOCAL)
                for connection, stamp, raw in reader.messages():
                    if connection.topic not in ("/nav_training/tf", "/nav_training/tf_static"):
                        continue
                    transforms = reader.deserialize(raw, connection.msgtype).transforms
                    self.assertEqual(len(transforms), 1)
                    transform = transforms[0]
                    self.assertEqual(transform.header.stamp.sec * 1_000_000_000 + transform.header.stamp.nanosec, stamp)
                    if connection.topic.endswith("tf_static"):
                        self.assertEqual((transform.header.frame_id, transform.child_frame_id), ("training_base", "training_lidar"))
                        self.assertEqual((transform.transform.translation.x, transform.transform.translation.y, transform.transform.translation.z), (0.2, 0.0, 0.1))
                        self.assertEqual(transform.transform.rotation.w, 1.0)
                    else:
                        self.assertEqual((transform.header.frame_id, transform.child_frame_id), ("training_odom", "training_base"))
                        elapsed = (stamp - START_NS) / 1_000_000_000
                        self.assertAlmostEqual(transform.transform.translation.x, elapsed * 0.2 if name == "forward" else 0.0)
                        self.assertAlmostEqual(transform.transform.translation.y, elapsed * 0.1 if name == "lateral" else 0.0)
                        import math
                        self.assertAlmostEqual(transform.transform.rotation.z, math.sin(elapsed * 0.1) if name == "rotation" else 0.0)
                        self.assertAlmostEqual(transform.transform.rotation.w, math.cos(elapsed * 0.1) if name == "rotation" else 1.0)

    def test_sqlite_integrity_cdr_format_and_ros2_hashes(self):
        output = self.dataset()
        for name in SCENARIOS:
            bag = output / name / "bag"
            metadata = YAML(typ="safe").load((bag / "metadata.yaml").read_text())["rosbag2_bagfile_information"]
            self.assertEqual(metadata["duration"]["nanoseconds"], 5_000_000_000)
            self.assertEqual(metadata["message_count"], 154)
            self.assertEqual(metadata["storage_identifier"], "sqlite3")
            # Humble decodes this field as std::string; v9 sequence encoding fails.
            for topic in metadata["topics_with_message_count"]:
                qos = topic["topic_metadata"]["offered_qos_profiles"]
                self.assertIsInstance(qos, str)
                self.assertIsInstance(YAML(typ="safe").load(qos), list)
            with sqlite3.connect(bag / metadata["relative_file_paths"][0]) as database:
                self.assertEqual(database.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(database.execute("SELECT count(*) FROM messages").fetchone()[0], 154)
                for msgtype, serialization, digest in database.execute("SELECT type, serialization_format, type_description_hash FROM topics"):
                    self.assertIn("/msg/", msgtype)
                    self.assertEqual(serialization, "cdr")
                    self.assertRegex(digest, r"^RIHS01_[0-9a-f]{64}$")

    def test_manifests_hash_all_assets_with_explicit_synthetic_provenance(self):
        for output in (self.dataset(), COMMITTED):
            with self.subTest(output=str(output)):
                manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["provenance"]["kind"], "synthetic_analytic")
                self.assertFalse(manifest["provenance"]["valid_pointlio_input"])
                assets = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"}
                self.assertEqual(set(manifest["files"]), assets)
                for relative, info in manifest["files"].items():
                    contents = (output / relative).read_bytes()
                    self.assertEqual(hashlib.sha256(contents).hexdigest(), info["sha256"])
                    self.assertEqual(len(contents), info["bytes"])
                self.assertLess(sum(info["bytes"] for info in manifest["files"].values()), 2_000_000)

    def test_two_runs_have_identical_generated_bytes(self):
        first = self.dataset()
        second = Path(self.temp.name) / "second"
        result = subprocess.run([sys.executable, "-X", "utf8", str(GENERATOR), "--output", str(second)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in first.rglob("*"):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (second / path.relative_to(first)).read_bytes(), str(path.relative_to(first)))

    def test_text_assets_keep_lf_for_checkout_and_cross_platform_hashes(self):
        for output in (self.dataset(), COMMITTED):
            for path in output.rglob("*"):
                if path.is_file() and path.suffix != ".db3":
                    self.assertNotIn(b"\r\n", path.read_bytes(), str(path.relative_to(output)))

    def test_time_anomalies_are_reproducible_teaching_events(self):
        directory = self.dataset() / "time_anomalies"
        with (directory / "timestamps.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        stamps = [int(row["stamp_ns"]) for row in rows]
        self.assertEqual(stamps, [100_000_000_000, 100_100_000_000, 100_100_000_000, 100_050_000_000, 100_450_000_000, 100_550_000_000])
        self.assertEqual(stamps[2] - stamps[1], 0)
        self.assertLess(stamps[3] - stamps[2], 0)
        self.assertGreater(stamps[4] - stamps[3], 200_000_000)
        expected = json.loads((directory / "expected.json").read_text())
        self.assertEqual(expected["events"], [{"row_index": 2, "kind": "duplicate"}, {"row_index": 3, "kind": "rollback"}, {"row_index": 4, "kind": "gap"}])


if __name__ == "__main__":
    unittest.main()
