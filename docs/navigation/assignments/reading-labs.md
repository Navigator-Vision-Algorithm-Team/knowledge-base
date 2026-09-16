# 源码导读与带解答练习

本页用于从“看得懂教程”过渡到“看得懂本队工程”。R1–R5 是 T1/T2/T4/T6/T7 的练习材料，**不增加新的实车准入等级**。先独立写答案，再看参考分析；参考分析是基于固定源码的推导，题目中的数值和时间线是教学输入，不是实测记录。

所有本队链接固定为 [Navigation-2027@183a410](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9)。只读源码无需 ROS；运行检查需已经配置好的 Ubuntu 22.04/Humble 教学环境。实验使用独立节点、Topic 和确认空闲的 domain，输出不接真实串口；不得把本页变成实车故障注入脚本。

## 先掌握一套读代码方法

每次只追一个输出，按“构建目标→启动入口→参数来源→订阅/回调→状态→输出→失败路径”读。用搜索定位函数再看上下文，不从第一行逐字翻完整仓库。

在导航仓库根目录的 Bash 中可做只读搜索：

```bash
rg -n 'create_subscription|create_publisher|declare_parameter' \
  ros_ws/src/pb2025_sentry_nav/loam_interface
rg -n 'cmdVelCallback|syncCallback|latest_cmd_vel_|CONTROLLER_TIMEOUT' \
  ros_ws/src/pb2025_sentry_nav/fake_vel_transform
rg -n 'RewrittenYaml|param_rewrites|use_sim_time|SetRemap' \
  ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch
```

每题交一页：问题→代码位置→自己的推理→需运行确认的证据。无法确定的地方写未知，不用注释或函数名代替执行逻辑。

## R1：读通 loam_interface（S1，60–90 分钟）

**读文件**：[CMakeLists.txt][loam-cmake]、[头文件][loam-header]、[实现][loam]、[reality 参数][params] 的 `loam_interface` 段。

**先回答**：

1. 源码没有手写 `main()`，如何生成可运行入口？
2. 两个订阅输入和两个发布输出是什么类型？在默认 namespace 下全名是什么？
3. `state_estimation_topic` 是消息还是参数？默认空字符串在哪里被替换？
4. 哪个回调第一次查询外参？查询目标帧、源帧和时间是什么？每次回调都会重查吗？
5. 消息有 pose，是否自动发布了 TF？如果第一条点云先于成功外参初始化，应检查什么？

**参考分析**：CMake 将源文件编成共享库，`rclcpp_components_register_node` 注册组件并声明 `loam_interface_node` 可执行入口。构造函数从参数读取输入名，YAML 提供 `aft_mapped_to_init` 与 `cloud_registered`。默认 namespace 是 `red_standard_robot1`；未另加 remap 时接口为：

| 方向 | 全名 | 类型 | 输出帧或用途 |
|---|---|---|---|
| 订阅 | `/red_standard_robot1/aft_mapped_to_init` | `nav_msgs/msg/Odometry` | LIO 位姿输入 |
| 订阅 | `/red_standard_robot1/cloud_registered` | `sensor_msgs/msg/PointCloud2` | 已配准点云输入 |
| 发布 | `/red_standard_robot1/lidar_odometry` | `nav_msgs/msg/Odometry` | header `odom`，child `front_mid360` |
| 发布 | `/red_standard_robot1/registered_scan` | `sensor_msgs/msg/PointCloud2` | `odom` |

首次成功的 `odometryCallback` 按消息 stamp 查询 `base_footprint ← front_mid360`，缓存变换并置初始化标志；之后不反复查这个外参。TF 查找失败会记录并返回。点云回调未检查这个标志，因此要审查启动先后和首批点云的变换，不能凭“有输出”断言初始外参正确。此节点发布 Odometry 消息，不负责广播 `odom→base_footprint`；后者在 [sensor_scan_generation][sensor]。

**运行证据要求**：若环境可运行，只读采集 `ros2 node info`、两条输出的首条消息和启动日志；比较实际 namespace、参数与上表。暂不能运行就提交表和待验证设计，不编造 CLI 输出。

**拓展**：解释将动态挂载关系只在初始化时缓存的假设；指出它与机器人模型、初始姿态和 LIO 局部原点的联系。未经建模核验，不直接把缓存改成每帧查询。

## R2：零速度为什么不一定输出零（S2 算式，S5 完整题，90–120 分钟）

