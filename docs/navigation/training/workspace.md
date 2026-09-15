# 教学工作区：从第一次运行到修改代码

本课提供[可下载的教学代码][kit]，对应 T0–T2、T7 和 T9 的练习。它是独立小系统：计数发布订阅、可配置 launch、理想全向运动、Odometry/TF、目标反馈与取消。主代码位于知识库 `training/`，比赛导航仓库保持原样。

**先确认使用哪条路径**：普通 Windows/macOS/Linux + Python 3.10 可完成数学、数据重算和两个 Debug 模型；Ubuntu 22.04 + ROS2 Humble 可进一步完成真实节点、DDS、TF 和 Action。最新实际验证记录见[验证状态](validation.md)，不是仅凭环境名字判定已跑通。

## 1. 获取与首次运行（约 30 分钟）

若当前 PR 尚未合入，先克隆知识库 PR 所在分支。以下命令在准备存放练习的目录执行，`navigation-training-kb` 应是尚不存在的新目录；已经克隆者直接进入对应仓库即可：

```text
git clone --branch codex/navigation-onboarding-20260914 --single-branch https://github.com/lkigai486/knowledge-base.git navigation-training-kb
cd navigation-training-kb
git rev-parse HEAD
```

合入后可以从组织仓库 main 获取。后续命令均以知识库根目录为起点；完整源文件见[配套目录][kit]，保留当前提交 SHA 作为练习版本。Ubuntu 若没有 `python` 命令，使用 `python3`。

```text
python --version
python -m unittest discover -s training/tests -p test_core.py -v
python training/tools/replay_motion.py training/datasets/synthetic-v1/forward/ground_truth.csv
```

第一次只要求说明输出中的 `samples`、`predicted_final`、`max_position_error_m` 与 `passed`。前进数据 51 个样本，0.2 m/s 持续 5 秒，预期终点 `(1,0,0)`；最后一个指令为零。重算模型从速度算位置，真值只用于比较和初始位姿，不直接复制后续答案。

接着把路径里的 `forward` 改为 `lateral`、`rotation`、`stationary`。侧移终点为 `(0,0.5,0)`，旋转终点为 `(0,0,1 rad)`，静止保持原点。数据采样、单位和地图说明见[数据包页](datasets.md)。

## 2. Ubuntu/Humble 编译（约 30–60 分钟，不含安装）

先按[环境页](../onboarding/environment.md)准备 Humble。在**全新终端**操作，只 source Humble 和本教学工作区；如果以前创建过同名 `nav_training` C++ 包，不能叠加那份 install。配套 Python 节点用于尽早观察运行，原路线的 C++ 编程训练仍需完成。

```bash
source /opt/ros/humble/setup.bash
sudo apt install python3-colcon-common-extensions ros-humble-launch-ros \
  ros-humble-tf2-ros ros-humble-action-tutorials-interfaces ros-humble-rosbag2 \
  ros-humble-geometry-msgs ros-humble-nav-msgs ros-humble-std-msgs ros-humble-tf2-msgs
cd training/ros2_ws
colcon build --symlink-install --packages-select nav_training
source install/setup.bash
ros2 pkg prefix nav_training
ros2 pkg executables nav_training
```

最后两步应指向当前教学工作区，并列出配套可执行程序。只有在这个小包正常后，才继续讨论完整导航工程缺包、地图或硬件问题。包目录和入口说明见[ROS 测试说明][ros-testing]。

## 3. 观察小系统（T1，约 45 分钟）

每个训练终端设置同一个空闲 domain，并限制当前机器通信；下面的 87 是示例，组内有冲突时统一换号。教学 launch 不启动底盘，输出只进入教学模型和观察器。

```bash
export ROS_DOMAIN_ID=87
export ROS_LOCALHOST_ONLY=1
ros2 launch nav_training healthy.launch.py
```

在另一终端加载相同环境后，逐条检查：

```bash
ros2 node list
ros2 topic list -t
ros2 topic echo /nav_training/sequence --once
ros2 topic echo /nav_training/received --once
ros2 topic info /nav_training/sequence --verbose
ros2 topic echo /nav_training/odom --once
```

**你应看到的关系**：`sequence_source` 发布递增计数，`sequence_sink` 收到后发布到 `received`；`ideal_model` 在无速度输入时持续发布静止位姿。看见 Topic 名称不等于订阅链路正确，下一课会专门构造这种情况。

交一张实际接口表：节点名、Topic 全名、类型、发布/订阅方向、QoS、频率。记录实测结果；这里的结构描述不能代替自己的日志。

## 4. 给模型输入速度并检查 TF（T2，约 60 分钟）

以下命令只发到教学 Topic，`--times 20` 在 10 Hz 下发送有限次；停止发消息后模型按 0.5 秒教学超时规则停止积分。运动时间需按实际事件计算，不能把终端运行时间直接作为精确参考。

```bash
ros2 topic pub /nav_training/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' \
  --rate 10 --times 20
```

在另一终端检查模型输出和命名空间内 TF：

