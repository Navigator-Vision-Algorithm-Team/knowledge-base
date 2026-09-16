"""Bounded ideal kinematics: cmd_vel -> odom and an isolated TF tree."""

import math

from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from tf2_msgs.msg import TFMessage

from nav_training.core import TimedModel, Twist2D
from nav_training.limits import bounded_number, bound_planar_command
from nav_training.runtime import spin_node, startup_parameter


class IdealModel(Node):
    def __init__(self):
        super().__init__('ideal_model', namespace='/nav_training')
        rate = bounded_number(startup_parameter(self, 'rate_hz', 20.0),
                              'rate_hz', 1.0, 200.0)
        timeout = bounded_number(startup_parameter(self, 'command_timeout', 0.5),
                                 'command_timeout', 0.05, 5.0)
        self.max_linear = bounded_number(startup_parameter(self, 'max_linear', 0.5),
                                         'max_linear', 0.01, 0.5)
        self.max_angular = bounded_number(startup_parameter(self, 'max_angular', 1.0),
                                          'max_angular', 0.01, 1.0)
        self.model = TimedModel(timeout=timeout)
        self.odom = self.create_publisher(Odometry, 'odom', 20)
        # Explicit relative TF publishers keep ros2 run isolated as well as launch.
        self.dynamic_tf = self.create_publisher(TFMessage, 'tf', 100)
        static_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.static_tf = self.create_publisher(TFMessage, 'tf_static', static_qos)
        self.create_subscription(Twist, 'cmd_vel', self.receive_command, 10)
        static = TransformStamped()
        static.header.stamp = self.get_clock().now().to_msg()
        static.header.frame_id = 'training_base'
        static.child_frame_id = 'training_lidar'
        static.transform.translation.x = 0.2
        static.transform.translation.z = 0.1
        static.transform.rotation.w = 1.0
        self.static_tf.publish(TFMessage(transforms=[static]))
        self.create_timer(1.0 / rate, self.tick)

    def receive_command(self, message):
        now = self.get_clock().now().nanoseconds * 1e-9
        values = (message.linear.x, message.linear.y, message.linear.z,
                  message.angular.x, message.angular.y, message.angular.z)
        try:
            twist = Twist2D(*bound_planar_command(values, self.max_linear, self.max_angular))
        except ValueError as exc:
            twist = Twist2D()
            self.get_logger().warning(f'Invalid command: zero applied ({exc})',
                                      throttle_duration_sec=1.0)
        self.model.set_command(twist, now)

    def tick(self):
        now = self.get_clock().now()
        seconds = now.nanoseconds * 1e-9
        pose = self.model.step(seconds)
        twist = self.model.active_twist(seconds)
        message = Odometry()
        message.header.stamp = now.to_msg()
        message.header.frame_id = 'training_odom'
        message.child_frame_id = 'training_base'
        message.pose.pose.position.x = pose.x
        message.pose.pose.position.y = pose.y
        message.pose.pose.orientation.z = math.sin(pose.yaw / 2.0)
        message.pose.pose.orientation.w = math.cos(pose.yaw / 2.0)
        message.twist.twist.linear.x = twist.vx
        message.twist.twist.linear.y = twist.vy
        message.twist.twist.angular.z = twist.wz
        transform = TransformStamped()
        transform.header = message.header
        transform.child_frame_id = message.child_frame_id
        transform.transform.translation.x = pose.x
        transform.transform.translation.y = pose.y
        transform.transform.rotation = message.pose.pose.orientation
        self.odom.publish(message)
        self.dynamic_tf.publish(TFMessage(transforms=[transform]))


def main(args=None):
    spin_node(IdealModel, args)
