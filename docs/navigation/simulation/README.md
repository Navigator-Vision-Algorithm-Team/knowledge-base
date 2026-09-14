# 仿真资源与统一训练环境验收

本课针对 **Navigation-2027** 提交 `183a4109b0de2030bb8970a54654937c8b039ba9`。仓库已经包含 RM 仿真世界、机器人模型、桥接和导航源码，可用于搭建训练环境；**本次仅完成静态核对，尚未在 Linux 上完成编译或 Gazebo 闭环运行**。因此当前交付状态是“训练方案与源码证据齐备，运行验收待完成”。

先学 [系统链路](../system/README.md)，定位原理和地图保存见 [传感器与 LIO](../sensor-lio/README.md)。本课集中回答：要装哪些部件、代码有哪些可证实的缺口、怎样让所有新人使用同一套可复现环境。

## 1. 仿真入口和导航入口是两件事

```text
rmu_gazebo_simulator / bringup_sim.launch.py
  ├─ gazebo.launch.py：Gazebo 世界、GUI、/clock 桥接
  ├─ spawn_robots.launch.py：机器人模型、基础执行器、joint_states/传感器桥接、TF
  └─ referee_system.launch.py：裁判系统

pb2025_nav_bringup / rm_navigation_simulation_launch.py
  ├─ ign_sim_pointcloud_tool：livox/lidar → velodyne_points
  ├─ bringup_launch.py：Point-LIO、地形、定位/建图、Nav2
  ├─ joy_teleop_launch.py
  └─ RViz
```

**只启动导航仿真 launch 不会启动 Gazebo，也不会凭空产生雷达点云。**先运行仿真器、让物理时钟前进并验证传感器，再运行导航。[仿真总入口][sim-bringup]、[导航仿真入口][nav-sim]

`world` 名称用于选择场景资源和地图文件。Gazebo 世界内部名称是 `default`，桥接中的 `/world/default/...` 因而不能仅看场景文件名就改成 `/world/rmul_2025/...`。[世界内部名称][world-file]、[传感器桥接][bridge]

## 2. 统一训练环境的固定项

仓库 README 声明的组合为 **Ubuntu 22.04、ROS 2 Humble、Gazebo Fortress**；gazebo.launch.py 使用 `ros_gz_sim` 并指定 `gz_version: 6`，同时保留 `ign` 命令和 Ignition 插件名。新人训练先沿用这套组合，不把 Gazebo Classic、其他 Gazebo 发行版或其他 ROS 版本的启动命令混入同一份验收记录。[环境声明][sim-readme]、[Gazebo 启动][gazebo-launch]

| 固定项 | 本课程要求 |
|---|---|
| 操作系统与 ROS | 记录 Ubuntu 完整版本、`ROS_DISTRO`、主要 ROS/Gazebo 包版本 |
| 源码 | Navigation-2027 固定上述 SHA；另有补丁时附补丁及独立版本号 |
| Gazebo/图形环境 | Fortress；记录原生、虚拟机或容器、GPU 和驱动；必须实际验证 gpu_lidar 能输出 |
| 机器人命名空间 | 初次单机器人导航固定 `/red_standard_robot1` |
| 场地 | 首轮固定 `rmul_2025`，与当前仿真器 gz_world.yaml 一致 |
| 机器人模型 | 当前 spawn 选 `pb2025_sentry_robot.sdf.xmacro`；记录雷达安装位姿 |
| 参数与地图 | 记录实际 params_file、PCD、YAML/PGM 的路径和文件校验值 |
| 时钟 | 仿真导航使用 use_sim_time；确认 `/clock` 实际递增 |
| 成果 | 环境清单、完整构建日志、启动日志、观测记录；有故障则保留原始报错 |

这是统一验收约定，不是宣称任何满足版本字符串的机器都会跑通。模型使用 `gpu_lidar`，虚拟机图形能力必须通过真实点云输出验证；仅看到 GUI 不够。[雷达模型][lidar-model]

## 3. 已有资源与依赖边界

