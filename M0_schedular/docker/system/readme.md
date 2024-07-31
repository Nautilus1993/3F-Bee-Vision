# 开机自启动配置
开机自启动三个服务：
1. redis消息队列
2. telemeter 遥测数据下行
3. remote_control 遥控指令接收

3f_vision_docker.service和3f_vision.env 文件放置在 $HOME/.config/systemd/user/文件夹下。如果用户名不同，则需要修改脚本汇中的文件路径。

自启动服务作为用户级服务，需要配置如下内容：

```bash
sudo loginctl enable-linger $USER 
```

以使得用户注销后，systemd --user 进程以及它管理的服务并不会退出.
对于单个服务，可以使用如下命令：

```bash
$ systemctl --user enable 3f_vision_docker
$ systemctl --user status 3f_vision_docker
$ systemctl --user restart 3f_vision_docker
$ journalctl --user -u 3f_vision_docker
```

日志存放在$HOME路径下的3f-vision-service.log文件中，目前存在的问题是日志大小累积速度太快了，需要想一个办法定时删除。