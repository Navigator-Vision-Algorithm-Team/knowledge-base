# ROS 2 Humble 教学包运行与验证

目标环境是 Ubuntu 22.04、ROS 2 Humble、Python 3.10。`nav_training` 是独立的 `ament_python` 包，使用标准消息和官方教程的 Fibonacci Action 接口。它只计算理想平面运动，不包含串口、底盘驱动、传感器驱动或真实导航算法。

## 安装和构建

以下命令从仓库根目录开始。在已安装 Humble 的 Ubuntu 机器上执行；每个新终端都需要 source 环境。选择未被其他实验占用的 ROS domain。

```bash
sudo apt-get update
sudo apt-get install -y python3-colcon-common-extensions python3-pytest \
  ros-humble-launch-ros ros-humble-action-tutorials-interfaces \
  ros-humble-geometry-msgs ros-humble-nav-msgs ros-humble-std-msgs \
  ros-humble-tf2-msgs ros-humble-rosbag2
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=87
export ROS_LOCALHOST_ONLY=1
cd training/ros2_ws
colcon build --symlink-install --packages-select nav_training
source install/setup.bash
ros2 pkg executables nav_training
```

最后一条命令应列出 `sequence_publisher`、`sequence_subscriber`、`ideal_model`、`fibonacci_server`、`fibonacci_client` 五个入口。回到仓库根目录后，可用 `source training/ros2_ws/install/setup.bash`。

## 健康和故障链路

```bash
ros2 launch nav_training healthy.launch.py
```

另一个已 source 的终端执行：

```bash
ros2 topic echo /nav_training/sequence
ros2 topic echo /nav_training/received
```

两个话题均应输出递增的 `std_msgs/msg/Int64`。按 Ctrl+C 结束当前命令后再执行下一条。健康 launch 同时启动运动模型；序号发布器不产生运动命令。

结束健康 launch，然后运行故障预设：

```bash
ros2 launch nav_training bad_topic.launch.py
ros2 node info /nav_training/sequence_sink
```

发布节点 `/nav_training/sequence_source` 输出 `/nav_training/sequence`，订阅节点 `/nav_training/sequence_sink` 却订阅 `/sequence`。此时 `/nav_training/received` 没有消息。结束故障 launch，使用相对话题修复：

```bash
ros2 launch nav_training bad_topic.launch.py sink_topic:=sequence
```

可直接运行单个节点练习参数：`ros2 run nav_training sequence_publisher --ros-args -p rate_hz:=5.0 -p topic:=sequence`。发布器参数为 `topic`、`rate_hz`（0.1–200 Hz）；订阅器参数为 `topic`、`output_topic`（默认 `received`）。这些参数启动时生效，运行时修改会被拒绝；重启后再比较行为。

## 运动、超时与 TF

健康 launch 默认订阅 `/nav_training/cmd_vel`，发布 `/nav_training/odom`、`/nav_training/tf` 和 `/nav_training/tf_static`。单独执行 `ros2 run nav_training ideal_model` 也使用这个命名空间。TF 消息直接发布到相对话题，避免 TF 广播器的默认全局话题。

```bash
ros2 topic pub --rate 10 /nav_training/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
```

在另一个终端查看 `ros2 topic echo /nav_training/odom`。结束命令发布后，模型默认在最后命令后 0.5 秒停止积分并输出零速度。显式的零命令和无效命令都立即替换旧命令。非有限值、非零 `linear.z`、`angular.x` 或 `angular.y` 属于无效输入；节点记录警告并应用全零速度。

平移速度按向量模长限制，保持方向；默认最大模长为 0.5 m/s，最大偏航角速度为 1 rad/s。输入 `(vx, vy, wz)=(3,4,5)` 因此输出 `(0.3,0.4,1)`。参数只能将默认速度限制调低。

| 参数 | 默认 | 允许范围 |
| --- | --- | --- |
| `rate_hz` | 20.0 | 1–200 Hz |
| `command_timeout` | 0.5 | 0.05–5 秒 |
| `max_linear` | 0.5 | 0.01–0.5 m/s |
| `max_angular` | 1.0 | 0.01–1 rad/s |

