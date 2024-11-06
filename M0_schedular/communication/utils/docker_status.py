import os
import subprocess
import json
import docker
from typing import List, Dict

# docker compose项目名称，用于筛选本项目相关的 docker container
COMPOSE_PROJECT = '3f-vision'

class DockerComposeManager:
    """
    用于管理指定docker-compose.yaml文件的服务
    """

    def __init__(self, compose_file_path: str = "docker-compose.yml"):
        """
        初始化 DockerComposeManager
        :param compose_file_path: Docker Compose 文件的路径,默认为 "docker-compose.yml"
        """
        self.compose_file_path = compose_file_path
    
    def start_services(self, service_list):
        """
        输入需要启动的服务列表，无返回值，等同于:
        docker compose -f [compose_file_path] up -d [service_list]
        """
        if not self._check_services_list(service_list):
            return
        command = ['docker', 'compose', '-f', self.compose_file_path, 'up', '-d'] + service_list
        try:
            result = subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"启动docker compose服务时报错: {e}")

    def stop_services(self, service_list):
        """
        输入需要关闭的服务列表，无返回值，等同于:
        docker compose -f [compose_file_path] up -d [service_list]
        """
        if not self._check_services_list(service_list):
            return
        command = ['docker', 'compose', '-f', self.compose_file_path, 'down'] + service_list
        try:
            result = subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"关闭docker compose服务时报错: {e}")

    def get_running_services(self) :
        """
        获取当前正在运行的 Docker Compose 服务实例
        :return: 正在运行的服务列表,每个服务以字典形式表示
        """
        client = docker.from_env()
        containers = client.containers.list()
        # 返回和docker-compose.yaml定义的project相关的容器实例列表
        filtered_containers = list(filter(lambda c: 
            c.labels.get('com.docker.compose.project') == COMPOSE_PROJECT, 
            containers))
        return filtered_containers

    def _get_project_services(self) -> list:
        """
        获取当前 Docker Compose 文件中所有的service，等同于:
        docker compose -f [compose_file_path] config --services
        :return: docker compose服务列表
        """
        try:
            # print(self.compose_file_path)
            docker_compose_config = subprocess.run(
                ["docker", "compose", "-f", self.compose_file_path, "config", "--services"],
                cwd=os.path.dirname(self.compose_file_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=True
            )
            service_list = docker_compose_config.stdout.strip().split("\n")
            return service_list
        except subprocess.CalledProcessError as e:
            print(f"Error running docker-compose: {e}")
            return []

    def _check_services_list(self, service_list) -> bool:
        """
        确认输入服务列表的值是否在docker-compose.yaml中定义过
        """
        compose_services = self._get_project_services()
        for s in service_list:
            if s not in compose_services:
                print(f"docker compose服务 {s} 不存在!")
                return False
        return True
# 使用示例

def get_service_status(manager, service_list, service_ids):
    running_services = manager.get_running_services()
    service_names = [service.name for service in running_services]
    status_bits = 0
    for service in service_list:
        if service in service_names:
            # # 将对应的 bit 置为 1  
            status_bits |= (1 << service_ids[service])
    # 返回一个长度为 16 的 bytes
    return status_bits.to_bytes(2, byteorder='big')

# 定义服务名称和编号
SERVICE_NAMES = ['M0_redis', 
                 'M0_remote_control',
                 'M0_telemeter', 
                 'M0_image_receiver',
                 'M1_quality',
                 'M2_detect',
                 'M3_analyze']
SERVICE_IDS = {name: idx for idx, name in enumerate(SERVICE_NAMES)}

if __name__ == "__main__":
    if 'DEVOPS_WORKSPACE' in os.environ:
        compose_file_path = os.environ['DEVOPS_WORKSPACE'] + "/docker-compose.yaml"
    else:
        compose_file_path = None
    print(compose_file_path)
    manager = DockerComposeManager(compose_file_path)
    # manager.start_services(['something-bad', 'redis']) # 返回错误信息：列表中有不存在的服务
    # manager.get_running_services()
    services_list = ['redis', 'remote_control','telemeter']
    services_list_2 = ['image_receiver', 'yolov5','quality']
    # manager.start_services(services_list)
    # manager.stop_services(services_list_2)
    status_bits = get_service_status(manager, SERVICE_NAMES, SERVICE_IDS)