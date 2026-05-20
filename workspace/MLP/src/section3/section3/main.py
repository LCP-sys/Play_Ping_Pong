import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Point
from rclpy.executors import SingleThreadedExecutor

# 引入機器學習必備套件
import numpy as np
import joblib
import os
import sys

class State(Node):
    def __init__(self):
        super().__init__('state')

        
        # 載入模型與標準化器
        model_path = '/workspace/MLP/src/model.pkl'
        scaler_path = '/workspace/MLP/src/scaler.pkl'
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            self.get_logger().error(f"啟動失敗！找不到 {model_path} 或 {scaler_path}。")
            sys.exit(1) 
            
        try:
            self.ai_model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.get_logger().info("成功載入模型與標準化器")
        except Exception as e:
            self.get_logger().error(f"讀取模型時發生錯誤: {e}")
            sys.exit(1)

        # 物理環境參數
        self.top_board_y = 0.349    
        self.bottom_board_y = 0.031 
        self.midpoint_y = (self.top_board_y + self.bottom_board_y) / 2.0 
        
        self.ball_p = [0.0, 0.0, 0.0]
        self.ball_v = [0.0, 0.0, 0.0]
        self.goal_ball = [0.0, 0.0, 0.0]

        # 建立訂閱者與發佈者 
        self.create_subscription(Float32, '/ball_vx', self.vx_cb, 10)
        self.create_subscription(Float32, '/ball_vy', self.vy_cb, 10)
        self.create_subscription(Float32, '/ball_vz', self.vz_cb, 10)
        self.create_subscription(Point, '/ball_position', self.ball_cb, 10)
        self.goal_pubs = {f'goal_s{i}': self.create_publisher(Float32, f'/goal_s{i}', 10) for i in range(1, 7)}

        # 啟動 AI 控制迴圈 (每 0.005 秒預測一次)
        self.create_timer(0.005, self.update_ai_control)
        # 啟動終端機顯示迴圈 (每 0.1 秒刷新一次畫面)
        self.create_timer(0.1, self.debug_print)

    # ROS 2 Callbacks
    def ball_cb(self, msg: Point): self.ball_p = [msg.x, msg.y, msg.z]
    def vx_cb(self, msg): self.ball_v[0] = msg.data
    def vy_cb(self, msg): self.ball_v[1] = msg.data
    def vz_cb(self, msg): self.ball_v[2] = msg.data

    def debug_print(self):
        bx, by, bz = self.ball_p
        if isinstance(self.goal_ball, tuple) and self.goal_ball[2] is not None:
            gz = self.goal_ball[2]
            print(f"\r[自動追蹤] 球位 (x:{bx: 5.2f}, y:{by: 5.2f}, z:{bz: 5.2f}) | 預測落點 Z:{gz: 6.3f}   ", end='', flush=True)
        else:
            print(f"\r[自動追蹤] 球位 (x:{bx: 5.2f}, y:{by: 5.2f}, z:{bz: 5.2f}) | 等待球體移動...         ", end='', flush=True)

    # 控制核心邏輯
    def update_ai_control(self):
        bx, by, bz = self.ball_p
        vx, vy, vz = self.ball_v
        
        # 根據 Y 軸速度決定目標牆面
        if vy > 1e-4:
            target_y = self.top_board_y
        elif vy < -1e-4:
            target_y = self.bottom_board_y
        else:
            return 

        # 1. 整理目前的 6 個特徵
        features = np.array([[bx, by, bz, vx, vy, vz]])
        
        # 2. 使用 scaler 將數值標準化
        scaled_features = self.scaler.transform(features)
        
        # 3. 呼叫模型進行預測
        predicted_z = self.ai_model.predict(scaled_features)[0]

        # 寫入預測目標
        self.goal_ball = (0.0, target_y, predicted_z)
        self.auto_go_to_goal()

    # 發佈目標與半場判斷
    def publish_goal(self, goal_name: str, value: float):
        msg = Float32()
        msg.data = float(value)
        self.goal_pubs[goal_name].publish(msg)

    def auto_go_to_goal(self):
        _, y, z = self.goal_ball
        goal_1 = -z 
        goal_2 = z 
        
        # 判斷球在哪半場，並歸零不需移動的板子
        if y > self.midpoint_y:
            for name in ['goal_s4', 'goal_s5', 'goal_s6']:
                self.publish_goal(name, goal_1)
            for name in ['goal_s1', 'goal_s2', 'goal_s3']:
                self.publish_goal(name, 0.0)
        elif y < self.midpoint_y:
            for name in ['goal_s1', 'goal_s2', 'goal_s3']:
                self.publish_goal(name, goal_2)
            for name in ['goal_s4', 'goal_s5', 'goal_s6']:
                self.publish_goal(name, 0.0)

def main():
    rclpy.init()
    print("==================================\n")
    print(" 提示：按 Ctrl+C 即可安全退出")
    print("==================================\n")
    
    node = State()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        print("\n\n 已手動斷開連線")
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()