"""Humble integration tests: actual launch processes, DDS messages and Actions.

Source the built training workspace first. Missing ROS is a SKIP locally;
NAV_TRAINING_REQUIRE_ROS=1 makes a missing dependency fail CI instead.
"""

from contextlib import contextmanager
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

# Isolate this local teaching graph; the caller can select another unused domain.
os.environ.setdefault('ROS_DOMAIN_ID', str(71 + os.getpid() % 20))
os.environ.setdefault('ROS_LOCALHOST_ONLY', '1')

ROS_ERROR = None
try:
    import rclpy
    from action_msgs.msg import GoalStatus
    from action_tutorials_interfaces.action import Fibonacci
    from ament_index_python.packages import get_package_share_directory
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from rclpy.action import ActionClient
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import Int64
    from tf2_msgs.msg import TFMessage
except ImportError as exc:
    ROS_ERROR = str(exc)


class RosSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = ROS_ERROR
        if missing is None and shutil.which('ros2') is None:
            missing = 'ros2 executable not on PATH'
        if missing is None:
            try:
                get_package_share_directory('nav_training')
            except LookupError as exc:
                missing = str(exc)
        if missing:
            reason = 'Humble smoke unavailable: ' + missing + '; build/source training/ros2_ws'
            if os.environ.get('NAV_TRAINING_REQUIRE_ROS') == '1':
                raise RuntimeError(reason)
            raise unittest.SkipTest(reason)

    def setUp(self):
        rclpy.init()
        self.probe = rclpy.create_node('training_smoke_probe')
        self.process = None

    def tearDown(self):
        self.probe.destroy_node()
        rclpy.shutdown()

    @contextmanager
    def running(self, *command):
        with tempfile.TemporaryFile(mode='w+t', encoding='utf-8') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            self.process = process
            try:
                yield process
            except BaseException:
                log.seek(0)
                print('\nROS child output:\n' + log.read(), file=sys.stderr)
                raise
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                self.process = None

    def spin_until(self, predicate, timeout=12.0):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            if self.process is not None:
                self.assertIsNone(self.process.poll(), 'ROS child exited early')
            rclpy.spin_once(self.probe, timeout_sec=0.05)
        self.assertTrue(predicate(), 'Timed out waiting for expected ROS data/state')

    def spin_for(self, duration):
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            if self.process is not None:
                self.assertIsNone(self.process.poll(), 'ROS child exited early')
            rclpy.spin_once(self.probe, timeout_sec=0.02)

    def sequence_probe(self):
        source, received = [], []
        self.probe.create_subscription(Int64, '/nav_training/sequence',
                                       lambda msg: source.append(msg.data), 20)
        self.probe.create_subscription(Int64, '/nav_training/received',
                                       lambda msg: received.append(msg.data), 20)
        return source, received

    def test_healthy_preset_delivers_increasing_sequence_to_sink(self):
        source, received = self.sequence_probe()
        with self.running('ros2', 'launch', 'nav_training', 'healthy.launch.py'):
            self.spin_until(lambda: len(source) >= 5 and len(received) >= 5)
            self.assertTrue(all(a < b for a, b in zip(source, source[1:])))
            self.assertTrue(all(a < b for a, b in zip(received, received[1:])))
            self.assertGreaterEqual(len(set(source).intersection(received)), 3)

    def test_bad_topic_has_a_live_source_but_disconnected_sink_then_repairs(self):
        source, received = self.sequence_probe()
        with self.running('ros2', 'launch', 'nav_training', 'bad_topic.launch.py'):
            self.spin_until(lambda: len(source) >= 5)
            self.spin_for(0.6)
            self.assertEqual(received, [], 'Absolute /sequence must miss namespaced source')
            sink_topics = dict(self.probe.get_subscriber_names_and_types_by_node(
                'sequence_sink', '/nav_training'))
            source_topics = dict(self.probe.get_publisher_names_and_types_by_node(
                'sequence_source', '/nav_training'))
            self.assertIn('/sequence', sink_topics)
            self.assertIn('/nav_training/sequence', source_topics)
        source.clear()
        received.clear()
        with self.running('ros2', 'launch', 'nav_training', 'bad_topic.launch.py',
                          'sink_topic:=sequence'):
            self.spin_until(lambda: len(received) >= 4)
            self.assertGreaterEqual(len(set(source).intersection(received)), 2)

    def test_model_odom_tf_bounds_invalid_stop_and_timeout(self):
        odom, dynamic, static = [], [], []
        self.probe.create_subscription(Odometry, '/nav_training/odom', odom.append, 100)
        self.probe.create_subscription(TFMessage, '/nav_training/tf',
                                       lambda msg: dynamic.extend(msg.transforms), 100)
        static_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                                reliability=ReliabilityPolicy.RELIABLE)
        self.probe.create_subscription(TFMessage, '/nav_training/tf_static',
                                       lambda msg: static.extend(msg.transforms), static_qos)
        publisher = self.probe.create_publisher(Twist, '/nav_training/cmd_vel', 10)
        with self.running('ros2', 'launch', 'nav_training', 'healthy.launch.py'):
            self.spin_until(lambda: len(odom) >= 3 and dynamic and static
                            and publisher.get_subscription_count() >= 1)
            self.assertEqual(odom[-1].header.frame_id, 'training_odom')
            self.assertEqual(odom[-1].child_frame_id, 'training_base')
            self.assertEqual(static[-1].header.frame_id, 'training_base')
            self.assertEqual(static[-1].child_frame_id, 'training_lidar')
            self.assertAlmostEqual(static[-1].transform.translation.x, 0.2)
            self.assertAlmostEqual(static[-1].transform.translation.y, 0.0)
            self.assertAlmostEqual(static[-1].transform.translation.z, 0.1)
            late_static = []
            self.probe.create_subscription(TFMessage, '/nav_training/tf_static',
                lambda msg: late_static.extend(msg.transforms), static_qos)
            self.spin_until(lambda: bool(late_static))
            self.assertEqual(late_static[-1], static[-1], 'Late joiner must receive static TF')
            initial_x = odom[-1].pose.pose.position.x
            command = Twist()
            command.linear.x = 0.3
            command.angular.z = 0.4
            for _ in range(12):
                publisher.publish(command)
                self.spin_for(0.05)
            self.spin_until(lambda: odom[-1].pose.pose.position.x > initial_x + 0.08)
            self.assertGreater(abs(odom[-1].pose.pose.orientation.z), 0.01)

            def stamp(msg):
                return msg.header.stamp.sec, msg.header.stamp.nanosec

            odom_by_time = {stamp(msg): msg for msg in odom}
            matched = [tf for tf in dynamic if stamp(tf) in odom_by_time]
            self.assertTrue(matched, 'TF and Odometry must use the identical ROS stamp')
            tf = matched[-1]
            msg = odom_by_time[stamp(tf)]
            self.assertEqual(tf.header.frame_id, msg.header.frame_id)
            self.assertEqual(tf.child_frame_id, msg.child_frame_id)
            self.assertEqual(tf.transform.translation.x, msg.pose.pose.position.x)
            self.assertEqual(tf.transform.translation.y, msg.pose.pose.position.y)
            self.assertEqual(tf.transform.rotation, msg.pose.pose.orientation)

            self.spin_for(0.8)
            self.assertEqual(odom[-1].twist.twist.linear.x, 0.0)
            self.assertEqual(odom[-1].twist.twist.angular.z, 0.0)
            stopped = odom[-1].pose.pose
            self.spin_for(0.25)
            self.assertEqual(odom[-1].pose.pose, stopped, 'Pose must hold after expiry')

            command.linear.x, command.linear.y, command.angular.z = 3.0, 4.0, 5.0
            publisher.publish(command)
            self.spin_until(lambda: abs(odom[-1].twist.twist.linear.x - 0.3) < 1e-9, 2)
            self.assertAlmostEqual(odom[-1].twist.twist.linear.y, 0.4)
            self.assertAlmostEqual(odom[-1].twist.twist.angular.z, 1.0)
            command.linear.x = math.nan
            publisher.publish(command)
            self.spin_until(lambda: odom[-1].twist.twist.linear.x == 0.0, 0.4)
            self.assertEqual(odom[-1].twist.twist.linear.y, 0.0)
            self.assertEqual(odom[-1].twist.twist.angular.z, 0.0)

    def test_action_feedback_cancel_success_and_reject(self):
        client = ActionClient(self.probe, Fibonacci, '/nav_training/fibonacci')
        try:
            with self.running('ros2', 'run', 'nav_training', 'fibonacci_server'):
                self.assertTrue(client.wait_for_server(timeout_sec=12))
                feedback = []
                future = client.send_goal_async(Fibonacci.Goal(order=30),
                    feedback_callback=lambda msg: feedback.append(list(msg.feedback.partial_sequence)))
                self.spin_until(future.done)
                handle = future.result()
                self.assertTrue(handle.accepted)
                result_future = handle.get_result_async()
                busy = client.send_goal_async(Fibonacci.Goal(order=2))
                self.spin_until(busy.done)
                self.assertFalse(busy.result().accepted, 'Server accepts only one active goal')
                self.spin_until(lambda: len(feedback) >= 3)
                self.assertEqual(feedback[0], [0, 1])
                self.assertEqual(feedback[2], [0, 1, 1, 2])
                cancel_future = handle.cancel_goal_async()
                self.spin_until(cancel_future.done)
                self.assertEqual(len(cancel_future.result().goals_canceling), 1)
                self.spin_until(result_future.done)
                self.assertEqual(result_future.result().status, GoalStatus.STATUS_CANCELED)
                self.assertGreaterEqual(len(result_future.result().result.sequence), 4)
                self.assertLess(len(result_future.result().result.sequence), 31)

                done_future = client.send_goal_async(Fibonacci.Goal(order=5))
                self.spin_until(done_future.done)
                self.assertTrue(done_future.result().accepted)
                result = done_future.result().get_result_async()
                self.spin_until(result.done)
                self.assertEqual(result.result().status, GoalStatus.STATUS_SUCCEEDED)
                self.assertEqual(list(result.result().result.sequence), [0, 1, 1, 2, 3, 5])

                for order, expected in ((0, [0]), (1, [0, 1])):
                    boundary = client.send_goal_async(Fibonacci.Goal(order=order))
                    self.spin_until(boundary.done)
                    self.assertTrue(boundary.result().accepted)
                    boundary_result = boundary.result().get_result_async()
                    self.spin_until(boundary_result.done)
                    self.assertEqual(boundary_result.result().status, GoalStatus.STATUS_SUCCEEDED)
                    self.assertEqual(list(boundary_result.result().result.sequence), expected)

                for order in (-1, 47):
                    rejected = client.send_goal_async(Fibonacci.Goal(order=order))
                    self.spin_until(rejected.done)
                    self.assertFalse(rejected.result().accepted)
        finally:
            client.destroy()

    def test_action_client_cli_success_cancel_and_reject_exit_codes(self):
        with self.running('ros2', 'run', 'nav_training', 'fibonacci_server'):
            for parameters, expected_code, expected_status in (
                (['-p', 'order:=5'], 0, 'status=4'),
                (['-p', 'order:=30', '-p', 'cancel_after:=0.3'], 0, 'status=5'),
                (['-p', 'order:=47'], 2, 'Goal rejected'),
            ):
                result = subprocess.run(
                    ['ros2', 'run', 'nav_training', 'fibonacci_client', '--ros-args',
                     '-p', 'wait_seconds:=10.0', *parameters],
                    capture_output=True, text=True, timeout=20)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, expected_code, output)
                self.assertIn(expected_status, output)

    def test_humble_reads_and_replays_committed_forward_bag(self):
        bag = Path(__file__).resolve().parents[1] / 'datasets/synthetic-v1/forward/bag'
        info = subprocess.run(['ros2', 'bag', 'info', str(bag)],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(info.returncode, 0, info.stdout + info.stderr)
        odom, dynamic, static = [], [], []
        self.probe.create_subscription(Odometry, '/nav_training/odom', odom.append, 100)
        self.probe.create_subscription(TFMessage, '/nav_training/tf',
                                       lambda msg: dynamic.extend(msg.transforms), 100)
        static_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                                reliability=ReliabilityPolicy.RELIABLE)
        with self.running('ros2', 'bag', 'play', str(bag), '--clock', '--delay', '1.0',
                          '--disable-keyboard-controls', '--wait-for-all-acked', '1000') as process:
            deadline = time.monotonic() + 15
            subscribed_static = False
            while time.monotonic() < deadline:
                rclpy.spin_once(self.probe, timeout_sec=0.05)
                # Subscribe after replay began, testing recorded transient-local QoS.
                if len(odom) >= 5 and not subscribed_static:
                    self.probe.create_subscription(TFMessage, '/nav_training/tf_static',
                        lambda msg: static.extend(msg.transforms), static_qos)
                    subscribed_static = True
                if process.poll() is not None:
                    break
            self.assertIsNotNone(process.poll(), 'Bag replay must terminate within 15 seconds')
            self.assertEqual(process.returncode, 0)
            drain_deadline = time.monotonic() + 0.3
            while time.monotonic() < drain_deadline:
                rclpy.spin_once(self.probe, timeout_sec=0.02)
            self.assertGreaterEqual(len(odom), 40, 'Expected at least 40 of 51 replay samples')
            self.assertGreaterEqual(len(dynamic), 40)
            self.assertAlmostEqual(odom[-1].pose.pose.position.x, 1.0, places=6)
            self.assertAlmostEqual(odom[-1].pose.pose.position.y, 0.0, places=6)
            self.assertEqual(odom[-1].header.frame_id, 'training_odom')
            self.assertEqual(dynamic[-1].child_frame_id, 'training_base')
            self.assertTrue(static, 'Bag must retain static TF for a late subscriber')
            self.assertEqual(static[-1].header.frame_id, 'training_base')
            self.assertEqual(static[-1].child_frame_id, 'training_lidar')
            self.assertAlmostEqual(static[-1].transform.translation.x, 0.2)
            self.assertAlmostEqual(static[-1].transform.translation.z, 0.1)


if __name__ == '__main__':
    unittest.main()
