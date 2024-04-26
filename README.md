# 3F-Bee-Vision
小蜜蜂项目视觉定位软件
M0: 调度系统
M1: 图像质量检测
M2: 目标识别

本项目通过docker compose管理各个服务，需要在运行的主机上配置下面环境变量(编辑 ~/.bashrc)：
```
export DEV_WORKSPACE=/home/ywang/Documents/3F-Bee-Vision
export DEVOPS_WORKSPACE=/home/ywang/Documents/3F-Bee-Vision/M0_schedular/docker/compose
```

1. 启动所有服务

```bash
cd $DEVOPS_WORKSPACE
docker compose up

# 在与上游调通之前，需要启动模拟发图程序
cd /home/ywang/Documents/3F-Bee-Vision/M0_schedular/simu_send/UDP
conda activate yolo
python udp_img_sender.py
```

2. 启动单个服务

```bash
cd $DEVOPS_WORKSPACE
docker compose up [service_name]
```

3. 关闭服务

```bash
cd $DEVOPS_WORKSPACE
docker compose down
```

4. 其他
```bash
python detect.py --weights runs/train/exp66/weights/best.pt --source ../datasets/bee_yolo/images/test2017/ --device 0 --save-txt
```

