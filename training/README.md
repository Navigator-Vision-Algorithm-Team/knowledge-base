# 导航教学工作区

这是知识库配套的独立练习代码，目标是让新人从可运行的小系统开始，再读本队 `Navigation-2027`。代码使用 Python 3.10+；ROS 适配包面向 Ubuntu 22.04 / ROS2 Humble。所有数据均为解析生成的教学数据，无雷达/IMU 实测数据，无串口或电机驱动。

完整入门步骤见[教学工作区教程](../docs/navigation/training/workspace.md)，数据说明见[标准教学数据包](../docs/navigation/training/datasets.md)。

## 普通 Python 即可开始

在知识库仓库根目录运行；Windows 使用 `python`，Ubuntu 也可改用 `python3`：

```text
python -m unittest discover -s training/tests -p test_core.py -v
python -m unittest discover -s training/tests -p test_replay.py -v
python training/tools/replay_motion.py training/datasets/synthetic-v1/forward/ground_truth.csv
python -m unittest discover -s training/cases/tests -p "test_*.py" -v
```

重算工具的退出码：`0` 表示符合教学真值，`1` 表示出现误差，`2` 表示输入文件或时间顺序无效。对外部实测数据不要套用这里的 `1e-8` 理想模型误差阈值。

## 安装数据检查工具

建议在独立 Python 虚拟环境安装，ROS 运行仍使用已配置的 Humble 系统 Python：

```text
python -m pip install -r training/requirements-data.txt
python -m unittest discover -s training/tests -p test_datasets.py -v
python training/tools/generate_data.py --output training/output/my-synthetic-data
```

生成器拒绝覆盖已有目录；再次生成时换一个新目录。提交的数据可直接读取，不需要先生成一遍。

## ROS2 包

Ubuntu/Humble 编译、启动、Action 和集成测试命令见 [ROS_TESTING.md](ROS_TESTING.md)。`ros2_ws` 是独立工作区，不能把它和自己的同名 `nav_training` C++ 练习包同时作为 overlay；使用新终端，只 source 需要的一份。

```text
training/
├── ros2_ws/src/nav_training/  ament_python 包、launch 与限幅测试
├── tools/                    数据生成与离线轨迹重算
├── datasets/synthetic-v1/    四种运动 bag、真值、地图与 manifest
├── cases/                    两个可执行故障模型、输入与回归
├── tests/                    数学、重算、数据与 Humble 集成检查
└── LICENSE                   新增教学代码的 Apache-2.0 许可证
```

学习时先跑基线，再在自己的分支只改一项。正常与故障配置是练习材料；修复教学模型不代表已修复本队导航源码。实际串口、定位、Nav2 和实车资格仍按知识库 T3–T10 验收。

## 自动验证

[Navigation teaching kit 工作流](../.github/workflows/training.yml)在 Humble 容器中构建包、检查数据、执行故障回归和 ROS 集成测试。`NAV_TRAINING_REQUIRE_ROS=1` 使缺少 ROS 成为失败，避免 CI 跳过测试却显示成功。没有 ROS 的普通开发机只跳过 ROS 测试；数学与数据测试应正常执行。运行记录与限制见[验证状态](../docs/navigation/training/validation.md)。
