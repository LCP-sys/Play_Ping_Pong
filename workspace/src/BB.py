import pandas as pd
import numpy as np
import joblib
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ===============================
# 1. 讀 CSV
# ===============================
df = pd.read_csv("all_data.csv")

# 到小數第二位
df = df.round(2)

# ===============================
# 2. 特徵和標籤
# 前6列 = 輸入
# 後3列 = 輸出
# ===============================
X = df.iloc[:, :6].copy()
y = df.iloc[:, 6:].values

# ===============================
# 3. 三個方向速度改成絕對值 = 1
# velX velY velZ 為第4~6欄 (index 3~5)
# 保留原本正負方向，只把大小變成1
# ===============================
for col in [3, 4, 5]:
    X.iloc[:, col] = np.sign(X.iloc[:, col])

X = X.values

# ===============================
# 4. 建立神經網路模型
# ===============================
model = MLPRegressor(
    hidden_layer_sizes=(64, 32, 16),
    activation="relu",
    solver="adam",
    learning_rate_init=0.001,
    max_iter=5000,
    random_state=42
)

# ===============================
# 5. 訓練模型（取消標準化）
# ===============================
model.fit(X, y)

# ===============================
# 6. 訓練集預測
# ===============================
y_pred_train = model.predict(X)

# ===============================
# 7. 整體評估
# ===============================
mse = mean_squared_error(y, y_pred_train)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y, y_pred_train)
r2 = r2_score(y, y_pred_train)

print("\n===== 整體評估 =====")
print(f"MSE  : {mse:.6f}")
print(f"RMSE : {rmse:.6f}")
print(f"MAE  : {mae:.6f}")
print(f"R²   : {r2:.6f}")

# ===============================
# 8. 各輸出列評估
# ===============================
cols = ["landX", "landY", "landZ"]

for i, col in enumerate(cols):
    mse_i = mean_squared_error(y[:, i], y_pred_train[:, i])
    rmse_i = np.sqrt(mse_i)
    mae_i = mean_absolute_error(y[:, i], y_pred_train[:, i])
    r2_i = r2_score(y[:, i], y_pred_train[:, i])

    print(f"\n===== {col} =====")
    print(f"MSE  : {mse_i:.6f}")
    print(f"RMSE : {rmse_i:.6f}")
    print(f"MAE  : {mae_i:.6f}")
    print(f"R²   : {r2_i:.6f}")

# ===============================
# 9. 預測新樣本
# ===============================
new_sample = np.array([[
    -0.15, 0.05, -0.12,   # posX posY posZ
    1, 1, 1               # velX velY velZ
]])

pred_land = model.predict(new_sample)

print("\n===== 新樣本預測著陸點 =====")
print(f"landX = {pred_land[0,0]:.2f}")
print(f"landY = {pred_land[0,1]:.2f}")
print(f"landZ = {pred_land[0,2]:.2f}")

# ===============================
# 10. 存模型
# ===============================
joblib.dump(model, "mlp_model.pkl")

print("模型已保存！")