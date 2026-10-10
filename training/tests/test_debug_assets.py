"""Check the published diagnostic script without ROS or robot hardware."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "docs/navigation/debug-real"
SCRIPT = PAGES / "assets/collect_navigation_debug.sh"
BASH = os.environ.get("NAV_DEBUG_BASH") or shutil.which("bash")


class DocumentAssetsTests(unittest.TestCase):
    def test_links_are_portable_and_resolve(self):
        for name in ("command-guide.md", "runbook.md"):
            text = (PAGES / name).read_text(encoding="utf-8")
            self.assertNotIn("C:/Users/", text)
            self.assertIn("Navigation-2027", text)
            self.assertIn("PB2025", text)
            self.assertIn("183a4109b0de2030bb8970a54654937c8b039ba9", text)
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                self.assertTrue((PAGES / link.split("#")[0]).exists(), link)

    def test_script_format(self):
        raw = SCRIPT.read_bytes()
        self.assertTrue(raw.startswith(b"#!/usr/bin/env bash\n"))
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.isascii())


@unittest.skipUnless(BASH, "Bash unavailable; CI requires Linux Bash")
class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nav-debug-test-")
        self.root = Path(self.temp.name)
        self.report_root = self.root / "reports with spaces"
        self.env = os.environ.copy()
        for key in ("NAV_WORKSPACE", "SERIAL_WORKSPACE", "ROBOT_NS", "SERIAL_NODE", "NAV_DEBUG_REPORT_ROOT"):
            self.env.pop(key, None)

    def tearDown(self):
        self.temp.cleanup()

    def run_collector(self, *args):
        return subprocess.run(
            [BASH, SCRIPT.as_posix(), *args], env=self.env,
            capture_output=True, text=True, encoding="utf-8", timeout=180,
        )

    def install_mocks(self):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        self.env["MOCK_LOG"] = (self.root / "commands.txt").as_posix()
        self.env["PATH"] = str(bin_dir) + os.pathsep + self.env["PATH"]
        timeout = bin_dir / "timeout"
        timeout.write_text("#!/usr/bin/env bash\nshift 3\nexec \"$@\"\n", encoding="ascii")
        timeout.chmod(0o755)
        ros2 = bin_dir / "ros2"
        ros2.write_text(r'''#!/usr/bin/env bash
printf '%s\n' "$*" >> "$MOCK_LOG"
case "$1:$2" in
  node:list)
    if [[ ${MOCK_NODE_FAIL:-0} == 1 ]]; then printf 'Discovery failed\n' >&2; exit 1; fi
    printf '/lab_robot/point_lio\n/lab_robot/point_lio\n/lab_robot/controller_server\n'
    ;;
  topic:list)
    printf '/lab_robot/cmd_vel [geometry_msgs/msg/Twist]\n'
    printf '/lab_robot/serial/gimbal_joint_state [sensor_msgs/msg/JointState]\n'
    ;;
  topic:echo) printf 'mock_sample: true\n' ;;
  topic:hz) printf 'average rate: 20.0\n' ;;
  param:get)
    if [[ $4 == auto_initialize || $4 == FollowPath.enable_collision_guard ]]; then
      printf 'Parameter not set\n' >&2; exit 1
    fi
    printf 'mock_parameter: true\n'
    ;;
  lifecycle:get) printf 'active [3]\n' ;;
  run:tf2_ros) printf 'Translation: [0.0, 0.0, 0.0]\n' ;;
  pkg:prefix) printf '/mock/install/pb2025_nav_bringup\n' ;;
  component:list|action:info|node:info|topic:info) printf 'mock_inspection: true\n' ;;
  *) printf 'Unexpected ROS command\n' >&2; exit 9 ;;
esac
''', encoding="ascii")
        ros2.chmod(0o755)

    def collect(self, *args):
        result = self.run_collector("--namespace", "/lab_robot", "--report-root", self.report_root.as_posix(), *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reports = list(self.report_root.glob("*/report.txt"))
        self.assertEqual(len(reports), 1)
        return reports[0].read_text(encoding="utf-8"), Path(self.env["MOCK_LOG"]).read_text(encoding="utf-8")

    def test_help_has_no_report_side_effect(self):
        result = self.run_collector("--report-root", self.report_root.as_posix(), "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage:", result.stdout)
        self.assertFalse(self.report_root.exists())

    def test_rejects_missing_option_value(self):
        result = self.run_collector("--namespace")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing value", result.stderr)

    def test_rejects_relative_namespace(self):
        result = self.run_collector("--namespace", "lab_robot")
        self.assertEqual(result.returncode, 2)
        self.assertIn("absolute ROS name", result.stderr)

    def test_rejects_missing_workspace_before_report(self):
        result = self.run_collector("--report-root", self.report_root.as_posix(), "--nav-workspace", (self.root / "missing").as_posix())
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.report_root.exists())

    def test_quick_report_preserves_failures_and_discovered_type(self):
        self.install_mocks()
        report, calls = self.collect()
        self.assertIn("/lab_robot/point_lio", report.split("===== Duplicate node names =====")[1])
        self.assertIn("Parameter not set", report)
        self.assertIn("[command exit=1]", report)
        self.assertIn("optional topic not discovered", report)
        self.assertIn("topic echo /lab_robot/serial/gimbal_joint_state sensor_msgs/msg/JointState --once", calls)
        self.assertNotIn("run tf2_ros", calls)
        for line in calls.splitlines():
            self.assertNotRegex(line, r"^(launch|daemon|topic pub|param set|lifecycle set)\b")

    def test_failed_node_discovery_is_not_a_clean_duplicate_check(self):
        self.install_mocks()
        self.env["MOCK_NODE_FAIL"] = "1"
        report, _ = self.collect()
        self.assertIn("duplicate check is inconclusive", report)
        self.assertNotIn("No names above means none duplicated", report)

    def test_full_mode_samples_rates_and_namespaced_tf(self):
        self.install_mocks()
        report, calls = self.collect("--full")
        self.assertIn("Received frequency: odometry", report)
        self.assertIn("average rate: 20.0", report)
        self.assertIn("run tf2_ros tf2_echo odom base_footprint", calls)
        self.assertIn("/tf:=/lab_robot/tf", calls)
        self.assertIn("/tf_static:=/lab_robot/tf_static", calls)


if __name__ == "__main__":
    unittest.main()
