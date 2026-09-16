# Debug 案例 1：能看到 Topic，订阅者却没有收到

这是一道可复现的教学故障题，适合 S1/S2，建议 45–60 分钟。Python 事件路由模型和配套 Humble 节点链路都已执行，结果见[验证记录](../training/validation.md)。下文的固定 5 条消息与 JSON 日志来自 Python 模型，ROS 测试另以真实端点和实际接收判断；没有队内事故记录或 DDS 抓包。准备方式见[教学工作区](../training/workspace.md)。

## 学生任务：先记录证据，再改配置

发布者每次发送整数 1–5。故障与修复模式中，发布者全名都为 `/nav_training/sequence`，但故障模式接收数为零。请先运行 broken，查看完整输入与两端解析后的名称，提出至少三个可能解释，随后只改变一个输入配置。

提交一页记录：运行命令及退出码、原始输入、发送/接收计数、首尾事件、假设与排除证据、最小改动、修复后的同输入回归、改变 namespace 后的回归、恢复故障的步骤。不要只交“把斜杠删掉了”。

从 `knowledge-base` 根目录运行，Windows 用 `python`；Ubuntu 若只有 `python3`，替换命令首词即可。每次使用新的输出目录。

```bash
python training/cases/run_case.py topic-mismatch --mode broken --input training/cases/inputs/topic-mismatch.json --out-dir training/cases/runs/topic-broken-1 --check-contract
```

broken 的验收退出码应为 **1**；`events.jsonl` 与 `report.json` 仍会写出。程序没有调用网络或 ROS，不能把这些文件贴成 `ros2 topic echo` 的输出。

## 导师解答：固定输入与已生成的证据

完整输入 `training/cases/inputs/topic-mismatch.json`：

```json
{
  "namespace": "/nav_training",
  "publisher": "sequence",
  "subscriber_broken": "/sequence",
  "subscriber_fixed": "sequence",
  "sequence": [1, 2, 3, 4, 5]
}
```

该文件原始字节 SHA256 为 `8fba88fa72aac18568b43dabbe4562a21fa8ef6664225a0bbb8ce3381d357600`。改换换行或内容会改变输入校验值，这是正常现象。

2026-09-14 在 Windows/Python 3.12.10 运行本脚本生成了 `training/cases/evidence/topic-mismatch/{broken,fixed}/`。以下是文件中的实际结果：

| 指标 | broken | fixed |
|---|---|---|
| publisher | `/nav_training/sequence` | `/nav_training/sequence` |
| subscriber | `/sequence` | `/nav_training/sequence` |
| sent / received | 5 / 0 | 5 / 5 |
| 收到的序列 | 空 | 1, 2, 3, 4, 5 |
| contract_passed / 验收退出码 | false / 1 | true / 0 |

broken 的第一条 `events.jsonl` 原文为：

```json
{"delivered": false, "index": 0, "publisher": "/nav_training/sequence", "sequence": 1, "subscriber": "/sequence"}
```

`run_case.py::resolve_topic` 保留普通绝对名，将普通相对名拼接到 namespace；`run_topic` 只有在两个全名相等时投递事件。因此这里的 `delivered` 是程序执行出来的模型结果，不是操作系统或 DDS 返回的投递状态。模型不支持完整 ROS 名称展开、remap 或私有名 `~`。

## 假设、排除与源码联系

| 假设 | 此次实际证据 | 能得出的结论 |
|---|---|---|
| 发布者没有发送 | 同一个发布全名下有 5 条带序号事件 | 在本模型中排除未发送 |
| 订阅者解析到其他名称 | 两端全名分别是 `/nav_training/sequence` 和 `/sequence` | 与模型唯一投递条件直接冲突，是本题根因 |
| 数据类型或 QoS 不兼容 | 本模型不实现类型协商和 QoS | 不属于本模型的原因；真实 ROS 中仍须另查 |
| domain、发现或网络故障 | 本模型没有网络和 DDS | 不能从本结果排除真实系统的网络问题 |

