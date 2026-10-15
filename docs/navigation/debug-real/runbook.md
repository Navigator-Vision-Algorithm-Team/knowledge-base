# 导航与建图 Debug 排查手册

<small>整理与维护：24cst朱鑫鹏</small>

知识库适配日期：2026-10-10。工具语法面向 Ubuntu 22.04 / ROS 2 Humble；实机结果来自 2026-09 的本地化 PB2025 历史案例。

**本队学习主线是 Navigation-2027，审查基线 `183a4109b0de2030bb8970a54654937c8b039ba9`。** 本文保留通用排障方法和历史修复证据，不把本地 PB2025 改动当成本队当前功能。先登记实际 commit、overlay、命名空间、串口接口与地图，参见[系统地图](../system/README.md)和[源码审查证据](../system/nav2-and-control-evidence.md)。所有 `/home/ubuntu/navigation_2025/...`、独立 `/home/ubuntu/ros_ws`、PID/IP/地图名均为历史示例，执行时以本次登记替换。

实车操作与停止验证沿用[实车流程](README.md)，本轮只更新知识库，不改生产导航源码。

给零基础新人：先阅读 [导航 Debug 代码详解：零基础新人版](command-guide.md)，再按本手册的故障章节排查。两份文档配套保留。

本文依据此前贴出的 Linux 输出、保存的源码和修改记录整理。**历史上成功的结果不代表机器人现在仍是同一状态；现场判断以本次命令输出为准。** 本文不修改机器人程序，也不修改底盘电控协议。

## 1. 怎么使用这份手册

按“检查命令 → 输出判断 → 处理 → 复查”使用。先找到数据链断在哪一段，再改对应模块。

把故障先写成一句带条件的事实，例如“导航模式、本次 Goal 执行中、上游有速度而最终 Topic 没消息”，不要只写“车不动”。这句话决定你应看控制转换还是传感器。每做一次检查就缩小候选原因，改动后再用原检查复验；重新启动后能跑属于恢复证据，还需要找出原触发条件。

所有 `bash` 命令都在机器人 Ubuntu 终端执行，不在 Windows PowerShell 执行。只复制代码块，不复制 `ubuntu@ubuntu:...$` 提示符。一次粘贴一个代码块，等待提示符回来再粘贴下一块，避免出现 `*.xmlcd`、`pb2025_nav_bringupcd`。

诊断终端里的 `Ctrl+C` 只停止正在运行的诊断命令；导航启动终端里的 `Ctrl+C` 才停止对应 launch。`timeout` 命令会自动结束检查，结束时打印信号或出现退出码 `124` 不等于导航崩溃。

### 1.1 新开诊断终端，先加载已登记环境

以下完整代码块属于历史双工作空间部署；Navigation-2027 的实际工作空间/串口依赖另见[环境页](../onboarding/environment.md)。先确认路径和 overlay，不直接覆盖生产终端环境。

```bash
cd /home/ubuntu/navigation_2025/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source /home/ubuntu/ros_ws/install/setup.bash
source /home/ubuntu/navigation_2025/ros_ws/install/setup.bash
```

这里依次加载 Humble、串口工作空间、导航工作空间。`unset LD_LIBRARY_PATH` 用来清掉这台机器上可能干扰 ROS/PCL 的旧库路径，之后 `source` 会重新设置需要的路径。

以前 `source install/setup.bash` 能单独工作，是因为它可以加载构建时记录的父工作空间；它必须在正确的工作空间目录下执行。出现环境问题时，优先使用上面的完整步骤。

### 1.2 路径与名字

| 项目 | 本项目使用的值 |
| --- | --- |
| 导航工作空间 | `/home/ubuntu/navigation_2025/ros_ws` |
| 导航源码 | `/home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav` |
| 串口工作空间 | `/home/ubuntu/ros_ws` |
| 主参数文件 | `/home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml` |
| 行为树目录 | `/home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees` |
| ROS 命名空间 | `/red_standard_robot1` |
| 导航 TF 话题 | `/red_standard_robot1/tf`、`/red_standard_robot1/tf_static` |
| 最近一次确认过的底盘尺寸 | 长 `0.60 m`、宽 `0.45 m` |

注意：话题名带命名空间，TF 中的 frame 名通常仍是 `map`、`odom`、`base_footprint`，不要直接给 frame 名前加命名空间。

### 1.3 快速按现象找问题

| 现象 | 优先检查 | 对应章节 |
| --- | --- | --- |
| 点云重叠、位置跨米跳、同名节点很多 | 重复 launch、重复组件、TF 多个发布者 | 3、4、8 |
| 雷达有数据，但车模型不动 | 数据链中间断开、`odometry`、TF | 4、5 |
| `queue is full`、旧时间戳被丢弃 | TF、时间、数据积压、重复发布 | 6 |
| Goal 点了没反应 | Action、生命周期、Goal 状态、速度链 | 7 |
| 规划有速度，底盘不动 | 串口订阅、端口、使能和反馈 | 7、9 |
| 会撞桌腿、绕不开 | 是否看见障碍、是否入代价地图、足迹与控制器 | 10 |
| 前后退、顿挫 | Action 是否进入恢复、进展检查、速度链 | 11 |
| 底盘转、云台不跟随 | 云台接口、真实关节反馈 | 12 |
| 模型斜着、雷达斜着 | 安装外参、`odom → base_footprint` | 13 |
| RViz 白色、地图显示报错 | 显示状态、材质、OpenGL、TF | 14 |
| 参数改了没效果 | source 的包路径、install 内容、运行参数 | 15 |
| 驱动退出、`-11`、`-9` | 首次错误、退出时序、进程与系统日志 | 16 |
| SSH 超时 | 当前 IP、路由、22 端口、抓包 | 17 |

## 2. 先理解两条数据链

### 2.1 定位与点云链

定位链像加工流水线：驱动给原始测量，LIO 估计传感器运动，接口换到导航需要的坐标，重定位再把局部运动对到先验地图。每一层都需要前一层的正确输入。因此“雷达有数据”只证明第一站，不能替最后一站作证。

```text
Livox 驱动
  ├─ livox/lidar、livox/lidar/pointcloud
  └─ livox/imu
        ↓
Point-LIO
  ├─ aft_mapped_to_init：里程计
  └─ cloud_registered：已配准点云
        ↓
loam_interface
  ├─ lidar_odometry
  └─ registered_scan
        ↓
sensor_scan_generation
  └─ odometry，以及本项目使用的相关运动 TF

导航模式：small_gicp_relocalization + 先验 PCD → map → odom
建图模式：slam_toolbox + 启动文件配置的 map/odom 关系 → 在线二维地图
```

这里的模块输出对应此前这套本地化工程；若工程后来修改过，用 `ros2 node info` 查实际输入输出。`sensor_scan_generation` 在本项目实机链路中也参与工作，不能只把它当作仿真节点。

本队可对照 [ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp][run-loam] 的输入参数与发布端点，以及 [ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp][run-scan-sync] 的双输入同步。例如 `lidar_odometry` 持续更新、`registered_scan` 不更新，后者的同步回调就缺一侧输入，最终 `odometry` 也可能停住。查两侧类型、stamp、QoS，再看日志；不能只数里程计频率。

### 2.2 Goal 到底盘链

Goal 是任务，路径是路线，速度是当前动作，串口是硬件接口。看路径成功，不代表控制器已输出；看速度非零，也不代表底盘已认可。按这个顺序查，就能把“导航失败”拆成请求、规划、跟踪、转换和执行几个有证据的边界。

```text
RViz 的 Nav2 Goal
  → /red_standard_robot1/navigate_to_pose Action
  → bt_navigator
  → planner_server / controller_server
  → cmd_vel_controller
  → velocity_smoother
  → cmd_vel_nav2_result
  → fake_vel_transform
  → cmd_vel
  → rm_serial_driver
  → 串口导航数据包
  → 电控执行
```

