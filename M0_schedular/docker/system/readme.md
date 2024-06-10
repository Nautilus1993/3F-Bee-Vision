# 开机自启动配置
开机自启动三个服务：
1. redis消息队列
2. telemeter 遥测数据下行
3. remote_control 遥控指令接收
其中1,2又docker compose服务启动，3暂时用python脚本启动，后面也改为docker compose服务。

三个文件放置在 $HOME/.config/systemd/user/文件夹下，自启动服务作为用户级服务，需要配置如下内容：

```bash
sudo loginctl enable-linger $USER 
```

以使得用户注销后，systemd --user 进程以及它管理的服务并不会退出.
对于单个服务，可以使用如下命令：

```bash
$ systemctl --user enable [service_name]
$ systemctl --user status [service_name]
$ systemctl --user restart [service_name]
$ journalctl --user -u [service_name]
```