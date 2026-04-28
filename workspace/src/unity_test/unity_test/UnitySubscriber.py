import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class UnitySubscriber(Node):
    def __init__(self):
        super().__init__('unity_subscriber')
        self.subscription = self.create_subscription(
            String,
            'unity_topic',
            self.listener_callback,
            10
        )

    def listener_callback(self, msg):
        self.get_logger().info(f'Received: {msg.data}')

def main(args=None):
    rclpy.init(args=args)
    node = UnitySubscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()