# Base Image
FROM nvcr.io/nvidia/l4t-base:35.3.1

RUN apt update && apt install -y python3.8 python3-pip
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

EXPOSE 8089
WORKDIR /usr/src/app
