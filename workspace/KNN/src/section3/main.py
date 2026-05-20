import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Point
import numpy as np
import joblib
import math

class State(Node):
    def __init__(self):
        super().__init__('state')
        
        # 1. 物理邊界與模型路徑 (請確認路徑正確)
        self.model_path = "/workspace/KNN/src/section3/knn_model.pkl"
        self.z_min, self.z_max = -0.1182, 0.1182
        
        try:
            self.model = joblib.load(self.model_path)
            self.get_logger().info("✅ 模型載入成功")
        except:
            self.get_logger().error("❌ 找不到模型檔案")
            self.model = None

        # 狀態變數
        self.ball_p = [0.0, 0.0, 0.0]
        self.ball_v = [0.0, 0.0, 0.0]
        self.goal_ball = [0.0, 0.0, 0.0]

        # Subscribers
        self.create_subscription(Float32, '/ball_vx', lambda m: self.set_v(0, m.data), 10)
        self.create_subscription(Float32, '/ball_vy', lambda m: self.set_v(1, m.data), 10)
        self.create_subscription(Float32, '/ball_vz', lambda m: self.set_v(2, m.data), 10)
        self.create_subscription(Point, '/ball_position', self.ball_cb, 10)

        # Publishers
        self.pubs = {f'goal_s{i}': self.create_publisher(Float32, f'goal_s{i}', 10) for i in range(1, 7)}

        # 🚀 啟動即進入 AI 模式 (0.01秒執行一次 update_ai)
        self.get_logger().info(">>> 按 Ctrl+C 退出 <<<")
        # 多印一行空白，避免後面的 \r 蓋掉上面這行提示
        print("") 
        self.ai_timer = self.create_timer(0.01, self.update_ai)

    def set_v(self, i, v): 
        self.ball_v[i] = v

    def ball_cb(self, m): 
        self.ball_p = [m.x, m.y, m.z]

    def update_ai(self):
        if self.model is None: return
        
        x, y, z = self.ball_p
        vx, vy, vz = self.ball_v

        # 1. 極低速過濾（防止球停下來時板子亂動）
        if abs(vy) < 1e-4: return

        # 2. 進行預測
        input_data = np.array([[x, y, z, vx, vy, vz]])
        pred = self.model.predict(input_data)[0]
        
        # 取得原始預測值
        raw_target_x = pred[0]
        raw_target_z = pred[2] if len(pred) > 2 else pred[1]

        # 🌟 即時輸出預測落點 Z (改為同一行持續刷新)
        print(f"\r預測落點 Z: {raw_target_z:.4f}      ", end='', flush=True)

        # 🌟 核心修正：穩定器邏輯
        # 如果新預測跟舊目標差不到 0.01 (1公分)，我們就維持舊目標，不讓板子抖動
        dist = math.hypot(raw_target_x - self.goal_ball[0], raw_target_z - self.goal_ball[2])
        
        if dist > 0.01: # 只有當預測落點變化夠大時，才更新目標
            self.goal_ball[0] = raw_target_x
            self.goal_ball[2] = raw_target_z
        
        # 3. 執行移動
        self.auto_go()

    def auto_go(self):
        # 取得球的垂直速度與預測座標
        vy = self.ball_v[1]
        target_x, _, target_z = self.goal_ball
        
        # 限制範圍，避免板子撞牆
        target_z = np.clip(target_z, self.z_min, self.z_max)
        
        # 初始化所有馬達指令
        out_vals = {f'goal_s{i}': 0.0 for i in range(1, 7)}
        
        # 關鍵邏輯：
        side_limit = 0.02 # 分辨左右邊的門檻
        
        if vy < -1e-4: # 球往下掉 -> 啟動下層防守
            if target_x > side_limit:    out_vals['goal_s1'] = float(target_z)
            elif target_x < -side_limit: out_vals['goal_s3'] = float(target_z)
            else:                        out_vals['goal_s2'] = float(target_z)
            
        elif vy > 1e-4: # 球往上升 -> 啟動上層防守
            if target_x > side_limit:    out_vals['goal_s4'] = float(-target_z) 
            elif target_x < -side_limit: out_vals['goal_s6'] = float(-target_z)
            else:                        out_vals['goal_s5'] = float(-target_z)

        # 發布指令
        for n, v in out_vals.items():
            self.pubs[n].publish(Float32(data=v))
            
# 確保 main 函數完全靠左，沒有縮排
def main(args=None):
    rclpy.init(args=args)
    node = State()
    
    try:
        # 直接使用原生的 spin 阻塞主執行緒即可，Timer 會自動在背景觸發
        rclpy.spin(node)
    except KeyboardInterrupt:
        # 收到 Ctrl+C 時，先換行避免提示字串跟預測值黏在一起
        print("") 
        node.get_logger().info(">>> 收到終止訊號，關閉節點中...")
    finally:
        node.destroy_node()
        # 確保 rclpy 正確關閉
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()