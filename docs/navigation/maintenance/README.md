# 资料、模板与知识库维护

知识库要让下一届找到入口、完成实验、复现错误，而不只是积累链接。当前新增专题放在 `docs/navigation/`，复用原 Linux/Git 页面，保留开源项目合集和既有路径。目录按课程专题合并，避免先建二十个空目录。

## 目录与归档规则

```text
docs/navigation/
├─ README.md                       学习入口与资源边界
├─ onboarding/                     最终路线、16周任务单、环境基础
├─ system/                         系统地图、固定版本源码证据
├─ ros2-tf/                        通信、TF、时间、全向运动
├─ sensor-lio/                     传感器、LIO、建图、重定位
├─ planning/                       环境表达、Costmap、规划
├─ nav2/                           Nav2、控制、BT、接口
├─ debug-real/                     Debug、实车、比赛流程
├─ assignments/                    任务与统一考核、带解答源码练习
├─ self-study/                     基础、数学定位、规划控制、ROS2系统
├─ training/                       教学代码入口、合成数据、验证状态
├─ simulation/                     统一仿真建设与验收
└─ maintenance/                    资源、模板、维护规则
```

课程模块统一包含：目标、前置、核心概念、真实代码/接口、分级要求、实践任务、验收、常见错误、参考和适用版本。后续常见错误按“现象—证据—根因—修复—回归—适用 commit”形成独立页；数量少时先放在相应专题，不建立空目录。

仓库根 `training/` 存可执行教学代码与小型合成数据；`docs/navigation/training/` 存对应教程。synthetic-v1 有解析来源、校验值、生成器和回归，见[数据包](../training/datasets.md)。大体积实车 bag 仍走队内数据存储。`.gitattributes` 保留数据原始字节，跨 Windows/Linux checkout 不改换行以免破坏 SHA256。

## 教学资料：每个链接都要对应一个任务

完整的指定章节、先修、学时、跳过范围与离线项目已拆到[自学与进阶导航](../self-study/README.md)。下面保留常用速查入口；新人按周选读，不以收藏链接数量作为学习进度。

