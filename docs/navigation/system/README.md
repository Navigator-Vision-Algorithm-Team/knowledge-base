# 本队系统地图：从启动入口追到机器人

本页依据 [Navigation-2027@183a410](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9) 的源码静态整理。**主仓库已确认，实际运行图、有效参数和硬件接线仍须实机采集。** 下文以 reality 默认 `namespace=red_standard_robot1`、`use_composition=True` 为例，记 `/N/topic` 为 `/red_standard_robot1/topic`；TF 的 frame ID 不自动带 namespace。

## 1. 先读五个文件

| 顺序 | 文件（固定版本链接） | 要回答的问题 |
|---|---|---|
| 1 | [根 README](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/README.md) | 为什么依赖自瞄端串口？工作区和辅助脚本在哪？ |
| 2 | [rm_navigation_reality_launch.py](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_reality_launch.py) | namespace、world、slam、use_robot_state_pub、composition 默认是什么？ |
| 3 | [bringup_launch.py](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/bringup_launch.py) | slam 如何选择分支？TF remap、参数替换在哪里？ |
| 4 | [navigation_launch.py](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py) | 哪些节点是组件？cmd_vel 如何改名？lifecycle 管理谁？ |
| 5 | [config/reality/nav2_params.yaml](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml) | 实际插件、frame、数据源、速度和地图设置是什么？ |

最先画“谁启动谁”，再画通信图。仓库中有文件不等于 launch 启用了它，有参数段也不等于运行节点读取了它。

## 2. 两个模式共用哪些模块

```text
reality 入口
 ├─ 可选机器人描述发布（use_robot_state_pub）
 ├─ Livox 驱动、手柄节点、可选 RViz
 └─ bringup（namespace、TF remap、参数替换、组件容器）
     ├─ slam=True：Point-LIO + 点云转scan + slam_toolbox + map_saver
     │            静态 map→odom；禁用 small_gicp
     ├─ slam=False：Point-LIO + small_gicp + map_server
     └─ navigation：loam_interface、sensor_scan_generation、terrain_analysis、
                    fake_vel_transform、Nav2 servers 与 lifecycle manager
```

`slam=True` 仍包含 navigation 分支，不能解释成“绝不会产生运动输出的录图模式”。建图、回放和源码实验都要隔离底盘执行端。建图分支在 [slam_launch.py](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/slam_launch.py)，定位分支在 [localization_launch.py](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/localization_launch.py)。

## 3. 实际 Topic 数据流

以下名称为该基线的发布/订阅及 launch 配置预期；上车后用 `ros2 node info`、`ros2 topic info --verbose` 复核完整名称、类型和端点。

| 发布模块 | Topic / 类型 | 接收模块与作用 |
|---|---|---|
| livox_ros_driver2 | `/N/livox/lidar`，`livox_ros_driver2/msg/CustomMsg`；`/N/livox/imu`，`sensor_msgs/msg/Imu` | Point-LIO；reality lidar_type=1 分支读取 CustomMsg，不能拿任意 PointCloud2 替换 |
| point_lio | `/N/aft_mapped_to_init`，`nav_msgs/msg/Odometry`；`/N/cloud_registered`，`sensor_msgs/msg/PointCloud2` | loam_interface；原始 frame 语义是 camera_init/body，与 Nav2 odom 不同 |
| loam_interface | `/N/lidar_odometry`，Odometry；`/N/registered_scan`，PointCloud2 | sensor_scan_generation、terrain_analysis；registered_scan 另供 small_gicp |
| sensor_scan_generation | `/N/odometry`，Odometry；`/N/sensor_scan`，PointCloud2 | odometry 供 Nav2/速度转换；sensor_scan 是雷达坐标点云，**当前地形节点订阅 registered_scan** |
| terrain_analysis | `/N/terrain_map`，PointCloud2（最终发布为 front_mid360 frame，intensity 为地形量） | global/local Costmap 的 IntensityObstacleLayer；建图时另供点云转 scan；内部先在 odom 处理再变换 |
| pointcloud_to_laserscan（建图） | `/N/obstacle_scan`，`sensor_msgs/msg/LaserScan` | slam_toolbox→`/N/map`（OccupancyGrid）→map_saver |
| map_server（定位） | `/N/map`，`nav_msgs/msg/OccupancyGrid` | StaticLayer；数据来自 YAML 指向的图像，不是直接加载 PCD |
| RViz/导航客户端 | `/N/initialpose`，`geometry_msgs/msg/PoseWithCovarianceStamped` | small_gicp 的初始位姿输入；不是 AMCL 专属 Topic |
| RViz/任务客户端 | `/N/navigate_to_pose`，`nav2_msgs/action/NavigateToPose` | bt_navigator，反馈/结果/取消必须检查 |
| planner_server | `/N/plan`，`nav_msgs/msg/Path`（Nav2 通常接口，运行时确认） | BT 的规划结果交给 FollowPath；不是靠订阅 plan Topic 才能跟踪 |
| controller_server | `/N/cmd_vel_controller`，`geometry_msgs/msg/Twist` | velocity_smoother |
| velocity_smoother | `/N/cmd_vel_nav2_result`，Twist | fake_vel_transform；组合分支 behavior_server 也输出到此处 |
| fake_vel_transform | `/N/cmd_vel`，Twist；输入还包括 `/N/cmd_spin` | 外部串口/底盘接收者必须实测；不要推断存在完整仲裁与超时停车 |

