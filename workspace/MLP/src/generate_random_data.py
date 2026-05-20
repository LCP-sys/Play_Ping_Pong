import numpy as np
import pandas as pd

# 物理邊界
EFF_X_MIN, EFF_X_MAX = -0.174, 0.174
EFF_Z_MIN, EFF_Z_MAX = -0.141, 0.139
TOP_BOARD_Y, BOTTOM_BOARD_Y = 0.349, 0.031 

def predict_land_z(posY, posZ, velY, velZ):

    if velY > 1e-4:
        target_y = TOP_BOARD_Y
    elif velY < -1e-4:
        target_y = BOTTOM_BOARD_Y
    else:
        return None

    t = (target_y - posY) / velY
    if t <= 0: 
        return None
    
    width = EFF_Z_MAX - EFF_Z_MIN
    if width <= 0: 
        return posZ
        
    unrolled_pos = posZ + velZ * t
    shifted = unrolled_pos - EFF_Z_MIN
    period = 2 * width
    rem = shifted % period 
    
    return EFF_Z_MIN + (rem if rem < width else period - rem)

def main():
    # 設定要生成的總筆數
    num_samples = 500000
    print("=== 開始生成訓練數據===")
    print(f"正在運算 {num_samples} 筆隨機組合...")

    data = []
    for _ in range(num_samples):
        # 1. 隨機均勻採樣 
        px = np.random.uniform(-0.17, 0.17)
        py = np.random.uniform(0.05, 0.33)
        pz = np.random.uniform(-0.135, 0.135)
        
        vx = np.random.uniform(-2.5, 2.5)
        vy = np.random.uniform(-2.5, 2.5)
        # 避開 vy==0
        if(abs(vy)<0.01):
            if(vy>0):
                vy=np.random.uniform(0.01, 2.5)
            else:
                vy=np.random.uniform(-2.5, -0.01)
            
        vz = np.random.uniform(-2.5, 2.5)
        
        # 2. 取得完美落點
        landZ = predict_land_z(py, pz, vy, vz)
        
        # 3. 記錄有效數據 
        if landZ is not None:
            data.append({
                'pos_x': round(px, 4),
                'pos_y': round(py, 4),
                'pos_z': round(pz, 4),
                'vel_x': round(vx, 4),
                'vel_y': round(vy, 4),
                'vel_z': round(vz, 4),
                'land_z': round(landZ, 4) 
            })

    # 4. 轉換為 DataFrame 
    df = pd.DataFrame(data)
    
    # 5. 徹底打亂整份資料的順序
    df = df.sample(frac=1).reset_index(drop=True)
    
    # 6. 輸出
    output_filename = "random_training_data.csv"
    df.to_csv(output_filename, index=False)
    print(f"有效數據共 {len(df)} 筆，已儲存至 {output_filename}")

if __name__ == "__main__":
    main()