"""Small lifecycle helpers shared by the single-threaded teaching nodes."""

import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException


def startup_parameter(node, name, default):
    """Parameters take effect at startup; reject misleading runtime changes."""
    return node.declare_parameter(
        name, default, ParameterDescriptor(read_only=True)).value


def spin_node(node_factory, args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = node_factory()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