主要实现证据：[Point-LIO 发布订阅](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/laserMapping.cpp#L368)、[loam_interface](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp#L46)、[sensor_scan_generation](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp#L44)、[terrain_analysis](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/terrain_analysis/src/terrain_analysis.cpp#L95)。速度链的分支差异与辅助脚本问题见[证据页](nav2-and-control-evidence.md)。

## 4. TF 按发布者学习

| TF 关系 | 该基线的发布者/条件 | 要验收的事情 |
|---|---|---|
| map→odom | 定位：small_gicp_relocalization；建图：静态发布器 | 同一运行模式只能有一个权威来源；slam_toolbox 的 transform_publish_period=0，不能另开一个重复源 |
| odom→base_footprint | sensor_scan_generation | 来自 LIO 与雷达/底盘变换，不能再无条件加轮速 odom 发布同一边 |
| base_footprint 到 chassis、gimbal_yaw 等模型链 | robot_state_publisher 根据转换后的机器人模型与关节状态发布 | 固定关节与可动关节区别；完整生成树应以实际模型为准 |
| gimbal_yaw→front_mid360 | 默认 uic2025 模型的雷达固定安装关系 | 雷达相对云台固定，不表示相对底盘也固定；外参与模型要成套 |
| gimbal_yaw→gimbal_yaw_fake | fake_vel_transform 的导航虚拟帧，零平移、相对 yaw 为负里程计 yaw | 动态抵消云台在 odom 中的 yaw；不是 odom 直接发布的分支，也不能用静态 TF 替代 |

模型入口：[uic2025_sentry_robot.sdf.xmacro](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/resource/xmacro/uic2025_sentry_robot.sdf.xmacro#L20)。关节状态配置：[robot_description.yaml](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/params/robot_description.yaml) 读取 `serial/gimbal_joint_state`。实际串口必须提供匹配名称、单位和时间戳的数据。

```text
map
└─ odom
   └─ base_footprint → [实际机器人模型链] → gimbal_yaw
                                               ├─ front_mid360
                                               └─ gimbal_yaw_fake （动态虚拟导航帧）
```

此图省略模型中间关节，不是完整 URDF。Point-LIO 的 `publish.tf_send_en=False`，不要为了“补齐 TF”擅自启用原始 `camera_init→aft_mapped`。`Odometry` 消息存在与 TF 边存在是两回事。[REP-105](https://github.com/ros-infrastructure/rep/blob/master/rep-0105.rst) 的 map/odom 语义可以迁移，帧名和发布节点必须依据本队实现。

## 5. 源码暴露的教学重点

1. **运行参数与文件默认值不同。** reality YAML 中 costmap 的 `use_sim_time: true` 经过 launch 重写；必须查运行值，不能仅据 YAML 判断实车在用仿真时钟。
2. **普通节点与组件分支需要分别核对。** composition=False 的 remap 与默认组合分支不完全相同；不能把它当作必然等价的 Debug 开关。
3. **有 TF 不代表定位正确。** small_gicp 可能继续发布旧估计；观察 stamp、配准结果、点云重合、实际位置，不只看 Topic 频率。
4. **里程计速度值得专项审查。** sensor_scan_generation 用 steady_clock 回调间隔差分位置；回放倍速可影响速度数值，且 twist 的参考系与消息约定需要核实。这是代码阅读/回归课题，不是本次已经修复的结论。
5. **外部依赖必须具名。** rm_robot_ws 是另一条 CAN/ros2_control 工程，不能替代本导航 README 所需的串口包；本次不把它列为所有导航新人的必修实现。

实践：完成节点图、Topic 表、TF 发布权表各一份，标出“源码已确认 / 运行已确认 / 待确认”。三张图必须能相互解释，见 [T3、T7](../assignments/README.md)。
