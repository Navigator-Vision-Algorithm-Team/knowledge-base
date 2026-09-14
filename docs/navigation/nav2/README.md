# 真实 Nav2 与控制链

本页对齐队伍确认的 Navigation-2027 主仓库，审查提交为 `183a4109b0de2030bb8970a54654937c8b039ba9`。先能解释一条目标如何变成最终底盘速度，再进行调参和换算法。源码定位、启动条件与未解决的问题集中在[Nav2 与控制接口证据页](../system/nav2-and-control-evidence.md)。本轮只完成静态审查，没有编译、ROS运行或实车验证；下列命令和实验供 Ubuntu / ROS 2 Humble 训练环境执行。

## 学完应能交付什么

1. 标出真实 launch、有效参数、插件 ID 和 TF/话题命名空间，区分“源码有”“配置加载”“运行已激活”。
2. 从目标、规划、控制、平滑、坐标变换一直追到最终 `cmd_vel`，指出每一段消息的发送者和接收者。
3. 解释自旋、恢复、取消目标、消息中断如何影响输出，提交有时间序列证据的停车边界说明。
4. 在不改参数的情况下定位一次“有目标却不动”或“障碍物没进 costmap”，把缺失部署依赖明确记录出来。

先修能力：能在 Ubuntu/Humble 中使用工作区环境、理解 topic/action/service、读取 Odometry/Path/Twist，能检查 map/odom/机器人坐标系。这里直接使用仓库实例，不重复通用 ROS 入门课。

## 1. 先读启动链

真实入口是 `pb2025_nav_bringup/launch/rm_navigation_reality_launch.py`，默认 namespace 为 `red_standard_robot1`，参数来自 `config/reality/nav2_params.yaml`，`use_composition=True`。入口包含 Livox、bringup、手柄和默认开启的 RViz；机器人描述发布受 `use_robot_state_pub` 控制。`bringup_launch.py` 在 SLAM/定位间二选一，但始终包含 `navigation_launch.py`。

