# RoboMaster 导航新人学习入口

这是一条面向零导航经验大一新人的学习路线。目标是看懂本队系统、修改代码、用证据排障，并通过值守实车考核后参与比赛调试。学习对象已由队内确认是 **Navigation-2027**，不包含自瞄算法；自瞄侧提供的串口和机器人状态属于必须掌握的系统接口。

**审查日期：2026-09-14。代码基线：[`Navigation-2027@183a410`](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9)。** 本轮完成源码、配置和文档静态审查，未在 Ubuntu/ROS 或机器人上运行导航。仓库中的默认值不等于已验证实车配置；使用时先填写[版本与资源登记](maintenance/README.md)。

## 从哪里开始

1. 阅读[最终培训路线与原稿审查结论](onboarding/learning-route.md)，确定当前阶段。
2. 按[环境与工程基础](onboarding/environment.md)完成 S0。没有机器人也能开始；不要一开始尝试运行整个实车工程。
3. 对照[系统、Topic 和 TF 地图](system/README.md)阅读少量真实代码；看不懂的概念回到对应专题。
4. 按[实践任务与考核](assignments/README.md)交付代码、日志、对照结果和恢复记录。完成一次作业不等于取得实车操作资格。
5. 用[16 周任务单](onboarding/weekly-plan.md)确定每周具体阅读与交付；读源码困难时做[带参考解答的练习](assignments/reading-labs.md)。当期任务完成后，从[自学与进阶导航](self-study/README.md)选择一个方向深入。

## 学习目录

| 入口 | 解决什么问题 | 主要阶段 |
|---|---|---|
| [培训路线](onboarding/learning-route.md) | 顺序、必学/了解/进阶、能力门槛 | 全程 |
| [16 周具体任务单](onboarding/weekly-plan.md) | 每周指定阅读、实际操作、交付、加餐和缺资源替代任务 | 全程 |
| [环境与工程基础](onboarding/environment.md) | Ubuntu/Humble、Git、C++/Python、构建缺口 | S0 |
| [ROS2、TF、时间与全向运动](ros2-tf/README.md) | Node/Action/QoS、真实 TF、bag、速度坐标系 | S1–S2 |
| [系统地图](system/README.md) | launch→节点→Topic→TF→输出 | 初读 S0，S3 后复读 |
| [传感器、LIO、建图与重定位](sensor-lio/README.md) | MID-360、Point-LIO、small_gicp、地图资产 | S3 |
| [环境表达与路径规划](planning/README.md) | 地形 intensity、Costmap、A*、Hybrid-A* | S4 |
| [Nav2、控制与接口](nav2/README.md) | 实际插件、BT、速度链、串口与控制权 | S5 |
| [源码审查证据](system/nav2-and-control-evidence.md) | 当前配置差异与需要复测的风险 | S5–S7 |
| [Debug、实车与比赛](debug-real/README.md) | 故障分层、停止、恢复、比赛交接 | 每阶段练习，S6–S7 实车 |
| [实践任务与考核](assignments/README.md) | 作业输入、验收方法、量化门槛 | 全程 |
| [源码导读与参考解答](assignments/reading-labs.md) | 节点接口、速度缓存、地图路径、参数加载、时间差分五道题 | S1–S5 |
| [自学与进阶材料](self-study/README.md) | 基础补课、数学定位、规划控制、ROS2 系统，指定章节与离线项目 | 随阶段选学 |
| [仿真环境建设](simulation/README.md) | 已有代码、缺失资产、统一环境验收 | 可选基础设施 |
| [资料、模板与维护](maintenance/README.md) | 阅读资源、数据集、问题记录、知识库更新 | 全程 |

## 目前可做与需要队伍提供的材料

| 条件 | 可以完成 | 不能据此声称完成 |
|---|---|---|
| Ubuntu 22.04 + ROS2 Humble 开发机 | S0–S2、栅格规划、源码追踪、教学节点故障注入 | 实车已能导航 |
| 增加已登记的 bag、消息定义和外参 | 数据体检、定位重跑、Costmap 输入观察 | 控制闭环、动态避障效果、可靠停车 |
| 增加已验收的仿真场景 | 闭环跟踪、目标取消、障碍与恢复实验 | 实车打滑、机械极限、传感器实测表现 |
| 增加负责人值守的机器人时段 | S6 实车资格与 S7 比赛演练 | 未覆盖场景的性能保证 |

本库当前没有统一训练 bag、完整的实车地图包或一键可复现实车环境。负责人应按[材料清单](maintenance/README.md)补齐；新人先做不依赖这些资源的任务。缺资产造成的失败应登记为环境问题，不能记为新人不合格。

已有的[Linux 教学](../Linux教学/2.0Linux基础.md)、[Linux 练习](../Linux教学/2.1Linux基础配套练习.md)、[SSH](../Linux教学/3.ubuntu-ssh-guide.md)和[Git 教学](../git教学/1.git下载和如何使用github.md)继续复用。[开源项目合集](../开源项目合集/index.md)用于专题拓展，其中 FAST-LIO、MINCO、MPC 等方案不自动成为本队必修栈。
