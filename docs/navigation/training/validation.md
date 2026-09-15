# 教学包验证状态与复验方法

本页区分配套教学代码、标准合成数据和本队实车系统。当前新增内容位于知识库 `training/`，不修改 Navigation-2027。合成轨迹、示例故障和离线数值结果均不代表实车采集或导航性能。

## 验证范围

| 对象 | 验证方法 | 能证明什么 |
|---|---|---|
| 理想全向模型 | 解析直行/侧移/圆弧、无效数值、超时、回跳单元测试 | 教学积分与时间边界满足定义 |
| CSV 重算入口 | 用命令重算轨迹，对比独立解析真值；错误输入和错误真值反例 | 入口不会把真值直接抄成预测 |
| 标准合成数据 | 重新生成、逐文件 SHA256、SQLite 完整性、CDR 反序列化、计数/时间/TF/地图几何检查 | 发布的数据可读、来源与几何一致、内容可复现 |
| 两个 Debug 模型 | broken/fixed 模式与命令行退出码、正常输入和边界回归 | 受控教学模型能复现并修复定义的故障 |
| Humble 节点与 bag | 在实际 ROS 环境构建、启动、通信、TF、取消和 bag 回放 | 配套小系统在该测试环境运行；不扩展为本队导航验收 |
| 知识库 | MkDocs strict、内部链接和固定源码链接检查 | 教学入口与引用可导航 |

## 本地复验

在仓库根目录、已安装 `training/requirements-data.txt` 的 Python 环境运行：

```text
python -m unittest discover -s training/tests -p test_core.py -v
python -m unittest discover -s training/tests -p test_replay.py -v
python -m unittest discover -s training/tests -p test_datasets.py -v
python -m unittest discover -s training/cases/tests -p "test_*.py" -v
python -m unittest discover -s training/ros2_ws/src/nav_training/test -p "test_*.py" -v
```

完整 Humble 验证按[ROS 测试说明][ros-testing]构建并 source 后运行：

```bash
export ROS_DOMAIN_ID=87
export ROS_LOCALHOST_ONLY=1
export NAV_TRAINING_REQUIRE_ROS=1
python3 -m unittest discover -s training/tests -p test_ros_smoke.py -v
```

缺少 ROS 时普通开发机可跳过 ROS 用例；设置 `NAV_TRAINING_REQUIRE_ROS=1` 后缺依赖必须失败。不能把 `SKIP` 计为实际运行通过。

## 实际运行记录

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

- 真正 MID-360/IMU、关节、Point-LIO 与 small_gicp 的数据包、依赖和地图资产。
- 外部串口、固件、控制权、真实机器人 TF/外参和停车路径验证。
- 完整 Nav2/Gazebo 闭环与 T8/T10 的值守实车考核。

这些材料没有混入 synthetic-v1。教学包的 `training_lidar` 只是静态坐标边，PCD 只是地图几何示例；不能输入 Point-LIO 来替代真实逐点时间与 IMU 数据。

[ros-testing]: https://github.com/lkigai486/knowledge-base/blob/codex/navigation-onboarding-20260914/training/ROS_TESTING.md
[workflow]: https://github.com/lkigai486/knowledge-base/blob/codex/navigation-onboarding-20260914/.github/workflows/training.yml
