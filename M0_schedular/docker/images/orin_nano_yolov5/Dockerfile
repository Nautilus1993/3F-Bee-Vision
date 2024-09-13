# Base Image: NVIDIA l4t Pytorch image (https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch)
FROM nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3

# Install YOLOv5 python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -U scikit-learn
RUN pip3 install -r /tmp/requirements.txt
RUN pip3 install redis protobuf

WORKDIR /usr/src/app