| 部件 | 当前仓库内容 | 静态结论 |
|---|---|---|
| 仿真器 | `ros_ws/src/rmu_gazebo_simulator` | 已包含 launch、桥接、裁判及网页脚本 |
| 场地 | rmul_2024、rmuc_2024、rmul_2025、rmuc_2025 的 world、model 与 mesh | 四套场地资源实际存在 |
| 机器人 | pb2025_robot_description + rmoss_gz_resources | 包含 PB/UIC 机器人、MID360、底盘等模型；rm25_example_robot 定义也存在 |
| RM 依赖 | rmoss_core、rmoss_gazebo、rmoss_interfaces、sdformat_tools | 源码目录存在；依赖是否编译通过尚未验证 |
| 模型生成器 | launch 中 import `xmacro.xmacro4sdf` | Python xmacro 是额外环境依赖；不能用名称相似的 xacro 替代 |
| small_gicp | 在主仓库根目录 `small_gicp/` | 不在 `ros_ws/src` 内；普通工作区构建不会遍历到它 |
| small_gicp_relocalization | include small_gicp 头文件；package.xml 未声明 small_gicp | rosdep/colcon 依赖自动解析不等于该库已可用，需要预先安装和验证 |
| Livox SDK | 驱动目录自带 amd64/arm64 `.so` 与头文件 | 文件存在；当前 CMake 仅接受 x86_64/aarch64 Linux 分支，动态加载兼容性待验证 |
| vision_interfaces | 仿真器 package.xml 声明依赖 | `ros_ws/src` 包清单中不存在；需确认团队环境提供来源和版本，不能臆造下载地址 |
| 地图 | 4 套仿真 YAML + PGM | 仿真 PCD 目录只有下载说明；定位模式仍缺先验点云 |

[资源目录][resource-tree]、[基础模型定义][robot-definition]、[模型生成依赖][spawn]、[仿真依赖声明][sim-package]、[small_gicp 目录][smallgicp-tree]、[重定位依赖与 include][gicp-deps]、[重定位 CMake][gicp-cmake]、[驱动 SDK 构建路径][driver-cmake]、[仿真点云说明][pcd-readme]

网页对战所需 Flask、Socket.IO 等并不是第一轮定位训练的验收目标；不要以网页启动失败直接判断激光定位失败。默认 bringup 会启动裁判系统，但不会自动替你启动 README 中的网页进程。[仿真总入口][sim-bringup]、[网页入口说明][sim-readme]

## 4. 当前源码必须先处理的兼容性问题

### 4.1 两个默认 world 不一致

仿真器 `config/gz_world.yaml:1` 为 `rmul_2025`，导航仿真入口 `world` 默认 `rmuc_2025`。导航的 world 参数只选择导航地图路径，不会修改仿真器配置。第一次训练明确传 `world:=rmul_2025`，避免在 A 场地加载 B 地图。[仿真场地配置][gz-world]、[导航默认地图路径][nav-sim-defaults]

### 4.2 仿真点云时间单位不一致

转换器 `point_cloud_converter.cpp:75` 计算 `time = (point_id % horizon_scan) * 0.1 / horizon_scan`，数值按秒构造，覆盖约 0～0.1。simulation YAML 却配置 `timestamp_unit: 2`，含义为微秒；Point-LIO 将其乘 `1e-3` 转成毫秒。以 0.1 秒为例，正确毫秒为 100，而当前参数路径得到 0.0001，比例相差 **10⁶**。[点时间生成][converter]、[仿真时间单位][sim-config]、[单位换算][preprocess-units]、[Velodyne 时间消费][preprocess-time]

这项是源码可直接推导出的单位不一致，尚未量化它在当前场景中的轨迹误差。除此之外，模型雷达更新频率为 20 Hz，而转换器假设一帧时间跨度为 0.1 秒；训练负责人应核对实际扫描定义。**统一环境验收前应统一点时间生成与消费单位，并记录修正版本及复现实验**；本文没有修改代码，也没有把修改参数当作已经完成的修复。

### 4.3 模型安装角和仿真重力配置需统一核对

spawn 加载 PB 模型，雷达固定到 chassis，roll 为 `-π/12`（-15°）；仿真 YAML 重力向量 `[0,-4.9,-8.487047...]` 对应 30° 倾角。另一实车默认 UIC 模型则把雷达装在 gimbal_yaw、roll 为 `-π/6`。这些文件不是同一安装条件；需据选定模型推导预期重力方向，再静止检查 IMU 与水平地面。不能把实车 YAML 原样复制过来。[spawn 模型][spawn]、[PB 模型][pb-model]、[仿真重力配置][sim-config]、[UIC 模型][uic-model]

这是配置一致性待验收项；本次没有运行仿真，不能据此直接报告“必然漂移多少度”。

### 4.4 缺 PCD 不等于缺整个仿真器

