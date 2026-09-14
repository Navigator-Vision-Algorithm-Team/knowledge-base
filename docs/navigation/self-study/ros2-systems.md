# ROS 2 系统能力：从会运行到能解释故障

本页给对照 [ROS2/TF 基础训练](../ros2-tf/README.md)的新人成套自学材料，补足通信、并发、时间、状态管理和性能诊断。S1–S2 可先读相应单元的官方入门章节；单元完整实验和文末挑战用于巩固或专项选学，不要求把全部网站从头读完。

学习基线为 Ubuntu / ROS 2 Humble；本队代码固定在 `Navigation-2027@183a4109b0de2030bb8970a54654937c8b039ba9`。以下命令在独立 Linux 训练环境执行，练习节点使用 `/nav_training` 或 `/training`，不加载串口、电机或实车导航入口。

## 怎样安排与阅读

| 学习顺序 | 层级 | 建议组合 | 完整单元估计投入 |
| --- | --- | --- | --- |
| S1–S2 | 基础对应材料 | 1 Action、2 QoS、3 TF/时间、4 bag | 10–14 小时，可与 T1–T3 合并 |
| S4–S5 前后 | 基础概念 + 系统方向核心 | 5 Executor、6 生命周期/组件、7 行为树 | 完整实验 10–15 小时，按需选做 |
| 能复现问题后 | 进阶 | 8 GDB/Memcheck、9 perf、10 tracing | 8–13 小时 |

学时包含阅读、编译、故障注入和报告；已做过的基础练习可直接提交已有证据，不再叠加同等课时。下文“必学”指现有 T1–T7 对应的知识点，完整实验深度按方向选择；尤其 callback group 死锁、并行调度不作为所有新人基础准入题。专项建议每周额外 2–3 小时，文末挑战另计、任选一个先完成，进阶成果不能代替 T8 实车验收。

本页入口均可免费公开阅读，无需购买证书。2026-09-14 核验时 `docs.ros.org` 部分页面触发反爬，因此 ROS 教程优先链接官方 `ros2/ros2_documentation` 的 `humble` 分支原文；遇到 `literalinclude`，按给出的同分支源码链接读代码。

英文阅读采用四步：先看 Goal/Prerequisites → 对照代码找输入输出 → 精读本页指定小节 → 用中文写五句话解释实验。浏览器翻译只用于正文，保留 `callback group`、`requested/offered`、`stamp`、`halt`、`CANCELED` 等术语和报错原文，不翻译代码、包名或参数。

先记录 `ROS_DISTRO`、RMW、安装包/overlay 路径及工具版本；命令选项查本机 `--help`。Humble 分支也会维护更新，网页不等于本机已安装补丁版本；Foxy/Jazzy/Rolling 的签名、参数和默认值不能直接复制。

## 1. Action：目标接受、反馈、结果与取消

**层级/前置/额外学时：**必学；完成 C++ pub/sub、Service 和基础 Action 作业；3–4 小时。

**主材料：**[Humble C++ Action server/client][action]，精读 Tasks 2「Writing an action server」和 3「Writing an action client」；接口尚未建好时先做 [Creating an action][action-interface] 的接口生成步骤。

**代码抓手：**打开同章 [client.cpp][action-client] 与 [server.cpp][action-server]，找 goal response、feedback、result、`handle_cancel`、`is_canceling()`、`canceled(result)`。先跳过 Windows 可见性机制的原理，但保留示例编译所需文件。

**输入与输出：**用 Fibonacci order=20 发长任务；客户端保存 goal handle，在第二次反馈后只发一次异步取消；输出包含目标 UUID、取消请求/响应、最后反馈及最终 result 的日志。

**验收：**成功完成与主动取消各跑一次；取消请求被发送、服务端接受取消、最终 `ResultCode::CANCELED` 分别有证据。使用 steady clock 统计取消耗时，回调中不阻塞等待 future；关闭客户端不算取消。

**本队映射：**读[手柄目标/取消实现][team-joy]，对照 [Nav2 速度链](../nav2/README.md)说明取消发生在哪一层；Action 成功取消不证明最终 `cmd_vel` 持续为零，更不证明物理停车。

## 2. QoS：先证明兼容性，再改参数

**层级/前置/额外学时：**必学；能写带序号的发布订阅节点；2–3 小时。

**主材料：**[Humble About Quality of Service settings][qos]，只先读 QoS policies、QoS profiles、QoS compatibilities 中 reliability/durability 的两张表，再看 QoS events。

