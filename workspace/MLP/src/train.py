import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import argparse
import os

def main():
    # 1. 設定命令列解析器
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        'csv_file', 
        nargs='?', 
        default='training_data.csv', 
        help="請輸入要訓練的 CSV 檔名"
    )
    args = parser.parse_args()
    CSV_FILE = args.csv_file
        
    if not os.path.exists(CSV_FILE):
        print(f"錯誤：找不到檔案 '{CSV_FILE}'。")
        return

    # 2. 讀取資料與預處理 
    print(f"正在讀取資料集: {CSV_FILE}")
    df = pd.read_csv(CSV_FILE)
    
    X = df.iloc[:, :6].values
    y = df.iloc[:, 6].values  
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 3. 建立 MLP 模型
    # hidden_layer_sizes=(64, 64) 代表兩個隱藏層，加上輸入與輸出層剛好是完整的結構
    print("\n建立並開始訓練模型")
    model = MLPRegressor(
        hidden_layer_sizes=(64,64),  # 神經元數量
        activation='relu',           # 激活函數
        solver='adam',               # 優化器 有慣性與自動換檔
        learning_rate_init=0.001,    # 初始學習率
        max_iter=500,                # 最大訓練回合數 (Epochs)
        random_state=42,             # 固定隨機數生成器的種子
        verbose=True,                # 設為 True 會在終端機印出每一輪的 Loss
        batch_size=128,              # 每個 iteration 輸入的資料量
        tol=1e-4,                    # loss 變化小於 0.0001 才算沒進步
        n_iter_no_change=10          # 連續 10 輪都沒進步就停止
    )
    
    # 4. 完成訓練
    model.fit(X_train_scaled, y_train)
    
    # 5. 評估模型準確度
    print("\n驗證模型準確度")
    y_pred = model.predict(X_test_scaled)
    
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"測試集 MSE: {mse:.6f}")
    print(f"測試集 MAE: {mae:.6f} m")
    
    # 6. 儲存模型與標準化器
    # sklearn 的模型可以直接用 joblib 存成一個檔案
    joblib.dump(model, 'model.pkl')
    joblib.dump(scaler, 'scaler.pkl')
    print("\n模型已儲存為 'model.pkl'，標準化器已儲存為 'scaler.pkl'")

if __name__ == '__main__':
    main()