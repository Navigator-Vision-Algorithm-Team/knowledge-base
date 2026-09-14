# Debug、实车调试与比赛流程

Debug 从 S1 开始。实车按 T8 的前置资料与无驱动验收、负责人确认停止链路、低速值守运动考核三个步骤推进，全部通过后才取得实车调试资格。目标是先判断故障层级、获取证据、做最小修正、恢复并回归。以下命令为 Humble/Bash 观察示例；命名空间按实际运行值修改。当前主机未接 ROS 和机器人，本页不是实车验收记录。

## 1. “机器人不动”按依赖检查

先确认应该运动以及底盘允许运动，再分层。安全状态不明时先停止，不继续发送试探性命令。

| 层级/现象 | 证据 | 下一步判断 |
|---|---|---|
| 无节点/找不到包 | 启动日志、`ros2 pkg prefix`、`ros2 node list` | 环境/overlay/launch/外部依赖；先读第一条错误 |
| 节点在但数据不通 | `ros2 node info`、`topic list -t`、`topic info --verbose` | namespace、消息类型、QoS、ROS domain/网络发现 |
| TF/定位失效 | TF 图、指定时间查询、stamp、传感器数据、配准日志 | 断链、错时、外参、输入中断、地图不匹配；不靠反复 initialpose 掩盖 |
| Goal 没进系统 | Action server、目标接受/反馈/result/cancel | 目标 frame、namespace、server 状态；发送成功不等于执行成功 |
| 没有规划路径 | planner lifecycle、请求结果、起终点、global costmap | 起点占据、unknown、无通路、TF、规划超时 |
| 有路径无跟踪输出 | controller lifecycle、FollowPath 结果、local costmap、progress/goal checker | 跟踪条件或控制失败；不是先换 Planner |
| 有上游速度无最终速度 | 三段速度 Topic、fake frame/odom/local_plan、日志 | remap、转换条件、同步输入、组件分支 |
| 最终速度存在但底盘不执行 | 最终订阅者、串口连接/接收统计、驱动使能、固件状态 | 软件命令/协议/电控边界；交给对应负责人共同验证 |
| 取消后仍运动 | 最终速度、cmd_spin、自旋偏置、缓存、串口输出/固件看门狗 | 不把取消 Action 或上游零命令等同物理急停 |

出现 CPU/内存/磁盘压力，记录进程级占用、队列和日志时间，再判断性能瓶颈。`top`/`htop`、`df -h`、`free -h` 是基础；gdb、core dump、profiling 在明确崩溃/热点后使用。

## 2. 本队只读诊断卡

```bash
export ROBOT_NS=/red_standard_robot1
ros2 node list
ros2 component list
ros2 node info "$ROBOT_NS/fake_vel_transform"
ros2 lifecycle get "$ROBOT_NS/planner_server"
ros2 lifecycle get "$ROBOT_NS/controller_server"
ros2 action list -t
ros2 action info "$ROBOT_NS/navigate_to_pose"
ros2 topic info "$ROBOT_NS/cmd_vel_controller" --verbose
ros2 topic info "$ROBOT_NS/cmd_vel_nav2_result" --verbose
ros2 topic info "$ROBOT_NS/cmd_vel" --verbose
ros2 param get "$ROBOT_NS/controller_server" use_sim_time
ros2 param dump "$ROBOT_NS/controller_server"
ros2 param dump "$ROBOT_NS/fake_vel_transform"
```

如果节点名字不同，用 list 结果替换；普通节点不一定支持 lifecycle。`lifecycle get` 是观察，不能为了消除报错就手动激活所有节点。有效参数要同 launch 参数、YAML 来源和 commit 一起记录。

在 RViz 同时看 TF、地图、注册点云、terrain_map、global/local Costmap、规划路径和机器人足迹。遇到错位，先验证 Fixed Frame 和时间；不要只凭点云“看起来像”判断定位正确。

## 3. 将真实风险转成隔离故障题

