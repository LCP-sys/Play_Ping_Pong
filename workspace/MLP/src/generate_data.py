import numpy as np
import pandas as pd
import itertools

# 物理邊界
EFF_X_MIN = -0.174
EFF_X_MAX =  0.174
EFF_Z_MIN = -0.141
EFF_Z_MAX =  0.139
TOP_BOARD_Y = 0.349    
BOTTOM_BOARD_Y = 0.031 

def predict_land_z(posY, posZ, velY, velZ):
    """
    只計算 Z 軸的最終落點
    """
    # 根據 Y 軸速度 (方向) 決定目標高度
    if velY > 1e-4:
        target_y = TOP_BOARD_Y
    elif velY < -1e-4:
        target_y = BOTTOM_BOARD_Y
    else:
        return None

    # 計算抵達目標平面的時間 t
    t = (target_y - posY) / velY
    if t <= 0:
        return None

    # 計算 Z 軸的反射落點
    width = EFF_Z_MAX - EFF_Z_MIN
    if width <= 0: 
        return posZ
        
    unrolled_pos = posZ + velZ * t
    shifted = unrolled_pos - EFF_Z_MIN
    period = 2 * width
    
    rem = shifted % period 
    landZ = EFF_Z_MIN + rem if rem < width else EFF_Z_MIN + (period - rem)
    
    return landZ

def main():    
    # 定義採樣範圍與點數 
    pos_x_vals = np.linspace(-0.17, 0.17, 5)
    pos_y_vals = np.linspace(0.05, 0.31, 5)
    pos_z_vals = np.linspace(-0.135, 0.135, 5)
    
    vel_x_vals = np.linspace(-2.5, 2.5, 5)
    vel_y_vals = np.array([-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]) 
    vel_z_vals = np.linspace(-2.5, 2.5, 5)

    all_combinations = list(itertools.product(
        pos_x_vals, pos_y_vals, pos_z_vals, 
        vel_x_vals, vel_y_vals, vel_z_vals
    ))
    
    print(f"預計計算總組合數: {len(all_combinations)} 筆")

    dataset = []
    
    # 開始跑模擬
    for combo in all_combinations:
        px, py, pz, vx, vy, vz = combo
        
        landZ = predict_land_z(py, pz, vy, vz)
        
        # 如果是有效的落點，就加入數據集
        if landZ is not None:
            dataset.append({
                'pos_x': round(px, 4),
                'pos_y': round(py, 4),
                'pos_z': round(pz, 4),
                'vel_x': round(vx, 4),
                'vel_y': round(vy, 4),
                'vel_z': round(vz, 4),
                'land_z': round(landZ, 4)
            })

    # 轉換成 Pandas DataFrame 並輸出 CSV
    df = pd.DataFrame(dataset)
    output_filename = "training_data.csv"
    df.to_csv(output_filename, index=False)
    
    print(f"有效數據共 {len(df)} 筆，已儲存至 {output_filename}")
if __name__ == "__main__":
    main()