**读懂的边界：**发布端 offered 必须满足订阅端 requested；Best Effort 发布与 Reliable 订阅不兼容。先跳过 deadline/liveliness 的细节调参，但知道所有影响兼容性的策略均须满足。

**输入与输出：**用同一消息类型、同一 Topic 的两个小节点，做 reliability 四种组合；启动后确认图中两端存在，再计数 10 秒。每轮输出端点 QoS、发送/接收总数及序号缺口。

**验收：**四格表有预测和实测，不兼容格接收为零时仍能找到端点；兼容格收到消息。Reliable 不是任意负载下零丢失的保证，接收少于发送要继续查启动区间、历史深度和处理能力。

**本队映射：**对照 [loam_interface.cpp][team-loam] 的订阅/发布和 [fake_vel_transform.cpp][team-fake] 的输入；先查实际 `topic info --verbose`，不把所有传感器订阅统一改为 Reliable。

## 3. TF 与时钟：名字正确仍可能查不到

**层级/前置/额外学时：**必学；完成静态 TF、动态广播与里程计练习；3–4 小时。

**主材料：**[Humble Debugging tf2 problems][tf-debug]，依次做「Finding the tf2 request」「Checking the frames」「Checking the timestamp」；补读 [Clock and Time][clock] 的 ROS Time、System Time、Steady Time 和时间跳变说明。

**具体读法：**比较 `TimePointZero` 与指定查询时间；用 `tf2_echo`、`tf2_monitor`、`view_frames` 区分帧不存在与时间外推。先跳过分布式时钟同步算法；ROS 时间设计页帮助理解概念，C++ 签名仍以 Humble 为准。

**输入与输出：**在教学 TF 链中各注入一次错误 frame 和错误时间源；输出异常原文、请求时刻、最新 TF stamp、`use_sim_time`、`/clock` 与 TF 图。

**验收：**修 frame 只能解决名字错误，修时钟才能解释另一例；不能靠把所有查询改成最新时刻或增大 tolerance 掩盖根因。重放前重启教学节点，避免旧 TF 缓存干扰结论。

**本队映射：**读 [fake_vel_transform.cpp][team-fake] 的 wall timer、`rclcpp::Clock()` 与 TF stamp，并对照[证据页 R4](../system/nav2-and-control-evidence.md)；TF Topic 的 namespace 和 frame ID 是两层命名。

## 4. rosbag2：构造可重复输入

**层级/前置/额外学时：**必学；完成单元 2、3 和基础录包练习；2–3 小时。

**主材料：**[rosbag2 Humble README][bag] 只读 Recording data、Simulation time、Replaying data、Analyzing data；再读 [Overriding QoS Policies][bag-qos] 的 YAML 格式与 Example。

**版本提醒：**README 中安装示例仍出现 `CHOOSE_ROS_DISTRO=crystal`，不要照抄；使用现有 Humble 环境。先跳过 ROS1 bag 插件、压缩、存储调优、合并转换；回放控制服务是否可用查本机包和帮助。

**输入与输出：**录一份含教学序号、动态 TF、静态 TF 的小 bag；写 Topic 白名单、消息类型/数量、录制时钟和回放命令；停止原发布者后，用单一 `/clock` 源回放。

**验收：**另一名队员能按清单重放并收到数据；迟加入的 TF 观察工具能获得所需静态边。若需要 QoS override，报告修改前后端点证据，只给确有问题的 Topic 配置。

**本队映射：**按 [ROS2/TF 回放分类](../ros2-tf/README.md)区分系统观察与重跑算法；重跑 [loam_interface][team-loam] 等链路时避免回放旧输出和重复 TF。**bag 不响应新的速度命令，不能证明闭环跟踪或避障。**

## 5. Executor 与 Callback Group：为什么多线程仍卡住

**层级/前置/额外学时：**系统方向核心，全员了解调度与阻塞概念；会读 C++ lambda、future，完成单元 1；完整实验 3–5 小时。

**主材料：**先读 [Humble Executors][executors] 的 Overview/Types/Callback groups，再做 [Using Callback Groups][callback] 中 Basics、Avoiding deadlocks、Examples 的 C++ 分支。

**只抓核心：**默认互斥组、分组、future 完成回调与 executor 线程之间的关系；示例 C++ 用等待 future 模拟同步调用。先跳过自定义 executor、WaitSet 和实时调度改造。

**输入与输出：**运行教材的服务/定时器案例，比较「同一互斥组」「两个互斥组」和「异步返回」；每轮保留 15 秒日志，标注请求、服务端响应、客户端完成回调的时刻。

