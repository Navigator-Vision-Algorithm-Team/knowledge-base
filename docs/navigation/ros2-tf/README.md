# S1–S2：ROS2、TF、时间与全向运动

前置：[最小环境](../onboarding/environment.md)已通过。目标是写小节点、看懂通信关系，并用实验区分通信、坐标和时间问题。先在独立开发机完成；本页的教学 Topic 不接真实底盘。

## 1. 第一个自己的节点

T1 在 `nav_training_ws` 添加 publisher/subscriber：发布带递增序号的数据，订阅端输出序号、接收时间和计数。再把发布频率设为参数，用 Python launch 同时启动节点、设置 namespace 和 remap。

从空包到可运行代码，按顺序做三个官方 Humble 章节：[C++ pub/sub](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Cpp-Publisher-And-Subscriber.rst) → [C++ 参数](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-CPP.rst) → [launch 入门](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Launch/Creating-Launch-Files.rst)。章节中的包名可以保留在另一个练习包里；迁移到 `nav_training` 时要一致修改 CMake、依赖与运行名。

在 `src/training_publisher.cpp`、`src/training_subscriber.cpp` 完成自己的节点后，CMakeLists.txt 在 `ament_package()` 之前至少需要以下目标和安装规则；这段只负责构建和安装，不会自动生成节点源码：

```cmake
add_executable(training_publisher src/training_publisher.cpp)
ament_target_dependencies(training_publisher rclcpp std_msgs)
add_executable(training_subscriber src/training_subscriber.cpp)
ament_target_dependencies(training_subscriber rclcpp std_msgs)
install(TARGETS training_publisher training_subscriber
  DESTINATION lib/${PROJECT_NAME})
# 创建 launch 目录并保存 training.launch.py 后再加入这一行
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
```

重新 `colcon build --symlink-install --packages-select nav_training`，source 后分别用 `ros2 run nav_training training_publisher`、`ros2 run nav_training training_subscriber` 验证，再用 `ros2 launch nav_training training.launch.py` 验证一起启动。节点名和 Topic 在源码/launch 中设为下例所用名称，或用查询结果替换。T1 先用启动参数设置频率，动态改频率是扩展项，不能以参数值改变就认为定时器周期自动改变。

必学：workspace/package/node、消息类型、Topic、参数、Service、Action、QoS、日志和 launch。Service 适合短请求，Action 适合有持续反馈、可取消的长任务；导航 Goal 的“已接受”不等于“已到达”。

```bash
# 在两个教学节点已运行的终端旁执行
ros2 node list
ros2 node info /training_publisher
ros2 topic list -t
ros2 topic info /training_data --verbose
ros2 topic echo /training_data --once
ros2 topic hz /training_data
ros2 param list /training_publisher
ros2 action list -t
```

名称由自己的代码决定，若不一致先用 list 查询，不照抄改生产配置。故障练习：将订阅 Topic 改错一次，再构造 Best Effort 发布/Reliable 订阅不兼容一次；先保留现象、端点与 QoS 证据再修。`hz` 是观察端收到的数据速率，受 QoS 和工具负载影响，不能直接当作驱动真实采样率。

真实代码从 [loam_interface](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp) 开始读：找构造函数、declare/get_parameter、create_subscription、回调、create_publisher。先不推导滤波公式。

Action 练习先按[自定义 Action](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Creating-an-Action.rst)建立 `action_tutorials_interfaces/Fibonacci.action`，再跟随 [Humble C++ Action 教程](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Writing-an-Action-Server-Client/Cpp.rst)编译服务端/客户端。GitHub 原文的 `literalinclude` 指向源码，可直接查看 [client.cpp](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Writing-an-Action-Server-Client/scripts/client.cpp) 和 [server.cpp](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Writing-an-Action-Server-Client/scripts/server.cpp)。

官方客户端通常只发目标，T1 需要额外实现取消：在 goal_response 回调保存非空 goal_handle，在第一次或第二次 feedback 回调中用布尔标记保证只请求一次 `client_ptr_->async_cancel_goal(goal_handle)`；不要在回调里阻塞等待。记录取消响应，并在 result 回调检查 `rclcpp_action::ResultCode::CANCELED`。服务端需要接受取消，并在执行循环中检查 `is_canceling()` 后调用 `canceled(result)`。选择足够长的 Fibonacci 任务避免取消前已完成。提交自己的改动与实际状态，不能只关闭客户端充当取消。

## 2. TF 与命名空间

坐标变换采用 `p_A = T_A_B · p_B`：T_A_B 把 B 中的坐标转换到 A。理解平移、旋转、齐次变换和四元数归一化；不需要先学李群推导。米、秒、弧度与右手系见 [REP-103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst)。

用教学帧 `training_base`、`training_lidar` 做静态实验，避免和实车帧重名：

```bash
ros2 run tf2_ros static_transform_publisher --x 0.2 --y 0.0 --z 0.3 \
  --roll 0 --pitch 0 --yaw 0 \
  --frame-id training_base --child-frame-id training_lidar
```

另一个终端运行 `ros2 run tf2_ros tf2_echo training_base training_lidar`，应看到设定平移和单位旋转。RViz Fixed Frame 设 `training_base`，添加 TF，解释为什么雷达原点在该位置。不要把所有传感器机械地串成一条链；本队树见[系统地图](../system/README.md)。

本队 bringup 将 TF topic 放入机器人 namespace，但 frame ID 保留 `map`/`odom` 等。只读检查示例（节点已启动且使用默认 namespace）：

```bash
export ROBOT_NS=/red_standard_robot1
ros2 run tf2_ros tf2_echo map base_footprint --ros-args \
  -r /tf:=$ROBOT_NS/tf -r /tf_static:=$ROBOT_NS/tf_static
ros2 run tf2_tools view_frames --ros-args \
  -r /tf:=$ROBOT_NS/tf -r /tf_static:=$ROBOT_NS/tf_static
ros2 topic info "$ROBOT_NS/tf" --verbose
ros2 topic info "$ROBOT_NS/tf_static" --verbose
```

工具参数以本机 `--help` 为准。若回放，工具也需要适配回放时间；不要同时混入另一台机器同名帧。报告每条边的发布者、静态/动态、时间源和所属模式；一个 child 在同一树里不能有两个父亲。

## 3. 理想全向运动模型

T2 自写教学节点：输入 `/training/cmd_vel`（Twist），输出 `/training/odom`（Odometry）和 `training_odom→training_base` TF；用实际 dt 积分。

创建独立运动包可用 `ros2 pkg create --build-type ament_cmake nav_training_motion --dependencies rclcpp geometry_msgs nav_msgs tf2 tf2_ros`。若沿用旧包，将这些依赖加入 package.xml、CMake 的 find_package 和 ament_target_dependencies；消息与 TF 发布方式参考[Humble C++ tf2 广播器](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Cpp.rst)。

```text
xdot = cos(yaw) * vx - sin(yaw) * vy
ydot = sin(yaw) * vx + cos(yaw) * vy
yawdot = wz
x += xdot * dt; y += ydot * dt; yaw += wz * dt
```

vx/vy 是机器人坐标系速度；Odometry 的 pose 对应 header.frame_id，twist 按 child_frame_id 语义填写。处理第一帧、dt≤0、时钟回跳、输入超时和角度归一化。至少做直行、侧移、纯旋转、yaw=90° 后前进、组合运动五例。

这只是运动积分和消息接口教学。没有轮速反馈、碰撞、打滑和传感器噪声，不能称为真实里程计，也不能用于给 Nav2 实车验收打分。

## 4. bag、时间与 QoS 一起学

先读 [ROS 时间设计](https://design.ros2.org/articles/clock_and_time.html)、[Humble QoS](https://github.com/ros2/ros2_documentation/blob/humble/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst)、[rosbag2 Humble](https://github.com/ros2/rosbag2/tree/humble)。

### 录制：先有清单，再收数据

S1 先录自己的 `/training_data`：`ros2 bag record -o training_intro /training_data`，结束后 `ros2 bag info training_intro`，检查类型、时长、数量。后续由负责人采集本队原始 LiDAR/IMU、关节状态、TF、定位输出及必要导航诊断数据，按[数据清单](../maintenance/README.md)登记。

不要无条件给实车录制加 `--use-sim-time`；只有原系统依赖仿真时钟且 `/clock` 正常时才使用相应选项。录制完成当场检查关键 topic 和静态 TF 是否齐全。

### 回放分为两种，不能混在一起

| 模式 | 回放什么 | 同时不应启动什么 |
|---|---|---|
| 系统观察 | 已记录的输入、输出、完整 TF；输出接 RViz/观察工具 | 同名算法输出发布者与底盘执行端 |
| 重跑算法 | 原始 LiDAR/IMU 和必要关节/静态 TF；具体按本次算法输入白名单 | 旧 LIO、旧 map→odom、旧 odom→base TF 等与重算结果重复的发布者 |

在独立开发机/独立 ROS domain 中进行，不加载真实串口和驱动执行端。先执行 `ros2 bag info BAG_DIR`，这里 `BAG_DIR` 替换为已登记数据集路径。再根据清单准备节点的 `use_sim_time=true`，最后 `ros2 bag play BAG_DIR --clock --topics ...`（`...` 必须替换成数据集中确认过的白名单；完整语法查本机帮助）。同一回放环境只保留一个预期 `/clock` 源。

`--clock` 不会修好传感器原始错误时间戳。回放暂停/跳转/重播会考验节点状态，重新开始实验时必要地重启算法，记录预热区间。bag 不响应新 cmd_vel，不能证明闭环控制或避障成功。

先用自己的教学数据走完整命令：停止原来的 publisher，在保存了 `training_intro` 的目录执行 `ros2 bag play training_intro --clock --topics /training_data`；另一终端执行 `ros2 topic echo /training_data`，应重新看到录制的序号。需要检查依赖 ROS 时间的订阅节点时，用 `ros2 run nav_training training_subscriber --ros-args -p use_sim_time:=true` 启动，并通过 `ros2 param get /training_subscriber use_sim_time` 验证。T2 的 TF bag 可用 `rviz2 --ros-args -p use_sim_time:=true` 观察，Fixed Frame 设 `training_odom`；`ros2 param get /rviz2 use_sim_time` 和 `ros2 topic echo /clock --once` 用于核对时间源。S1 的 std_msgs 序号 bag 不包含 TF，不能要求它在 RViz 显示机器人。

QoS 先通过端点证据定位。仅在确实不兼容时，按照[官方覆盖说明](https://github.com/ros2/ros2_documentation/blob/humble/source/How-To-Guides/Overriding-QoS-Policies-For-Recording-And-Playback.rst)创建覆盖 YAML；`/tf_static` 的 transient local 历史数据也要验证。

## 5. 常见错误与通过标准

| 现象 | 优先检查 | 不应直接做 |
|---|---|---|
| 能看到 Topic，但订阅没数据 | 完整名字、类型、端点 QoS、发布计数 | 先重装 ROS |
| TF 树有边但查某个时刻失败 | header.stamp、use_sim_time、/clock、缓存、数据是否停止 | 随便加大 tolerance |
| 单车正常，多机帧乱 | ROS domain、namespace、TF topic remap、frame ID、重复发布者 | 把所有 topic 改成全局名 |
| 侧移方向错 | vx/vy 定义、yaw 旋转、接口坐标约定 | 直接把某轴乘 -1 掩盖问题 |
| 倍速回放速度变了 | 时间差分使用消息 stamp 还是墙钟/steady_clock | 把回放结果当实车速度结论 |

按 [T1–T3](../assignments/README.md)提交代码、TF 图和至少两个不同根因的故障记录。完成后进入[传感器与定位](../sensor-lio/README.md)。

具体官方章节与进阶实验见[ROS2 系统自学](../self-study/ros2-systems.md)；二维变换和时间差分可先做[带解答源码练习](../assignments/reading-labs.md)。
