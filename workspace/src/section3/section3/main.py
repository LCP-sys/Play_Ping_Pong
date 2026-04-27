import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class State(Node):
    def __init__(self):
        super().__init__('state')

        self.ball_p = 0.0
        self.ball_v = [0.0, 0.0, 0.0]

        self.s1 = 0.0
        self.s2 = 0.0
        self.s3 = 0.0
        self.s4 = 0.0
        self.s5 = 0.0
        self.s6 = 0.0


        self.create_subscription(Float32, '/ball_vx', self.vx_cb, 10)
        self.create_subscription(Float32, '/ball_vy', self.vy_cb, 10)
        self.create_subscription(Float32, '/ball_vz', self.vz_cb, 10)

        self.create_subscription(Float32, '/ball_position', self.ball_cb, 10)

        self.create_subscription(Float32, '/down_plus', self.s1_cb, 10)
        self.create_subscription(Float32, '/down_min', self.s2_cb, 10)
        self.create_subscription(Float32, '/down_minus', self.s3_cb, 10)
        self.create_subscription(Float32, '/up_plus', self.s4_cb, 10)
        self.create_subscription(Float32, '/up_min', self.s5_cb, 10)
        self.create_subscription(Float32, '/up_minus', self.s6_cb, 10)

        self.timer = self.create_timer(1.0, self.debug_print)

    # ===== callbacks =====
    def ball_cb(self, msg):
        self.ball_p = msg.data

    def vx_cb(self, msg):
        self.ball_v[0] = msg.data

    def vy_cb(self, msg):
        self.ball_v[1] = msg.data

    def vz_cb(self, msg):
        self.ball_v[2] = msg.data

    def s1_cb(self, msg): self.s1 = msg.data
    def s2_cb(self, msg): self.s2 = msg.data
    def s3_cb(self, msg): self.s3 = msg.data
    def s4_cb(self, msg): self.s4 = msg.data
    def s5_cb(self, msg): self.s5 = msg.data
    def s6_cb(self, msg): self.s6 = msg.data

    # ===== debug =====
    def debug_print(self):
        self.get_logger().info(
            f'ball={self.ball_p:.3f}, '
            f'vx={self.ball_v[0]:.3f}, '
            f'vy={self.ball_v[1]:.3f}, '
            f'vz={self.ball_v[2]:.3f}, '
            f's1={self.s1:.3f}, s2={self.s2:.3f}'
        )


def main():
    rclpy.init()
    node = State()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()