**验收：**能解释服务端已响应而客户端等不到的原因；两个互斥组也需要有能力并行调度的 executor。保留 callback group 的成员引用，说明共享可变数据如何避免竞争；仅增加线程数不算修复证据。

**本队映射：**检查 [fake_vel_transform][team-fake] 的订阅、同步回调和定时器；本单元只建立诊断方法，不凭源码有多个回调就声称本队节点存在死锁。

## 6. 生命周期与组件：节点存在不等于可执行

**层级/前置/额外学时：**必学概念；了解单元 5 的调度与阻塞概念，读过 launch 与 namespace；完整实验 3–4 小时，不要求先完成并发专项实验。

**主材料：**[Humble lifecycle demo][lifecycle] 的 Basic Concept、Run the demo、CLI；[Composition][composition] 的 Discover available components、运行时 pub/sub、Composition using launch actions、namespace/remap。

**先跳过：**直接调用底层生命周期服务、dlopen 手工加载和自定义容器。旧示例的服务类型缩写不应照抄；优先用 `ros2 lifecycle get/list/set` 查询教学节点。

**输入与输出：**仅用 lifecycle talker/listener，在 configure→activate→deactivate 前后各观察 5 秒；另加载官方 Talker/Listener 组件，输出节点列表、容器列表与进程 PID 的对应表。

**验收：**报告至少三个状态与实际发布行为；讲清节点、组件、进程、生命周期状态分别是什么。修改生命周期只在教学节点上做，不为排错而批量激活真实 Nav2 server。

**本队映射：**逐项标注 [navigation_launch.py][team-launch] 的 lifecycle node 名单、ComposableNode 与 remap；对照[证据页 R5](../system/nav2-and-control-evidence.md)指出两种 composition 分支的恢复速度输出差异。

## 7. BehaviorTree.CPP 3.x：从 tick 走到本队 XML

**层级/前置/额外学时：**必学；完成 Action、生命周期，能阅读 XML；4–6 小时。

**主材料：**[官方 3.8 Reactive and Asynchronous behaviors][bt-async] 的 StatefulActionNode、Sequence/ReactiveSequence 对比；从 [3.8.6 first-tree 示例][bt-example] 学注册 ID、创建树和 tick。先跳过 Groot、脚本语言和 BT4 新特性。

**版本边界：**本队两份 XML 标注 `BTCPP_format="3"`；[Nav2 humble package.xml][nav2-bt-dep] 依赖 `behaviortree_cpp_v3`。3.8.6 示例用于 v3 学习，不宣称部署机恰好安装 3.8.6；编译前查实际版本，不能只把 BT4 头文件名改一下。

**必读补充：**Nav2 的 [RecoveryNode::tick/halt][recovery]、[PipelineSequence::tick/halt][pipeline]，这两个控制节点不能用普通 Sequence 语义代替。`RUNNING` 与 `halt()` 要能逐步解释。

**输入与输出：**对[单点树][team-tree]与[多点树][team-tree-multi]各画一张控制流图；整理 XML ID→插件/服务器→输入输出表；用给定 SUCCESS/FAILURE/RUNNING 序列逐 tick 记录路径。

**验收：**至少解释一次正常跟踪、一次规划失败清图重试、一次恢复失败；把 RateController 的 3 Hz 与根 tick 分开。`BackUp` 对应本队自由方向恢复，离线走读不能证明恢复时车体运动正确。

## 8. GDB 与 Memcheck：给崩溃一份可定位的报告

**层级/前置/额外学时：**进阶；会用 CMake、指针、栈与堆；3–4 小时。

**主材料：**[GDB Backtraces][gdb] 中 `bt full`、多线程 backtrace；[Valgrind Quick Start][valgrind] 的 Preparing、Running、Interpreting output。先跳过 GDB Python 扩展和 Valgrind 内部实现。

**输入与输出：**写一个只在训练目录运行的 C++ 小程序，用 `vector.at()` 越界制造未捕获异常，再用带 `-g` 的构建取栈；另跑 Valgrind 官方的小型越界/泄漏例子，修复并保存前后报告。

**验收：**崩溃报告含可执行文件、构建选项、输入、异常与第一处自己的源码位置；Memcheck 报告区分 invalid write、definitely lost 与 still reachable，不能把内存占用高直接叫泄漏。

**本队映射：**参照 [fake 节点成员与输入](../system/nav2-and-control-evidence.md)列出初始化检查点，但不在生产代码制造故障。系统工具手册的 current 不是 ROS API 版本；以本机 `gdb --version`、`valgrind --version` 核对选项。

