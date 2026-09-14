# Navigation-2027：Nav2 与控制接口证据

审查对象：[Navigation-2027 固定提交](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9)，SHA `183a4109b0de2030bb8970a54654937c8b039ba9`。审查日期：2026-09-14。本页依据完整浅克隆中的源码、launch、参数和 XML，只读审查；没有编译 ROS 工作区、启动 ROS 节点、连接串口或做实车测试。未发现仓库内及本地工作区祖先目录中的 `AGENTS.md`。

本文使用三种结论：**代码事实**表示文件中可直接定位；**启动配置**表示给定 launch 的默认分支会尝试加载，不能等同于已经成功运行；**待验证**表示源码推断或缺少部署、硬件证据。配套学习页：[真实 Nav2 与控制链](../nav2/README.md)。

## 1. 真实入口与启动边界

| 证据 | 可确认内容 | 边界 |
| --- | --- | --- |
| [实车入口 L50–134][reality-defaults] | 默认 namespace=`red_standard_robot1`、slam=False、world=`rmul_2024`、use_sim_time=False、use_composition=True、use_respawn=False、use_robot_state_pub=False、use_rviz=True；默认参数来自 `config/reality/nav2_params.yaml` | 根 README 的命令显式覆盖了部分参数，必须记录实际启动命令 |
| [入口节点与 include L146–199][reality-includes]、[添加动作 L218–223][reality-actions] | 启动 Livox、bringup、joy_teleop；robot_state_publisher 与 RViz 分别受条件控制 | 入口没有启动 `rm_serial_driver`、根目录 `serial_node.py`、`standard_robot_pp_ros2` 或比赛决策节点 |
| [bringup L54–80][bringup-rewrite]、[L140–197][bringup-branches] | 替换 `<robot_namespace>`，重写 `use_sim_time`，为子图添加 namespace，并将 `/tf`、`/tf_static` 映射到相对话题；slam=True/False 分别包含 SLAM/定位，navigation 始终包含 | YAML 中 local/global costmap 的原始 `use_sim_time: true` 不代表实车有效参数为 true，必须检查 launch 重写结果 |
| [定位 launch L119–199][localization] | 定位分支启动 Point-LIO、map_server、small_gicp_relocalization；map_server 与 small_gicp 支持组件方式 | 本导航启动链没有加载 AMCL；传感器与重定位细节见系统其他页面 |
| [SLAM launch L111–180][slam] | SLAM 分支把 terrain_map 转成 obstacle_scan，启动 slam_toolbox 与 Point-LIO，发布静态 map→odom | `slam=True` 并不会关闭 navigation；不能直接把建图模式理解成“不会输出底盘指令” |
| [navigation L42–50][lifecycle]、[L253–342][composition] | 默认组件分支加载 loam_interface、sensor_scan_generation、terrain_analysis、fake_vel_transform，以及 controller/smoother/planner/behavior/bt_navigator/waypoint_follower/velocity_smoother 和生命周期管理器 | 生命周期列表只含七个 Nav2 server；节点存在不等于这些 server 已 active |

## 2. Nav2 插件和行为树

