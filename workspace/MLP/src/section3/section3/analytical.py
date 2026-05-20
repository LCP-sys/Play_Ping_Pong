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

        self.get_logger().info("=== 純粹理論解 (Math) 終極校準版啟動 ===")
        self.get_logger().info("已套用 [實測極值]、[形狀高度補償] 與 [非對稱邊界]")

        # ================= 根據實際診斷數據修正後的參數 =================
        # 這裡的數值是「球心能到達的極限」，因此不需要再額外加減半徑
        self.x_eff_min = -0.174
        self.x_eff_max =  0.174
        self.z_eff_min = -0.141
        self.z_eff_max =  0.139
        
        # Y 軸目標：依據板子肋條形狀與球體碰撞的實測極值
        self.top_board_y = 0.349    
        self.bottom_board_y = 0.031 
        
        # 上下半場判定中線
        self.midpoint_y = (self.top_board_y + self.bottom_board_y) / 2.0 
        # ================================================================
        
        self.mode = None
        self.ball_p = [0.0, 0.0, 0.0]
        self.ball_v = [0.0, 0.0, 0.0]
        self.goal_ball = [0.0, 0.0, 0.0]
        
        # 板子狀態
        self.s1 = self.s2 = self.s3 = self.s4 = self.s5 = self.s6 = 0.0
        self.goal_s1 = self.goal_s2 = self.goal_s3 = self.goal_s4 = self.goal_s5 = self.goal_s6 = 0.0

        self.keyboard_thread = None
        self.running = False
        self.debug_timer = None
        self.ai_control_timer = None  
        self.exit_requested = False

        # --- 建立訂閱者 (接收 Unity 資訊) ---
        self.create_subscription(Float32, '/ball_vx', self.vx_cb, 10)
        self.create_subscription(Float32, '/ball_vy', self.vy_cb, 10)
        self.create_subscription(Float32, '/ball_vz', self.vz_cb, 10)
        self.create_subscription(Point, '/ball_position', self.ball_cb, 10)
        self.create_subscription(Float32, '/down_plus', self.s1_cb, 10)
        self.create_subscription(Float32, '/down_min', self.s2_cb, 10)
        self.create_subscription(Float32, '/down_minus', self.s3_cb, 10)
        self.create_subscription(Float32, '/up_plus', self.s4_cb, 10)
        self.create_subscription(Float32, '/up_min', self.s5_cb, 10)
        self.create_subscription(Float32, '/up_minus', self.s6_cb, 10)

        # --- 建立發佈者 (控制 Unity 板子) ---
        self.goal_pubs = {f'goal_s{i}': self.create_publisher(Float32, f'/goal_s{i}', 10) for i in range(1, 7)}

    # ----- ROS 2 Callbacks -----
    def ball_cb(self, msg: Point): self.ball_p = [msg.x, msg.y, msg.z]
    def vx_cb(self, msg): self.ball_v[0] = msg.data
    def vy_cb(self, msg): self.ball_v[1] = msg.data
    def vz_cb(self, msg): self.ball_v[2] = msg.data
    def s1_cb(self, msg): self.s1 = msg.data
    def s2_cb(self, msg): self.s2 = msg.data
    def s3_cb(self, msg): self.s3 = msg.data
    def s4_cb(self, msg): self.s4 = msg.data
    def s5_cb(self, msg): self.s5 = msg.data
    def s6_cb(self, msg): self.s6 = msg.data

    def set_mode(self, mode: str):
        self.mode = mode
        self.get_logger().info(f"\n當前模式切換為: {mode.upper()}")
     
        if self.ai_control_timer is not None:
            self.ai_control_timer.cancel()
            self.ai_control_timer = None
            
        if self.debug_timer is not None:
            self.debug_timer.cancel()
            self.debug_timer = None

        if mode == 'manual':
            self.get_logger().info("keyboard：")
            self.get_logger().info("  q/w → goal_s1  +/-   |  e/r → goal_s2  +/-")
            self.get_logger().info("  t/y → goal_s3  +/-   |  u/i → goal_s4  +/-")
            self.get_logger().info("  o/p → goal_s5  +/-   |  a/s → goal_s6  +/-")
            self.get_logger().info("  ESC → exit manual mode")
            self.start_keyboard_listener()

        elif mode == 'math':
            self.ai_control_timer = self.create_timer(0.005, self.update_math_control)
            # 每 0.1 秒刷新一次儀表板
            self.debug_timer = self.create_timer(0.1, self.debug_print)

    def debug_print(self):
        if self.mode == 'math':
            bx, by, bz = self.ball_p
            # 確保不會印出 None 報錯
            if isinstance(self.goal_ball, tuple) and self.goal_ball[0] is not None:
                gx, gy, gz = self.goal_ball
                print(f"\r[精準追蹤] 球位 (x:{bx: 6.3f}, y:{by: 6.3f}, z:{bz: 6.3f}) | 🎯 預測落點 X:{gx: 6.3f}, Z:{gz: 6.3f}   ", end='', flush=True)
            else:
                print(f"\r[精準追蹤] 球位 (x:{bx: 6.3f}, y:{by: 6.3f}, z:{bz: 6.3f}) | ⏳ 等待 Y 軸動能...         ", end='', flush=True)

    def update_math_control(self):
        vy = self.ball_v[1]
        
        # 根據 Y 軸速度決定目標牆面 (加入微小閥值防抖)
        if vy > 1e-4:
            target_y = self.top_board_y
        elif vy < -1e-4:
            target_y = self.bottom_board_y
        else:
            return 

        result = self.predict_landing_with_formula(
            self.ball_p[0], self.ball_p[1], self.ball_p[2],
            self.ball_v[0], self.ball_v[1], self.ball_v[2],
            target_y,
            self.x_eff_min, self.x_eff_max,
            self.z_eff_min, self.z_eff_max
        )

        if result[0] is None:
            return

        self.goal_ball = result
        self.auto_go_to_goal()

    def predict_landing_with_formula(self, posX, posY, posZ, velX, velY, velZ, target_y,
                                     eff_x_min, eff_x_max, eff_z_min, eff_z_max):
        
        if abs(velY) < 1e-6: return (None, None, None)
            
        t = (target_y - posY) / velY
        if t <= 0: return (None, None, None)

        # 更簡潔的反射公式 (直接使用實測有效邊界)
        def calculate_reflection(p0, v, t, eff_min, eff_max):
            width = eff_max - eff_min
            if width <= 0: return p0
            
            unrolled_pos = p0 + v * t
            shifted = unrolled_pos - eff_min
            period = 2 * width
            
            rem = shifted % period 
            return eff_min + rem if rem < width else eff_min + (period - rem)

        landX = calculate_reflection(posX, velX, t, eff_x_min, eff_x_max)
        landZ = calculate_reflection(posZ, velZ, t, eff_z_min, eff_z_max)
        
        return (landX, target_y, landZ)

    def publish_goal(self, goal_name: str, value: float):
        if goal_name in self.goal_pubs:
            msg = Float32()
            msg.data = float(value)
            self.goal_pubs[goal_name].publish(msg)

    def auto_go_to_goal(self):
        x, y, z = self.goal_ball
        
        # Z 軸鏡像轉換
        goal_1 = -z
        goal_2 = z 
        
        self.goal_s1 = self.goal_s2 = self.goal_s3 = self.goal_s4 = self.goal_s5 = self.goal_s6 = 0.0

        # 使用計算出來的精準中線來判斷球在哪半場
        if y > self.midpoint_y:
            # 球往上飛 -> 上排 3 塊板子出動
            self.goal_s4 = goal_1
            self.goal_s5 = goal_1
            self.goal_s6 = goal_1
        elif y < self.midpoint_y:
            # 球往下飛 -> 下排 3 塊板子出動
            self.goal_s1 = goal_2
            self.goal_s2 = goal_2
            self.goal_s3 = goal_2
                
        for name in ['goal_s1','goal_s2','goal_s3','goal_s4','goal_s5','goal_s6']:
            self.publish_goal(name, getattr(self, name))

    # ================= 鍵盤控制保留 =================
    def start_keyboard_listener(self):
        if self.keyboard_thread and self.keyboard_thread.is_alive(): return
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
        step = 0.1
        mapping = {
            'q': ('goal_s1', +step), 'w': ('goal_s1', -step),
            'e': ('goal_s2', +step), 'r': ('goal_s2', -step),
            't': ('goal_s3', +step), 'y': ('goal_s3', -step),
            'u': ('goal_s4', +step), 'i': ('goal_s4', -step),
            'o': ('goal_s5', +step), 'p': ('goal_s5', -step),
            'a': ('goal_s6', +step), 's': ('goal_s6', -step),
        }
        if key == '\x1b':
            self.running = False
            self.exit_requested = True
            return
        if key in mapping:
            attr, delta = mapping[key]
            new_val = getattr(self, attr) + delta
            setattr(self, attr, new_val)
            self.publish_goal(attr, new_val)
            robot_attr = attr.replace('goal_', '')
            robot_val = getattr(self, robot_attr)
            print(f"\r{attr} = {new_val:.3f} | {robot_attr} = {robot_val:.3f}  ", end='', flush=True)

    def stop_keyboard_listener(self):
        self.running = False
        if self.keyboard_thread:
            self.keyboard_thread.join(timeout=1.0)

def main():
    rclpy.init()
    while True:
        node = State()
        while True:
            print("\n==================================")
            print(" m  : 手動鍵盤測試 (Manual)")
            print(" mm : 物理理論解預測 (Math) - 終極校準版")
            print("==================================")
            choice = input("請選擇模式 (m / mm): ").strip().lower()
            if choice == 'm':
                node.set_mode('manual')
                break
            elif choice == 'mm':
                node.set_mode('math')
                break
            else:
                print("輸入錯誤，請重新輸入。")

        executor = SingleThreadedExecutor()
        executor.add_node(node)
        try:
            while rclpy.ok() and not node.exit_requested:
                executor.spin_once(timeout_sec=0.1)
        except KeyboardInterrupt:
            print("\n 已手動斷開連線")
            break
        finally:
            node.stop_keyboard_listener()
            executor.shutdown()
            node.destroy_node()
            
        if not node.exit_requested:
            break
            
    rclpy.shutdown()

if __name__ == '__main__':
    main()