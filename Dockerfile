FROM ros:jazzy

# 基本工具
RUN apt update && apt install -y \
    git \
    python3-colcon-common-extensions \
    python3-pip \
    python3-pandas \ 
    python3-sklearn \
    python3-joblib \
    python3-numpy

# 1. 建立 KNN 與 MLP 兩個獨立工作區的 src 資料夾
RUN mkdir -p /workspace/KNN/src /workspace/MLP/src /workspace/TCP/src /workspace/THM/src /workspace/ROS-TCP-Endpoint

# 2. 設定專屬的快捷編譯指令 (自動記錄當前路徑 -> 進工作區編譯 -> 載入環境 -> 跳回原路徑)
RUN echo "alias r-knn='CURDIR=\$(pwd) && cd /workspace/KNN && colcon build --symlink-install && source install/setup.bash && cd \$CURDIR'" >> /root/.bashrc
RUN echo "alias r-mlp='CURDIR=\$(pwd) && cd /workspace/MLP && colcon build --symlink-install && source install/setup.bash && cd \$CURDIR'" >> /root/.bashrc
RUN echo "alias r-tcp='CURDIR=\$(pwd) && cd /workspace/TCP && colcon build --symlink-install && source install/setup.bash && cd \$CURDIR'" >> /root/.bashrc
RUN echo "alias r-thm='CURDIR=\$(pwd) && cd /workspace/THM && colcon build --symlink-install && source install/setup.bash && cd \$CURDIR'" >> /root/.bashrc
RUN echo "alias r-ros='CURDIR=\$(pwd) && cd /workspace/ROS-TCP-Endpoint && colcon build --symlink-install && source install/setup.bash && cd \$CURDIR'" >> /root/.bashrc

# 3. 載入底層 ROS 2 Jazzy 環境變數
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

# 4. 將容器預設工作目錄設在最上層的 /workspace
WORKDIR /workspace