`slam:=False` 会启动 small_gicp，默认 PCD 路径指向 `pcd/simulation/<world>.pcd`，当前文件不存在。`slam:=True` 则禁用 small_gicp、开启 Point-LIO PCD 保存并以静态 map→odom 建图，可作为**补齐依赖并处理时间/外参一致性后**的第一轮传感器训练路径。将以后验收通过的 PCD 和 YAML/PGM 作为统一地图数据包，记录来源、SHA256 和地图坐标。[导航默认路径][nav-sim-defaults]、[建图分支][slam]

## 5. 阶段 A：环境和构建验收

以下均在 **Ubuntu 22.04 / Humble 的 Bash** 执行，不是在本次文档编辑所用的 Windows PowerShell 执行。前置：训练负责人已经提供完整源码、系统软件安装权限和统一依赖清单；`/path/to/Navigation-2027` 必须替换为真实目录。源码目录已经准备好，不需要在其中再次克隆一层仓库。

```bash
cd /path/to/Navigation-2027/ros_ws
source /opt/ros/humble/setup.bash
cat /etc/os-release
uname -m
printenv ROS_DISTRO
command -v ros2 colcon cmake ign
python3 -c 'from xmacro.xmacro4sdf import XMLMacro4sdf; print("xmacro import OK")'
colcon list
rosdep check --from-paths src --ignore-src --rosdistro humble
```

提交完整检查输出。若 rosdep 提示无法解析 vision_interfaces，先向负责人取得该依赖的正式来源/版本，或由维护者确认声明是否应调整；不能使用 `--skip-keys` 后在记录里声称依赖检查通过。`vision_interfaces` 未在本仓库出现，只能证明需要外部补全，不能证明训练机必然没有安装它。

前置：系统 CMake、C++ 编译器、Eigen、OpenMP 等已准备好，训练负责人选用本仓库根目录的 small_gicp。下面按仓库说明的系统安装方式预装该库；`sudo cmake --install` 会写入系统安装目录。若训练环境采用其他前缀，维护者还需验证重定位编译器能找到其头文件，不能只设置 CMAKE_PREFIX_PATH 就假定成功。

```bash
cd /path/to/Navigation-2027
cmake -S small_gicp -B small_gicp/build -DCMAKE_BUILD_TYPE=Release
cmake --build small_gicp/build --parallel 2
sudo cmake --install small_gicp/build
```

前置：系统依赖及团队额外依赖已解决，rosdep check 无未解释错误，small_gicp 已安装。构建工作区并保留日志；并行数 2 是初次训练便于控制内存的选择，可以按机器调整。[仓库环境与构建说明][nav-readme]

```bash
cd /path/to/Navigation-2027/ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --parallel-workers 2 \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
ros2 pkg prefix rmu_gazebo_simulator
ros2 pkg prefix pb2025_robot_description
ros2 pkg prefix point_lio
ros2 pkg prefix small_gicp_relocalization
python3 -c 'from sdformat_tools.urdf_generator import UrdfGenerator; print("SDF tools import OK")'
```

本仓库通过环境 hook 设置模型搜索路径，必须加载工作区安装环境。模型 include 失败先检查路径和包安装，再判断文件丢失。[模型环境 hook][description-hooks]、[资源环境 hook][resource-hooks]

阶段 A 通过条件：完整构建日志中所需包成功，四个 pkg prefix 解析到本工作区，模型生成模块可导入，无未说明的系统/团队依赖；仅有 build 目录或二进制文件不算通过。

## 6. 阶段 B：世界、传感器与时钟验收

前置：阶段 A 通过。以下各终端均 source 系统与同一工作区环境；未同时运行其他同 namespace 的机器人/仿真。当前 world 使用仓库的 `rmul_2025` 配置。

终端 1：

```bash
ros2 launch rmu_gazebo_simulator bringup_sim.launch.py
```

仓库 README 提醒需点击 Gazebo 左下角开始按钮。前置：世界与机器人已生成；启动物理仿真后，终端 2 读取传感器，不发底盘命令。频率命令各观察 10～20 秒后 Ctrl+C。

```bash
ros2 topic echo /clock --once
ros2 topic hz /clock
ros2 topic list -t
ros2 topic info /red_standard_robot1/livox/lidar --verbose
ros2 topic hz /red_standard_robot1/livox/lidar
ros2 topic hz /red_standard_robot1/livox/imu
ros2 topic echo /red_standard_robot1/joint_states --once
```

