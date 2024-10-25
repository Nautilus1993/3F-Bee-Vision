# Base Image
FROM nvcr.io/nvidia/l4t-base:35.3.1

RUN apt update && apt install -y python3.8 python3-pip
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
# 注意python jtop的版本需要和host保持一致
RUN pip3 install --upgrade setuptools
RUN pip3 install -U jetson-stats==4.2.9

# 安装docker compose plugin
RUN apt-get update && \
    apt-get install -y ca-certificates curl && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc &&\
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update
ENV VERSION_STRING=5:24.0.5-1~ubuntu.20.04~focal
RUN apt-get update && \
    apt-get install -y docker-ce=$VERSION_STRING docker-compose-plugin

EXPOSE 8089
WORKDIR /usr/src/app