| 位置 | 实际选择与含义 |
| --- | --- |
| [controller 参数 L315–366][controller-config] | `FollowPath`=`pb_omni_pid_pursuit_controller::OmniPidPursuitController`，20 Hz，平移 PID=3.0/0.1/0.3，`enable_rotation: false`，`v_linear_max: 0.5`。SimpleProgressChecker：0.5 m/10 s；SimpleGoalChecker：xy=0.15 m，yaw=6.28 rad。不能据此宣称严格目标朝向验收 |
| [控制器实现 L219–286][controller-code]、[局部路径发布 L164–169][local-plan] | 变换全局路径、选前视点、PID、曲率和接近目标减速，输出 x/y；rotation 关闭时 angular.z=0；发布 `local_plan`、`lookahead_point`。`setSpeedLimit` 只打印“未实现” |
| [planner 参数 L468–503][planner-config] | `GridBased`=`nav2_smac_planner/SmacPlannerHybrid`，搜索模型 DUBIN，最小转弯半径0.05 m，`smooth_path: True`。教学不能直接把默认算法写成 NavFn、DWB、TEB、MPPI 或标准 RPP |
| [local/global costmap L368–451][costmap-config] | 两者均为 StaticLayer + 自定义 IntensityObstacleLayer + InflationLayer，输入 `<robot_namespace>/terrain_map`，PointCloud2，intensity 范围0.1–2.0；分辨率0.05 m，robot_radius=0.2 m，膨胀半径0.7 m。local 为 odom 下5×5 m滚动图；global 为 map 下全局图 |
| [IntensityObstacleLayer L377–430][intensity-code]、[插件注册 XML L1–10][costmap-plugins] | 标记障碍时读取 PointCloud2 的 `intensity` 字段并过滤；仓库也注册了 IntensityVoxelLayer，但 reality 的 plugins 列表没有选它。不能用“源码存在”判断实际启用 |
| [BT 参数 L255–313][bt-config]、[单点树 L5–38][bt-pose]、[多点树 L5–43][bt-through] | 参数指向仓库这两份 XML。单点树以3 Hz限频重规划，ComputePathToPose 用 GridBased，FollowPath 用 FollowPath；失败清 costmap，外层恢复含清图与 BackUp。多点树增加 RemovePassedGoals（0.7 m）和 ComputePathThroughPoses |
| [行为参数 L515–545][behavior-config]、[BackUpFreeSpace L54–155][backup-code] | backup 实现是自定义 BackUpFreeSpace：查询 `global_costmap/get_costmap`，搜索自由方向，输出x/y。XML的 BackUp 请求距离1.0 m、速度1.0 m/s；它不保证朝车后方退，也不受 FollowPath 的0.5 m/s参数约束 |
| [smoother/waypoint/velocity 参数 L505–571][other-config] | 配置并启动 SimpleSmoother、WaitAtWaypoint、OPEN_LOOP VelocitySmoother（20 Hz，平移上限2.5 m/s，timeout=1.0 s） |

行为树实际没有 `SmoothPath`、`Spin`、`Wait`、`AssistedTeleop` 节点。库可加载、server 可启动、参数有配置、BT 实际调用是四件不同的事。规划器内部 `smooth_path` 与独立 `smoother_server` 也要区分。

## 3. 速度、TF、手柄与串口边界

在实车入口默认 namespace 和组件分支下，以下相对话题解析到 `/red_standard_robot1/…`。frame 名仍为 `map`、`odom`、`gimbal_yaw`、`gimbal_yaw_fake`，不能机械地给 frame 字符串加 namespace。

| 发送者 → 接收者 | 话题/接口与消息 | 精确证据 |
| --- | --- | --- |
| controller_server → velocity_smoother | `cmd_vel_controller`；Humble 此链使用 `geometry_msgs/msg/Twist`。控制器 C++ API 的返回值为 TwistStamped，不代表 ROS 输出话题也为 TwistStamped | [组件 remap L281–328][composition-speed]、[控制器接口 L219–277][controller-code]、[fake 输入订阅 L51–73][fake-subscriptions] |
| velocity_smoother → fake_vel_transform | `cmd_vel_nav2_result`；Twist | [remap L321–328][composition-speed]、[参数 L137–146][fake-config] |
| behavior_server → fake_vel_transform | `cmd_vel_nav2_result`；Twist；默认组件分支绕过 velocity_smoother | [组件 behavior remap L300–307][composition-speed]、[行为发布 L140–155][backup-code] |
| fake_vel_transform → 外部底盘接口 | `cmd_vel`；Twist；本仓库实车入口没有为该输出启动串口接收节点 | [fake 参数][fake-config]、[发布与旋转公式 L115–154][fake-transform]、[入口 actions][reality-actions] |
| odometry/local_plan/cmd_spin → fake_vel_transform | `odometry`：nav_msgs/msg/Odometry；`local_plan`：nav_msgs/msg/Path；`cmd_spin`：example_interfaces/msg/Float32 | [订阅/近似同步 L31–77][fake-subscriptions]、[类型定义 L22–58][fake-header] |
| fake_vel_transform → TF | 50 Hz发布 `gimbal_yaw`→`gimbal_yaw_fake`，相对 yaw=-里程计 yaw，无平移 | [定时器 L75–77][fake-subscriptions]、[TF L135–144][fake-transform] |
| joy_node → pb_teleop_twist_joy_node | `joy`：sensor_msgs/msg/Joy；默认 `auto_control`，手柄平移转成 NavigateToPose action；manual_control 才直接发送平移 Twist | [手柄 launch L82–111][joy-launch]、[配置 L573–594][joy-config]、[代码 L61–74][joy-interfaces]、[模式分支 L160–181][joy-mode] |
| pb_teleop_twist_joy_node → Nav2/底盘接口 | `navigate_to_pose`：nav2_msgs/action/NavigateToPose；还可发 `cmd_vel`、`cmd_gimbal_joint`：sensor_msgs/msg/JointState、`cmd_shoot`：example_interfaces/msg/UInt8 | [接口创建][joy-interfaces]、[松开按钮 L141–158][joy-release]、[目标/取消/零输出 L216–264][joy-stop] |