## 9. perf：从 CPU 高到具体函数

**层级/前置/额外学时：**进阶；完成单元 5、8，已有稳定可重复工作负载；2–4 小时。

**主材料：**[Brendan Gregg 作者站 Linux perf Examples][perf] 的 4.1 Prerequisites、4.2 Symbols、6.1 Event Counting、6.2 Timed Profiling；先跳过硬件 raw counters、内核探针和整本性能书。

**输入与输出：**固定同一教学节点、输入、编译优化级别和运行时长，用 `perf stat` 记录计数，用 `perf record`/`perf report` 找 CPU 样本最多的函数；保存原始数据、文本报告和版本。

**验收：**能从样本回到源码，并报告前三个热点与各自占比；不同工具下的运行时间分开统计。CPU 采样热点不等于端到端时延，更不能从函数宽度直接推断回调的 p99。

**本队映射：**候选对象是 [fake_vel_transform][team-fake] 的合成输入实验，或 [loam_interface][team-loam] 的固定回放；尚未测量时不得写“某函数是本队瓶颈”。perf、内核和权限需匹配，虚拟机/WSL 缺少某事件时记录限制，换可用事件。

## 10. ROS tracing：把回调放到同一时间轴

**层级/前置/额外学时：**进阶；完成单元 5、9，能区分回调耗时和排队等待；3–5 小时。

**主材料：**[ros2_tracing Humble README][tracing] 的 Building、Tracing、Trace command、Launch file trace action；先跳过 kernel tracing、实时内核调优与论文中的全部性能数字。

**版本边界：**此分支说明 Linux/LTTng 支持，并有构建时关闭插桩的情况；先执行 `ros2 run tracetools status`、`ros2 trace --help`。README 的历史构建说明不是要求重编整套部署环境，缺能力时仅在独立训练 overlay 解决。

**输入与输出：**用单元 5 的教学节点，在节点启动前开始 trace，记录初始化与 callback start/end；采集至少 100 个完整回调，导出 callback 标识、线程、开始/结束时间与 duration 表。

**验收：**按同一线程/回调正确配对，报告丢失或未配对事件；给出 p50/p95/p99 与样本数，展示一段慢回调阻塞其他工作或被并行调度的时间轴。未采集到初始化映射时不能随意给地址命名。

**本队映射：**将相同方法用于 [navigation_launch.py][team-launch] 的组件容器时，先区分进程与组件，再关联 [fake_vel_transform][team-fake] 的回调；只有合成输入验证时，报告名称必须写明“训练节点实验”。

## 不依赖运动真车的进阶挑战

所有挑战均在无底盘连接的独立训练机与组内分配的独立 ROS domain 完成；文中时间/样本要求是练习验收条件，不是整车安全指标。输入、脚本、环境和结果一起交付，失败日志也属于结果。

### A. Action 取消监测器（额外 3–4 小时）

基于单元 1 保存目标 UUID，为接受、反馈、发起取消、取消响应、最终结果输出一条条 CSV 事件；取消响应核对对应 goal，不能只有一个“cancel sent”字符串。

连续做 10 次第二次反馈后取消，另做 2 次自然完成和 2 次服务端拒绝目标的受控变体。提交代码、CSV、状态转换图和取消请求到最终结果的时间统计；最终终态缺失必须列为失败，不能预填 CANCELED。

验收还需解释取消接受后可能仍有在途反馈，以及为何该工具只能证明 Action 契约；用本队[手柄取消代码][team-joy]补一段“还需观察哪些下游输出”。

### B. QoS 最小复现包（额外 2–3 小时）

把单元 2 的四格实验做成参数化 launch，启动后先确认端点发现，再发送 100 个带序号消息；每次运行保存 YAML、端点信息、计数、RMW 与日志。

再做迟加入订阅者实验：Transient Local 发布者保活，先发布一条数据后停止继续发布，稍后启动两种 durability 的订阅者。提交“历史消息/后续消息”分开的结果表，不能靠持续发消息掩盖历史数据是否收到。

验收由另一名队员只改一行可靠性配置重现“有 Topic 无数据”，再恢复；同时说明这不是数据格式错误，也不是网络性能测试。

### C. 时钟/TF 诊断档案（额外 3–4 小时）

同一教学 bag 分别做全节点正确仿真时间、一个查询节点误用系统时间、停止动态 TF 后继续查询三组实验；每组使用全新节点，保留完全相同的 Topic 白名单。

提交 TF 图、查询时间与最新 TF stamp 的对照表、异常原文、每节点 `use_sim_time` 和 `/clock` 来源。至少取得两种不同根因的失败；写清查询的 source/target 与时刻，不能仅交 RViz 截图。

