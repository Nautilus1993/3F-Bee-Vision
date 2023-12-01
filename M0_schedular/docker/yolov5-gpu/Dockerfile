# Base Image: NVIDIA l4t Pytorch image (https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch)
FROM nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3

# RUN apt-get update && apt-get install -y python3-pip

# Install YOLOv5 python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
RUN pip3 install redis protobuf

WORKDIR /usr/src/yolov5

# Set the entry point to run the YOLOv5 script
# ENTRYPOINT ["python3", "detect.py"]
# docker run -it --rm --ipc=host --runtime nvidia --gpus all -p 6379:6379 -e DISPLAY=$DISPLAY -v /tmp/.X11-unix/:/tmp/.X11-unix -v /home/ywang/Documents/Davince:/usr/src/app --name test_davince nano_torch_test:20231114
