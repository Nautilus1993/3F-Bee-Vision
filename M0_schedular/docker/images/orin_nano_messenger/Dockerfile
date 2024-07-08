# Base Image
FROM nvcr.io/nvidia/l4t-base:35.3.1

# 设置非交互模式
ARG DEBIAN_FRONTEND=noninteractive

# 将本地包复制到镜像中
COPY local_packages /local_packages

# 更新包列表（使用本地的包列表）
RUN cp /local_packages/sources.list /etc/apt/sources.list

# 安装基础工具（如需要可以通过dpkg安装本地包）
RUN dpkg -i /local_packages/ubuntu/*.deb || apt-get -f install -y

# 安装本地的 Python 包
RUN pip3 install /local_packages/python/*.whl

EXPOSE 8089
WORKDIR /usr/src/app