恢复行为也可能直接向 `cmd_vel_nav2_result` 发布，所以该话题出现控制器之外的发布者不一定是重复启动。必须结合节点名称判断。

上图的 `rm_serial_driver` 属于历史部署末端；本队末端必须换成登记的实际消费者。控制器/smoother remap 及组合模式行为服务器输出可查 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py][run-velocity-launch]。把源码中的相对名、launch 的 namespace/remap 与现场端点全名对应起来，再判断连接。

## 3. 两套导航同时存在、同一容器重复加载

重复来源会让下游收到相互矛盾的状态。示意：两份 Point-LIO 对同一时刻分别报告 x=1 与 x=3 米，下游交替接收时表现为跳变，而两个程序都可能没有崩溃。这里要验证的是“同一用途是否存在多个独立来源”，不是把所有多发布者话题都删成一个。

组件应装到哪里，见 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py][run-components] 的 `target_container` 和列表。对照现场列表，若同容器同名组件出现两份，才把“重复加载”作为直接证据；若本机只有一份，继续检查同 ROS 域其他主机。

### 检查

```bash
ps -eo pid,ppid,stat,etimes,args | grep -E '[r]m_navigation_reality_launch|[c]omponent_container.*nav2_container|[p]ointlio_mapping|[l]ivox_ros_driver2_node|[r]m_serial_driver'
```

```bash
ros2 node list | sort | uniq -d
```

```bash
ros2 component list
```

```bash
ros2 topic info /red_standard_robot1/aft_mapped_to_init -v
```

### 输出判断

| 输出 | 意义 |
| --- | --- |
| `ps` 中两个同命名空间的导航 launch | 本机确实运行了两套启动程序，检查是否一套建图、一套导航 |
| 只有一个 launch，但组件列表里同名组件出现两次 | 组件确实重复加载；一个进程不等于一套组件 |
| `uniq -d` 输出 `loam_interface`、`sensor_scan_generation`、`fake_vel_transform` 等 | 图中有重名节点，继续结合组件、进程和话题端点确认来源 |
| 本应唯一的 `aft_mapped_to_init` 有两个不同 Point-LIO 发布端点 | 两个来源可能交替输入下游，容易引起位置、时间和点云异常 |
| `/tf` 有很多发布者 | 不足以判定冲突，多个不同 TF 边的发布者是正常的；冲突指同一个 child frame 被重复驱动 |
| Foxglove 组件管理器单独无响应 | 先查 Foxglove 自身，不能据此认定 Nav2 容器也坏了 |

**我们以前确实出现过：开机自动启动 `world:=final2 slam:=False`，随后又手动启动建图。** 后来组件/节点中出现多份 `loam_interface`、`sensor_scan_generation`、`fake_vel_transform`，TF 和点云异常。清理旧实例后，无重复节点，`odometry` 恢复约 `20 Hz`。

重名节点也可能来自同一 ROS_DOMAIN_ID 下的另一台电脑。`ps` 只显示本机进程；若本机进程正常但重复端点还在，检查同实验室其他电脑和 ROS 域配置。

### 处理

优先回到旧 launch 的终端，按一次 `Ctrl+C`，等待完整退出。若旧终端找不到，先通过下面命令核对 PID：

```bash
ps -p 3199 -o pid,ppid,stat,args
```

`3199` 只是历史例子，**必须换成这次查到且属于旧导航 launch 的 PID**。确认后才执行：

```bash
kill -INT 3199
```

等待退出后重新运行本节最上面的 `ps` 检查。仍有残留时，逐个核对残留 PID 的命令和所属 launch，再定向处理。不要直接复制旧 PID，不要批量杀掉实验室所有 ROS 进程。

如果同一容器已经重复加载，通常完整停止对应 launch/容器并重新启动更清楚；逐个卸载可能破坏 lifecycle manager 与其他组件的依赖。

### 检查开机自启动

```bash
grep -RniE 'nav_test|rm_navigation_reality_launch|start_nav_tuned|world:=final2' /home/ubuntu/.config/autostart /etc/xdg/autostart 2>/dev/null
```

```bash
ls -l /home/ubuntu/.config/autostart /home/ubuntu/.config/autostart-disabled
```

此前找到的是 `/home/ubuntu/.config/autostart/nav_test.desktop`，其中 `Exec=/home/ubuntu/start_nav_test.sh`。若它现在又出现在 autostart 中，可保留文件并移出自动启动目录：

```bash
mkdir -p /home/ubuntu/.config/autostart-disabled
mv -i /home/ubuntu/.config/autostart/nav_test.desktop /home/ubuntu/.config/autostart-disabled/nav_test.desktop
```

已经在 disabled 中就不用再移动。这只影响后续桌面登录，**不会停止已经启动的导航**。若进程停止后又自动出现，还要查其他启动来源：

```bash
systemctl --user list-units --all | grep -Ei 'nav|robot|ros'
systemctl list-units --all | grep -Ei 'nav|robot|ros'
crontab -l
```

### 复查

`uniq -d` 不再列出关键导航节点；组件没有重复；Point-LIO 等应唯一的话题只剩预期发布端点；相关 TF 连通。这些证据一起满足，才认为重复启动问题解决。

## 4. `odom → base_footprint` 不存在、TF 树断开

TF 是将传感器位置换算到机器人、再换算到地图的坐标关系。一个 frame 存在，不代表它和另一个 frame 连通；链路连通，也不代表查询时刻在缓存范围内。先分别检查安装、局部运动、全局校正三段，就能知道缺的是哪种关系。

本队 [ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp][run-scan-handler] 在同步回调里发布 odom 到 base_frame 的关系，并使用点云 stamp。若点云与里程计有数据、这条边却缺失，查看是否真正进入回调和参数 frame 名；若边存在但查旧消息时失败，则转第 6 节查时间。

### 检查

```bash
timeout --signal=INT --kill-after=2s 8s ros2 run tf2_ros tf2_echo odom base_footprint --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

```bash
timeout --signal=INT --kill-after=2s 8s ros2 run tf2_ros tf2_echo map odom --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

```bash
timeout --signal=INT --kill-after=2s 8s ros2 run tf2_ros tf2_echo base_footprint front_mid360 --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

| 输出 | 判断与下一步 |
| --- | --- |
| 最初一条 `Invalid frame ID`，随后持续打印矩阵 | 通常是订阅刚建立；此前我们也遇到过，不能把第一条警告当最终结果 |
| 一直 `frame does not exist` | 当前监听范围里没有该 frame，查是否启动、名称是否正确、TF 话题是否选对 |
| `two or more unconnected trees` | 两端 frame 存在，但缺少中间 TF 边，沿第 2 节链路检查发布节点 |
| 时间持续推进、数值连续 | 动态 TF 存在；还要确认静止时没有大跳 |
| `map → odom` 为 `At time 0.0`，平移零、单位旋转 | 表示读到静态单位变换；在之前的建图配置中正常，导航模式则应核对是不是错误保留了建图用静态发布者 |
| `/tf` 有 `500 Hz`，但上述检查失败 | 总 TF 频率不能证明需要的两帧已经连通 |

不能在缺少真实里程计时，用静态 `odom → base_footprint` 假装修好，它会把运动位置固定住。

### 生成实际 TF 树

在下面目录生成图文件，不覆盖导航配置：

```bash
mkdir -p /home/ubuntu/nav_debug_tf
cd /home/ubuntu/nav_debug_tf
ros2 run tf2_tools view_frames --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

执行后检查该目录里的 `frames*.pdf`、`.gv`；不同 Humble 版本生成的文件名可能带时间。若提示缺少 `dot`，是绘图依赖问题，前面三个 `tf2_echo` 仍可用于检查。树中至少应能沿正确路径连接 `map`、`odom`、`base_footprint` 和雷达。