### 仓库内 C++ 串口包提供的接口

以下只是 `standard_robot_pp_ros2-main` 的[源码接口][serial-cpp-interfaces]，不是默认导航入口已加载的节点。它自身launch的[namespace默认空，source_list为serial/gimbal_joint_state][serial-launch-defaults]；若直接用默认值运行，`cmd_vel`位于根命名空间，不能自动接到导航默认的 `/red_standard_robot1/cmd_vel`。

| 方向 | 相对话题 | 消息类型 |
| --- | --- | --- |
| 接收控制 | `cmd_vel` / `cmd_gimbal_joint` / `cmd_shoot` | geometry_msgs/msg/Twist / sensor_msgs/msg/JointState / example_interfaces/msg/UInt8 |
| 发布运动状态 | `serial/imu` / `serial/gimbal_joint_state` / `serial/robot_motion` | sensor_msgs/msg/Imu / sensor_msgs/msg/JointState / geometry_msgs/msg/Twist |
| 发布机器人状态 | `serial/robot_state_info` | pb_rm_interfaces/msg/RobotStateInfo |
| 发布裁判信息 | `referee/event_data` / `referee/all_robot_hp` / `referee/game_status` | pb_rm_interfaces/msg/EventData / GameRobotHP / GameStatus |
| 发布裁判信息 | `referee/ground_robot_position` / `referee/rfid_status` / `referee/robot_status` | pb_rm_interfaces/msg/GroundRobotPosition / RfidStatus / RobotStatus |

这些发布器表明可提供的策略输入；当前审查没有找到默认导航launch中消费这些裁判消息并生成比赛策略的节点，且本克隆缺少对应 `pb_rm_interfaces` 消息包，字段与部署侧契约需要补齐。

### 停机不能只看上游 Twist

设里程计 yaw 为 θ，fake_vel_transform 计算：

```text
vx_out =  vx_in cosθ + vy_in sinθ
vy_out = -vx_in sinθ + vy_in cosθ
wz_out =  wz_in + spin_speed
```

[reality 参数 L146][fake-config] 的 `init_spin_speed=0.5`，而[转换函数 L147–154][fake-transform]总是叠加 spin。因此在未收到改变 spin 的消息时，**输入全零 Twist 会输出 angular.z=0.5**；这只是源码可确定的 ROS 输出规则，不是本轮观测到的车体运动。`cmd_spin=0` 只更新变量，回调本身也不立即发布停车消息（[L80–83][fake-callbacks]）。

## 4. 待核实风险与文档差异