固定源版本为 [Navigation-2027@183a410](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9)，完整 SHA `183a4109b0de2030bb8970a54654937c8b039ba9`。本题的 `sequence` 是新建教学接口，联系的是源码中真实存在的名称差异：

- [导航 reality launch](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_reality_launch.py#L50-L54) 默认 namespace 为 `red_standard_robot1`。
- [C++ 串口订阅](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp#L105-L108)使用相对 `cmd_vel`，[其 launch](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/launch/standard_robot_pp_ros2.launch.py#L74-L78) 的 namespace 默认空。
- [根目录 Python 串口脚本](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/serial_node.py#L50-L56)则订阅绝对 `/red_standard_robot1/cmd_vel`。不能因为代码中都含 `cmd_vel` 就当作连接同一端点。

这些是只读源码事实，不能推断两份串口实现已在同一部署中同时运行。完整背景见[接口证据页](../system/nav2-and-control-evidence.md)。本实验没有启动其中任一串口实现。

## 最小修复、回归与回滚

修复是改变接收端配置，让其跟随教学 namespace：

```diff
- subscriber_topic = "/sequence"
+ subscriber_topic = "sequence"
```

本包 `--mode` 选择 JSON 中对应的订阅名；修复只改变接收端，消息列表与发送端不变。

```bash
python training/cases/run_case.py topic-mismatch --mode fixed --input training/cases/inputs/topic-mismatch.json --out-dir training/cases/runs/topic-fixed-1 --check-contract
python -m unittest discover -s training/cases -p 'test_*.py' -v
```

fixed 退出 0、接收 5/5；共享案例套件共 10 个测试，其中本题覆盖相同发布者在两模式的计数，以及 namespace 改成 `/second_team`、输入 `[7,8]` 时 fixed 仍接收 2、broken 仍为 0。导师可以要求学生把固定输入复制到自用文件，换 namespace 后通过 `--input` 再跑一次。

恢复故障时不用修改源码，重新以 `--mode broken` 和新目录 `training/cases/runs/topic-rollback-1` 运行原命令，应再次得到 0/5、退出 1。恢复正常再使用 fixed。输出目录已存在时返回 2，保留旧证据；不要把目录重用错误当作故障复现成功。

## ROS2 Humble 复验：端点检查与真实通信

在已按[工作区说明](../training/workspace.md)构建并 source 的 Ubuntu 22.04/Humble 教学环境，使用 `nav_training` 包。远程 CI 已用 rclpy 检查真实发布/订阅端点，确认故障模式无接收、参数修复后恢复递增消息；以下 CLI 步骤供学生手动观察并记录自己的输出，不是 CI 终端日志的逐字抄录。两终端应采用相同、已确认空闲的教学 domain，仅启动教学节点。

终端 A：

```bash
ros2 launch nav_training bad_topic.launch.py
```

终端 B：

```bash
ros2 node info /nav_training/sequence_source
ros2 node info /nav_training/sequence_sink
ros2 topic info /nav_training/sequence --verbose
ros2 topic info /sequence --verbose
ros2 topic echo /nav_training/sequence --once
timeout 5 ros2 topic echo /nav_training/received --once
```

教学 publisher 发布 `std_msgs/msg/Int64`，sink 把真正收到的整数转发到 `/nav_training/received`。需实际记录 source/sink 的全名、类型和 QoS，以及两个 echo 的结果和退出码；超时通常返回 124，单次超时本身不能排除发现延迟。

终端 A 按 Ctrl+C 停止本次 launch，再启动相同入口并只修复 sink 参数：

```bash
ros2 launch nav_training bad_topic.launch.py sink_topic:=sequence
```

重复终端 B 的端点检查，并采集 `/nav_training/received` 的多条递增整数。source 持续发布，ROS 计数受订阅建立时间影响，不以“恰好 5 条”验收；5/5 仅属于固定 Python 输入。ROS 回滚是停止本次 launch 后重新运行未加覆盖参数的 bad_topic 入口。保存自己的命令、端点与接收证据，并记录对应提交和运行环境。
