# 标准教学数据：从命令到轨迹、TF 与地图

本页配套[可下载的数据目录][data]包含四组实际 rosbag2 SQLite3/CDR 文件、解析真值 CSV、对齐的 YAML/PGM/PCD 地图和时间异常练习。整套 18 个文件共 385,599 bytes，可直接随知识库克隆；`manifest.json` 记录另外 17 个资产的 SHA-256、大小、单位、Topic、frame 和生成来源。

**全部数据由公式构造。** 这里没有 Livox 原始包、IMU、Point-LIO 输出、真实比赛场地或传感器噪声。它能训练读包、命令积分、时间戳、TF 和地图坐标；真实 LIO 重定位、传感器同步与 Nav2 实地闭环仍需要另行提供的真实数据。小地图的 PCD 只是占据格中心点，不能作为雷达原始输入。

先完成[教学工作区](workspace.md)的获取与首次运行。下面所有相对路径均以克隆后的知识库根目录为起点。

## 1. 四组数据的共同约定

每组为 5 秒、10 Hz，含起点和终点共 51 个样本。时间从 `100000000000 ns` 到 `105000000000 ns`，是任意仿真时钟起点，不是 UTC 采集时间。前 50 个采样点给定恒定命令，第 51 点在第 5 秒写入零命令；位姿已经完成前 5 秒的运动。

| 目录 | 0 ≤ t < 5 s 的 `(vx,vy,wz)` | 5 秒终点 `(x,y,yaw)` |
|---|---|---|
| `stationary` | `(0,0,0)` | `(0,0,0)` |
| `forward` | `(0.2,0,0)` | `(1,0,0)` |
| `lateral` | `(0,0.1,0)` | `(0,0.5,0)` |
| `rotation` | `(0,0,0.2)` | `(0,0,1)` |

位置单位 m，线速度 m/s，角度 rad，角速度 rad/s。右手系：机体 +x 向前、+y 向左、+z 向上，正 yaw 从上方看逆时针。四组分别做平移或旋转，不包含边走边转。真值直接用 `x=vx*t, y=vy*t, yaw=wz*t` 计算，与教学模型的积分实现独立。

每组的 `ground_truth.csv` 包含 `stamp_ns, elapsed_s, x_m, y_m, yaw_rad, vx_m_s, vy_m_s, wz_rad_s`。`bag/` 里有 `metadata.yaml` 和 `bag.db3`；每个 bag 正好 154 条消息：

| Topic | 标准 ROS2 类型 | 条数 | 语义 |
|---|---|---:|---|
| `/nav_training/cmd_vel` | `geometry_msgs/msg/Twist` | 51 | 机体坐标下速度；Twist 本身无 header，时间来自 bag 记录 |
| `/nav_training/odom` | `nav_msgs/msg/Odometry` | 51 | 解析真值，header 为 `training_odom`，child 为 `training_base` |
| `/nav_training/tf` | `tf2_msgs/msg/TFMessage` | 51 | 动态边 `training_odom → training_base`，与 odom 同时同位姿 |
| `/nav_training/tf_static` | `tf2_msgs/msg/TFMessage` | 1 | 静态边 `training_base → training_lidar`，平移 `(0.2,0,0.1)`，无旋转 |

所有连接为 reliable；前三种为 volatile，静态 TF 为 transient_local、depth 1。带 header 的消息，其 stamp 等于 bag 记录时间。Odometry 的 covariance 是全零的合成占位值，不能据此估计真实传感器精度或调融合参数。

## 2. 先做不依赖 ROS 的精确重算

此命令使用已提交 CSV 和教学核心，无须安装下面的制包依赖：

```text
python training/tools/replay_motion.py training/datasets/synthetic-v1/forward/ground_truth.csv
```

它按时间顺序将速度交给模型，逐点比较模型位置与解析真值，默认误差门槛为 `1e-8`；退出码 0 表示比较通过。2026-09-14 在 Windows/Python 3.12.10 实际运行的前进结果节选：

```json
{
  "samples": 51,
  "duration_s": 5.0,
  "predicted_final": {"x": 0.9999999999999999, "y": 0.0, "yaw": 0.0},
  "max_position_error_m": 2.220446049250313e-16,
  "max_yaw_error_rad": 0.0,
  "passed": true
}
```

同次运行中，静止误差为 0，侧移最大位置误差 `1.11e-16 m`，旋转最大角误差 `2.22e-16 rad`，四组均通过。末尾浮点小数差异属于计算舍入；重新生成或修改公式后，应重新运行比较，而不是手动改真值迎合输出。