```bash
ros2 topic echo /nav_training/odom --once
ros2 run tf2_ros tf2_echo training_odom training_base --ros-args \
  -r /tf:=/nav_training/tf -r /tf_static:=/nav_training/tf_static
```

动态边为 `training_odom→training_base`；静态边为 `training_base→training_lidar`，平移 `(0.2,0,0.1) m`，无旋转。静态边只是坐标教学，没有模拟雷达测量。Odometry 与动态 TF 同次发布应共享 stamp 和位姿。

依次试前进、侧移、旋转，然后观察断流、零命令和无效输入的行为。默认平移模长上限 0.5 m/s、角速度上限 1 rad/s，仅约束教学模型。**这套限制不能作为机器人停车设计或实车许可速度。**

精确运动公式和超时边界使用[核心测试][core-test]验证，读 [core.py][core] 的 `integrate_body`、`set_command`、`step`：哪段时间使用旧指令、何时失效、时钟回跳后哪些状态保留？

## 5. 目标反馈与取消（T1 巩固，约 45 分钟）

启动配套 `fibonacci_server`，再用 `fibonacci_client` 的默认受控目标练习反馈和取消；确切参数与运行命令见[ROS 测试说明][ros-testing]。它是已有标准接口的教学任务，不会使模型运动。

观察目标接受、至少两次反馈、发起取消、取消响应和最终状态；再做自然完成与非法目标被拒绝。用目标 ID 串起日志，区分取消请求发送成功与最终 `CANCELED`。随后回到本队 NavigateToPose：取消导航 Action 还需检查哪些下游速度和底盘状态？

## 6. 从可运行基线开始做六个改动

在自己的练习分支修改，不更改知识库基线数据来迎合结果。每次按“基线→单项变化→观察→恢复”提交记录。

| 练习 | 具体改动 | 交付与检查 | 对应本队 |
|---|---|---|---|
| E1 参数 | 修改教学发布频率并重启；确认有效参数和 60 秒计数 | 两组频率、端点、命令和差异解释；T1 的 5/10 Hz 两组仍照常完成 | 参数声明、YAML/launch 传递 |
| E2 名字 | 跑 bad_topic 预设，再只修 sink_topic | [完整案例一](../debug-real/case-topic-mismatch.md)的证据与回归 | loam 输入参数、namespace/remap |
| E3 运动 | 在独立练习文件实现二维积分，与核心解析测试比较 | 前进/侧移/转弯至少各一个固定输入；解释自己用的离散或解析方法 | odometry 与 fake 速度旋转 |
| E4 时间 | 将真值 CSV 复制到 output，改一个 stamp 为重复或回跳 | 重算入口退出码 2；解释为什么拒绝这一数据，另查核心回跳测试 | 消息时间与 steady_clock 差分 |
| E5 取消 | 调整受控目标长度与取消时机 | 反馈、取消响应、终态；不以关闭进程代替取消 | NavigateToPose/手柄 Goal 契约 |
| E6 缓存 | 跑旧速度复发模型，再应用最小修复 | [完整案例二](../debug-real/case-stale-command.md)的破坏/修复/正常输入回归 | fake_vel_transform 的缓存路径 |

E3 的学生实现放个人仓库，例如 `student_integrate.py`；先写自己推导的预期，不直接把 `core.py` 的输出当唯一答案。参考实现可用于完成后对照。合格代码不要求结构相同，但接口、单位和边界行为必须能解释。

## 7. 从教学接口映射回本队

| 教学对象 | 回到哪里读 | 相同点与不同点 |
|---|---|---|
| sequence pub/sub | [loam_interface][loam] | 都有参数化输入与回调；真实节点处理点云和 TF，计数练习没有这些复杂度 |
| ideal_model odom/TF | [sensor_scan_generation][sensor] | 都需要一致的位姿/frame/stamp；教学是真值模型，本队来自 LIO 和外参转换 |
| body twist 与超时 | [fake_vel_transform][fake] | 可理解速度旋转、缓存和时间；本队自旋/同步策略不能用教学超时替代 |
| Action server/client | [Nav2 与控制链](../nav2/README.md) | 接受/反馈/取消/结果契约可迁移；Fibonacci 不包含导航或停车逻辑 |

最后按 [T0–T2](../assignments/README.md)提交代码与证据。通过教学工作区不等于通过真实数据定位、Nav2 闭环或实车准入；标准合成包支持的范围见[数据说明](datasets.md)。

[kit]: https://github.com/lkigai486/knowledge-base/tree/codex/navigation-onboarding-20260914/training
[ros-testing]: https://github.com/lkigai486/knowledge-base/blob/codex/navigation-onboarding-20260914/training/ROS_TESTING.md
[core]: https://github.com/lkigai486/knowledge-base/blob/codex/navigation-onboarding-20260914/training/ros2_ws/src/nav_training/nav_training/core.py
[core-test]: https://github.com/lkigai486/knowledge-base/blob/codex/navigation-onboarding-20260914/training/tests/test_core.py
[loam]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp
[sensor]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp
[fake]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp
