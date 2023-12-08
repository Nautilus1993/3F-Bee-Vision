# 3F-Bee-Vision
小蜜蜂项目视觉定位软件
M0: 调度系统
M1: 图像质量评估
M2: 目标识别(yolov5)

1. start redis container

```docker
docker run --name M0_redis -d -p 6379:6379 redis
```

2. start M0 container

```docker
docker run -it --network=host \
-e DISPLAY=$DISPLAY \
-v /tmp/.X11-unix:/tmp/.X11-unix \
-v /home/ywang/Documents/3F-Bee-Vision/M0_schedular:/usr/src/app \
--name M0_scheduler orin_nano_scheduler:20231127
```


3. start M2 container(put M1 inside this container for test)

```docker
docker run -it --network=host \
--runtime nvidia --gpus all \
-e DISPLAY=$DISPLAY \
-v /tmp/.X11-unix/:/tmp/.X11-unix \
-v /home/ywang/Documents/3F-Bee-Vision/M1_quality:/usr/src/M1_quality \
-v /home/ywang/Documents/3F-Bee-Vision/M2_detect:/usr/src/M2_detect \
--name M2_detect orin_nano_yolov5:20231128
```