ROS 官方也使用 `tf2_echo`、`view_frames` 和 `tf2_monitor` 区分 frame 与时间问题：[Humble TF2 调试说明](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.rst)。

## 5. 雷达正常，但 `odometry` 没数据

找“第一处断点”比找“最后一个没数据的话题”有用。假设原始点云、IMU、LIO 输出都在更新，而 `lidar_odometry` 没有，先查 loam_interface；若两路转接输入都有，最终没有，再查同步与外参。这里的逐段命令就是让你画出一个带实测值的流水线。

尤其注意 [ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp][run-loam-tf] 的首次 TF 查询失败会直接返回，不发布该次里程计。源码中的这个分支能解释“节点活着、publisher 存在、却没消息”；现场仍需用 `TF lookup failed` 日志及对应变换查询支持判断。

### 逐段检查频率

这些命令每条运行约 6 秒，**按顺序逐条执行**：

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/livox/lidar/pointcloud
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/livox/imu
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/aft_mapped_to_init
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/cloud_registered
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/lidar_odometry
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/registered_scan
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/odometry
```

### 怎么判断断在哪

| 上游结果 | 下游结果 | 优先检查 |
| --- | --- | --- |
| 雷达点云、IMU 都没有 | Point-LIO 没有 | 雷达供电、网卡/地址、Livox 驱动、重复占用 |
| 雷达点云有，IMU 没有 | Point-LIO 无输出或不稳定 | IMU 驱动输出、配置的订阅话题、QoS |
| 雷达和 IMU 有 | `aft_mapped_to_init` 没有 | Point-LIO 是否存活、实际输入话题、日志、时间戳 |
| `aft_mapped_to_init` 有 | `lidar_odometry` 没有 | `loam_interface` 是否加载、参数与 remap |
| `lidar_odometry`、`registered_scan` 有 | `odometry` 没有 | `sensor_scan_generation` 的订阅与外参 TF |
| `odometry` 有 | `odom → base_footprint` 不通 | TF 发布逻辑、frame 名、命名空间、重复发布 |

以前稳定的观测值是雷达点云约 `20 Hz`，最终 `odometry` 约 `20 Hz`。Point-LIO 里程计可能比点云频率高很多；不能因为 `aft_mapped_to_init` 高达几百或上千 Hz，就直接认定重复发布。

`registered_scan` 低频可能来自处理负载、过滤、同步或重复程序，必须看上下游对比。`ros2 topic hz` 是这个诊断订阅者收到数据的频率，不是发布者内部计时器的绝对频率。

### 深入看端点

```bash
ros2 topic info /red_standard_robot1/odometry -v
ros2 node info /red_standard_robot1/loam_interface
ros2 node info /red_standard_robot1/sensor_scan_generation
```

发布数为 `1` 只说明注册了发布端点，还需 `hz` 或 `echo` 确认真有数据。订阅数很多也不直接代表重复，RViz、控制器和调试终端都会增加订阅者。

QoS 中发布者为 `BEST_EFFORT`、订阅者要求 `RELIABLE` 时可能收不到数据。可先用兼容的诊断订阅读取一条消息头：

```bash
timeout --signal=INT --kill-after=2s 8s ros2 topic echo /red_standard_robot1/registered_scan sensor_msgs/msg/PointCloud2 --qos-reliability best_effort --field header --once
```

实际模块的 QoS 仍需根据 `topic info -v` 和源码核对，诊断终端能读到不代表其他订阅者也兼容。

## 6. 点云队列满、旧时间戳、向未来外推

点云可能已经到达，但处理器在等“这条消息采集时刻”的 TF。一直等不到，排队的消息就越来越多，最终显示队列满。示意：当前 TF 只到 10.00 秒，点云请求 10.03 秒，就需要后续数据或合理等待；把队列从 10 改成 100 并不会生成缺失的变换。

本队 [ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp][run-scan-tf] 按点云 stamp 查询安装关系，失败时返回单位变换；这又可能表现为“输出还在，但位置不对”。因此同时记录 stamp、请求/最新 TF 时间和日志，不以话题存在判定该级处理正确。

常见日志：`queue is full`、`earlier than all the data in the transform cache`、`extrapolation into the future`。

### 检查

先完成第 3 节的去重检查和第 4 节的 TF 连通检查，再读取消息时间：

```bash
date +%s
```

```bash
timeout --signal=INT --kill-after=2s 8s ros2 topic echo /red_standard_robot1/livox/lidar/pointcloud sensor_msgs/msg/PointCloud2 --qos-reliability best_effort --field header --once
```

```bash
timeout --signal=INT --kill-after=2s 8s ros2 topic echo /red_standard_robot1/registered_scan sensor_msgs/msg/PointCloud2 --qos-reliability best_effort --field header --once
```

```bash
ros2 param get /red_standard_robot1/point_lio use_sim_time
ros2 param get /red_standard_robot1/sensor_scan_generation use_sim_time
ros2 param get /red_standard_robot1/bt_navigator use_sim_time
ros2 param get /red_standard_robot1/rviz use_sim_time
```

```bash
top -b -n 1 | head -n 25
free -h
timedatectl status
```

| 现象 | 判断 | 对应处理 |
| --- | --- | --- |
| 消息时间正常推进，TF 链一直断 | 等不到正确变换导致队列积压 | 补回真正缺失的节点或 TF 边 |
| 点云时间比当前时间持续落后十几秒 | 可能是积压、错误时间源或旧发布者 | 比较原始点云与注册点云，定位延迟首次出现的模块 |
| `use_sim_time: true`，实机却没有有效 `/clock` | 节点时钟配置不一致 | 改对应实机参数为 false，重建并完整重启相关 launch |
| 仅启动最初几条旧消息，随后恢复 | 可能是 TF 缓存建立阶段 | 观察后续数据，避免把瞬时启动日志当持续故障 |
| `Requested time` 只比 `latest data` 晚几毫秒，但持续刷屏 | TF 到达稍晚或查询时序不匹配 | 查该模块是否按消息时间查询、是否支持合理等待；不能直接返回单位变换当成功 |
| CPU/内存持续紧张，注册点云明显比原始点云落后 | 处理能力不足或队列积压 | 先减少重复实例，再考虑下采样、处理频率和显示负载 |

`queue is full` 是消息等不到处理条件的结果，不一定是 queue 数值太小。直接扩大队列可能让旧数据积压更久。用于点云融合时，应保留消息时间对应的变换语义，不随意改成“最新 TF”。

## 7. 点击 Goal 没反应、Action 不可用、车不走

“没反应”要拆开：点击有没有成为本次 Action，请求有没有被接受，规划有没有给路径，控制有没有给速度，最终有没有消费者。比如新目标 UUID 已是 EXECUTING，说明任务进入系统，重点应转到路径和控制日志；只有旧目标 SUCCEEDED 则还无法判断这次点击。

### 7.1 先确认接收目标的服务

```bash
ros2 action list -t | grep navigate_to_pose
ros2 action info /red_standard_robot1/navigate_to_pose
```

```bash
ros2 lifecycle get /red_standard_robot1/bt_navigator
ros2 lifecycle get /red_standard_robot1/planner_server
ros2 lifecycle get /red_standard_robot1/controller_server
```

预期：存在 `nav2_msgs/action/NavigateToPose`，有 `1` 个预期的 Action server，三项 lifecycle 都为 `active [3]`。Action clients 有多个很正常；`inactive`/`unconfigured` 时先查 lifecycle manager 的配置失败日志。

`navigate_to_pose action server is not available. Is the initial pose set?` 后半句是提示，不是已经证明定位失败。可能是服务器没启动、命名空间错误、DDS 未发现或 lifecycle 没激活。

本工程此前建图模式也启动 Nav2，可以使用顶部 `Nav2 Goal`。不要把别的工程“建图只负责建图”的结论套过来；如果 launch 后来改过，以上 Action 与 lifecycle 输出才是依据。

### 7.2 点击是否真的进入 Action

在诊断终端运行下面命令，再在 RViz 点击一次 Goal：

```bash
ros2 topic echo /red_standard_robot1/navigate_to_pose/_action/status action_msgs/msg/GoalStatusArray --qos-durability transient_local --qos-reliability reliable
```

| `status` | 含义 |
| --- | --- |
| `1` | ACCEPTED：目标已接收 |
| `2` | EXECUTING：正在执行 |
| `3` | CANCELING：正在取消 |
| `4` | SUCCEEDED：成功 |
| `5` | CANCELED：已取消 |
| `6` | ABORTED：失败中止 |

数组可能包含历史目标，结合新 Goal 的 UUID、时间和本次日志判断。没有新的目标状态变化时检查 RViz 的命名空间和所用按钮；有 `2` 后变 `6` 时，说明请求到达了，继续找运行失败原因。

有些工具通过 `goal_pose` 转发目标，有些直接用 Action。**不能只凭 `/goal_pose` 没消息就说 RViz 没发出 Goal。**

### 7.3 沿速度链读取

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel_controller geometry_msgs/msg/Twist
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel_nav2_result geometry_msgs/msg/Twist
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel geometry_msgs/msg/Twist
```