**读文件**：[fake_vel_transform.cpp][fake] 的 `transformVelocity`、`cmdVelCallback`、`localPlanCallback`、`syncCallback`，以及 [reality YAML][params] 的 `init_spin_speed`。详细风险背景见[证据页](../system/nav2-and-control-evidence.md)。

**题 A：计算而不是猜方向**。给定 `yaw=π/2`、输入 `(vx,vy,wz)=(0.2,0,0)`、spin 为 `0.5 rad/s`，算最终三个分量；再算输入全零、spin 为 0.5 和 spin 为 0 两种情况。

参考：按源码，`vx_out = vx cos(yaw) + vy sin(yaw)`，`vy_out = -vx sin(yaw) + vy cos(yaw)`，`wz_out = wz + spin`。所以第一组约为 `(0,-0.2,0.5)`；全零输入的输出分别为 `(0,0,0.5)`、`(0,0,0)`。浮点计算允许舍入误差。这只是输入变换，底盘如何解释坐标仍需协议确认。

**题 B：手推缓存时间线**。为隔离缓存问题，假定已收到有效 odometry，角度为 0、spin 为 0、local_plan 始终新鲜，按以下顺序执行回调：

| 步骤 | 输入事件 | 你应写出的状态与输出 |
|---|---|---|
| 1 | `localPlanCallback` 被调用 | 更新最近 local_plan 活动时间 |
| 2 | 收到非零 Twist `(0.2,0,0)` | 进入缓存分支，`latest_cmd_vel_` 保存该消息 |
| 3 | 一对 odometry/local_plan 触发同步回调 | 使用缓存，发布 `(0.2,0,0)` |
| 4 | 收到全零 Twist | 走立即变换发布分支，发布零，但没有清除原非零缓存 |
| 5 | 后续同步回调再次发生 | 在该构造序列下仍能读到旧缓存，再发布非零 |

这说明存在需要复现的缓存路径，不说明实车每次取消都会发生同样事件序列。同步器实际配对、回调顺序、输入源和底盘消费者都应记录。

**题 C：三个判断**。① 0.5 秒常量是否是 cmd_vel 独立 watchdog？② 发布一次 `cmd_spin=0` 是否立刻发布停止？③ `ros2 param get init_spin_speed` 是否等于当前 spin 成员值？

参考：① 它依据 local_plan 回调活动时间判定，没有独立定时检查速度输入年龄并强制停车；② spin 回调只改成员，不立即发布；③ 参数在构造时读取，Topic 回调更新成员不等于更新 ROS 参数。需要分别观察配置、运行成员影响和最终输出。

**交付**：三组算式、五步状态表、一份隔离实验的输入事件与采集项设计。要做 T9 修复，先与维护者定义“取消、零命令、断流、自旋保留”的协议，再覆盖这些行为的回归；不能只把 spin 设零就声称修复缓存。

## R3：world:=dona 为什么还可能找不到地图（S3，45–60 分钟）

**读文件**：[reality launch][reality] 的 map/prior_pcd_file 默认值、[dona.yaml][dona]、[地图审查表](../sensor-lio/README.md)。

**题目**：设安装包 share 目录为 `/opt/training/share/pb2025_nav_bringup`，只覆盖 `world:=dona`。写出会查找的 YAML 和 PCD 路径；再解释源码中 `ros_ws/dona.yaml` 为什么不会自动被选中。YAML 的 `image: dona.pgm` 应相对哪里解析？

**参考**：默认路径是 `/opt/training/share/pb2025_nav_bringup/map/reality/dona.yaml` 和 `/opt/training/share/pb2025_nav_bringup/pcd/reality/dona.pcd`。launch 按安装 share 路径拼接，不搜索整个源码树；源码根工作区有同名 YAML 也不改变默认路径。相对 image 以 YAML 所在目录解析。

**做什么**：列出 YAML、图像、PCD 的真实绝对路径、大小与 SHA256；写出显式 `map:=...` 和 `prior_pcd_file:=...` 参数，但先只检查文件和内容。环境齐备后运行步骤见定位页，不为验证路径就启动完整 reality 导航。

**验收**：文件可解析只是第一关；还必须解释 PCD 与二维地图的坐标、场地和外参一致性如何验证。`prior_pcd.enable=False` 是 Point-LIO 的开关，不免除定位分支 small_gicp 的 PCD 需求。缺训练地图标记待资源，不反复改规划参数。

## R4：改 YAML 后为何没有效果（S4–S5，60–90 分钟）

