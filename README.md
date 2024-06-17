# 3F-Bee-Vision
小蜜蜂项目视觉定位软件
* M0: 调度系统
* M1: 图像质量检测
* M2: 目标识别

项目平台jetson orin nano

# Quick Start
## 环境配置
### docker安装
https://docs.docker.com/desktop/install/archlinux/
安装aarch64版本的docker
https://github.com/docker/compose/releases/ 安装aarch64版本的docker compose

本项目通过docker compose管理各个服务，需要在运行的主机上配置下面环境变量(编辑 ~/.bashrc)：
```bash
export DEV_WORKSPACE=/home/user_name/Documents/3F-Bee-Vision
export DEVOPS_WORKSPACE=/home/user_name/Documents/3F-Bee-Vision/M0_schedular/docker/compose
```
添加docker到用户组
```bash
sudo groupadd docker
```
添加当前用户到docker用户组
```bash
sudo usermod -aG docker username
```
### 构建镜像
一共需要三个镜像。构建2,3所用到的 base image比较大，建议先从902下载.tar文件，然后用下面这条命令导入：

   ```bash
   docker load -i [image_file]
   ```
然后用docker images查看后可以看到下面的信息：
   ```bash
   docker load -i [image_file]
   ```

1. redis:latest 
   可以在docker compose自动拉取，可能需要登录docker hub
   ```bash
   docker login -u username -p password
   ```
2. orin_nano_messenger:[tag]
   ```bash
   cd $DEV_WPRKSPACE/M0_schedular/docker/scheduler
   docker build -t orin_nano_messenger:[tag] .
   ```
3. orin_nano_yolov5:[tag]
   ```bash
   cd $DEV_WPRKSPACE/M0_schedular/docker/yolov5-gpu
   docker build -t orin_nano_yolov5:[tag] .
   ```
请把上面命令中的[tag]换为打包镜像的时间戳，并相应调整docker-compose.yaml文件中的镜像名称。

### 启动服务

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
# service_name:
# 1. redis                      
# 2. image_receiver             depends on：redis
# 3. result_sender              depends on：redis
# 4. quality                    
# 5. yolov5
```

3. 关闭服务

```bash
cd $DEVOPS_WORKSPACE
docker compose down
```

4. 其他
```bash
# 目标检测输出检测框txt
python detect.py --weights runs/train/exp66/weights/best.pt --source ../datasets/bee_yolo/images/test2017/ --device 0 --save-txt

# 各类别中心点精度评定，注意修改路径
python precision_center.py
```