## 3. 直接回放 bag 内真值

本节需要 Ubuntu 22.04/ROS2 Humble 和 `ros-humble-rosbag2`，环境与构建见[工作区页](workspace.md)。最新真实 ROS 验证结果统一记录在[验证状态](validation.md)；本页的 Python 读包结果本身不证明 DDS 或 RViz 已运行。

在所有相关终端统一 source Humble，并设置相同空闲 domain。以下 87 是示例；练习仅在当前机器通信。

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=87
export ROS_LOCALHOST_ONLY=1
ros2 bag info training/datasets/synthetic-v1/forward/bag
```

用上面的表核对四种 Topic、154 条消息和 5 秒 duration。先启动观察终端，再启动回放，防止错过开头。观察终端可以运行：

```bash
ros2 topic echo /nav_training/odom
```

另一个观察终端检查完整 TF 链；两个 TF Topic 需要显式 remap：

```bash
ros2 run tf2_ros tf2_echo training_odom training_lidar --ros-args \
  -p use_sim_time:=true \
  -r /tf:=/nav_training/tf -r /tf_static:=/nav_training/tf_static
```

回放终端执行下面的 Topic 白名单，只发布 bag 中的 odom/TF 真值和 `/clock`。本次观察时应结束此前的 `healthy.launch.py` 或 `ideal_model` 进程，使动态边只有 bag 一个发布来源：

```bash
ros2 bag play training/datasets/synthetic-v1/forward/bag \
  --clock 100 --delay 2 \
  --topics /nav_training/odom /nav_training/tf /nav_training/tf_static
```

预期前进末点 `training_base` 的 x 为 1 m，`training_lidar` 的 x 为 1.2 m、z 为 0.1 m。不要把雷达原点当成底盘原点。静态 TF 只写一次，late-join 依赖 transient_local 和仍存活的发布者；bag 播放进程结束后，新启动的观察器可能收不到静态边，应先启动观察器再重新播放。

如用 RViz，同样给 `/tf`、`/tf_static` 做上述 remap，启用 `use_sim_time`，Fixed Frame 设为 `training_odom`。本 bag 没有地图 Topic 或雷达点云 Topic。

## 4. 只回放命令，让模型重新生成 odom/TF

重新打开两个终端，source 已构建的教学工作区，使用与上一节相同的 domain。模型终端从一个新模型进程开始：

```bash
source /opt/ros/humble/setup.bash
source training/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=87
export ROS_LOCALHOST_ONLY=1
ros2 run nav_training ideal_model --ros-args -p use_sim_time:=true
```

播放终端也 source Humble 并设置相同 domain，然后执行：

```bash
ros2 bag play training/datasets/synthetic-v1/forward/bag \
  --clock 100 --delay 2 --topics /nav_training/cmd_vel