默认 Nav2 组件包括 controller、planner、smoother、behavior、bt_navigator、waypoint_follower、velocity_smoother，并用生命周期管理器管理。`fake_vel_transform`、loam_interface、sensor_scan_generation、terrain_analysis 也由 navigation launch 加载。**建图模式不等于关闭导航或禁止速度输出。**完整证据见[启动边界](../system/nav2-and-control-evidence.md#1)。

参数阅读顺序应为：启动命令覆盖值 → 被包含的 launch → 参数重写/namespace → YAML → 插件实现 → 运行时 `ros2 param get`。例如 reality YAML 的 costmap 原文写 `use_sim_time: true`，bringup 会按入口参数重写，不能只凭那一行判断实车时钟错误。

## 2. 必学、了解与进阶

| 优先级 | 本仓库对象 | 学到什么程度 |
| --- | --- | --- |
| 必学 | launch、namespace、TF、生命周期 | 能说明默认组件分支，找到三个速度话题的remap；知道节点存在与active不同 |
| 必学 | `nav2_smac_planner/SmacPlannerHybrid` / `GridBased` | 理解当前DUBIN搜索、可通行代价、最小转弯半径和内部平滑；能定位规划失败证据 |
| 必学 | `pb_omni_pid_pursuit_controller::OmniPidPursuitController` / `FollowPath` | 读前视点→PID→曲率/接近减速→x/y输出；解释0.5 m/s参数和rotation关闭的作用范围 |
| 必学 | StaticLayer、IntensityObstacleLayer、InflationLayer | 找到terrain_map来源、PointCloud2的intensity过滤、清除与标记、0.2 m机器人半径和0.7 m膨胀半径 |
| 必学 | 两份BT XML、SimpleProgressChecker、SimpleGoalChecker | 能沿成功/失败分支走读；解释3 Hz重规划、清图、重试和自由方向恢复；知道xy容差0.15 m与yaw容差6.28 rad |
| 必学 | VelocitySmoother、fake_vel_transform、底盘接口边界 | 区分限速/加速度平滑、坐标变换、自旋叠加；验证最终输出，找实际串口实现 |
| 了解 | SimpleSmoother、WaitAtWaypoint、Spin/Wait/AssistedTeleop等 | 虽配置或加载，当前默认BT并未调用独立SmoothPath、Spin、Wait等节点。能查到即可 |
| 进阶 | IntensityVoxelLayer、替换规划器/控制器、编写自定义BT与插件 | 先完成当前系统验收再对照实验；不能把库中存在的插件写成默认配置 |

实际插件、源码函数与 XML 的对应关系见[插件证据](../system/nav2-and-control-evidence.md#2-nav2)。当前默认局部控制器不是DWB、TEB、MPPI或标准RPP。控制器日志字符串中出现其他名称，也不能替代plugin参数和导出类的证据。

## 3. 从目标到最终速度

以下是默认实车组件分支。所有相对topic/action名通常加 `/red_standard_robot1/`；frame名保持 `map`、`odom`、`gimbal_yaw`、`gimbal_yaw_fake`。

```text
navigate_to_pose (nav2_msgs/action/NavigateToPose)
       ↓ bt_navigator：仓库指定的BT XML
ComputePathToPose → planner_server：GridBased / SmacPlannerHybrid
       ↓ path
FollowPath → controller_server：OmniPidPursuitController
       ↓ cmd_vel_controller (geometry_msgs/msg/Twist)
velocity_smoother
       ↓ cmd_vel_nav2_result (geometry_msgs/msg/Twist)
fake_vel_transform ← odometry / local_plan / cmd_spin
       ↓ cmd_vel (geometry_msgs/msg/Twist)
实际部署的串口/底盘接口 → 下位机 → 车体

behavior_server：BackUpFreeSpace
       └─ cmd_vel_nav2_result → fake_vel_transform（绕过velocity_smoother）
```

手柄也是控制来源：默认 `auto_control` 把平移操作转换成 NavigateToPose，manual模式才直接发Twist。松开使能键时，代码会取消此前目标并向最终cmd_vel发一次零速度。它与fake_vel_transform共同发布最终话题，当前启动链未见速度仲裁器。不能把一条零消息当作持续停车保证。

控制器 `enable_rotation=false` 时只保证它自己输出的angular.z为0；fake_vel_transform还会加上默认 `init_spin_speed=0.5`。对于里程计yaw=π/2、输入vx=0.2、vy=0，转换后应为vx≈0、vy≈-0.2；输入全零时仍可能输出wz=0.5。具体公式、同步缓存与停机风险见[速度与TF证据](../system/nav2-and-control-evidence.md#3-tf)及[风险R3–R7](../system/nav2-and-control-evidence.md#4)。

BackUpFreeSpace会向自由空间方向输出x/y，名字不代表固定倒车。默认树请求速度1.0 m/s、距离1.0 m，而FollowPath的0.5 m/s限制不约束该行为。VelocitySmoother配置的2.5 m/s上限也不是整车所有来源共有的限速。

## 4. 在部署机做只读诊断

以下命令用于已经按队伍流程启动的 Ubuntu / ROS 2 Humble 系统。先进入实际 `Navigation-2027/ros_ws`，加载环境；不要在Windows本地审查目录执行ROS命令。`timeout`结束订阅时返回124是预期的采样结束，不表示ROS节点崩溃。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 pkg prefix pb2025_nav_bringup
ros2 pkg prefix rm_serial_driver
ros2 pkg prefix standard_robot_pp_ros2
ros2 pkg prefix pb_rm_interfaces
ros2 node list
ros2 component list
ros2 action list -t
ros2 lifecycle get /red_standard_robot1/controller_server
ros2 lifecycle get /red_standard_robot1/planner_server
ros2 lifecycle get /red_standard_robot1/bt_navigator
```

先保存成功结果和明确错误。README要求的rm_serial_driver在当前源码克隆中未找到；部署机可能通过其他overlay提供，也可能缺失。包路径是定位部署来源的证据，不要为让命令通过而临时混装另一份串口实现。

核对有效参数与话题连接：

```bash
ros2 param get /red_standard_robot1/controller_server controller_plugins
ros2 param get /red_standard_robot1/controller_server FollowPath.plugin
ros2 param get /red_standard_robot1/controller_server FollowPath.enable_rotation
ros2 param get /red_standard_robot1/planner_server GridBased.plugin
ros2 param get /red_standard_robot1/local_costmap/local_costmap use_sim_time
ros2 param get /red_standard_robot1/fake_vel_transform init_spin_speed
ros2 param get /red_standard_robot1/pb_teleop_twist_joy_node control_mode
ros2 node info /red_standard_robot1/fake_vel_transform

ros2 topic info /red_standard_robot1/cmd_vel_controller --verbose
ros2 topic info /red_standard_robot1/cmd_vel_nav2_result --verbose
ros2 topic info /red_standard_robot1/cmd_vel --verbose
ros2 topic info /red_standard_robot1/terrain_map --verbose
ros2 topic info /red_standard_robot1/serial/gimbal_joint_state --verbose
ros2 topic info /serial/gimbal_joint_state --verbose
```

`init_spin_speed`是初始化参数；收到cmd_spin后，成员变量会变化，但源码没有把参数同步更新。运行时只读param结果不能代表当前spin值，必须同时查cmd_spin来源与实际输出。

分别采样速度、里程计与TF（需要对齐时在不同终端同时运行）：

```bash
timeout 8s ros2 topic echo /red_standard_robot1/cmd_vel_controller
timeout 8s ros2 topic echo /red_standard_robot1/cmd_vel_nav2_result
timeout 8s ros2 topic echo /red_standard_robot1/cmd_vel
timeout 8s ros2 topic hz /red_standard_robot1/odometry
timeout 8s ros2 topic hz /red_standard_robot1/local_plan
timeout 8s ros2 topic hz /red_standard_robot1/terrain_map
timeout 8s ros2 run tf2_ros tf2_echo map gimbal_yaw_fake --ros-args \
  -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
timeout 8s ros2 run tf2_ros tf2_echo gimbal_yaw gimbal_yaw_fake --ros-args \
  -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

没有消息时按上游逐段检查，不能马上归因于PID。Twist没有header时间戳，以上终端输出不足以精确判断时延；时序考核需要同步记录消息接收时间，例如在训练日志或rosbag记录中保留时间轴。本轮没有实际采集这些数据。

| 现象 | 下一项只读检查 | 应提交的证据 |
| --- | --- | --- |
| 有目标、无路径 | action名称/状态、planner生命周期、map→gimbal_yaw_fake、global costmap | action/server名称、状态、TF和错误日志 |
| 有路径、无controller速度 | FollowPath状态、controller生命周期、进度检查、碰撞异常、local costmap | BT失败位置和对应消息时间 |
| 有controller速度、无最终速度 | smoother连接、fake的odometry/local_plan同步、namespace、多个publisher | 三段速度话题的类型和连接表 |
| 最终有速度、车不动 | 实际串口节点、订阅话题、包路径、协议/使能/下位机回传 | 导航输出与底盘回传的边界；缺少信息如实记录 |
| 零输入但仍有旋转 | cmd_spin来源、fake参数与最终输出、其他cmd_vel发布者 | 上游全零与最终wz的对照 |
| RViz中有点云，costmap无障碍 | terrain_map的PointCloud2字段、intensity/高度范围、TF、订阅者与QoS | 原始字段与实际costmap障碍的对应 |

## 5. 隔离训练实验与考核

### 实验A：还原默认启动图

只读文件和运行图，提交一张带消息类型的接口表，解释slam切换、use_composition切换、namespace和参数重写。及格要求是区分默认组件分支与非组件分支的behavior remap差异，并指出串口不是由实车导航入口启动。证据页R1/R5可作为检查项，不能只照抄节点列表。

### 实验B：在独立训练机验证坐标变换与自旋

只运行fake_vel_transform，不启动导航、串口、自瞄或电机。训练机不连接底盘，使用组内分配且不与实车共用的ROS_DOMAIN_ID；所有实验终端必须相同。下面87只是示例值。这是发布合成消息的实验，不属于上一节只读诊断。

Ubuntu / ROS 2 Humble终端1，进入已编译的ros_ws后：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=87
ros2 run fake_vel_transform fake_vel_transform_node --ros-args \
  -r __ns:=/nav_training -r /tf:=tf -r /tf_static:=tf_static \
  -p robot_base_frame:=gimbal_yaw -p fake_robot_base_frame:=gimbal_yaw_fake \
  -p odom_topic:=odometry -p local_plan_topic:=local_plan \
  -p input_cmd_vel_topic:=cmd_vel_nav2_result -p output_cmd_vel_topic:=cmd_vel \
  -p cmd_spin_topic:=cmd_spin -p init_spin_speed:=0.5
```

终端2加载同一环境并设置同一ROS_DOMAIN_ID，然后观察输出：

```bash
ros2 topic echo /nav_training/cmd_vel
```

终端3加载同一环境并设置同一ROS_DOMAIN_ID，先发里程计初始化方向，再发零速度：

```bash
ros2 topic pub --once /nav_training/odometry nav_msgs/msg/Odometry \
  "{header: {frame_id: odom}, child_frame_id: gimbal_yaw, pose: {pose: {orientation: {w: 1.0}}}}"
ros2 topic pub --once /nav_training/cmd_vel_nav2_result geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0}, angular: {z: 0.0}}"
ros2 topic pub --once /nav_training/cmd_spin example_interfaces/msg/Float32 "{data: 0.0}"
ros2 topic pub --once /nav_training/cmd_vel_nav2_result geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0}, angular: {z: 0.0}}"
```

**源码预测，尚未实测：**第一次零Twist后输出wz=0.5；cmd_spin设0以后再次发零Twist，输出wz=0。cmd_spin消息本身不触发输出。进阶变体：将里程计四元数设为z≈0.70710678、w≈0.70710678，再发vx=0.2，预期vx≈0、vy≈-0.2。不要把这个只测fake节点的结论写成整车停车验证。

### 实验C：同步、缓存和停车边界

继续使用独立训练域，以同时间戳的Odometry/Path合成输入，覆盖：有local_plan→非零Twist缓存→零Twist→继续成对发布Odometry/Path；再分别中断cmd_vel、local_plan、odometry。每一步记录时间、三个输入与最终输出。要检查旧平移是否被再次发送，区分“没有输出”“输出全零”“输出含自旋”。该实验验证证据页R3/R4的待核实路径，不能预填结果。

整车阶段另由队伍现有上车流程测试取消目标、松开手柄、串口中断和下位机超时。通过标准需要最终消息与车体运动同时证明停止，记录延迟、固件/驱动版本及测试条件。本仓库C++串口发送路径会反复发送缓存，固件看门狗未知，单测fake节点不能覆盖这个边界。

### 实验D：一次可解释的导航失败

优先在已验收的隔离仿真中，用固定地图和固定起终点观察规划失败、局部障碍和恢复。若使用实车训练场，先完成 [T8 前置与停止链路确认](../debug-real/README.md)，并在值守下进行，不能把本节当作绕过准入的入口。记录GridBased/FollowPath/BackUp的触发顺序、costmap变化及最终速度。一次只改变一个参数；先做基础记录，再比较路径长度、到达误差、失败原因、最大最终速度和恢复行为。恢复是自由方向移动，必须纳入速度考核。

## 6. 验收清单

| 交付件 | 合格标准 |
| --- | --- |
| 启动与接口表 | 包含有效namespace、运行参数、生命周期、消息类型、TF发布者，以及真实串口来自哪个仓库/overlay |
| 插件阅读记录 | 能由BT ID找到实际类和参数；分清独立smoother、规划器内平滑与velocity smoother |
| 控制实验记录 | 用数据说明yaw变换、自旋叠加、零命令与缓存时序；未做实车测试必须标明 |
| 故障定位报告 | 从现象定位到具体链路；有源码行、运行证据与仍缺失的信息 |
| 边界说明 | 不把“有源码/节点启动/规划成功/最终零命令”替代“完整实车系统验证”；指出未闭合的串口、决策和停车部分 |

`nav.py`、`nav_run.sh`、`to_home.sh`、`to_center.sh`只是辅助入口，其中存在消息类型、namespace或持续发布问题，详见证据页R10/R11。当前审查未找到默认启动的比赛策略状态机；新人应先掌握NavigateToPose的目标、反馈、结果与取消契约，再接实际决策端。
