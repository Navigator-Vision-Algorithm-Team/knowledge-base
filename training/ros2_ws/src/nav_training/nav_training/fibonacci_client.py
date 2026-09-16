"""One-shot Action client with optional cancel_after and finite wait limits."""

import time

from action_msgs.msg import GoalStatus
from action_tutorials_interfaces.action import Fibonacci
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from nav_training.limits import bounded_number
from nav_training.runtime import startup_parameter


class FibonacciClient(Node):
    def __init__(self):
        super().__init__('fibonacci_client', namespace='/nav_training')
        self.order = startup_parameter(self, 'order', 10)
        if isinstance(self.order, bool) or not isinstance(self.order, int):
            raise ValueError('order must be an integer')
        self.cancel_after = bounded_number(startup_parameter(self, 'cancel_after', 0.0),
                                            'cancel_after', 0.0, 60.0)
        self.wait_seconds = bounded_number(startup_parameter(self, 'wait_seconds', 60.0),
                                            'wait_seconds', 1.0, 120.0)
        self.action = ActionClient(self, Fibonacci, 'fibonacci')

    def wait(self, future, deadline):
        while rclpy.ok() and not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
        if not future.done():
            raise TimeoutError('Action operation exceeded wait_seconds')
        return future.result()

    def feedback(self, message):
        self.get_logger().info(f'feedback={list(message.feedback.partial_sequence)}')

    def run(self):
        if not self.action.wait_for_server(timeout_sec=min(10.0, self.wait_seconds)):
            raise TimeoutError('Fibonacci server unavailable')
        deadline = time.monotonic() + self.wait_seconds
        handle = self.wait(self.action.send_goal_async(
            Fibonacci.Goal(order=self.order), feedback_callback=self.feedback), deadline)
        if not handle.accepted:
            self.get_logger().error('Goal rejected: require order 0..46 and idle server')
            return 2
        result_future = handle.get_result_async()
        cancel_at = time.monotonic() + self.cancel_after
        canceled = False
        try:
            while not result_future.done() and time.monotonic() < deadline and rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.05)
                if self.cancel_after > 0 and not canceled and time.monotonic() >= cancel_at:
                    response = self.wait(handle.cancel_goal_async(), deadline)
                    self.get_logger().info(f'cancel accepted={bool(response.goals_canceling)}')
                    canceled = True
            response = self.wait(result_future, deadline)
        except TimeoutError:
            # A client timeout must not silently leave its bounded goal running.
            self.wait(handle.cancel_goal_async(), time.monotonic() + 2.0)
            raise
        self.get_logger().info(
            f'status={response.status} result={list(response.result.sequence)}')
        return 0 if response.status in (
            GoalStatus.STATUS_SUCCEEDED, GoalStatus.STATUS_CANCELED) else 1

    def destroy_node(self):
        self.action.destroy()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    code = 1
    try:
        node = FibonacciClient()
        code = node.run()
    except (KeyboardInterrupt, ExternalShutdownException):
        code = 130
    except (TimeoutError, ValueError) as exc:
        if node is not None:
            node.get_logger().error(str(exc))
        else:
            print(str(exc))
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return code