**读文件**：[reality launch][reality]、[公共 bringup][bringup] 的 `ReplaceString/RewrittenYaml`、[navigation launch][navigation] 的参数与组合分支。

**教学场景**：你修改了源码目录里一份 YAML 的 `use_sim_time` 或插件参数，界面行为没有变化。先给出四种可区分的原因，再写检查顺序；不能把“重启全部”作为第一条解释。

**参考诊断顺序**：

| 假设 | 要取的证据 | 能得出什么结论 |
|---|---|---|
| source 了另一套工作区 | `ros2 pkg prefix pb2025_nav_bringup`、当前 overlay 顺序 | 运行包可能来自其他 install |
| launch 使用另一份 params_file | 完整命令、launch 参数传递、安装目录文件内容 | 编辑源文件不等于实际输入已改变 |
| launch 改写了参数 | `RewrittenYaml` 的 `param_rewrites` 与节点有效参数 | bringup 会改写 use_sim_time 和地图文件；不能只看 YAML 原值 |
| YAML 节点名/namespace 不匹配 | `ros2 node list`、YAML 根键、参数 dump | 文件被读取不代表目标节点取到这段配置 |
| 值已改变但模块未加载或未重新配置 | 插件列表、lifecycle、模块日志与功能输出 | 参数存在不证明当前代码消费了该值 |

在已启动的隔离环境可用以下只读命令收集证据，实际节点名以 `node list` 为准：

```bash
ros2 pkg prefix pb2025_nav_bringup
ros2 node list
ros2 param dump /red_standard_robot1/controller_server
ros2 param get /red_standard_robot1/controller_server use_sim_time
ros2 lifecycle get /red_standard_robot1/controller_server
```

**验收**：至少一组“编辑文件→启动传递→有效参数→功能输出”的闭合证据；值已生效但行为不变时也允许结论为假设错误。恢复基线后再改下一项。进阶阅读组合/非组合的 behavior remap 差异，不能因为默认组合模式正常就宣称另一条启动路径等价。

## R5：bag 倍速下的速度为何不同（S2–S3，45–60 分钟）

**读文件**：[sensor_scan_generation][sensor] 的 `laserCloudAndOdometryHandler` 和 `publishOdometry` 中速度差分代码，配合[ROS 时间设计](https://design.ros2.org/articles/clock_and_time.html)。

**题目**：两帧位置相差 0.1 m，消息 stamp 相差 0.1 s。正常播放时两个回调墙钟相差 0.1 s，二倍速播放时相差 0.05 s。分别以消息 dt 与回调 dt 算速度。暂停、重复 stamp 或时间回跳应如何处理？

**参考**：消息差分两次都是 `1 m/s`；以给定回调间隔差分得到 `1 m/s` 和 `2 m/s`。真实调度会有抖动，数值未必恰好翻倍。本队此处使用 `steady_clock` 回调间隔，所以 bag 倍速可能改变计算输出；统一 use_sim_time 不会自动改写这一实现。

**做什么**：用 [F5 CSV 练习](../self-study/foundations.md)比较两种 dt，并记录 dt≤0 时的拒绝、重置或等待策略；将首次样本、重复时间、回跳、长暂停分别列出。若有已登记 bag，再采相同片段不同倍速的输出，明确重播起止与预热，不将数据处理性能当成定位精度。

**验收**：公式、单位和时间来源正确；不把绝对值 dt 或默默跳过坏样本当成通用修复。准备改生产代码时，还要核对 Twist 的 child frame 语义、坐标旋转和第一帧状态，不能只换一个时钟就结束。

## 同伴复核用这张表

| 复核项 | 通过表现 |
|---|---|
| 来源 | 每个关键判断能定位到固定版本文件与函数 |
| 因果 | 能解释输入如何经过状态变成输出，不只背节点名 |
| 边界 | 主动区分源码推断、合成实验和实际运行 |
| 复现 | 输入、命令、参数和预期齐全；资源不足写明 |
| 回归 | 改动后覆盖原故障和正常输入，能恢复基线 |

参考答案不是要背的口试标准句。导师可换 namespace、角度、时间间隔或目录，让新人现场重新推导；达到同样正确结论即可。

[loam-cmake]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/CMakeLists.txt
[loam-header]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/include/loam_interface/loam_interface.hpp
[loam]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp
[params]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml
[fake]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp
[sensor]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp
[reality]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_reality_launch.py
[bringup]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/bringup_launch.py
[navigation]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py
[dona]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/dona.yaml