| 编号 | 源码事实 / 文档差异 | 待验证内容与训练要求 |
| --- | --- | --- |
| R1 | [根 README L35–43][root-serial]要求运行 `rm_serial_driver/serial_driver.launch.py`；全仓库路径与 package.xml 检索未发现该包。现有 C++ 串口包名是 [standard_robot_pp_ros2][serial-package]，位于 `ros_ws` 之外，并依赖未在此克隆发现的 `pb_rm_interfaces` | 在部署机只读检查 `ros2 pkg prefix rm_serial_driver`、实际 launch 和 overlay；补齐自瞄端仓库、提交和协议。不能声称克隆本仓库就拥有完整串口链 |
| R2 | [serial_node.py L34–56][serial-python]用 /dev/ttyUSB0、921600，订阅绝对 `/red_standard_robot1/cmd_vel`，发布绝对 `/serial/gimbal_joint_state`（Float32MultiArray）。[C++串口 L75–113][serial-cpp-interfaces]发布同用途相对话题（JointState），[其配置][serial-cpp-config]为 /dev/ttyACM0、115200 | 两份实现不是已证明等价的替代件；需核对包格式、CRC、字段、单位、坐标系、namespace。root Python接收 L66–83 只检查帧头，未校验接收CRC；具体协议正确性未验证 |
| R3 | [fake 回调 L93–132][fake-callbacks]：零消息直接转换发布，但不覆盖/清空 `latest_cmd_vel_`；同步回调复用已有缓存，未做缓存年龄判断 | 源码存在“非零缓存→零输入→后续同步再次发旧平移”的路径，是否出现及持续多久取决于回调时序。必须在不连接底盘的独立 ROS 域复现；不能把0.5 s `CONTROLLER_TIMEOUT`理解成输出看门狗，它检测的是 local_plan 活跃时间 |
| R4 | [fake 成员 L73–78][fake-members]的 `current_robot_base_angle_` 没有显式初值；[构造与50 Hz定时器][fake-subscriptions]在首次 odometry 到来前就可发布 TF；回调使用 `rclcpp::Clock()`，TF时间戳使用节点时钟 | 首包前TF值以及 use_sim_time 回放行为需单独检查；本轮没有证明每次必现异常 |
| R5 | [非组件分支 L191–212][noncomposition-speed]没有给 behavior_server remap cmd_vel，却给 bt_navigator 放了该 remap；[组件分支 L300–313][composition-speed]则给 behavior_server 正确配置输出到 `cmd_vel_nav2_result` | `use_composition=False` 的恢复输出链与默认分支不等价，可能绕过 fake坐标变换并与最终cmd_vel并发。切换模式做实验必须比对 publisher 与实际消息 |
| R6 | [C++串口 L633–662][serial-cache]每5 ms发送缓存，cmdVelCallback只更新速度字段，所读发送路径无cmd_vel年龄检查；[Python发送 L90–117][serial-python-send]在收到Twist时才写串口 | 上游停止发布不等于底盘收到零指令。实际部署用哪份驱动、下位机看门狗、断线与断电停车策略均未知；验收必须覆盖最终cmd_vel、串口发送和实际车体停止 |
| R7 | [手柄 L251–264][joy-stop]在auto模式取消导航并向最终cmd_vel发一次零命令；[fake发布路径][fake-callbacks]也是最终cmd_vel的发布者；启动链未见速度仲裁器 | 无法从单条零消息证明停车持续成立。检查publisher数量、取消响应、fake后续输出和底盘超时；“松开L1”不能在文档里直接写成已验证急停 |
| R8 | [控制器 L258–275][controller-code]在局部路径采样10点，按[代价值检测 L451–469][collision-code]判断碰撞，遇到某点不在costmap时直接返回false；[setSpeedLimit L282–286][controller-code]未实现 | 这是当前碰撞检查的边界，未证明所有姿态/速度下都能安全避障，也不能假定通用速度限制接口生效。规划碰撞、控制输出和制动距离分别考核 |
| R9 | [pb_nav2_plugins README L24–30][plugin-readme]列出BackUpFreeSpace的robot_radius/free_threshold；[实现 L21–39][backup-configure]实际读取global_frame/max_radius/service_name/visualize，无前述两个参数 | 以实现和运行时参数为准，不能把README参数表直接当成调参清单。`BackUp`的实际含义是搜索自由方向移动 |
| R10 | [nav.py L15–20][nav-script-interfaces]使用未加namespace的action与绝对/odom；[L64–71][nav-script-call]创建PoseStamped却传其`.pose`给[赋值到goal.pose的函数 L29–36][nav-script-send]。部署默认图的odometry/action名称不匹配，且有消息类型问题 | 属于辅助脚本的静态缺陷，未执行；不能作为新人可直接运行的完整决策样例 |
| R11 | [nav_run.sh L3–10][nav-run]使用全局/goal_pose，第一次`ros2 topic pub`没有--once；[to_home.sh L3][to-home]和[to_center.sh L3][to-center]才是命名空间内单次发布 | nav_run.sh按命令通常持续发布的语义无法正常进入后续sleep/回家；在训练机验证CLI行为。后两脚本也只有硬编码目标，不含状态机、结果处理或比赛决策 |

