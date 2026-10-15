# 教学包验证状态与复验方法

<small>整理与维护：24cst朱鑫鹏</small>

本页区分配套教学代码、标准合成数据和本队实车系统。原有小系统位于知识库 `training/`；新增巡逻、A* 与对照实验资产位于 `docs/navigation/training/assets/`。合成轨迹、示例故障和离线数值结果均不代表实车采集或导航性能。

## 验证范围

验证不是一个笼统的“跑通了”，而是用固定输入检查某条具体主张。你可以把证据想成逐层递进：数学测试确认公式和边界；数据测试确认文件写入后还能正确读回；ROS 集成检查节点间的实际消息；机器人验证再检查物理执行。前一层给后一层减少未知量，但不会自动替后一层作答。

例如模型前进 5 秒得到 1 m，能检查理想积分；它没有摩擦、打滑或通信延迟，不能据此保证实车也走 1 m。类似地，能够解码 bag 说明数据格式可读，只有真的启动回放和订阅节点，才检查到 ROS 消息链。

| 对象 | 验证方法 | 能证明什么 |
|---|---|---|
| 理想全向模型 | 解析直行/侧移/圆弧、无效数值、超时、回跳单元测试 | 教学积分与时间边界满足定义 |
| CSV 重算入口 | 用命令重算轨迹，对比独立解析真值；错误输入和错误真值反例 | 入口不会把真值直接抄成预测 |
| 标准合成数据 | 重新生成、逐文件 SHA256、SQLite 完整性、CDR 反序列化、计数/时间/TF/地图几何检查 | 发布的数据可读、来源与几何一致、内容可复现 |
| 两个 Debug 模型 | broken/fixed 模式与命令行退出码、正常输入和边界回归 | 受控教学模型能复现并修复定义的故障 |
| A* 两步练习 | 固定边界案例、小图独立 BFS 最优代价、路径逐段检查、拒绝错误学生答案 | 参考搜索与作业检查器满足四邻接单位代价契约 |
| 离线巡逻 | 正常完成、等待恢复、取消、断流与终态不再运动 | 固定步长模型的状态与速度规则正确；未涉及 DDS 或 ROS Action |
| TF/地图/滤波图 | 独立手算几何、固定输入复算、SVG 与数值报告一致 | 合成输入与图示可复现；未证明真实外参、地图或 LIO 性能 |
| Humble 节点与 bag | 在实际 ROS 环境构建、启动、通信、TF、取消和 bag 回放 | 配套小系统在该测试环境运行；不扩展为本队导航验收 |
| 知识库 | MkDocs strict、内部链接和固定源码链接检查 | 教学入口与引用可导航 |

## 本地复验

先选与改动直接相关的检查。改积分时重点看圆弧、超时和回跳；改数据生成时看独立读回、地图坐标与摘要；只改讲解时则核对数值、代码路径、链接和文档构建。下面命令保留完整复验入口，不要求每次小幅文案修改都重新做所有机器人实验。

