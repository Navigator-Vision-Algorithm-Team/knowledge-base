"""A visible source/sink pair for namespace and topic diagnosis."""

from rclpy.node import Node
from std_msgs.msg import Int64

from nav_training.limits import bounded_number
from nav_training.runtime import spin_node, startup_parameter


class SequencePublisher(Node):
    def __init__(self):
        super().__init__('sequence_source', namespace='/nav_training')
        topic = startup_parameter(self, 'topic', 'sequence')
        rate = bounded_number(startup_parameter(self, 'rate_hz', 10.0),
                              'rate_hz', 0.1, 200.0)
        self.publisher = self.create_publisher(Int64, topic, 20)
        self.sequence = 0
        self.create_timer(1.0 / rate, self.publish_next)
        self.get_logger().info(f'Publishing Int64 on {self.publisher.topic_name}')

    def publish_next(self):
        self.publisher.publish(Int64(data=self.sequence))
        self.sequence += 1
        if self.sequence > 2**63 - 1:
            self.sequence = 0


class SequenceSubscriber(Node):
    def __init__(self):
        super().__init__('sequence_sink', namespace='/nav_training')
        topic = startup_parameter(self, 'topic', 'sequence')
        output_topic = startup_parameter(self, 'output_topic', 'received')
        self.publisher = self.create_publisher(Int64, output_topic, 20)
        self.subscription = self.create_subscription(Int64, topic, self.receive, 20)
        self.get_logger().info(f'Subscribing to {self.subscription.topic_name}')

    def receive(self, message):
        self.publisher.publish(message)
        self.get_logger().info(f'received={message.data}', throttle_duration_sec=1.0)


def publisher_main(args=None):
    spin_node(SequencePublisher, args)


def subscriber_main(args=None):
    spin_node(SequenceSubscriber, args)