验收者按档案能够区分时间源错配、数据停止和帧不存在；结论明确 bag 只能重现记录输入，不能闭环验证新的导航控制命令。

### D. BT 离线走读册（额外 3–5 小时）

输入为本队两份原始 XML，输出 `bt-ports.csv`、控制流图、四个逐 tick 场景：正常、规划失败后清图成功、控制失败后恢复、恢复本身失败。表中记录节点状态、重试计数、下一节点和 halt 对象。

说明根 tick 与 3 Hz 限频的时间假设，用 Nav2 humble 的 RecoveryNode/PipelineSequence 源码交叉校验。可写无 ROS 的桩节点程序验证子树；未经注册的 Nav2 节点不能直接交给通用 BT.CPP parser 当作可运行树。

验收需指出单点/多点树的差别与 BackUp 的本队实现，不能将纸面路径称为 Nav2 运行测试，更不能把恢复节点名理解成固定朝后运动。

### E. 一页性能报告（额外 4–6 小时）

选择单元 5 的固定负载：输入频率、一次回调的工作量与持续时长不变；单线程与合理分组的多线程各跑 3 次，每次 60 秒。开启/关闭采集分组记录，报告 CPU、处理消息数、回调耗时分位数和采集开销。

交付 perf 原始数据、trace 或明确说明替代测量方法的原始日志、统计脚本、热点源码位置和一页结论。先定义耗时起止点；只记录 callback start/end 时，不得声称测到了消息从发布到处理完成的总延迟。

验收要求结论可由原始数据重算，解释一次“CPU 较低却延迟较高”的原因；若未观察到该现象，写假设与下一项实验，不伪造数据。GDB 断点、Memcheck 下的时间不能当作正常运行性能。

完成后把代码、README、依赖版本、原始日志与复现命令交给导师，结果标记“已实测/源码预测/未完成”。将结论映射回 [Nav2](../nav2/README.md) 和 [Debug](../debug-real/README.md) 的具体故障卡；本页网页核验与静态阅读不代表已在当前 Windows 主机完成 ROS 实验。

[action]: https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Writing-an-Action-Server-Client/Cpp.rst
[action-interface]: https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Creating-an-Action.rst
[action-client]: https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Tutorials/Intermediate/Writing-an-Action-Server-Client/scripts/client.cpp
[action-server]: https://raw.githubusercontent.com/ros2/ros2_documentation/humble/source/Tutorials/Intermediate/Writing-an-Action-Server-Client/scripts/server.cpp
[qos]: https://github.com/ros2/ros2_documentation/blob/humble/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst
[tf-debug]: https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.rst
[clock]: https://design.ros2.org/articles/clock_and_time.html
[bag]: https://raw.githubusercontent.com/ros2/rosbag2/humble/README.md
[bag-qos]: https://github.com/ros2/ros2_documentation/blob/humble/source/How-To-Guides/Overriding-QoS-Policies-For-Recording-And-Playback.rst
[executors]: https://github.com/ros2/ros2_documentation/blob/humble/source/Concepts/Intermediate/About-Executors.rst
[callback]: https://github.com/ros2/ros2_documentation/blob/humble/source/How-To-Guides/Using-callback-groups.rst
[lifecycle]: https://raw.githubusercontent.com/ros2/demos/humble/lifecycle/README.rst
[composition]: https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Composition.rst
[bt-async]: https://www.behaviortree.dev/docs/3.8/tutorial-basics/tutorial_04_sequence/
[bt-example]: https://raw.githubusercontent.com/BehaviorTree/BehaviorTree.CPP/3.8.6/examples/t01_build_your_first_tree.cpp
[nav2-bt-dep]: https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_behavior_tree/package.xml
[recovery]: https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_behavior_tree/plugins/control/recovery_node.cpp
[pipeline]: https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_behavior_tree/plugins/control/pipeline_sequence.cpp
[gdb]: https://sourceware.org/gdb/current/onlinedocs/gdb.html/Backtrace.html
[valgrind]: https://valgrind.org/docs/manual/quick-start.html
[perf]: https://www.brendangregg.com/perf.html
[tracing]: https://raw.githubusercontent.com/ros2/ros2_tracing/humble/README.md
[team-joy]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_teleop_twist_joy/src/pb_teleop_twist_joy.cpp
[team-loam]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp
[team-fake]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp
[team-launch]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py
[team-tree]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml
[team-tree-multi]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_through_poses_w_replanning_and_recovery.xml
