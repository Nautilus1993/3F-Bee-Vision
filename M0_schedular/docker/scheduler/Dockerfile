# Base Image: NVIDIA l4t Pytorch image (https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch)
FROM nvcr.io/nvidia/l4t-base:35.3.1

RUN apt update && apt install -y python3.8 python3-pip
# Install YOLOv5 python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /usr/src/app
# protobuf>=3.3.0
# docker run -it --rm -p 6379:6379 --ipc=host --runtime nvidia --gpus all -e DISPLAY=$DISPLAY -v /tmp/.X11-unix/:/tmp/.X11-unix -v /home/ywang/Documents/Davince:/usr/src/app --name test_davince davince_base:20231114
