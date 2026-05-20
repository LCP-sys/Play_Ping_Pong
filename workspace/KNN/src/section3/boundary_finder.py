import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point

class BoundaryFinder(Node):
    def __init__(self):
        super().__init__('boundary_finder')
        
        # 初始化極端值 (先設定成無限大與無限小，這樣任何數字進來都會被記錄)
        self.x_min = float('inf')
        self.x_max = float('-inf')
        self.y_min = float('inf')
        self.y_max = float('-inf')
        self.z_min = float('inf')
        self.z_max = float('-inf')
        
        # 訂閱球的位置頻道
        self.sub_pos = self.create_subscription(
            Point, 
            '/ball_position', 
            self.pos_callback, 
            10)
            
        self.get_logger().info('🕵️‍♂️ 邊界探測器已啟動！請讓 Unity 裡面的球開始瘋狂亂撞！')
        self.get_logger().info('等待接收資料中...')

    def pos_callback(self, msg):
        x, y, z = msg.x, msg.y, msg.z
        
        # 為了避免球掉出界外(掉到地板以下)污染數據，設定一個合理範圍 (假設 y 不會低於 -1)
        if y < -1.0:
            return

        updated = False

        # 檢查 X 軸
        if x < self.x_min: self.x_min = x; updated = True
        if x > self.x_max: self.x_max = x; updated = True
        
        # 檢查 Y 軸 (順便測量反彈高度)
        if y < self.y_min: self.y_min = y; updated = True
        if y > self.y_max: self.y_max = y; updated = True
        
        # 檢查 Z 軸
        if z < self.z_min: self.z_min = z; updated = True
        if z > self.z_max: self.z_max = z; updated = True

        # 只有在發現「新邊界」的時候才印出畫面，避免終端機被洗版
        if updated:
            print("\n" + "="*40)
            print(f"🔥 發現新邊界！目前極值：")
            print(f"X 軸 (左右): Min = {self.x_min:.4f}  |  Max = {self.x_max:.4f}")
            print(f"Z 軸 (前後): Min = {self.z_min:.4f}  |  Max = {self.z_max:.4f}")
            print(f"Y 軸 (上下): Min = {self.y_min:.4f}  |  Max = {self.y_max:.4f}")
            print("="*40)

def main(args=None):
    rclpy.init(args=args)
    node = BoundaryFinder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('邊界探測已結束。')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()