import numpy as np
import pandas as pd
import joblib
import os
from sklearn.metrics import mean_squared_error, mean_absolute_error

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
    # 1. 設定你要測驗的模型檔案 (你可以改成你想測試的特定檔名)
    model_file = 'model.pkl'
    scaler_file = 'scaler.pkl'
    
    if not os.path.exists(model_file) or not os.path.exists(scaler_file):
        print(f"錯誤：找不到 '{model_file}' 或 '{scaler_file}'。")
        print("請確保你有先執行 train.py 把模型存下來喔！")
        return

    print("=== 1. 開始生成 100000 筆純隨機題目 ===")
    valid_samples = []
    target_count = 100000
    
    # 不斷生成，直到收集滿 10,000 筆有效落點的數據
    while len(valid_samples) < target_count:
        px = np.random.uniform(-0.17, 0.17)
        py = np.random.uniform(0.05, 0.33)
        pz = np.random.uniform(-0.135, 0.135)
        vx = np.random.uniform(-2.5, 2.5)
        vy = np.random.uniform(-2.5, 2.5)
        vz = np.random.uniform(-2.5, 2.5)
        
        # 避開 vy 趨近於 0，導致球停滯的情況
        if abs(vy) < 0.01:
            continue
            
        true_landZ = predict_land_z(py, pz, vy, vz)
        
        # 只要是有效數據，就加入考卷中
        if true_landZ is not None:
            valid_samples.append([px, py, pz, vx, vy, vz, true_landZ])

    # 轉成 DataFrame 方便萃取特徵與解答
    columns = ['pos_x', 'pos_y', 'pos_z', 'vel_x', 'vel_y', 'vel_z', 'land_z']
    df_test = pd.DataFrame(valid_samples, columns=columns)
    
    # X_test_new 是題目，y_test_true 是標準答案
    X_test_new = df_test.iloc[:, :6].values
    y_test_true = df_test.iloc[:, 6].values
    
    print("題目生成完畢")

    # 2. 載入模型與標準化器
    print(f"\n=== 2. 載入模型 ({model_file}) 準備考試 ===")
    model = joblib.load(model_file)
    scaler = joblib.load(scaler_file)
    
    # 關鍵步驟：對這 10,000 筆新題目進行特徵縮放
    # 一定要用 scaler.transform()，不能用 fit_transform()，這樣才符合當初訓練的尺度
    X_test_scaled = scaler.transform(X_test_new)
    
    # 3. 讓模型作答
    y_pred = model.predict(X_test_scaled)
    
    # 4. 批改考卷並輸出成績
    mse = mean_squared_error(y_test_true, y_pred)
    mae = mean_absolute_error(y_test_true, y_pred)
    
    print("\n=== 盲測結果 ===")
    print(f"測試資料量: {target_count} 筆純隨機未知數據")
    print(f"MSE (均方誤差): {mse:.6f}")
    print(f"MAE (平均絕對誤差): {mae:.6f} m")

if __name__ == "__main__":
    main()