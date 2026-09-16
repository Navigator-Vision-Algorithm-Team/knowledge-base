"""A bounded, cancelable Action exercise using the Humble tutorial interface."""

import threading
import time

from action_tutorials_interfaces.action import Fibonacci
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node

from nav_training.limits import bounded_number
from nav_training.runtime import startup_parameter


class FibonacciServer(Node):
    def __init__(self):
        super().__init__('fibonacci_server', namespace='/nav_training')
        self.step_seconds = bounded_number(startup_parameter(self, 'step_seconds', 0.1),
                                           'step_seconds', 0.02, 1.0)
        self._goal_lock = threading.Lock()
        self._busy = False
        self.action = ActionServer(
            self, Fibonacci, 'fibonacci', self.execute,
            callback_group=ReentrantCallbackGroup(),
            goal_callback=self.accept_goal, cancel_callback=self.accept_cancel)

    def accept_goal(self, request):
        # F46 is the largest Fibonacci number that fits the int32[] interface.
        with self._goal_lock:
            if not 0 <= request.order <= 46 or self._busy:
                return GoalResponse.REJECT
            self._busy = True
        return GoalResponse.ACCEPT

    def accept_cancel(self, _handle):
        return CancelResponse.ACCEPT

    def execute(self, handle):
        sequence = [0] if handle.request.order == 0 else [0, 1]
        try:
            while True:
                if handle.is_cancel_requested:
                    handle.canceled()
                    return Fibonacci.Result(sequence=sequence)
                if not rclpy.ok():
                    handle.abort()
                    return Fibonacci.Result(sequence=sequence)
                handle.publish_feedback(Fibonacci.Feedback(partial_sequence=sequence))
                if len(sequence) >= handle.request.order + 1:
                    handle.succeed()
                    return Fibonacci.Result(sequence=sequence)
                # The second executor thread remains free to accept cancellation.
                # This is wall-time pacing, deliberately independent of /clock.
                time.sleep(self.step_seconds)
                if not handle.is_cancel_requested:
                    sequence.append(sequence[-1] + sequence[-2])
        finally:
            with self._goal_lock:
                self._busy = False

    def destroy_node(self):
        self.action.destroy()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    executor = MultiThreadedExecutor(num_threads=2)
    try:
        node = FibonacciServer()
        executor.add_node(node)
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