Odometry 和动态 TF 使用同一个 ROS 时间戳、位置与姿态。动态边为 `training_odom → training_base`；静态边为 `training_base → training_lidar`，平移为 `(0.2,0,0.1)` m，旋转为单位四元数。静态话题使用 reliable + transient-local，迟到的订阅者也能读取。使用 TF 工具时需将 `/tf`、`/tf_static` 重映射到对应教学话题。

`healthy.launch.py use_sim_time:=true` 只给运动模型启用 ROS 仿真时钟，需要外部 `/clock`。时钟暂停时模型也暂停；回退时保留当前位置并清除旧命令。这个超时属于教学运动模型规则，不是实物急停装置。ROS 时间中的输入看门狗也不会在暂停的 `/clock` 上继续倒计时。

## Action 的反馈、结果和取消

终端 A 启动：

```bash
ros2 run nav_training fibonacci_server
```

终端 B 逐条执行：

```bash
ros2 run nav_training fibonacci_client --ros-args -p order:=5
ros2 run nav_training fibonacci_client --ros-args -p order:=30 -p cancel_after:=0.3
ros2 run nav_training fibonacci_client --ros-args -p order:=47
```

首个结果应为 `[0,1,1,2,3,5]`，状态 4（成功）。第二个命令收到逐步反馈后请求取消，返回已完成的部分序列，状态 5（取消）。第三个目标被拒绝，客户端退出码为 2。成功与已确认取消的退出码为 0，通信超时/异常结果为 1。

Action 名称为 `/nav_training/fibonacci`，类型为 `action_tutorials_interfaces/action/Fibonacci`；反馈字段是 `partial_sequence`。目标含 0 到 46 阶的非负整数，结果包含 F0 至 Fn。超过 46 会超出该接口的 int32 容量，因此拒绝；服务器一次只接受一个目标，忙时也拒绝新目标。`order:=0` 返回 `[0]`。

服务器 `step_seconds` 默认 0.1，允许 0.02–1 秒，用墙钟控制教学反馈间隔；双线程 executor 让取消回调能在计算等待期间执行。客户端 `cancel_after` 默认 0（不主动取消），允许 0–60 秒；`wait_seconds` 默认 60，允许 1–120 秒。客户端运行超时会请求取消已接受目标。

## 自动验证与 bag 兼容性

在仓库根目录、已 source 的 Humble 环境执行：

```bash
python3 -m unittest discover -s training/ros2_ws/src/nav_training/test -v
NAV_TRAINING_REQUIRE_ROS=1 python3 -m unittest discover \
  -s training/tests -p test_ros_smoke.py -v
```

集成测试会真实启动 `ros2 launch` / `ros2 run` / `ros2 bag` 子进程，订阅 DDS 消息并检查：健康序号转发；故障订阅端点及修复；运动、速度裁剪、无效输入清零、超时停住；Odometry/TF 一致性和静态 TF 迟到订阅；Action 反馈、取消、结果、拒绝和客户端退出码。

另一个测试对已提交的 `datasets/synthetic-v1/forward/bag` 执行 `ros2 bag info` 与 `ros2 bag play --clock`，检查至少 40/51 个 Odometry 与动态 TF 样本、终点 x=1 m，以及迟到订阅的静态 TF。它验证合成 bag 在目标 Humble 运行时的实际可读性。回放时不同时启动理想模型，避免两个发布者混合 `/nav_training/odom`。

本次 Windows 工作区本地没有 ROS、WSL 或 Docker：纯 Python 速度边界 7 项通过，Python 语法检查通过；本地 ROS 集成测试因缺少 rclpy 跳过。仓库的 [Humble CI](../.github/workflows/training.yml) 设置 `NAV_TRAINING_REQUIRE_ROS=1`，缺少依赖时会失败，不能以跳过冒充通过。远程运行结论以对应提交的 CI 日志为准。

接口依据：[Humble Fibonacci 定义](https://github.com/ros2/demos/blob/humble/action_tutorials/action_tutorials_interfaces/action/Fibonacci.action)、[Humble Action 服务器示例](https://github.com/ros2/examples/blob/humble/rclpy/actions/minimal_action_server/examples_rclpy_minimal_action_server/server.py)、[Humble bag play 参数](https://github.com/ros2/rosbag2/blob/humble/ros2bag/ros2bag/verb/play.py)。本包源代码适用 [Apache-2.0](LICENSE)。
