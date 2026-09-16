# 导航组大一新人培训路线：按本队工程学习

适用对象：零导航经验的大一新人。主仓库为 [Navigation-2027，审查基线 183a410](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9)。这是对原稿的工程化修订：保留“尽早动手、Debug 优先、稳定性优先”，把通用算法清单改为本队代码和能力门槛。源码证据见[系统地图](../system/README.md)，每关任务见[考核手册](../assignments/README.md)。

## 原稿哪些保留、哪些调整

| 原稿内容 | 审查结论与调整 | 对本队的原因 |
|---|---|---|
| 工程基础先行，C++ 随用随学 | 保留这个原则，落实为最小编译与协作任务；加入 Python/launch 阅读 | 主工程同时有 C++ 组件、Python launch 与顶层 Python 辅助脚本 |
| 熟悉完整导航理论后才进入队内代码 | 改为 S0 看目录和入口，S1 读一个小节点，S3 后追完整链路 | 避免学完通用课程仍不知道本队节点是什么；不要求一开始读完 LIO |
| Debug 早学，但等级在“能开发”之后 | 修正为“观察并排障 → 修改并回归 → 负责模块” | Debug 是每关交付，不是最后一门课 |
| 固定 map→odom→base_link→lidar→imu | 改成发布权表；本队涉及 base_footprint、chassis、gimbal_yaw、front_mid360、gimbal_yaw_fake | 雷达在模型中挂在云台；旋转关节和虚拟导航帧都不能省略 |
| LIO/SLAM 泛讲，FAST-LIO 与 Point-LIO 并列 | Point-LIO 配置、输出和异常必学；small_gicp/initialpose 必学；FAST-LIO 对比了解 | 当前启动链使用 Point-LIO 与 small_gicp_relocalization |
| 地图、Nav2、Costmap、Controller 多次分散 | 合并依赖顺序：输入/TF → 地图/地形/足迹 → 规划 → 控制 → BT 恢复 | 错地图、错地形输入不能靠 Controller 调参补救 |
| BFS→Dijkstra→A* 的建议顺序与编程训练 | 进一步明确 BFS/Dijkstra 看懂，必做一份带边界检查的 A*；解释当前 Smac Hybrid 的 DUBIN 约束 | 保留算法训练，但不能把二维 A* 作业冒充实际 Planner |
| 建议实现 Pure Pursuit，后续学习其他控制器 | 调整为优先全向几何跟踪/PID 与 OmniPidPursuitController；其他控制器了解/进阶 | 横移 vy 与旋转解耦是实际接口问题，差速 Pure Pursuit 不覆盖全部能力 |
| 常见 Costmap 层都必学 | Static、IntensityObstacleLayer、Inflation 必学；Voxel/IntensityVoxel 了解 | 当前 reality YAML 的加载列表才是判断依据；terrain_map intensity 有地形语义 |
| BT 用低血量回家等例子作为工程主线 | 先读实际重规划/清图/BackUp XML，再学决策→Action 边界 | 本库未验证完整比赛决策状态机；不能把例子写成已有功能 |
| 仿真未来从零建设 | 改为复用已有 rmu_gazebo_simulator 等包，补模型、PCD、版本和验收 | 代码已经存在，统一可用的训练环境仍需建设 |
| “程序跑不了禁止直接问学长” | 改成带证据求助，实车异常立即报告 | 不鼓励盲改和隐瞒问题；求助质量可以考核 |
| 自定义 Nav2/BT 插件作为基础能力 | 降为 S7 专项进阶 | 全员先能配置、定位错误、改小段代码并回归；维护插件另设门槛 |

## 必学、了解、进阶怎样区分

**必学**：每个人必须解释、实际操作并交证据，包含本队正在用的模块接口与故障特征。**了解**：能说明用途和不适用条件，会查资料；不要求从零实现。**进阶**：选定方向后完成源码改动和对照实验，不作为全员基础合格条件。

| 主题 | 必学 | 了解 | 进阶 |
|---|---|---|---|
| 工程 | shell/SSH、Git 分支与 PR、CMake/colcon、overlay、C++ 类/引用/智能指针/回调、Python/YAML/launch | rebase/cherry-pick、多线程基本风险 | executor/锁、profiling、部署与依赖锁定 |
| ROS2 | Topic/消息、QoS、Service/Action、反馈/取消、参数、namespace/remap、lifecycle | DDS 发现原理、组件通信 | executor 调度、通信性能与多机配置 |
| TF/运动 | 父子帧与唯一发布者、stamp/clock、四元数、静动态变换、vx/vy/wz、机器人与世界坐标转换 | 麦轮/舵轮/差速约束 | 底盘模型、误差传播、李群李代数 |
| 传感器/定位 | MID-360 输入类型、IMU 单位/时间/外参、Point-LIO 输出、small_gicp 初始化、两类地图 | EKF/ESKF/ICP/GICP 思想，FAST-LIO/NDT 对比 | Point-LIO 滤波推导、配准鲁棒性、初始化与失效检测 |
| 地形/规划 | terrain_map intensity、footprint、标记/清除/膨胀/unknown、A* 实作、Smac Hybrid 配置与约束 | BFS/Dijkstra、Smac2D、Lattice、NavFn | Hybrid-A*/JPS/D* Lite 的设计与场景对照 |
| 控制 | 本队全向追踪插件、PID 基本作用、速度限幅、fake frame、自旋偏置、最终指令和串口 | Pure Pursuit/RPP、DWB、MPPI、TEB 的适用边界 | MPPI/MPC、控制插件与稳定性/碰撞验证 |
| 系统可靠性 | 日志/bag、lifecycle、Goal 状态、停止与控制权、恢复记录、回退 | watchdog/超时/fallback 设计、比赛状态接口 | 自动化故障回归、BT 插件、性能与长期可靠性 |