此时 `livox/lidar` 应是 **PointCloud2**，不是实机 Livox CustomMsg；IMU 为 sensor_msgs/Imu。MID360 模型配置 IMU 200 Hz、雷达 20 Hz；实测接收频率还受仿真速度和机器性能影响，记录真实值，不把配置值伪装成测量值。[雷达模型][lidar-model]、[ROS-Gazebo 桥接][bridge]

前置：机器人状态发布器已经随 spawn 启动，使用默认 namespace。核对雷达到底盘 TF，不需要另行启用实车入口的 robot_state_publisher。

```bash
ros2 run tf2_ros tf2_echo base_footprint front_mid360 --ros-args \
  -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

阶段 B 通过条件：时钟持续前进；点云、IMU、joint_states 有数据；消息类型/QoS 与桥接匹配；模型 TF 可查询；不存在持续模型、插件、桥接加载报错。Gazebo 画面静止时优先看是否暂停及 `/clock`，而不是先调 LIO。

## 7. 阶段 C：定位链路与建图验收

前置：阶段 A、B 通过；第 4 节的点时间和模型配置问题已由维护者处理并记录验证版本；使用该版本的 simulation YAML。首次进入建图分支，以避免不存在的先验 PCD。

终端 3：

```bash
ros2 launch pb2025_nav_bringup rm_navigation_simulation_launch.py \
  world:=rmul_2025 slam:=True use_sim_time:=True
```

先检查节点有效参数，再按链路从上游到下游观察。以下为只读命令；频率观察后 Ctrl+C。

```bash
ros2 param get /red_standard_robot1/point_lio use_sim_time
ros2 param get /red_standard_robot1/point_lio preprocess.timestamp_unit
ros2 topic info /red_standard_robot1/velodyne_points --verbose
ros2 topic hz /red_standard_robot1/velodyne_points
ros2 topic hz /red_standard_robot1/cloud_registered
ros2 topic hz /red_standard_robot1/registered_scan
ros2 topic hz /red_standard_robot1/odometry
ros2 topic hz /red_standard_robot1/terrain_map
ros2 topic hz /red_standard_robot1/obstacle_scan
ros2 topic echo /red_standard_robot1/map --once --field info
```

PointCloud2 转换器保留原消息 header，补出 ring、time 并把 intensity 设为 0。它是为了兼容 Point-LIO 的机械雷达输入而存在，**不是真实 MID360 扫描模式和设备时间的完整模拟**。[转换器实现][converter]、[上游项目说明][nav-readme]

阶段 C 通过条件：每级有正确类型、frame 与时间的数据；地图更新；静止地面没有持续翻转或发散；TF 日志无持续错误；完成直线、转弯采集后能正常保存 PCD 和 YAML/PGM。仅复用 [传感器/LIO 课](../sensor-lio/README.md) 的 map_saver 与 PCD 归档步骤，**不执行其中的 reality launch 命令**；仿真保存时给 map_saver_cli 的 ROS 参数增加 `-p use_sim_time:=true` 并确认 `/clock` 前进。控制动作仅在仿真场景执行，控制接口见课程系统/控制章节。

不要跳过阶段 C 直接评价 Nav2。上游时间、坐标或地图问题会表现为障碍物乱跳、定位漂移、规划失败，换规划器不能解决这些输入缺陷。

## 8. 阶段 D：先验地图与完整导航验收

前置：已取得与当前场地、机器人模型、坐标约定一致的 PCD 和 YAML/PGM；阶段 C 已通过；此前的建图导航进程已正常退出并保存。示例 map 与 PCD 路径需换成验收数据包的真实文件。

```bash
ros2 launch pb2025_nav_bringup rm_navigation_simulation_launch.py \
  world:=rmul_2025 slam:=False use_sim_time:=True \
  map:=/path/to/validated-map/map.yaml \
  prior_pcd_file:=/path/to/validated-map/map.pcd
