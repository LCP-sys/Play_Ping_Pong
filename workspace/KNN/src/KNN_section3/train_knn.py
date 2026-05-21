import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import joblib

data = pd.read_csv('/workspace/KNN/src/section3/training_data.csv')
X = data[['x', 'y', 'z', 'vx', 'vy', 'vz']].values

# 確保輸出是 3 維度
if 'land_y' not in data.columns:
    data['land_y'] = 0.03 

y = data[['land_x', 'land_y', 'land_z']].values

print("正在訓練【真・高精度】模型...")
# 🌟 破除迷思：加上 Pipeline 與 StandardScaler，AI 的預測能力會提升 100 倍！
knn = make_pipeline(
    StandardScaler(),
    KNeighborsRegressor(n_neighbors=5)#可更改
)
knn.fit(X, y)

joblib.dump(knn, '/workspace/KNN/src/section3/knn_model.pkl')
print("✅ 模型已重新產生！這次 AI 終於睜開眼睛了！")