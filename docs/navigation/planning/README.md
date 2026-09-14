# S4：环境表达、Costmap 与规划

前置：TF、消息坐标、二维全向运动；真实地形实验还需 S3 数据包。目标是解释机器人为何可走/不可走、如何生成路径，以及规划模型和实际全向底盘的差异。必学一份 A* 和本队 Costmap 数据路径；无需把所有搜索算法各写一遍。

## 1. 三类地图与地形输入

| 表达 | 数据和用途 | 常见误解 |
|---|---|---|
| PCD 点云地图 | small_gicp 对齐先验地图 | 以为 map_server 直接加载 PCD |
| YAML+图像/OccupancyGrid | map_server/SLAM 提供二维占据地图；resolution、origin、free/occupied/unknown | 同名文件必然坐标对齐 |
| global/local Costmap | 叠加静态图、实时障碍、足迹清除和膨胀后的规划/控制代价 | 把未知当自由，把可视化颜色当算法全部输入 |

本队路径是 `registered_scan + lidar_odometry → terrain_analysis → terrain_map → IntensityObstacleLayer`。地形节点把相对地面高度等结果写入 intensity，**不是直接用雷达反射强度当碰撞代价**。先核对点云 frame、字段、地面处理与阈值，再调 Costmap。[terrain_analysis 实现](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/terrain_analysis/src/terrain_analysis.cpp)，[IntensityObstacleLayer 实现](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/src/layers/intensity_obstacle_layer.cpp)。

## 2. 当前 Costmap 应读什么

基线 [reality YAML](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml) 的 global/local 都使用 StaticLayer、IntensityObstacleLayer、InflationLayer；local 以 odom 为 global_frame，global 以 map 为 global_frame，robot_base_frame 为 gimbal_yaw_fake。这些是本课必读项。

VoxelLayer 与 IntensityVoxelLayer 先了解，不因代码存在就称其已加载。默认 `robot_radius=0.2`、`inflation_radius=0.7` 是仓库值，不能作为未知尺寸实车的安全参数。实车须记录测量外形、云台转动后包络与实际 footprint；用半径还是多边形由维护者确认。

T6 每次只改变一个参数类别：

1. 足迹/半径：固定地图、起终点，比较窄通道能否通过及膨胀区域；不得通过缩小足迹“解决”碰撞。
2. inflation_radius/cost_scaling_factor：解释通道中心偏好与墙边代价变化，不能只写“更流畅”。
3. obstacle 的 marking/clearing、观测距离：添加/移除障碍，区分真实清除、数据断流和手工清图。
4. terrain intensity 阈值：对同一平地/坡面/低障碍数据，记录哪些点被保留、Costmap 如何变化。不能凭注释承诺“开启就能上坡”。

对照表至少包括：commit、地图校验值、输入 bag/场景、有效参数、唯一改动、Costmap 截图、路径长度、规划成功/失败、耗时与失败日志。每组重复三次；无闭环环境时只验输入与规划，不计算实车到达率。

## 3. A* 必做，但不要求先完成算法大全

先了解 BFS 用于等权图、Dijkstra 用于非负权图，再实现 A*：`f(n)=g(n)+h(n)`。推荐先固定四邻接、每步代价 1、曼哈顿启发式；八邻接作为扩展时，明确对角代价和禁止穿角规则。加权地图必须保持启发式与代价单位一致。

实现要求：输入地图和起终点，输出有序网格路径、总代价、扩展节点数、运行耗时或清楚的失败原因。处理边界/障碍上的起终点、无解、起终点相同、窄通道、unknown 策略；没有路径时不能无限循环。路径每一段都必须可通行。用 Dijkstra（或 A* 的 h=0 模式）作为小图代价参照，不能只看动画。

将网格路径转换为 `nav_msgs/msg/Path` 可作加分：格子中心要结合地图 resolution 与 origin 旋转转换到 map 坐标；不直接把像素坐标当米。T5 先用教学地图，不能把作业包替换上车 Planner。

## 4. 再读本队 Planner

当前 `GridBased` 选择的是 **`nav2_smac_planner/SmacPlannerHybrid`**，`motion_model_for_search=DUBIN`、`angle_quantization_bins=64`、`minimum_turning_radius=0.05`；不是普通二维 A*。Hybrid-A* 在位置和朝向状态上考虑运动约束。DUBIN 不包含横向平移原语，因此全向控制器能侧移不代表 Planner 充分利用了全向能力。

学习结论：**读懂和调试现用 Planner 必学，从零实现 Hybrid-A* 进阶。** 不能仅凭“全向”就判定现配置错误，也不能说它已经最合适。后续专项可在同一 footprint、代价图和任务集下对照 Smac2D/Hybrid/Lattice，比较可达性、路径长度、计算时间、跟踪误差和碰撞余量，再决定是否换插件。

Humble 配置/API 交叉核对 [Nav2 Humble Smac 源码](https://github.com/ros-navigation/navigation2/tree/humble/nav2_smac_planner)。现行 [Nav2 Smac 文档](https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/planners_plugins/smac/)用于概念阅读，Rolling/Jazzy 参数和插件分隔符不能直接照抄到 Humble。

## 验收与排错

完成 [T5–T6](../assignments/README.md)。能分别解释：地图无通路、unknown 策略、起点碰撞、TF 不可用、规划超时；知道清 Costmap 不能修复地图坐标错位。下一步沿[Nav2 与控制链](../nav2/README.md)检查路径如何变成最终速度。