| 资源 | 指定用途 | 任务与版本边界 |
|---|---|---|
| [MIT Missing Semester](https://missing.csail.mit.edu/) | Shell、Git、调试工具选读 | T0；不要求完整刷课 |
| [Learn Git Branching](https://learngitbranching.js.org/?locale=zh_CN) | HEAD、分支、merge 可视化 | T0；用练习仓库操作 |
| [LearnCpp](https://www.learncpp.com/) | 类/引用/指针/标准库查询 | T1/T9；不是进入 ROS 的前置全集 |
| [鱼香《动手学 ROS2》](https://fishros.com/d2lros2/#/) | 中文通信、包、参数与 launch 的辅助解释 | 当前入口标注 Foxy 版；T0–T2 可参考概念，安装/API/命令以 Humble 官方原文为准，不跟随降版 |
| [ROS2 官方 Humble 教程源码](https://github.com/ros2/ros2_documentation/tree/humble/source/Tutorials) | CLI、C++ 节点、Action、tf2 的准确说明 | T1–T3；官网受限时可读官方源码 |
| [Humble QoS](https://github.com/ros2/ros2_documentation/blob/humble/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst) | offered/requested 与兼容性 | T1/T3 |
| [tf2 Debug 教程](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.rst) | frame 与时间问题分离 | T2/T8 |
| [ROS 时间设计](https://design.ros2.org/articles/clock_and_time.html) | 系统/steady/ROS time、回跳 | T2–T4 |
| [REP-103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst)、[REP-105](https://github.com/ros-infrastructure/rep/blob/master/rep-0105.rst) | 单位、坐标系、map/odom 语义 | T2/T3，不能覆盖本队 TF 实现 |
| [PythonRobotics](https://github.com/AtsushiSakai/PythonRobotics) | 选 Dijkstra/A* 动画后自己实现 | T5；其他算法按专题选读 |
| [Nav2 Humble 源码](https://github.com/ros-navigation/navigation2/tree/humble) | 现用服务器/插件概念和接口 | T5–T9；安装版本需另记录 |
| [Humble Controller 接口](https://github.com/ros-navigation/navigation2/blob/humble/nav2_core/include/nav2_core/controller.hpp) | setPlan 与 computeVelocityCommands | T9 进阶；现行 Rolling 接口不同 |
| [Humble RPP](https://github.com/ros-navigation/navigation2/blob/humble/nav2_regulated_pure_pursuit_controller/README.md)、[Humble MPPI](https://github.com/ros-navigation/navigation2/blob/humble/nav2_mppi_controller/README.md) | 对比全向支持和适用边界 | 了解/专项，不替代本队 OmniPid 必学 |
| [PolarBear 仿真上游](https://github.com/SMBU-PolarBear-Robotics-Team/rmu_gazebo_simulator) | 参考已有仿真组件维护 | 由负责人做兼容性验收，见[仿真页](../simulation/README.md) |

核对日期 2026-09-14。外部教程只作学习资料，本队实际组件由固定 commit 的代码与运行快照证明。部分旧 Nav2 `.html` 链接已变更；优先使用官方 Humble 仓库核对 API，本机 `--help` 和有效参数决定命令是否适用。

## 开课前由负责人补齐的资源

配套代码、标准合成包和两个教学故障案例已建入口，状态见[验证记录](../training/validation.md)。下表列的实测材料仍需队内建立，不是假定已存在的下载入口；负责人在首次授课前指定具体姓名、存储位置和截止日期。

| 优先级/责任角色 | 交付材料 | 最小验收 |
|---|---|---|
| P0 导航维护者 | 实际运行的仓库、commit、依赖锁定、overlay 顺序、launch 命令和参数快照 | 一台干净 Ubuntu/Humble 机器可复现；确认是否有未提交本地修改 |
| P0 导航+自瞄/串口+电控负责人 | 外部串口包、协议、Topic/TF/关节状态、控制权、超时/停车约定 | 最终命令与底盘接收一致；停止链路逐项通过 |
| P0 定位维护者 | 配套 YAML+图像+PCD、模型/外参及校验值 | 路径可解析，地图坐标对齐，启动无资产缺失 |
| P0 教学/定位维护者 | 一段静止、一段运动、一段典型故障 bag；消息定义、QoS、TF、基线 | 新人可回放同一异常；不含密钥等无关数据 |
| P1 场地/设备负责人 | 值守时段、硬件急停方式、低速上限、停止时间/距离阈值 | T8 开始前填妥；未填不开展运动测试 |
| P1 仿真维护者 | 统一模型/世界/时间单位、地图、依赖和启动入口 | 按[仿真验收](../simulation/README.md)通过后才能称为统一训练环境 |
| P2 导师 | 盲测题库、评分样例、合格作业、常见错误条目 | 下一届导师无需口头补完所有步骤 |

地图和 bag 存队伍指定数据盘/对象存储；知识库只存 manifest 和可访问入口。现阶段不虚构 URL，也不把数百 MB 数据塞进普通 Git。

## 可复制的版本与资源登记模板

```text
实验编号 / 日期 / 操作人 / 复核人：
机器人编号 / 硬件与驱动使能状态：
Ubuntu / ROS_DISTRO / RMW_IMPLEMENTATION / ROS_DOMAIN_ID：
导航仓库 URL / branch / commit / git status：
外部串口与消息包 URL / commit / overlay 来源：
Nav2、Livox SDK、small_gicp、仿真器等安装版本：
namespace / TF topic / use_sim_time / clock 来源：
完整启动命令 / 有效参数快照位置：
模型 / 外参 / 地图 YAML+图像+PCD 路径与 SHA256：
输入 bag ID / 存储入口 / SHA256 / 消息包与 QoS：
只读回放或闭环实车 / 预热与测试时间区间：
速度限值 / 停车时间与距离阈值 / 值守与急停负责人：
结果、证据路径、未验证项与回退版本：
```

SHA256 可用 `sha256sum FILE` 计算；填真实值。bag manifest 还要列 Topic、类型、数量、时长、原始/算法输出分类、TF 发布者和回放白名单，避免重算时同时发布旧结果。

## 可复制的问题/实验记录模板

```text
标题与适用代码版本：
预期行为 / 实际现象 / 首次异常时间：
最小复现命令与输入：
观察证据（日志原文、端点/QoS、stamp、TF、有效参数）：
已排除的原因及依据：
当前判断 / 尚不确定的边界 / 需要哪个负责人：
唯一修改因素与代码/配置 diff：
改后结果、重复次数、失败样本：
临时恢复步骤 / 根因修复 / 回退步骤：
原任务与停止路径是否回归 / 未做的测试：
```

## 更新与发布

维护者每次变更启动入口、插件、Topic、TF、地图、串口或 ROS 版本，必须同步修订系统表、相关课程和受影响作业；课程明确保存审查基线。只把实测结果写入“运行已确认”，源码推断继续标注待验证。

按仓库现有流程向 main 提交 PR。检查相对链接、代码来源、命令前置和 MkDocs 构建；新页面须进入 `mkdocs.yml` 的导航。main 合入后由现有 GitHub Actions 发布网站，不手工修改生成的 `site/` 文件。

本地验证示例：`python -m mkdocs build --strict --site-dir ../knowledge-base-preview`，在仓库目录运行，将输出放到仓库外；不向训练材料提交临时构建产物。必要的旧页面错误修订应局部进行，保持原有入口可用。