```

本次 `/nav_training/odom` 和两类 TF 由教学模型发布；bag 只提供速度和 `/clock`。用 `ros2 topic info /nav_training/odom --verbose` 和 TF Topic 的同类命令确认发布者数量。每次换场景重启模型，保证从零位姿开始。

这里的 Twist 没有时间头，模型使用回调时刻的 ROS 时间；DDS 发现、消息调度和 `/clock` 频率会影响重算结果。观察“前进约 1 m、末速度归零”后，记录实际误差。严格逐样本终点比较使用第 2 节的 CSV 重算，不将现场回调时序误差解释为解析公式错误。也不要把包含旧真值 odom/TF 的整包同时送进已运行模型，否则会混入两个发布来源。

## 5. 地图三件套如何对齐

`map/teaching_map.yaml` 指向同目录的 `teaching_map.pgm`，分辨率 0.25 m/cell，20×16 格，原点 `[-1,-1,0]`；几何范围为 x ∈ [-1,4]、y ∈ [-1,3]。图像 P2 ASCII PGM 的第一行在北侧，0 为占据，254 为空闲。地图有边界墙和一段内部障碍，共 75 个占据格。

`teaching_map.pcd` 为 ASCII PCD，每个占据格恰好一个 z=0 的中心点，同样在 `training_odom` 坐标系。YAML 本身不携带 ROS frame；若自行加载 map_server，应显式设置 `frame_id=training_odom`。

对图像从零计数的 `(row,col)`，点云坐标是：

```text
x = -1 + (col + 0.5) * 0.25
y = -1 + (15 - row + 0.5) * 0.25
z = 0
```

例如西南角占据格中心为 `(-0.875,-0.875,0)`，东北角中心为 `(3.875,2.875,0)`。练习时先手算这两个点，再检查像素行方向；漏掉 y 翻转或半格偏移，会让图像和点云错位。本地图可用于坐标读取练习，未经过 Nav2 地图质量或真实场地验收。

## 6. 时间异常练习

`time_anomalies/timestamps.csv` 按到达顺序存放 6 个纳秒时间戳，`expected.json` 给出零起点行号和判定规则。相邻差分应为：

```text
100000000, 0, -50000000, 400000000, 100000000
```

索引 2 为重复、3 为回跳、4 为大间隔；此练习把超过 200 ms 定义为 gap。先计算差分并标记异常，再讨论排序会丢失什么证据。该文件不是运动真值 CSV，也不另造乱序 bag：bag 的存储时间排序会混淆“消息到达顺序”这个练习目标。

## 7. 重新制包与校验

使用 Python 3.10+，把制包依赖装进独立虚拟环境。Linux/macOS 示例：

```bash
python3 -m venv .venv-data
source .venv-data/bin/activate
python -m pip install -r training/requirements-data.txt
python -m pip check
python training/tools/generate_data.py --output training/output/synthetic-v1-new
python -m unittest discover -s training/tests -p test_datasets.py -v
```

Windows 可用 `py -3 -m venv .venv-data`，随后用 `.venv-data\Scripts\python.exe` 代替 `python` 执行相同命令。`training/output/synthetic-v1-new` 必须尚不存在；生成器拒绝覆盖已有目录，包括空目录。中断时保留部分结果以便检查，下次请选新的输出路径。测试在临时目录制包，不改提交的基线。

本次实际环境为 Python 3.12.10、pip 25.0.1、SQLite 3.49.1、rosbags 0.10.11；其余依赖在 `requirements-data.txt` 固定。生成器输出：

```json
{"asset_bytes": 379468, "bag_messages": 616, "dataset_id": "synthetic-v1", "hashed_assets": 17, "scenarios": 4}
```

实际测试结果：`Ran 10 tests ... OK`，`pip check` 返回 `No broken requirements found.`。测试通过 AnyReader 独立打开新生成的 bag，反序列化 CDR，核对消息类型/数量、时间、速度、终点、四元数和静态 QoS；另做 SQLite integrity check、PGM/PCD 格中心比对、manifest 校验、覆盖保护与连续两次生成的字节一致性。

所有文本资产明确保存 LF，仓库的 `.gitattributes` 保留数据原始字节以防换行转换破坏 SHA-256。字节一致性是在相同依赖环境的两次生成中验证；跨 SQLite/依赖版本重新制包时，应优先核对消息语义，并对新产物重新计算 manifest，不能假定所有数据库文件字节都相同。

制包显式选择 rosbag2 metadata v8。上游 [Humble metadata 解码器][metadata] 把 `offered_qos_profiles` 读成字符串；[rosbags 的制包 API][rosbags]在 v8 使用这种表示，不能直接换成 v9 的序列表示。Humble 的 [SQLite 读取实现][sqlite]按已知列取消息，制包文件的额外类型哈希列不会改变该查询。实际 Humble 的 `ros2 bag info/play` 是否通过，仍以[运行验证记录](validation.md)为准。

## 8. 学生与导师验收

学生提交四组终点计算、一次 CSV 重算日志、Topic/frame 表、一张地图格到点云坐标的手算说明，以及时间异常的差分表。ROS 条件具备时，再提交一次只回放真值和一次模型重算的节点/发布者证据，并解释为何两次命令的白名单不同。

导师先用 manifest 检查数据是否被改动，再抽查旋转最后一个四元数 `z=sin(0.5), w=cos(0.5)`、侧移终点 0.5 m、最后零命令，以及 `training_base→training_lidar` 外参。把 `ground_truth.csv` 当实测里程计、把 PCD 当 Livox 原始扫描，或仅因 bag 能打开就宣称 Point-LIO 可跑，均不算通过此项理解检查。

[data]: https://github.com/lkigai486/knowledge-base/tree/codex/navigation-onboarding-20260914/training/datasets/synthetic-v1
[rosbags]: https://ternaris.gitlab.io/rosbags/topics/rosbag2.html
[metadata]: https://github.com/ros2/rosbag2/blob/humble/rosbag2_storage/src/rosbag2_storage/metadata_io.cpp
[sqlite]: https://github.com/ros2/rosbag2/blob/humble/rosbag2_storage_default_plugins/src/rosbag2_storage_default_plugins/sqlite/sqlite_storage.cpp