根 README 的“先自瞄、串口、再导航”是[部署要求][root-serial]；嵌套 README 则以[standard_robot_pp_ros2提供关节位姿][embedded-readme]作为完整系统示例。两者描述的是不同集成前提，当前克隆不能独自说明队伍部署机采用哪条。不要自行补写成已经存在的决策链或串口验证结果。

## 5. 更新本页时留下的记录

下次实测应附：部署仓库SHA、ROS发行版及overlay、完整launch参数、生命周期状态、三个速度话题的publisher/类型/频率、实际TF发布者、串口驱动与固件版本、零命令/取消/消息中断/串口中断的时间序列。每个风险分别记“未验证、复现、未复现的条件、已修复及回归证据”，不要用“导航能跑”替代这些记录。

[reality-defaults]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_reality_launch.py#L50-L134
[reality-includes]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_reality_launch.py#L146-L199
[reality-actions]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_reality_launch.py#L218-L223
[bringup-rewrite]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/bringup_launch.py#L54-L80
[bringup-branches]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/bringup_launch.py#L140-L197
[localization]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/localization_launch.py#L119-L199
[slam]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/slam_launch.py#L111-L180
[lifecycle]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L42-L50
[composition]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L253-L342
[controller-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L315-L366
[controller-code]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_omni_pid_pursuit_controller/src/omni_pid_pursuit_controller.cpp#L219-L286
[local-plan]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_omni_pid_pursuit_controller/src/omni_pid_pursuit_controller.cpp#L164-L169
[planner-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L468-L503
[costmap-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L368-L451
[intensity-code]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/src/layers/intensity_obstacle_layer.cpp#L377-L430
[costmap-plugins]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/costmap_plugins.xml#L1-L10
[bt-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L255-L313
[bt-pose]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml#L5-L38
[bt-through]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_through_poses_w_replanning_and_recovery.xml#L5-L43
[behavior-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L515-L545
[backup-code]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/src/behaviors/back_up_free_space.cpp#L54-L155
[other-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L505-L571
[composition-speed]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L281-L328
[fake-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L137-L146
[fake-subscriptions]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L31-L77
[fake-transform]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L115-L154
[fake-callbacks]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L80-L132
[fake-header]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/include/fake_vel_transform/fake_vel_transform.hpp#L22-L58
[fake-members]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/include/fake_vel_transform/fake_vel_transform.hpp#L73-L78
[joy-launch]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/joy_teleop_launch.py#L82-L111
[joy-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L573-L594
[joy-interfaces]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_teleop_twist_joy/src/pb_teleop_twist_joy.cpp#L61-L74
[joy-mode]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_teleop_twist_joy/src/pb_teleop_twist_joy.cpp#L160-L181
[joy-release]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_teleop_twist_joy/src/pb_teleop_twist_joy.cpp#L141-L158
[joy-stop]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_teleop_twist_joy/src/pb_teleop_twist_joy.cpp#L216-L264
[root-serial]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/README.md#L35-L43
[serial-package]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/package.xml#L3-L30
[serial-python]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/serial_node.py#L34-L83
[serial-python-send]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/serial_node.py#L90-L117
[serial-cpp-interfaces]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp#L75-L115
[serial-launch-defaults]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/launch/standard_robot_pp_ros2.launch.py#L74-L99
[serial-cpp-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/config/standard_robot_pp_ros2.yaml#L1-L7
[serial-cache]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp#L633-L662
[noncomposition-speed]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L191-L212
[collision-code]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_omni_pid_pursuit_controller/src/omni_pid_pursuit_controller.cpp#L451-L469
[plugin-readme]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/README.md#L24-L30
[backup-configure]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/src/behaviors/back_up_free_space.cpp#L21-L39
[nav-script-interfaces]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/nav.py#L15-L20
[nav-script-call]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/nav.py#L64-L71
[nav-script-send]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/nav.py#L29-L36
[nav-run]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/nav_run.sh#L3-L10
[to-home]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/to_home.sh#L3
[to-center]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/to_center.sh#L3
[embedded-readme]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/README.md#L196