```

验证 small_gicp 成功加载地图、场景点云重合、map→odom 持续有效。RViz 初始位姿只给配准提供初值，不能代替收敛证据。随后在仿真中完成多次起终点导航，保存目标结果、轨迹、碰撞/急停情况、耗时和失败原因。阈值由训练负责人在机器基线上实测后固定；本文没有预填“成功率 100%”。

仿真桥接还提供 `chassis_odometry_gt`，可作为评估参考，但其 frame、原点及机器人模型位姿必须先与 LIO 对齐。不能直接把不同原点的坐标相减，也不能将真实值 topic 直接替代主链路 `odometry` 后仍声称验证了 LIO。[真实值桥接][bridge]

## 9. 常见故障从哪里开始排查

| 现象 | 第一个检查点 | 本课不接受的结论 |
|---|---|---|
| 启动导航后完全没有点云 | 仿真器是否另行启动、物理是否暂停、桥接及 namespace | “Point-LIO 算法坏了” |
| model:// 找不到资源 | 安装环境是否 source；资源包、环境 hook、实际模型文件 | “重新复制一份模型就一定能好” |
| 没有 velodyne_points | ign_sim_pointcloud_tool 是否启动、输入是否为 PointCloud2、QoS | 直接把 livox/lidar 重命名绕过转换器 |
| 点云有数据但姿态异常 | time 单位、IMU 单位、安装 TF、重力向量 | 只改滤波尺寸而不检查输入 |
| GICP 报 Couldn't read PCD | 展开 prior_pcd_file 后检查文件存在、格式和场地 | 用任意其他场地 PCD 顶替 |
| TF 只在根命名空间可见/找不到 | `/red_standard_robot1/tf`、`tf_static` 与观测工具 remap | 把 frame 名统一加前缀碰运气 |
| 用世界默认值定位失败 | 仿真 world 与导航地图是否同时为 rmul_2025 | 认为导航 world 参数会重启世界 |

## 10. 新人提交与环境发布门槛

提交一个训练记录目录：环境清单、依赖来源、源码 SHA/补丁、构建日志、分阶段日志、topic/QoS/TF 表、地图清单与校验值、三段轨迹结果、未解决问题。记录每阶段“通过 / 未通过 / 未执行”，不把后两者合并。

建议练习按顺序进行：

1. 在源码中找出两个 world 默认值并解释为什么互不覆盖。
2. 写出转换器 0.1 秒在当前 Point-LIO 参数下被解释成多少毫秒；附计算和行号。
3. 列出 UIC 与 PB 模型雷达 parent、平移、转角的差别；只解释，不擅自改实车外参。
4. 在暂停/继续仿真时比较 `/clock`、传感器与下游 topic，提交断点定位过程。
5. 完成建图保存，然后用**自己验收过的成套地图**重启定位，复查初始位姿与场景重合。

只有阶段 A～D 都有记录并通过，负责人才能把该机器镜像、依赖清单和数据包标成“统一训练环境已验收”。目前本页只完成源码事实、风险与验收步骤的编写，运行结果留待训练机产生。

[sim-bringup]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/launch/bringup_sim.launch.py#L10-L55
[nav-sim]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_simulation_launch.py#L139-L202
[world-file]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/resource/worlds/rmul_2025_world.sdf#L3-L42
[bridge]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/config/ros_gz_bridge.yaml#L1-L43
[sim-readme]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/README.md#L21-L105
[gazebo-launch]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/launch/gazebo.launch.py#L35-L68
[lidar-model]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/resource/models/mid360/model.sdf.xmacro#L25-L61
[resource-tree]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/resource
[robot-definition]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmoss_gz_resources/resource/models/rm25_example_robot/rm25_example_robot.def.xmacro#L1-L23
[spawn]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/launch/spawn_robots.launch.py#L1-L137
[sim-package]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/package.xml#L12-L29
[smallgicp-tree]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9/small_gicp
[gicp-deps]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/small_gicp_relocalization/package.xml#L11-L20
[gicp-cmake]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/small_gicp_relocalization/CMakeLists.txt#L19-L31
[driver-cmake]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/livox_ros_driver2/CMakeLists.txt#L94-L119
[pcd-readme]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/pcd/simulation/readme.md#L1-L5
[gz-world]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmu_gazebo_simulator/config/gz_world.yaml#L1-L48
[nav-sim-defaults]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_simulation_launch.py#L59-L107
[converter]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/ign_sim_pointcloud_tool/src/point_cloud_converter.cpp#L38-L93
[sim-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/simulation/nav2_params.yaml#L1-L77
[preprocess-units]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/preprocess.cpp#L51-L79
[preprocess-time]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/preprocess.cpp#L442-L455
[pb-model]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/resource/xmacro/pb2025_sentry_robot.sdf.xmacro#L14-L27
[uic-model]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/resource/xmacro/uic2025_sentry_robot.sdf.xmacro#L15-L22
[slam]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/slam_launch.py#L142-L199
[nav-readme]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/README.md#L37-L109
[description-hooks]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/env-hooks/gazebo.dsv.in#L1-L3
[resource-hooks]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/rmoss_gz_resources/env-hooks/gazebo.dsv.in#L1
