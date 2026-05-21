import csv
import random
import math

# 🎯 採用你的專屬黃金邊界 (以你實測為準！)
X_MIN = -0.1737
X_MAX = 0.1744
Z_MIN = -0.1407
Z_MAX = 0.1393
Y_MIN = 0.0308
Y_MAX = 0.3491

def calculate_theoretical_landing(x, y, z, vx, vy, vz):
    if abs(vy) < 1e-6:
        return None
        
    target_y = Y_MAX if vy > 0 else Y_MIN
    t = (target_y - y) / vy
    
    if t <= 0:
        return None

    z_width = Z_MAX - Z_MIN
    unrolled_z = z + vz * t
    shifted_z = (unrolled_z - Z_MIN)
    rem_z = shifted_z % (2 * z_width)
    land_z = Z_MIN + rem_z if rem_z < z_width else Z_MIN + (2 * z_width - rem_z)

    x_width = X_MAX - X_MIN
    unrolled_x = x + vx * t
    shifted_x = (unrolled_x - X_MIN)
    rem_x = shifted_x % (2 * x_width)
    land_x = X_MIN + rem_x if rem_x < x_width else X_MIN + (2 * x_width - rem_x)

    return land_x, target_y, land_z

def main():
    csv_path = '/workspace/KNN/src/KNN_section3/training_data.csv'
    target_samples = 300000 
    
    # 🌟 核心對齊 3b.pdf：將速度強制鎖死在這 4 個離散等級
    speed_levels = [0.01, 0.1, 0.2, 0.3]
    
    print(f"🚀 開始生成 {target_samples} 筆訓練資料...")
    print("✨ 座標採用【專屬黃金邊界】，速度採用 3b.pdf 的離散等級 ✨")
    
    with open(csv_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['x', 'y', 'z', 'vx', 'vy', 'vz', 'land_x', 'land_z'])
        
        count = 0
        while count < target_samples:
            # 依據你的黃金邊界生成球體位置
            x = random.uniform(X_MIN, X_MAX)
            y = random.uniform(Y_MIN + 0.01, Y_MAX - 0.01) 
            z = random.uniform(Z_MIN, Z_MAX)
            
            # 1. 隨機抽取一個離散速度等級
            speed = random.choice(speed_levels)
            
            # 2. 隨機生成 3D 方向向量
            dx = random.uniform(-1.0, 1.0)
            dy = random.uniform(-1.0, 1.0)
            dz = random.uniform(-1.0, 1.0)
            
            # 3. 計算向量長度
            length = math.sqrt(dx**2 + dy**2 + dz**2)
            if length < 1e-6:
                continue
                
            # 4. 正規化並乘上離散速度 (確保總速度大小絕對等於 speed_levels 的值)
            vx = (dx / length) * speed
            vy = (dy / length) * speed
            vz = (dz / length) * speed
            
            result = calculate_theoretical_landing(x, y, z, vx, vy, vz)
            
            if result is not None:
                land_x, target_y, land_z = result
                writer.writerow([x, y, z, vx, vy, vz, land_x, land_z])
                count += 1
                
                if count % 10000 == 0:
                    print(f"✅ 已生成 {count} / {target_samples} 筆...")
                    
    print(f"🎉 成功！所有資料已寫入 {csv_path}")

if __name__ == '__main__':
    main()