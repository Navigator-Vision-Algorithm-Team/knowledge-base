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

本轮记录会在配套代码与数据完成集成后更新。当前 Windows 主机已执行核心与重算测试；本机没有可用的 Humble/WSL/Docker。ROS 运行由[独立 Humble CI 工作流][workflow]验证，结果以具体运行记录为准。

## 仍需队内完成

- 真正 MID-360/IMU、关节、Point-LIO 与 small_gicp 的数据包、依赖和地图资产。
- 外部串口、固件、控制权、真实机器人 TF/外参和停车路径验证。
- 完整 Nav2/Gazebo 闭环与 T8/T10 的值守实车考核。

这些材料没有混入 synthetic-v1。教学包的 `training_lidar` 只是静态坐标边，PCD 只是地图几何示例；不能输入 Point-LIO 来替代真实逐点时间与 IMU 数据。

[ros-testing]: https://github.com/lkigai486/knowledge-base/blob/codex/navigation-onboarding-20260914/training/ROS_TESTING.md
[workflow]: https://github.com/lkigai486/knowledge-base/blob/codex/navigation-onboarding-20260914/.github/workflows/training.yml