```bash
ros2 topic info /red_standard_robot1/cmd_vel -v
```

| 结果 | 问题位置 | 处理方向 |
| --- | --- | --- |
| Goal 执行，但控制器无消息或始终零 | 规划、TF、代价地图、控制器或到达判断 | 查执行日志和路径，不先改串口 |
| `cmd_vel_controller` 非零，`cmd_vel_nav2_result` 无消息 | velocity_smoother 或 remap | 查 smoother lifecycle、输入输出端点 |
| `cmd_vel_nav2_result` 非零，`cmd_vel` 无消息 | fake_vel_transform 或同步依赖 | 查 odometry、local_plan、节点参数和端点 |
| `cmd_vel` 非零，没有预期串口订阅者 | 串口 launch 没运行或订阅名不匹配 | 只启动一套正确串口驱动 |
| `cmd_vel` 非零，串口发送日志也非零，底盘仍不动 | 串口后端、模式/使能、通信或执行 | 接着查第 9 节反馈 |
| 输入零，输出还持续非零 | 旧命令缓存、其他发布者或转发逻辑 | 查唯一发布者与零命令路径，不能归因于“Goal 没发布” |

`linear.x`/`linear.y` 为平移速度，`angular.z` 为绕 Z 轴角速度。我们以前见过另一个工程将 `wz` 从 `linear.z` 取值的代码；若当前实际消费者仍这样取值，要交给对应模块维护者核对。仅有 `angular.z` 非零不能证明串口使用了同一个字段。

## 8. 重定位跳动、地图与点云不重合

重定位把当前局部点云与先验 PCD 对齐，结果决定 map 到 odom 的校正。错地图、错初值、错坐标或重复发布，都可能让它找到错误关系；连续稳定的 TF 也可能稳定地错在另一处墙角。判断要同时看“是否收敛”和“是否对到当前场地的正确位置”。

打开 [ros_ws/src/pb2025_sentry_nav/small_gicp_relocalization/src/small_gicp_relocalization.cpp][run-gicp]：从 PCD 加载，到累积点云，再到 `align` 与 `result.converged` 分支。若日志是 `Couldn't read PCD`，先处理路径/资产；若是 `GICP did not converge`，再核对输入和初值。这两种错误不应通过反复发送 initialpose 混为一类。

先在静止状态比较两段 TF：

```bash
timeout --signal=INT --kill-after=2s 10s ros2 run tf2_ros tf2_echo odom base_footprint --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

```bash
timeout --signal=INT --kill-after=2s 10s ros2 run tf2_ros tf2_echo map odom --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

| 结果 | 判断 |
| --- | --- |
| `odom → base_footprint` 自己就跨米跳 | 优先查重复 Point-LIO/TF、原始传感器和外参，尚不能归因于 GICP |
| `odom → base_footprint` 连续，`map → odom` 大跳 | 优先查全局重定位、先验地图、重复 map/odom 发布者 |
| 两段连续但整体错位 | 可能是错误初始匹配、错误地图或外参；“稳定”不代表“正确” |
| 只在转云台时异常 | 查真实云台关节反馈、雷达运动外参和 TF；不是静态雷达安装角能完全解释 |

### 导航模式核对实际加载的地图

下方 `auto_initialize` 为历史可选扩展，前两项用于核对地图路径：

```bash
ros2 param get /red_standard_robot1/map_server yaml_filename
ros2 param get /red_standard_robot1/small_gicp_relocalization prior_pcd_file
ros2 param get /red_standard_robot1/small_gicp_relocalization auto_initialize
```

```bash
ls -lh /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/map/reality/lab_20260826_01.yaml /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/map/reality/lab_20260826_01.pgm /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/pcd/reality/lab_20260826_01.pcd
```

`lab_20260826_01` 是例子，替换为当前地图名。文件名一致、非零大小只是必要检查；还必须来自同一次建图，二维 YAML 的 `image` 也要指向对应图片。`final2` 若不是当前场地，不应期待正确匹配。

### 根据日志处理

下表的自动初始化参数与日志来自历史本地 GICP 修改；当前 Navigation-2027 基线没有据此被证明支持免 initialpose 自动重定位。运行参数不存在时登记版本差异，按[重定位专题](../sensor-lio/README.md)查当前入口。

| 日志 | 意义 | 处理 |
| --- | --- | --- |
| `Couldn't read PCD file` | 先验 PCD 加载失败 | 查实际参数路径、文件、权限与格式 |
| `GICP did not converge` | 本轮匹配未收敛 | 查 registered_scan、外参、场地与地图、起始位置 |
| `Rejected GICP jump` | 本轮校正超过限幅，被拒绝 | 看是否起始匹配不对，不直接无限放宽限幅 |
| `Auto-initialized at the map origin...` | 从地图原点开始初始化 | 不是已经找到真实位置的证明 |
| `Automatic GICP initialization is complete` | 自动初始化阶段结束 | 仍需静止点云、真实环境、二维地图对应关系确认 |

保存源码里的自动初始化采用地图原点附近的 GICP 初值，不是任意地点的全地图搜索。以前配置的启动限幅是 `3 m / 45°`，持续校正限幅是 `0.4 m / 10°`，`smoothing_alpha=0.15`；现场用 `ros2 param get` 核对当前值。

必要时用一次 `2D Pose Estimate` 提供正确位置与方向，等待匹配稳定。只有确认真实场地与旧图已经不符，或旧图本身存在明显失真，才把重新建图作为下一步；单纯 TF 断开或重复实例不靠重建地图解决。

## 9. 串口冲突、掉线、底盘收不到速度

把这节当作边界核对：ROS 一侧是否有正确消息和消费者，系统一侧是否打开正确设备，协议一侧是否被接收认可，硬件一侧是否允许执行。设备名存在只支持其中一项。示意：最终速度有 `0.2 m/s` 而订阅数为 0，先找消费者；消费者已连上而 CRC 连续失败，则需要串口/电控负责人查数据包。

本队 C++ 实现的字段映射可读 [standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp][run-serial-callback]：`cmdVelCallback` 将 x、y、angular.z 写入发送状态。它说明这份实现如何取字段，不能证明当前部署用它，也不能证明固件已经执行这些数值。下方独立 rm_serial_driver 的反馈命令仍属于历史条件。

本节 `/rm_serial_driver` 及 `/serial/chassis_*` 来自历史独立驱动。Navigation-2027 克隆中另有不同 Python/C++ 串口实现，节点名、状态类型与设备配置不等价；先按[接口证据 R1–R2](../system/nav2-and-control-evidence.md)登记本次使用哪一套。

