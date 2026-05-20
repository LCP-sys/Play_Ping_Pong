import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import Float32
from geometry_msgs.msg import Point
import math

class State(Node):
    def __init__(self):
        super().__init__('state')

        # ==========================================
        # 1. 真實物理牆壁邊界 (從截圖精確計算，用於反彈)
        # ==========================================
        self.wall_x_min, self.wall_x_max = -0.184, 0.184
        self.wall_z_min, self.wall_z_max = -0.150, 0.150

        # ==========================================
        # 2. 板子移動極限 (保護 Unity Slider)
        # ==========================================
        self.slider_z_limit = 0.12 

        # === 其他環境常數 ===
        self.ball_radius = 0.01       
        self.bottom_board_y = 0.053   
        self.top_board_y = 0.332      
        
        self.bottom_hit_y = self.bottom_board_y + self.ball_radius
        self.top_hit_y = self.top_board_y - self.ball_radius

        self.ball_p = [0.0, 0.0, 0.0]
        self.ball_v = [0.0, 0.0, 0.0]
        self.goal_ball = (0.0, 0.0, 0.0, 0.0, 0.0) 
        
        self.goal_s1 = self.goal_s2 = self.goal_s3 = 0.0
        self.goal_s4 = self.goal_s5 = self.goal_s6 = 0.0
        
        self.s1 = self.s2 = self.s3 = 0.0
        self.s4 = self.s5 = self.s6 = 0.0

        self.create_subscription(Point, '/ball_position', lambda msg: self._update_list(self.ball_p, msg.x, msg.y, msg.z), 10)
        self.create_subscription(Float32, '/ball_vx', lambda msg: self._update_val(self.ball_v, 0, msg.data), 10)
        self.create_subscription(Float32, '/ball_vy', lambda msg: self._update_val(self.ball_v, 1, msg.data), 10)
        self.create_subscription(Float32, '/ball_vz', lambda msg: self._update_val(self.ball_v, 2, msg.data), 10)

        self.create_subscription(Float32, '/down_plus',  lambda msg: setattr(self, 's1', msg.data), 10)
        self.create_subscription(Float32, '/down_min',   lambda msg: setattr(self, 's2', msg.data), 10)
        self.create_subscription(Float32, '/down_minus', lambda msg: setattr(self, 's3', msg.data), 10)
        self.create_subscription(Float32, '/up_plus',    lambda msg: setattr(self, 's4', msg.data), 10)
        self.create_subscription(Float32, '/up_min',     lambda msg: setattr(self, 's5', msg.data), 10)
        self.create_subscription(Float32, '/up_minus',   lambda msg: setattr(self, 's6', msg.data), 10)

        self.goal_pubs = {
            f'goal_s{i}': self.create_publisher(Float32, f'/goal_s{i}', 10) for i in range(1, 7)
        }

        self.get_logger().info("✅ 純理論解已啟動！(物理牆壁與滑桿極限已精確校正)")
        
        self.debug_timer = self.create_timer(1.0, self.debug_print)
        self.math_control_timer = self.create_timer(0.001, self.update_math_control)

    def _update_list(self, lst, x, y, z): lst[:] = [x, y, z]
    def _update_val(self, lst, idx, val): lst[idx] = val

    def update_math_control(self):
        vy = self.ball_v[1]
        
        if abs(vy) < 1e-3:
            target_y = self.top_hit_y if self.ball_p[1] >= 0.15 else self.bottom_hit_y
            self.goal_ball = (self.ball_p[0], target_y, self.ball_p[2], 999.0, 999.0)
            self.auto_go_to_goal()
            return

        target_y = self.top_hit_y if vy > 0 else self.bottom_hit_y

        # 這裡使用真實的 0.15 與 0.184 牆壁來算反彈
        result = self.predict_landing_with_walls_and_radius(
            *self.ball_p, *self.ball_v, target_y,
            self.wall_x_min, self.wall_x_max,
            self.wall_z_min, self.wall_z_max,
            self.ball_radius
        )

        if result[0] is not None:
            self.goal_ball = result
            self.auto_go_to_goal()

    def predict_landing_with_walls_and_radius(self, posX, posY, posZ, velX, velY, velZ, target_y,
                                              x_min, x_max, z_min, z_max, radius):
        if abs(velY) < 1e-6:
            return (None, None, None, None, None)
            
        t_ratio = (target_y - posY) / velY
        if t_ratio <= 0:
            return (None, None, None, None, None)

        x_min_eff, x_max_eff = x_min + radius, x_max - radius
        z_min_eff, z_max_eff = z_min + radius, z_max - radius

        span_x, span_z = x_max_eff - x_min_eff, z_max_eff - z_min_eff
        bounces_x = abs(velX * t_ratio) / span_x if span_x > 0 else 0
        bounces_z = abs(velZ * t_ratio) / span_z if span_z > 0 else 0
        expected_bounces = max(bounces_x, bounces_z)

        def reflect_1d(p, v, low, high, ratio):
            span = high - low
            if span <= 0: return p + v * ratio
            offset = (p + v * ratio) - low
            cycles = math.floor(offset / span)
            remainder = offset - cycles * span
            return low + remainder if cycles % 2 == 0 else high - remainder

        landX = reflect_1d(posX, velX, x_min_eff, x_max_eff, t_ratio)
        landZ = reflect_1d(posZ, velZ, z_min_eff, z_max_eff, t_ratio)
        
        return (landX, target_y, landZ, expected_bounces, t_ratio)

    def auto_go_to_goal(self):
        x, y, pred_z, expected_bounces, time_to_hit = self.goal_ball
            
        if pred_z is None: return

        current_z = self.ball_p[2]
        
        # 最終發佈給 Unity 前，強制鎖在滑桿極限 (±0.12)
        # 這樣如果球落點在 0.14，板子會停在 0.12，剛好用邊角接住球！
        clamped_pred_z = max(-self.slider_z_limit, min(self.slider_z_limit, pred_z))
        clamped_current_z = max(-self.slider_z_limit, min(self.slider_z_limit, current_z))

        if expected_bounces > 3.0 and time_to_hit > 0.6:
            active_target_z = clamped_current_z
        else:
            active_target_z = clamped_pred_z

        top_dir, bottom_dir = -1.0, 1.0 
        goal_top_active = active_target_z * top_dir
        goal_bottom_active = active_target_z * bottom_dir 
        goal_top_idle = clamped_current_z * top_dir
        goal_bottom_idle = clamped_current_z * bottom_dir

        if y >= 0.15:  
            self.goal_s4 = self.goal_s5 = self.goal_s6 = goal_top_active
            self.goal_s1 = self.goal_s2 = self.goal_s3 = goal_bottom_idle
        else:          
            self.goal_s1 = self.goal_s2 = self.goal_s3 = goal_bottom_active
            self.goal_s4 = self.goal_s5 = self.goal_s6 = goal_top_idle

        for name in self.goal_pubs.keys():
            self.publish_goal(name, getattr(self, name))

    def publish_goal(self, goal_name: str, value: float):
        if goal_name in self.goal_pubs:
            msg = Float32()
            msg.data = float(value)
            self.goal_pubs[goal_name].publish(msg)

    def debug_print(self):
        active_side = "TOP " if self.ball_v[1] > 0 else "DOWN"
        self.get_logger().info(
            f"\n[Ball] P=({self.ball_p[0]:.3f}, {self.ball_p[1]:.3f}, {self.ball_p[2]:.3f}) | "
            f"ETA: {self.goal_ball[4]:.2f}s | Target Z: {self.goal_ball[2]:.3f}\n"
            f"[{'>> ' if active_side=='DOWN' else '   '}DOWN 板子 (s1,s2,s3)] 實際位置: {self.s1:.3f}, {self.s2:.3f}, {self.s3:.3f} | 指令: {self.goal_s1:.3f}\n"
            f"[{'>> ' if active_side=='TOP ' else '   '}TOP  板子 (s4,s5,s6)] 實際位置: {self.s4:.3f}, {self.s5:.3f}, {self.s6:.3f} | 指令: {self.goal_s4:.3f}"
        )

def main():
    rclpy.init()
    node = State()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        print("\n程式已安全終止")
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()