| 题目 | 实验环境和注入方式 | 必须观察/恢复 |
|---|---|---|
| Namespace 错误 | 教学节点或无驱动 launch 修改一个 remap | 发布/订阅完整名，恢复该 remap 后重试 |
| TF 缺边 vs 错时 | 缺边使用从未发布过的新教学 frame；错时用指定消息时刻查询；停发另作为数据陈旧题 | 区分不存在、过期和已缓存的 latest；恢复唯一发布者并重新查询 |
| QoS 不兼容 | 教学 pub/sub 改可靠性 | 端点 offered/requested 区别与修复后计数 |
| 时钟错误 | 隔离回放用 sim time 但不给 clock | 参数与 clock 来源，恢复统一时间后重启有状态节点 |
| 地图/生命周期错误 | 使用配置副本，把地图指到不存在路径或保持未激活 | 首条错误、map_server/planner 状态，恢复正确资产/生命周期 |
| 速度缓存/自旋 | 输出只接观察器，先非零再零/断流/取消 | 三段速度、cmd_spin、同步输入与最终输出；复现后方能设计修复 |

故障题不可在比赛生产运行配置上制造；独立 ROS domain 之外，还要确保没有实车串口/驱动/跨域桥接。原始 bag 的速度消息不得回放到执行端。具体缓存/自旋证据见[源码审查](../system/nav2-and-control-evidence.md)。

## 4. 实车运动前检查单

负责人和新人共同填写[基线登记](../maintenance/README.md)。必须明确：

1. 哪台机器人、底盘/雷达/云台安装、软件 commit、依赖版本、地图与外参；实际串口包来自哪里。
2. 硬件急停、驱动使能、人工接管方式；谁持有急停、谁观察机器人、谁记录。
3. 当前运动命令的唯一控制权，手柄/导航/串口/决策是否争抢；最终 Topic 的发布者和消费者是否符合登记。
4. 硬件负责人事先确认低速上限、空场边界、最大允许停车时间/距离；文档不把仓库默认速度当作已许可值。
5. 雷达、IMU、关节与 TF 数据正常，定位初始化与地图对齐，足迹正确，导航节点生命周期正常。
6. 最终停止链已经完成无驱动台架观察和受控验证，所有输出（包括自旋）可归零/禁止执行；初始旋转偏置与旧缓存不会重新驱动车辆。

停止链没通过，先完成问题复现与修复，不能以“速度很低”继续运动测试。

## 5. 分步上车顺序

| 步骤 | 操作 | 通过证据 |
|---|---|---|
| A 无驱动观察 | 驱动不使能，运行传感器/定位与接口观察；确认最终指令含义 | 三段 Topic、TF、串口接收日志，正确的坐标和单位 |
| B 停止路径 | 按设备负责人安排验证正常停止、取消、输入断流、人工接管及硬件急停 | 最终输出、底盘状态和停车时间/距离记录；不是只看上游 Twist |
| C 单自由度低速 | 有人值守，分别前进、侧移、旋转；每次后停稳 | 正方向、限速、状态反馈和停止全部正确 |
| D 简单导航 | 固定开阔场地点对点→转弯→窄通道，逐步增加难度 | 目标结果、跟踪/定位误差与所有失败记录 |
| E 障碍/恢复 | 在已验收场景放置静态障碍，再引入可控移动障碍；先停再改变配置 | 清除/重规划/失败恢复可解释，保持安全距离 |
| F 比赛演练 | 冻结配置后执行任务序列、恢复和交接 | [T10](../assignments/README.md)完整报告 |

需要重新摆放机器人时先停止任务、禁用驱动并确认静止，再由值守人员操作。定位失效测试先在回放/仿真完成；实车不通过撞击、遮挡高速运动雷达或运行中搬车制造故障。

## 6. 比赛调试要能交接

比赛前冻结一套可回退版本，包含地图校验值、外参、启动命令、有效参数、接口依赖和测试报告。检查开机耗时、初始化、重启、Goal 切换、运行资源及日志容量；不要临赛切换算法或更新全部依赖。

比赛决策的边界是 Goal 输入、反馈、结果、取消、失败处理和控制权。当前 BT XML 主要负责导航重规划与恢复，不等于完整比赛状态机。若实际系统已有比赛状态节点，维护者需补充精确来源和接口，再提升为必学内容。

出现故障：先确保停止/接管，记时间与现象，保存关键日志和短 bag，再按表定位；只改变一个已证实相关的因素。恢复后必须重做原任务和停止检查。不能将“重启后能跑”当作已找到根因，记录中分开写临时恢复和根因修复。

毕业标准见 [T8–T10](../assignments/README.md)。独立诊断不取消实车值守要求。
