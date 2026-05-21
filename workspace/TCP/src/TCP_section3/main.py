import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Point
import threading
import sys
import termios
import tty
import select
from rclpy.executors import SingleThreadedExecutor

class State(Node):
    def __init__(self):
        super().__init__('state')

        # 實測有效物理邊界限制
        self.limit_max = 0.17
        self.limit_min = -0.17
        
        self.mode = 'manual'
        self.ball_p = [0.0, 0.0, 0.0]
        self.ball_v = [0.0, 0.0, 0.0]
        self.goal_s1 = self.goal_s2 = self.goal_s3 = self.goal_s4 = self.goal_s5 = self.goal_s6 = 0.0

        self.keyboard_thread = None
        self.running = False
        self.exit_requested = False

        # Subscribers (接收 Unity 傳來的球體資訊)
        self.create_subscription(Float32, '/ball_vx', self.vx_cb, 10)
        self.create_subscription(Float32, '/ball_vy', self.vy_cb, 10)
        self.create_subscription(Float32, '/ball_vz', self.vz_cb, 10)
        self.create_subscription(Point, '/ball_position', self.ball_cb, 10)
        
        # Publishers (發送馬達目標位置給 Unity)
        self.goal_pubs = {
            'goal_s1': self.create_publisher(Float32, '/goal_s1', 10),
            'goal_s2': self.create_publisher(Float32, '/goal_s2', 10),
            'goal_s3': self.create_publisher(Float32, '/goal_s3', 10),
            'goal_s4': self.create_publisher(Float32, '/goal_s4', 10),
            'goal_s5': self.create_publisher(Float32, '/goal_s5', 10),
            'goal_s6': self.create_publisher(Float32, '/goal_s6', 10),
        }

        self.get_logger().info("✅ Manual 純手動鍵盤控制節點已啟動")
        self.start_keyboard_listener()

    # ----- callbacks -----
    def ball_cb(self, msg: Point): self.ball_p = [msg.x, msg.y, msg.z]
    def vx_cb(self, msg): self.ball_v[0] = msg.data
    def vy_cb(self, msg): self.ball_v[1] = msg.data
    def vz_cb(self, msg): self.ball_v[2] = msg.data

    # ==========================================
    # 硬體控制訊號輸出 (Actuator Control)
    # ==========================================
    def publish_goal(self, goal_name: str, value: float):
        if goal_name in self.goal_pubs:
            msg = Float32()
            msg.data = value
            self.goal_pubs[goal_name].publish(msg)

    # ==========================================
    # 鍵盤監聽與控制邏輯 (I/O & Logging)
    # ==========================================
    def start_keyboard_listener(self):
        if self.keyboard_thread and self.keyboard_thread.is_alive():
            return
        self.running = True
        self.exit_requested = False
        self.keyboard_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        self.keyboard_thread.start()

    def _keyboard_loop(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            print("\r", end='', flush=True)
            while self.running:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    self._handle_key(key)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            print("\r\n", end='', flush=True)

    def _handle_key(self, key: str):
        step = 0.03
        
        mapping = {
            'w': (['goal_s1', 'goal_s2', 'goal_s3'], -step),
            's': (['goal_s1', 'goal_s2', 'goal_s3'], +step),
            'i': (['goal_s4', 'goal_s5', 'goal_s6'], +step),
            'k': (['goal_s4', 'goal_s5', 'goal_s6'], -step),
        }
        
        if key == '\x1b':
            self.running = False
            self.exit_requested = True
            return
            
        if key in mapping:
            attrs, delta = mapping[key]
            for attr in attrs:
                current_val = getattr(self, attr)
                new_val = max(self.limit_min, min(self.limit_max, current_val + delta))
                setattr(self, attr, new_val)
                self.publish_goal(attr, new_val)
            
            status_line = f"\r目前深度 -> [下板 w/s]: {self.goal_s1: .3f}   |   [上板 i/k]: {self.goal_s4: .3f}        "
            print(status_line, end='', flush=True)

    def stop_keyboard_listener(self):
        self.running = False
        if self.keyboard_thread:
            self.keyboard_thread.join(timeout=1.0)

def main():
    rclpy.init()
    
    print("\r=========================================================")
    print("\r純手動控制模式已啟動！")
    print("\r[左手] 使用 w/s 鍵控制下方板子")
    print("\r[右手] 使用 i/k 鍵控制上方板子")
    print("\r按下 ESC 鍵即可安全退出系統")
    print("\r=========================================================")
    
    node = State()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    
    try:
        while rclpy.ok() and not node.exit_requested:
            executor.spin_once(timeout_sec=0.1)
    except KeyboardInterrupt:
        print("\r\n ROS 2 Execution Terminated.")
    finally:
        node.stop_keyboard_listener()
        executor.shutdown()
        node.destroy_node()
        
    rclpy.shutdown()

if __name__ == '__main__':
    main()