“了解”不表示永远不学：当代码切换到相应模块时，把它的接口、配置和调试升为必学，并更新基线。

## 推荐节奏：16 周，按门槛推进

每周建议 6–8 小时，包括自学、实践和一次短复盘。周次用于排期，验收未通过则补实验；有基础的新人可用交付证据跳过重复练习。S3/S5/S6 的排期由数据包和实车资源决定。

具体执行见[16 周任务单](weekly-plan.md)：逐周列出阅读范围、代码入口、实验、交付与选做内容。零基础补课见[基础自学](../self-study/foundations.md)，学有余力进入[专项材料](../self-study/README.md)；专项深度不成为全员新增门槛。

| 阶段/建议周次 | 目标与前置 | 对应本队代码/接口 | 本关交付与通过门槛 |
|---|---|---|---|
| S0，第 1–2 周 | 无前置；会配置最小环境、提交小改动 | README→ros_ws/src→package.xml→CMakeLists.txt；观察 reality launch 参数 | T0：新终端跑通 talker/listener；小包编译成功；提交可复现 README；说明缺失依赖与版本 |
| S1，第 3–4 周 | S0；掌握通信、参数、launch、Action 与证据化 Debug | 先读 loam_interface 的 pub/sub；理解相对 Topic 与默认 namespace | T1：自写教学 pub/sub 与参数 launch，修复错名/QoS 两题；完成教学 Action 反馈与取消 |
| S2，第 5–6 周 | S1；理解 TF、时钟、二维全向运动 | sensor_scan_generation、robot_description、gimbal_yaw_fake；odometry | T2：五种运动、TF 发布权表；独立区分断链与错时；非正 dt 处理有证据 |
| S3，第 7–8 周 | S2 + 已登记 bag；会检查输入与定位 | livox→Point-LIO→loam_interface→sensor_scan_generation；small_gicp/initialpose；SLAM 分支 | T3–T4：输入体检、两次同条件回放、建图/定位区别与地图包检查；无 bag 先完成静态部分 |
| S4，第 9–10 周 | S2；S3 数据用于地形实验 | terrain_analysis→terrain_map→IntensityObstacleLayer；SmacPlannerHybrid | T5：A* 边界测试通过；T6：足迹/膨胀/地形阈值单因素对照，解释图与路径变化 |
| S5，第 11–12 周 | S3–S4；能沿导航闭环定位配置与代码 | BT→GridBased→FollowPath→velocity_smoother→fake_vel_transform→串口 | T7：追踪真实 Action/Path/速度链，完成可回退参数改动；解释零输入仍自旋风险；能识别未加载与未生效 |
| S6，第 13–14 周 | T0–T7 + 停止路径负责人验收；受控实车 | 传感器/TF/Costmap/最终速度/底盘反馈全链 | T8：先无驱动输出检查，再低速值守测试；通过陌生故障题和恢复回归；取得实车资格 |
| S7，第 15–16 周及后续 | T9 离线代码开发可在 S5 后进行；T10 实车比赛演练需先通过 S6 | 选定位/规划/控制/系统之一；比赛 Goal 接口和恢复 | T9–T10：小段真实代码改动、复现与回归、模块交接；值守演练后才能承担比赛岗位 |

Nav2 概览在 S0 就可以讲 15 分钟；不等待全部理论学完再看系统图。建图/定位和规划两条学习线在 S2 后可部分并行，S5 再合流。

## 能力等级与参加比赛的边界

| 等级 | 判定依据 | 可以承担 |
|---|---|---|
| L0 能运行与观察 | T0–T1 | 开发机实验、带记录跟随调试 |
| L1 能排基础故障 | T2–T3，能说明证据与因果 | TF/Topic/时钟体检，整理 bag 和复现 |
| L2 能修改与回归 | T4–T7，一项真实配置改动、一项教学代码改动 | 在审查下改参数/launch/局部代码 |
| L3 能值守实车 Debug | T8；停止、陌生故障、恢复、回归全部通过 | 独立完成诊断流程，实车测试仍有安全值守 |
| L4 能负责模块/比赛岗位 | T9–T10 + 维护者签字 | 模块维护、赛前回归、比赛分工与新人指导 |

“独立 Debug”指不依赖学长一步步提示就能形成和验证诊断；不等于一个人在场地无值守操作。遇到机械危险、接口责任不明或不可恢复故障，应及时升级处理。

## 导师每周做什么

提前发输入数据与本周验收项；每次只引入一类主要变量；复盘时要求新人展示实际日志和原始数据，而非只展示截图。对缺少完整地图、串口包或训练 bag 的阶段，导师先修复训练材料，再组织考核。正式准入统一按[考核手册](../assignments/README.md)执行。