### 检查设备与占用

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/serial/by-id/* 2>/dev/null
```

```bash
ros2 param get /rm_serial_driver device_name
```

```bash
sudo fuser -v /dev/ttyACM0
```

```bash
sudo lsof /dev/ttyACM0
```

`ttyACM0` 必须换成上面参数里的实际端口。`lsof` 未安装时使用 `fuser`。若同时有 `rm_serial_driver` 和 SP 视觉工程串口程序占用同一设备，是我们曾经遇到的冲突方式；两者不能同时作为这个端口的控制者。

### 检查返回反馈

```bash
ros2 topic info /serial/chassis_enabled -v
ros2 topic info /serial/chassis_velocity_feedback -v
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /serial/chassis_enabled std_msgs/msg/UInt8
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /serial/chassis_velocity_feedback geometry_msgs/msg/Twist
```

这些是之前加到串口驱动的只读诊断话题，旧版本驱动可能没有。没有诊断话题不能直接证明电控没回包，先查驱动版本。`enabled` 的取值是直接转发的电控字段，具体值/位含义由电控协议确认，不能一律把任意非零都解释为使能成功。

| 结果 | 判断与处理 |
| --- | --- |
| `No such file` | 拔插后设备号改变、未识别或参数不对；查真实设备路径 |
| `Permission denied` | 查 `id` 和设备所属组；若确为缺少 `dialout`，由管理员授予并重新登录 |
| 两个程序打开相同端口 | 定向停止重复程序，只保留本次使用的串口驱动 |
| 不断 `reopen port`、接收错误 | 查线缆、供电、设备重枚举、占用和驱动日志 |
| CRC 错误反复出现 | 查通信/数据包解析、协议一致性，不能靠改 Nav2 参数修复 |
| 输入速度非零，发送成功但反馈为零 | 发送 API 成功不代表电控已执行；查控制模式、使能和返回数据 |
| 反馈持续非零而实际运动不符 | 查反馈字段单位/来源以及硬件执行，由电控维护者核对 |

设备重连日志：

```bash
sudo journalctl -k -b --no-pager | grep -Ei 'ttyACM|ttyUSB|usb|disconnect|reset' | tail -n 60
```

处理后复查：仅预期程序占用端口，`cmd_vel` 有正确订阅者，回包恢复，物理运动与请求一致。共享实验室设备上不要通过给串口 `chmod 777` 掩盖权限和占用问题。

## 10. 撞桌腿、绕障失败、膨胀半径该不该改

障碍要先被感知和保留，再进入 costmap，最后才影响路径与运动。若桌腿在点云中消失，增加膨胀半径只会膨胀其他已识别障碍；若桌腿已标记而车角扫过去，则要看足迹、坐标与最终旋转。按这些层级观察，才能知道参数该改在哪一层。

本队输入与门限在 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml][run-costmap]，控制器速度/采样调用在 [ros_ws/src/pb2025_sentry_nav/pb_omni_pid_pursuit_controller/src/omni_pid_pursuit_controller.cpp][run-controller] 的 `computeVelocityCommands`。先把现场障碍与 costmap 标记对上，再读代码使用了什么检查；不能由源码存在 `isCollisionDetected` 就宣称实车完整扫掠已验收。

先在 RViz 打开原始点云、`terrain_map`、局部/全局代价地图和足迹，确认桌腿依次出现在这些层里。

```bash
ros2 node info /red_standard_robot1/local_costmap/local_costmap
ros2 param get /red_standard_robot1/local_costmap/local_costmap obstacle_layer.observation_sources
ros2 param get /red_standard_robot1/local_costmap/local_costmap obstacle_layer.terrain_map.topic
```

以前的配置使用 `pb_nav2_costmap_2d::IntensityObstacleLayer`，其直接观测输入是 `terrain_map` 点云。**`obstacle_scan` 正常不等于代价地图一定收到、采纳了障碍。** 以运行参数和订阅端点确认实际输入。

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/terrain_map
```

```bash
ros2 param get /red_standard_robot1/local_costmap/local_costmap footprint
ros2 param get /red_standard_robot1/local_costmap/local_costmap footprint_padding
ros2 param get /red_standard_robot1/local_costmap/local_costmap robot_base_frame
ros2 param get /red_standard_robot1/local_costmap/local_costmap inflation_layer.inflation_radius
ros2 param get /red_standard_robot1/global_costmap/global_costmap inflation_layer.inflation_radius
ros2 param get /red_standard_robot1/controller_server FollowPath.enable_collision_guard
```

| 观察 | 问题位置 | 处理方向 |
| --- | --- | --- |
| 原始点云就看不到桌腿 | 视野盲区、遮挡、距离或传感器 | 改进传感覆盖；膨胀不能创造缺失障碍 |
| 原始点云看得到，terrain_map 没有 | 地面/高度/强度过滤、动态清除或坐标变换 | 定位是哪一级把桌腿滤掉 |
| terrain_map 看得到，costmap 没标记 | 观测话题、QoS、marking、TF 或强度/高度门限 | 查代价地图运行参数和日志 |
| costmap 标记了，但路径贴障碍 | 足迹、规划器代价权重、膨胀势场 | 小步调整对应参数并复查路径 |
| 路径安全但实际轨迹扫到障碍 | 速度坐标系、旋转扫掠、跟踪误差或反馈 | 对比轨迹、足迹 TF 与真实车体 |

长 `0.60 m`、宽 `0.45 m` 且底盘坐标原点在矩形中心时，角点旋转扫掠半径为 `sqrt(0.30² + 0.225²) = 0.375 m`，还要计入余量与定位误差。若代价地图足迹挂在 `gimbal_yaw_fake`，必须核对它的位置/朝向是否真实代表底盘；云台与底盘独立转动时，这一点尤其重要。

**此前我们将膨胀从 `0.50` 调到 `0.60 m`，但不能据此承诺实际绕障距离增加 `10 cm`。** 膨胀是对已识别障碍建立代价势场，不是整圈都不可走的硬墙；`cost_scaling_factor` 越大，代价衰减通常越快。影响还取决于规划器如何使用代价与足迹。参数含义见 [Nav2 Inflation Layer](https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/costmap_2d/costmap_plugins/inflation/)，本文只使用 Humble 已有参数。

历史本地控制器曾增加可选 `enable_collision_guard` 并设置为 `false`。该参数不属于所有版本；Navigation-2027 审查基线有不同的采样碰撞逻辑与边界，见[风险 R8](../system/nav2-and-control-evidence.md)。若当前仍为 false，不能假设“有代价地图就一定有完整轨迹碰撞检查”。后置 `fake_vel_transform` 添加的自旋也可能改变控制器原本检查的运动，需要核对最终输出轨迹。把膨胀变大、把速度变慢都不能替代这项核对。

## 11. 底盘一顿一顿、前进后退、恢复频繁

顿挫可能来自上游主动停止/恢复，也可能来自转换同步间断或执行端反馈。把同一时间区间的三段速度、Action 和底盘反馈放在一起，才能区分。示意：控制器先报进展失败，随后上游速度改成恢复动作，这是任务决策；上游始终稳定、最终输出忽零忽非零，则先查转换节点。

恢复顺序可读 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml][run-bt]：规划与跟踪各有清图恢复，外层还会轮换恢复动作。XML 说明“可能走哪些分支”，日志、反馈与时间顺序才说明“这次走了哪条”。

### 读频率与速度值

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/cmd_vel_nav2_result
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/cmd_vel
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel geometry_msgs/msg/Twist --field angular.z
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel geometry_msgs/msg/Twist --field linear
```

以前输入约 `20 Hz`，输出约 `17–19 Hz`，最大间隔约 `0.1 s`。它显示转发存在间隔变化，但**不能单独证明这是物理顿挫的根因**。看非零、零、反向速度是否与停顿同步，再结合反馈区分控制决策和硬件执行。

### 查恢复与进展参数

`BackUp` 的名字不保证是标准沿车后退：本队基线可能装载 `BackUpFreeSpace` 搜索自由方向。先查运行插件与[BT/控制链](../nav2/README.md)，下方距离和速度仅为历史案例。

```bash
ros2 param get /red_standard_robot1/controller_server progress_checker.required_movement_radius
ros2 param get /red_standard_robot1/controller_server progress_checker.movement_time_allowance
ros2 param get /red_standard_robot1/bt_navigator default_nav_to_pose_bt_xml
```

```bash
grep -nE 'BackUp|backup_dist|backup_speed' /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_through_poses_w_replanning_and_recovery.xml
```

```bash
grep -RniE 'Failed to make progress|BackUp|Collision|collision|Failed to control|abort|Failed to find' /home/ubuntu/.ros/log/latest 2>/dev/null | tail -n 80
```

`~/.ros/log/latest` 可能已经指向后来启动的 RViz/其他 launch，也可能没有保存控制器终端的全部输出。无匹配行只能说明这批日志没搜到，不能证明没有恢复。需要结合本次导航终端、Action 状态与实际速度。

| 证据 | 处理方向 |
| --- | --- |
| `Failed to make progress` 后开始后退 | 查平移是否真实受阻、进展距离/时间是否过严 |
| 只看到了行为树里有 BackUp | 只能说明“具备这个行为”，不能证明本次正在执行恢复 |
| Nav2 输入先归零，输出跟着归零 | 上游停止决策，查规划、控制和恢复 |
| 输入稳定，输出间断或异常 | fake_vel_transform 的同步、缓存、TF 或其他发布者 |
| 命令稳定，串口反馈仍顿挫 | 通信与执行链，交给相关维护者结合反馈查 |

之前按你的选择改为：进展距离 `0.15 m`、时间 `7 s`、恢复后退 `0.50 m`、速度 `0.20 m/s`。这是历史试验值，不是已证明适合所有场地的标准值。`7 s` 比 `10 s` 更容易触发超时。

`SimpleProgressChecker` 看的是相对基准位置的平移，不是累计路程，也不把原地自旋当作平移进展。因此一直旋转或短距离来回可能仍超时。依据：[Humble SimpleProgressChecker 源码](https://github.com/ros-navigation/navigation2/blob/humble/nav2_controller/plugins/simple_progress_checker.cpp)。

## 12. 底盘在自旋，云台/雷达没有跟随

底盘和云台是两个控制对象。给 Twist 的 angular.z 加值只提出底盘旋转请求，没有自动产生云台关节位置请求。示意：底盘转了 90°，云台保持世界朝向时，相对底盘关节就可能反向转 90°；如果只是模型 TF 被固定，看起来一起转也不能证明硬件跟随。

接口位置可对照 [standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp][run-gimbal-callback] 的 `cmdGimbalJointCallback`：它按 JointState 的 joint name 读取 position，和底盘 Twist 是不同订阅。实际控制模式与反馈仍需部署登记；先查消费者、类型与关节反馈，再由负责人安排硬件验证。

历史案例的云台跟随尚未完成接口/反馈验证。Navigation-2027 的 C++ 串口接口另有 JointState 云台通路，不能把历史 rm_serial_driver 没有订阅等结论直接套到本队部署；先查实际订阅者，不猜格式发送新命令。

```bash
ros2 topic info /red_standard_robot1/cmd_gimbal_joint -v
```

```bash
ros2 topic list | grep -Ei 'gimbal|joint|serial'
ros2 node info /rm_serial_driver
ros2 param get /red_standard_robot1/fake_vel_transform init_spin_speed
```

| 输出 | 判断 |
| --- | --- |
| 存在 cmd_gimbal_joint，但 Subscription count 为 0 | 该 ROS 话题没有消费者；向它发布也不会经这个话题控制硬件 |
| 有发布者、无订阅者 | 发布者并不能构成完整云台控制通路 |
| 有订阅者 | 继续查消费者源码、协议和控制模式，不猜角度/角速度含义 |
| cmd_vel.angular.z 非零、底盘转 | 只证明底盘旋转请求与现象，不能证明云台也收到旋转请求 |
| RViz 的云台跟车转，但实物不转 | 检查关节反馈是否真实，模型显示不是硬件执行证据 |

已读过的 `fake_vel_transform` 只将附加自旋加到 `Twist.angular.z`，没有云台控制发布。云台可能在世界坐标下保持朝向，也可能受独立控制模式约束；**具体原因尚未通过接口和反馈验证，不能直接下定论。**

历史修改后的实现按“非零平移速度”添加自旋，并没有直接监听 Goal 状态。**Navigation-2027 审查基线却是始终叠加 spin_speed，全零输入也可能输出旋转**；见[停止路径证据 R3–R7](../system/nav2-and-control-evidence.md)，两者不可混作同一版本。因此前进、后退或其他经过同一通路的平移都可能触发附加自旋；不能严格称为已经实现“仅 Goal 期间整体旋转”。

`init_spin_speed` 是初始化参数。`/cmd_spin` 回调可以直接改内部速度，参数读数未必同步反映这个变量；最终仍需对比输入输出速度。云台相对底盘固定的真实状态应由实际关节反馈验证，不能添加假的静态 TF 让 RViz 看起来跟随。

## 13. 机器人斜着、点云斜着，雷达安装倾斜 30°

先分清“传感器相对车斜”与“车相对地面斜”。真实安装角应该进入外参，使雷达坐标中的斜地面换算到车体时成为正确地面；把外参归零反而可能把安装倾角留在点云里。下面同时看安装 TF 与车体 TF，正是为了分离这两种角度。

模型差异也要查来源：[ros_ws/src/pb2025_robot_description/resource/xmacro/uic2025_sentry_robot.sdf.xmacro][run-uic] 的雷达在 gimbal_yaw 上、roll 为 -π/6；[ros_ws/src/pb2025_robot_description/resource/xmacro/pb2025_sentry_robot.sdf.xmacro][run-pb] 则在 chassis 上、roll 为 -π/12。下方历史 -30° 记录不能自动套到选用 PB 模型的仿真，先确认本次模型与实物。

```bash
timeout --signal=INT --kill-after=2s 8s ros2 run tf2_ros tf2_echo base_footprint front_mid360 --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

```bash
timeout --signal=INT --kill-after=2s 8s ros2 run tf2_ros tf2_echo odom base_footprint --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

以前 `base_footprint → front_mid360` 输出 `RPY [-30°, 0°, 0°]`，平移约 `[-0.036, 0.093, 0.576] m`，你也确认雷达确实倾斜 `30°`。

这表示安装变换中存在约 `-30°` 的 **roll**，并不等于云台 pitch 向下 `30°`。判断方向必须结合轴定义和实物。正确外参本来就应保留真实安装角，不能为了模型好看直接归零。

| 结果 | 处理 |
| --- | --- |
| 雷达相对车倾斜符合安装，车体相对 odom 近似水平 | 雷达斜着本身正常 |
| 静止平地，车体 TF 也出现大角度倾斜 | 查外参组合、IMU 轴、Point-LIO 变换、是否重复补偿 |
| 地面点云变成倾斜平面或障碍物高度错误 | 查点云 frame_id 与安装变换是否一致 |
| 实物云台朝下但 TF 正常 | 查云台反馈/控制模式，显示变换不一定能解释物理姿态 |

小幅几度姿态变化要结合实际地面、车体和 IMU 误差评估；单纯 yaw 约 `96°` 只是朝向，不能叫“车体倾斜”。

## 14. RViz 白色模型、OpenGL 报错、显示冻结

RViz 是数据的观察窗口。窗口的渲染失败、订阅配置错误与导航内部失败可以有相同的“画面不动”，所以先用 CLI 独立确认数据和 TF，再判断窗口。比如 odometry 连续更新、TF 可查、只有 Map 的 GLSL 报错，先查显示链；若 odometry 本身没消息，转回第 5 节。

独立显示入口在 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rviz_launch.py][run-rviz]，只创建 RViz 并 remap TF。它解释了为什么单独重开显示不必再启动整个导航，也提醒你核对 RViz namespace 与 TF Topic。

此前出现过：`active samplers with a different type refer to the same texture image unit`，属于渲染器/显卡/材质相关错误，不直接证明串口或 Goal 坏了。

先展开 RViz 左侧 `RobotModel`、点云、Map 的 `Status`，记录具体红色错误。再用第 4、5、7 节独立确认 TF、odometry、Action 和速度。

| 现象 | 优先检查 |
| --- | --- |
| 白色但 TF 和数据正常 | 模型材质、资源路径、光照/OpenGL |
| 模型不更新且 odometry 也没有 | 运动数据链问题 |
| 模型状态显示缺少 TF | frame 链或消息时间问题 |
| 地图出现 GLSL 错误、其他话题仍正常 | RViz 渲染问题，可单独测试软件渲染 |

如需单独测试 RViz 软件渲染，先关闭原 RViz；不要额外启动第二套导航。在 Ubuntu 桌面、已加载环境的诊断终端执行：

```bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch pb2025_nav_bringup rviz_launch.py namespace:=red_standard_robot1
```

软件渲染可能增加 CPU 负载，若显示恢复也要复查点云处理没有明显积压。此前的 `start_rviz_safe.sh` 还固定了显示会话路径；换用户或桌面会话后不要假设它仍通用。

## 15. 参数改了没效果、构建 0 个包、环境错误

同一名字的包可能有多份：src 是编辑来源，install 是启动通常使用的产物，旧进程还保存着启动时读入的值。示意：你改了工作区 A 的 YAML，prefix 却在 B，运行参数不变是合理结果。按“prefix→安装文件→启动选择→有效参数”查，才能确定改变真正到达了节点。

本队 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py][run-yaml] 会用 `RewrittenYaml` 改写 namespace、use_sim_time 与 autostart。这解释了为什么原文件与最终参数可能有差异；读原文件之后还要读 launch 的覆盖来源与本次 param dump。

### 检查实际运行的包

```bash
ros2 pkg prefix pb2025_nav_bringup
```

预期指向 `/home/ubuntu/navigation_2025/ros_ws/install/...`，而不是另一个旧工作空间。isolated/merged install 的具体层级可能不同。

```bash
cd /home/ubuntu/navigation_2025/ros_ws
colcon list | grep pb2025_nav_bringup
```

| 输出 | 意义与处理 |
| --- | --- |
| `ros2: command not found` | 没加载环境，先执行 1.1 |
| 包找不到 | 工作空间/overlay 不对或包没安装，核对 colcon list 和 pkg prefix |
| `unknown package 'pb2025_nav_bringupcd'` | 两条命令粘连，重新输入正确包名 |
| `Summary: 0 packages finished` | 没完成目标包构建，不能当成功 |
| `Summary: 1 package finished` 且无失败 | 本次选中的包构建完成；仍需重新加载环境并检查运行配置 |
| 源文件与 install 内容相同 | 只证明文件一致，不能证明旧进程已重新读取它 |

### 更新 bringup 配置

先完整退出相关 launch，再执行：

```bash
cd /home/ubuntu/navigation_2025/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source install/setup.bash
colcon build --symlink-install --packages-select pb2025_nav_bringup
```

确认成功后：

```bash
source /home/ubuntu/navigation_2025/ros_ws/install/setup.bash
```

只改 YAML/XML，更新 bringup 即可；修改 C++ 则必须构建对应 C++ 包，例如 `fake_vel_transform` 或 `small_gicp_relocalization`，仅构建 bringup 不会编译这些源码。

`--symlink-install` 可以让部分文件改动直接反映到 install，但已有进程不会因此自动重新加载启动参数。比较 install 文件时，以实际包路径为准：

```bash
grep -nE 'init_spin_speed|required_movement_radius|movement_time_allowance|inflation_radius' "$(ros2 pkg prefix pb2025_nav_bringup)/share/pb2025_nav_bringup/config/reality/nav2_params.yaml"
```

最后用 `ros2 param get` 查运行节点，这比只看 YAML 更接近真正在使用的值。行为树还要查 `default_nav_to_pose_bt_xml` 的实际路径与 XML 文件；它不一定会直接作为已展开参数显示。

### ROS 命令自己报 `RuntimeError: !rclpy.ok()`

这是此前出现过的 ROS CLI daemon 故障。可执行：

```bash
ros2 daemon stop
ros2 daemon start
```

然后重新运行诊断命令。重启 daemon 不会停止或重启导航，也不会修复断开的真实 TF。显式写出消息类型有助于排除类型自动发现问题，但不能保证绕过所有 daemon/QoS 查询。

`Invalid field 'angular.zvvvvvv'` 是字段名粘贴错误，应改回 `angular.z`。若出现 `^[[200~` 一类字符，按 `Ctrl+C` 清掉当前输入，再重新粘贴干净的一条。

## 16. 驱动退出、`-11`、`-9`、库冲突

退出码告诉你“怎么结束”，根因要靠此前发生的事件定位。-11 是段错误，但可能涉及错误数据、对象生命周期或库兼容；-9 可能来自 OOM，也可能来自 launch 停止超时。先记下首条异常和按停止键的时刻，再看内核日志，就不会把退出清理失败误记成导航运行崩溃。

### 查首次错误与退出时序

```bash
ls -lt /home/ubuntu/.ros/log | head -n 12
```

```bash
grep -RniE 'process has died|ERROR|segmentation|symbol lookup|undefined symbol|cannot open shared object|failed to terminate' /home/ubuntu/.ros/log/latest 2>/dev/null | tail -n 100
```

```bash
ps -eo pid,ppid,stat,args | grep -E '[l]ivox_ros_driver2_node|[p]ointlio_mapping|[c]omponent_container.*nav2_container'
```

| 输出 | 判断 |
| --- | --- |
| `exit code -11` | 进程收到 SIGSEGV，需找崩溃位置；错误码本身不告诉你根因 |
| `exit code -9` 且前面有 launch 升级到 SIGKILL | launch 等待退出超时后强制终止，不一定是运行阶段崩溃 |
| 内核有 `Out of memory`、`Killed process` | 查内存压力与 OOM，区别于 launch 主动 SIGKILL |
| `undefined symbol`、库加载错误 | 查 overlay 与实际加载库，使用干净环境重新 source |
| 只在 Ctrl+C 后驱动出现错误 | 可能是退出清理路径问题，和正常运行时崩溃分开记录 |

```bash
sudo journalctl -k -b --no-pager | grep -Ei 'out of memory|oom|killed process|segfault' | tail -n 60
```

```bash
printenv LD_LIBRARY_PATH
```

若需要进一步查 Point-LIO 库加载，可先读：

```bash
ldd /home/ubuntu/navigation_2025/ros_ws/install/point_lio/lib/point_lio/pointlio_mapping | grep -Ei 'not found|pcl|usb|MVS'
```

先确认程序没有重复运行，再处理库路径和驱动错误。重复启动、时间问题、网络问题不能单靠升级到 SIGKILL 修复。建图正常退出时可能写 PCD，强制终止会影响保存，先区分“正常停止保存”与“清理已坏掉的残留”。

## 17. SSH 连不上时怎么分段判断

SSH 连线分为找地址、走路由、建立 TCP、认证四步。示意：`TcpTestSucceeded=True` 后仍 Permission denied，网络已走到认证边界，应查用户和密钥；一直 timeout 时，还没有证据支持修改用户口令。抓包是用来确认请求走到了哪一端，必须用本次客户端/服务器地址。

在 Linux 检查当前地址和监听：

```bash
hostname -I
ip -br addr
sudo ss -lntp | grep ':22'
sudo ufw status verbose
```

在 Windows PowerShell 检查选中的地址：

```powershell
Test-NetConnection 192.168.1.50 -Port 22
```

历史 IP `172.16.183.83`、`192.168.1.50`、`192.168.1.48` 不能保证现在仍有效。根据本次双方的 IP 和路由选择可达的网卡，`172.17.0.1` 通常是 Docker 网桥，先用 `ip -br addr` 确认。

| 结果 | 意义与处理 |
| --- | --- |
| `TcpTestSucceeded: True` | TCP 22 可达，再检查用户名、密钥或认证 |
| `Connection timed out` | 没收到有效建立连接响应，查网络、路由、防火墙和目标地址 |
| `Connection refused` | 通常到达了拒绝连接的主机/设备，查 sshd 服务与监听 |
| `Permission denied` | 已进入 SSH 认证阶段，查用户、密钥或口令 |
| `Could not resolve hostname lab-linux` | Windows SSH 别名配置缺失或写错 |
| Ping `TtlExpired` | 可能存在路由循环；不说明 sshd 未启动 |

Linux 抓包时将 Windows 地址换成这次实际地址：

```bash
sudo tcpdump -ni any 'tcp port 22 and host 192.168.1.64'
```

然后 Windows 再连接一次。无任何匹配包：请求可能没到 Linux，先查客户端地址/路由和中间网络；重复 SYN 没有回复：查 Linux 网络/过滤；能看到 SYN、SYN-ACK 但没有完成握手：查回程或客户端过滤。空抓包前提是选对本次客户端 IP。

## 18. 每次重启后的复测流程

重启会清空部分状态，但不一定消除触发条件。复测要重复原来的模式、地图和输入，让“这次又通过”能与“原来在哪失败”比较。比如清掉重复启动后，除了节点数正常，还要看原先跳动的里程计、TF 与任务是否恢复；若改了停止路径，则零、取消、断流也应回归。

以下两终端启动代码仅对应已登记的历史双工作空间案例。当前 Navigation-2027 先按[环境页](../onboarding/environment.md)补齐实际串口包/地图/模型，并按[实车流程](README.md)确认停止链；不要直接把历史路径与参数作为本队默认启动。

1. 先查第 3 节进程，确认开机没有意外自动启动导航；已有实例就不要再启动一套。
2. 终端 1 启动串口，终端 2 启动所需模式并包含 RViz。
3. 等数据稳定，检查无重复组件、`odometry` 有数据、三段 TF 连通。
4. 建图确认在线地图更新；导航确认加载的二维图与先验 PCD 是同一次建图且定位正确。
5. 确认 Action server 与三个 lifecycle 状态，再测试 Goal。
6. 有异常时先收集数据，记录模式、地图名、机器人是否静止、异常时间和本次日志目录。
7. 只改有证据指向的参数或模块，重启对应程序后用同一流程复查。

### 终端 1：串口

```bash
cd /home/ubuntu/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch rm_serial_driver serial_driver.launch.py
```

### 终端 2：建图，二选一

```bash
cd /home/ubuntu/navigation_2025/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py slam:=True use_robot_state_pub:=True use_rviz:=True
```

### 终端 2：导航，二选一

```bash
cd /home/ubuntu/navigation_2025/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py world:=lab_20260826_01 slam:=False use_robot_state_pub:=True use_rviz:=True
```

根据当前地图替换 `world`，不要同时执行建图和导航两条。诊断或保存地图需要临时再开一个终端，不是另启动一套导航。

### 历史试验参数核对表

| 项目 | 最近一次对话确认的值 | 当前怎么确认 |
| --- | --- | --- |
| 初始附加底盘自旋 | `0.8 rad/s` | fake_vel_transform 的初始化参数 + 最终 cmd_vel；云台跟随未完成 |
| 进展距离 | `0.15 m` | controller_server 的 progress_checker.required_movement_radius |
| 进展等待 | `7.0 s` | controller_server 的 progress_checker.movement_time_allowance |
| 恢复后退距离 | `0.50 m` | 实际使用的行为树 XML |
| 恢复后退速度 | `0.20 m/s` | 实际使用的行为树 XML |
| 局部/全局膨胀 | `0.60 m` | 两个 costmap 的 inflation_layer.inflation_radius |
| 足迹余量 | `0.03 m` | 两个 costmap 的 footprint_padding |

这些值是调试记录，不是碰撞安全保证。此前老文档中的 `0.0` 自旋、`0.5` 膨胀等值属于更早状态，不用老文档替代运行参数。

## 19. 一键收集报告

报告是一张按顺序拍出的快照，不是同时录下所有量的电影。前半段 Action 在执行，后半段速度已归零，可能只是任务在采样期间结束；不能凭两段输出说“执行中却没速度”。需要因果时序时，还要结合本次连续日志或短 bag。

源码蓝色入口是 [docs/navigation/debug-real/assets/collect_navigation_debug.sh][run-collector]。读 `run_probe` 时看它如何记录命令与退出码，再看后面的循环如何依次查询；它返回 0 是为了继续收集，真实探测退出码写在报告中。

下载[只读采集脚本](assets/collect_navigation_debug.sh)。从知识库根目录，先在当前终端加载已登记的 ROS/工作空间，再执行：

```bash
bash docs/navigation/debug-real/assets/collect_navigation_debug.sh --help
```

```bash
bash docs/navigation/debug-real/assets/collect_navigation_debug.sh --namespace /red_standard_robot1
```

默认快速检查当前终端的图信息；加 `--full` 采样频率和三段 TF。只有显式提供 `--nav-workspace`、可选 `--serial-workspace` 时，脚本才 source 这些工作空间。`--serial-node` 使用本次登记的节点名；缺失的历史接口不会被当成已提供功能。

报告保存在当前用户的 `$HOME/nav_debug_reports/时间_随机后缀`，可用 `--report-root` 指定新位置。包含 report.txt、nodes.txt、topics.txt。脚本只查询状态、写报告，不发 Goal/速度/云台命令，不停止进程、不改参数、不重启 daemon、不自动 sudo。

采样顺序执行；空闲时零速度正常。源参数文件与运行参数不是同一层，latest 日志也可能来自另一条 launch。接口不存在、查询超时、类型不同都会保留证据；脚本结束只表示采集完成，不代表机器人健康。

本次知识库更新验证 Bash 语法与离线模拟场景，未连接真实机器人。报告送审时同时写明“工程 commit、模式、地图、命名空间、静止/Goal 执行中、具体异常时间”。脚本详解见[新人版第 20 节](command-guide.md)。

[run-loam]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp#L23-L51
[run-scan-sync]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp#L38-L59
[run-velocity-launch]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L160-L306
[run-components]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L253-L286
[run-scan-handler]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp#L62-L85
[run-loam-tf]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp#L63-L97
[run-scan-tf]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp#L88-L100
[run-gicp]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/small_gicp_relocalization/src/small_gicp_relocalization.cpp#L95-L167
[run-serial-callback]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp#L658-L663
[run-costmap]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L368-L450
[run-controller]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_omni_pid_pursuit_controller/src/omni_pid_pursuit_controller.cpp#L219-L277
[run-bt]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml#L5-L38
[run-gimbal-callback]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp#L665-L680
[run-uic]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/resource/xmacro/uic2025_sentry_robot.sdf.xmacro#L15-L22
[run-pb]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/resource/xmacro/pb2025_sentry_robot.sdf.xmacro#L14-L27
[run-rviz]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rviz_launch.py#L27-L62
[run-yaml]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L52-L63
[run-collector]: https://github.com/Navigator-Vision-Algorithm-Team/knowledge-base/blob/main/docs/navigation/debug-real/assets/collect_navigation_debug.sh#L106-L225