| 要理解的反例 | 仓库内路径和蓝链接 | 测试为什么这样设计 |
|---|---|---|
| 过期后的定时器隔很久才触发 | `training/tests/test_core.py`：[超时截断](https://github.com/Navigator-Vision-Algorithm-Team/knowledge-base/blob/main/training/tests/test_core.py#L79-L86) | 0.2 m/s 只生效 0.5 s，下一次观测很晚也应停在 0.1 m |
| 真值故意改错，程序会不会还报成功 | `training/tests/test_replay.py`：[错误真值反例](https://github.com/Navigator-Vision-Algorithm-Team/knowledge-base/blob/main/training/tests/test_replay.py#L36-L43) | 防止把真值当预测，或只看程序有没有异常 |
| 写文件和读文件用了同一个错误假设 | `training/tests/test_datasets.py`：[独立解码与几何检查](https://github.com/Navigator-Vision-Algorithm-Team/knowledge-base/blob/main/training/tests/test_datasets.py#L85-L172) | 从存储结果重新检查类型、时序、TF 和格中心，不仅比较生成函数自身的输出 |

读测试时按“安排输入 → 调用被测逻辑 → 对照预期”三步写一句话。测试名给你场景，断言给你要保住的行为；它们也是读实现遇到边界问题时很好的第二入口。

在仓库根目录、已安装 `training/requirements-data.txt` 的 Python 环境运行：

```text
python -m unittest discover -s training/tests -p test_core.py -v
python -m unittest discover -s training/tests -p test_replay.py -v
python -m unittest discover -s training/tests -p test_datasets.py -v
python -m unittest discover -s training/cases/tests -p "test_*.py" -v
python -m unittest discover -s training/ros2_ws/src/nav_training/test -p "test_*.py" -v
```

新增三组离线练习不需要 ROS 或额外 Python 库，在知识库根目录运行：

```text
python -m unittest discover -s docs/navigation/training/assets -p test_astar_workshop.py -v
python -m unittest discover -s docs/navigation/training/assets -p test_patrol_workshop.py -v
python -m unittest discover -s docs/navigation/training/assets -p test_comparison_figures.py -v
```

测试入口也可以从 [A*](astar-workshop.md)、[巡逻](patrol-workshop.md)、[对照实验](controlled-experiments.md)页面下载。保存实现和输入后，用各页的命令复验；巡逻 ROS 版的多节点实现由学生在个人工作区完成，按巡逻页另交实际运行证据。

原有小系统的完整 Humble 验证按[ROS 测试说明][ros-testing]构建并 source 后运行：

```bash
export ROS_DOMAIN_ID=87
export ROS_LOCALHOST_ONLY=1
export NAV_TRAINING_REQUIRE_ROS=1
python3 -m unittest discover -s training/tests -p test_ros_smoke.py -v
```

缺少 ROS 时普通开发机可跳过 ROS 用例；设置 `NAV_TRAINING_REQUIRE_ROS=1` 后缺依赖必须失败。不能把 `SKIP` 计为实际运行通过。

看输出时分清三件事：`OK` 表示本次执行的断言通过；`skipped` 表示有测试没有执行；退出码用于让脚本和 CI 判断整个命令是否成功。报告应记录命令、环境、commit、通过数和跳过数。只截最后一行 `OK`，会丢掉解释验证范围所需的信息。

## 本次新增练习的本地复验（2026-10-15）

### 图文上手入口

本轮增加 7 张中文 SVG、2 段多帧 GIF 及对应静态海报，配套[免安装的演示总览](../visuals/playground.html?gallery=1)。六个场景覆盖导航总览、消息传递、车体/世界方向、A*、障碍代价圈、巡逻走停。13 个入门页按主题安排图解和小任务；章节中的演示只呈现当前主题，全部场景切换保留在独立总览。重复的静态图和动图按需展开，原理、源码和考核也按章节展开；不加载脚本时原文与图片仍完整显示。

```text
node --test docs/navigation/visuals/test_models.mjs
```

本次 14 项 JavaScript 模型测试通过。浏览器另实际检查播放/暂停、单步、错误 Topic 后恢复、90°方向、正常完成/取消/断流终态，以及目录跳转自动展开原文。320 px 窄屏六个场景均无横向溢出。GIF 可暂停为静态海报；偏好减少动态效果时默认显示静态帧。

章节布局调整后再次通过严格构建、14 项模型测试和站内链接检查。浏览器复查消息同名/异名、说明展开后的演示高度，以及六个单主题场景在 320 px 下的宽度；巡逻的播放与故障按钮分组显示，嵌入高度随内容自动调整。

随后完善环境、周计划、系统、排障、考核、自学、维护、数据、仿真共 9 处入口，新增 8 张对应主题的 SVG 和 2 份纯文本交接模板。逐页检查图像加载、默认折叠与 320 px 页面宽度；周次、考核与仿真阶段链接可展开目标章节。5 处首部选择表在窄屏改为纵向卡片，详细参考表保持原样。两份模板实际点开确认中文显示；排障练习按页面步骤得到 3/3、3/0、3/3 的收发计数。

数据课的两条离线命令在 Windows/Python 3.12.14 重新执行：forward 为 51 个样本、5 s、最终 x 约 1 m；lateral 为 51 个样本、5 s、最终 y 约 0.5 m，两者 `passed` 均为 `true`。这一检查只覆盖教学运动重算，没有新增 ROS、Gazebo 或实车运行结论。

这些图和动画使用本地合成模型，不连接 ROS 或底盘。浏览不需要额外安装；作者重新生成 GIF 时使用 Pillow，生成器要求新的输出目录，不覆盖已有目录。原有 Python 教学实现未因本轮图文改版改变，下面保留其独立复验记录。

### 离线代码练习

Windows、Python 3.12.14，在当前未提交的导航培训改稿上运行以下相关检查，共 **69 项通过、0 项跳过**。这是本次选定的离线回归范围，不是整仓全部测试的总数；原有数据制包和 ROS 集成未在这次环境重新运行。

| 检查组 | 数量 | 实际结果 |
|---|---:|---|
| 新增 A*、固定输入与作业检查器 | 14 | 通过；12 个固定案例及 128 幅小图纳入检查 |
| 新增巡逻协议与报告 | 18 | 通过；完成、等待恢复、取消、断流、终态及坏输入 |
| 新增几何、Kalman、SVG 与输出保护 | 15 | 通过；独立手算、同窗口指标、确定性及拒绝覆盖 |
| 原有运动核心 | 9 | 通过 |
| 原有 CSV 重算 | 3 | 通过 |
| 原有两个 Debug 模型 | 10 | 通过 |

当前受限执行环境的默认临时目录不可写，运行测试时仅把 `tempfile.tempdir` 指向仓库外的可写临时目录；没有修改系统临时目录设置或教学实现来绕过断言。独立审查另用 BFS 核对 12,199 组小图起终点组合，结果一致；用通用矩阵计算重算 Kalman 全部输出，与实现差异小于 `1e-14`。三张图与报告在新目录重生后逐字节一致。

本轮知识库使用 MkDocs 1.6.1 严格构建，并检查导航培训页的内部链接、锚点、图片、下载资产和源码行号。新增巡逻 ROS 多节点系统及两个接口模板尚未构建运行，TF/地图图示也不是 ROS 实测；这些项目继续按各页独立验收。

## 既有小系统的历史运行记录

下面保留的是已有的 2026-09 运行记录，蓝链接中的个人仓库、固定提交和运行编号用于追溯当时证据。本次培训文档扩写不把这些结果改成新的实测日期。复验后另记对应提交和日志，才能比较“同一功能在两个版本中是否都成立”。

2026-09-15，教学代码提交 `061bd082ca2c5417be7f09c069740dadf5c3fce8` 已在 GitHub Actions 的 Ubuntu 22.04 runner、`ros:humble-ros-base-jammy` 容器中完成构建与运行。[完整 CI 记录：34911735913](https://github.com/lkigai486/knowledge-base/actions/runs/34911735913)结论为 **success**，共 **45 项测试通过，0 项跳过**。

| 测试组 | 数量 | 实际结果 |
|---|---:|---|
| 核心积分与时间边界 | 9 | 通过 |
| CSV 重算与错误输入 | 3 | 通过 |
| 数据生成、读回、校验与地图 | 10 | 通过 |
| 两个 Debug 模型及命令行 | 10 | 通过 |
| 速度与参数边界 | 7 | 通过 |
| 真实 Humble 集成 | 6 | 通过，耗时 23.911 秒 |

6 项集成测试覆盖：Action 客户端成功/取消/拒绝退出码；Action 服务端反馈/取消/结果/忙时拒绝；错误 Topic 的真实端点及修复后通信；健康序号链；已提交 forward bag 的 `info` 与 `play --clock`；理想模型运动、TF、速度限制、无效输入清零与超时停止。静态 TF 还检查了迟到订阅。详情见[测试源文件](https://github.com/lkigai486/knowledge-base/blob/061bd082ca2c5417be7f09c069740dadf5c3fce8/training/tests/test_ros_smoke.py)。

Windows/Python 3.12.10 本地另通过上述 39 项非 ROS 测试、四种 CSV 轨迹重算和 `pip check`。本地缺少 ROS 的集成组标为跳过，未计入这 39 项；远程通过记录来自真实 Humble 运行。四组 bag 均完成离线 CDR 读回，真实 ROS 回放测试抽取其中的 forward 包，不声称四组都做了 ROS 回放。

知识库通过 MkDocs 1.6.1 严格构建；构建后检查 40 个 HTML 页面、内部链接/锚点以及 160 个固定 SHA 源码引用。复验代码与数据使用[独立 Humble CI 工作流][workflow]，后续修改以相应提交的新运行记录为准。

## 仍需队内完成

新人遇到这些缺口时，应交付已经能够证明的部分和清晰的缺失输入。例如完成地图坐标核对，却没有实测点云，可写“地图几何已检查，LIO 重跑等待指定 bag”，并附版本和期望消息清单。导师由此能补材料，也能避免把没有输入的实验误记成个人能力不合格。

- 真正 MID-360/IMU、关节、Point-LIO 与 small_gicp 的数据包、依赖和地图资产。
- 外部串口、固件、控制权、真实机器人 TF/外参和停车路径验证。
- 完整 Nav2/Gazebo 闭环与 T8/T10 的值守实车考核。

这些材料没有混入 synthetic-v1。教学包的 `training_lidar` 只是静态坐标边，PCD 只是地图几何示例；不能输入 Point-LIO 来替代真实逐点时间与 IMU 数据。

[ros-testing]: https://github.com/Navigator-Vision-Algorithm-Team/knowledge-base/blob/main/training/ROS_TESTING.md
[workflow]: https://github.com/Navigator-Vision-Algorithm-Team/knowledge-base/blob/main/.github/workflows/training.yml
