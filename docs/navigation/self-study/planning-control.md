# 规划与控制：学有余力后的自学材料和选做项目

本页配合 [S4 环境表达与规划](../planning/README.md)、[Nav2 与控制链](../nav2/README.md)。开始 T5 时可先读基础 A 的作者教程；完成 T5 后再做 P1 对照，T6–T7 前后按需进入其他专题。目标是用固定输入解释：为什么路径变了、为什么出现横向速度、一个新算法是否值得继续验证。

队内参照固定为 Navigation-2027 的 `183a4109b0de2030bb8970a54654937c8b039ba9`。此提交使用 `SmacPlannerHybrid + DUBIN`、`OmniPidPursuitController`、`IntensityObstacleLayer` 和 `fake_vel_transform`。下面的练习指标是教学设计，没有宣称本队已经取得这些成绩。

## 怎么选，而不是从头刷完

| 你现在的情况 | 建议顺序 | 额外投入 |
|---|---|---|
| A* 能跑，但解释不了最优性或带权地图 | 基础 A → 项目 P1 | 阅读 3–4 h，实验 4–6 h |
| PID 只会背公式，侧移和坐标转换容易混 | 基础 B → 专项 D → 项目 P2 | 阅读 5–7 h，实验 6–8 h |
| 想调 Costmap / Smac 参数 | 专项 C、E → 项目 P3 的参数组 | 阅读 5–7 h，实验 6–8 h |
| 想研究更换规划器或控制器 | 先完成以上对应项 → 研究 F → P3 扩展 | 阅读 4–6 h，扩展实验 10–16 h |

只选一条也可以；学时不包含首次安装 Ubuntu、Humble 和依赖。纯 Python 项目下载好材料后可断网完成；Nav2 实验需提前准备已编译的隔离训练环境，但不依赖网络、雷达或底盘。这里不要求购买教材、课程或 MATLAB。

阅读时把英文术语与代码变量一起记：`cost-to-come/g`、`heuristic/h`、`lookahead/carrot`、`saturation/限幅`、`windup/积分饱和`、`motion primitive/运动原语`。每次只精读下面指定段落，遇到暂时不需要的证明和框架代码先跳过。

## 第一层：基础巩固

### A. 从“找得到路”到“知道路径代价为什么正确”

**前置与学时：**会 Python 的字典、列表、堆；完成 T5 四邻接与无解处理。额外阅读 3–4 h。

1. 先读 [R01：Red Blob Games 的 A* 交互教程](https://www.redblobgames.com/pathfinding/a-star/introduction.html)，按 `Representing the map → Breadth First Search → Early exit → Movement costs → Heuristic search → The A* algorithm` 的顺序操作图。作者 Amit Patel 的这份教程讲解 A*；不要误写成他发明了 A*。
2. 接着读 [R02：同作者实现页](https://www.redblobgames.com/pathfinding/a-star/implementation.html)的 Python 部分：图接口、`SquareGrid`、`GridWithWeights`、`PriorityQueue`、Dijkstra、A* 与 `reconstruct_path`。对照你的 T5，标出“发现节点”和“确定当前最低代价节点”的区别。
3. 最后看 [R03：PythonRobotics 的 Grid based search](https://atsushisakai.github.io/PythonRobotics/modules/5_path_planning/grid_base_search/grid_base_search.html)中 `Dijkstra algorithm`、`A* algorithm`，进入 [AStar/a_star.py](https://github.com/AtsushiSakai/PythonRobotics/blob/master/PathPlanning/AStar/a_star.py)读 `planning`、`calc_heuristic`、`get_motion_model`、`verify_node`。先抄出邻接动作与代价，再比较结果。

**先跳过：**R02 的 C++/C# 重复实现和队列微优化；R03 的双向 A*、D*、Theta*、势场。教学示例中的欧氏启发式和动作集不能直接替换你“四邻接、单位代价”的定义。

**理解问题：**`h=0` 时为什么可以作为参照？地图格子的代价不是 1 后，BFS 还优化什么？更早遇到终点是否就能立刻返回？加权地图与 `f=g+w·h` 的 Weighted A* 是不是同一件事？

**离线小练习与验收：**在五个节点的非负权图上手算队列弹出顺序，再跑 P1。交付一张 `节点 / g / h / parent / 是否扩展` 表；手算与程序总代价一致，不能只交一段动画。

**队内映射：**T5 建立搜索、代价和可达性的基本功；实际 `GridBased` 是带朝向状态的 Hybrid-A*，有运动模型、碰撞检查、代价惩罚和内部平滑。网格 A* 作业不等于实现了当前规划器。

### B. 把控制公式变成离散时间实验

**前置与学时：**会二维坐标旋转，理解误差和导数；完成 T2 的侧移、旋转。额外阅读 3–4 h。

1. 读 [R04：Åström / Murray《Feedback Systems》PID 章节](https://www.cds.caltech.edu/~murray/FBS/PID_Control.html)。本页对应 AM08 的第 10 章；按 `10.1 Basic Control Functions → 10.4 Integrator Windup → 10.5 Implementation` 阅读，[公开章节 PDF](https://www.cds.caltech.edu/~murray/books/AM08/pdf/am08-pid_28Sep12.pdf)为 2012-09-28 版本。
2. 用作者的 [CDS 101/110 PID 课程页](https://murray.cds.caltech.edu/CDS_101/110_-_PID_Control)核对学习目标：反馈、执行器饱和、anti-windup。先画位置误差、控制速度、积分状态三条时间曲线。
3. 再读 [R05：PythonRobotics Pure pursuit tracking](https://atsushisakai.github.io/PythonRobotics/modules/6_path_tracking/pure_pursuit_tracking/pure_pursuit_tracking.html)，进入 [pure_pursuit.py](https://github.com/AtsushiSakai/PythonRobotics/blob/master/PathTracking/pure_pursuit/pure_pursuit.py)依次看 `State.update`、`proportional_control`、`TargetCourse.search_target_index`、`pure_pursuit_steer_control`。

**先跳过：**AM08 10.2 的复杂系统案例、10.3 的整定公式推导和课程 MATLAB 作业；先用 Python 做数值积分即可。PythonRobotics 的演示面向车式转向；文档称速度 PID，但要按实际函数判断是否仅用了 P 项。

**理解问题：**积分里是否乘了 `dt`？误差突变为何放大微分项？最终速度限幅为什么不等于积分状态得到正确处理？前视距离变长，跟踪误差和弯道切角可能怎样变化？

**离线小练习与验收：**固定 `dt=0.05 s`，对误差序列 `[1,1,1,0,-1]` 手算离散 P/I/D 各项；再把 `dt` 改为 `0.1 s`。代码应与手算逐项一致，说明每个增益的单位及限幅发生的位置。

**队内映射：**这些材料解释前视与反馈概念；本队控制器对前视点距离做标量 PID，再按方向分解 `vx/vy`。把汽车转向角公式直接拿来控制全向底盘，会遗漏本队允许的侧移自由度。

## 第二层：专项选学

### C. 搞清 Dubin 约束，再读 Smac 的实现选择

**前置与学时：**基础 A、T2；能写 `(x,y,yaw)` 状态。额外阅读 3–4 h。

1. 读 [R06：LaValle《Planning Algorithms》第 2 章](https://lavalle.pl/planning/ch2.pdf)的 2.1、2.2.1、2.2.2，只把状态、动作、转移和搜索队列对应起来。
2. 接着读同书[第 13 章](https://lavalle.pl/planning/ch13.pdf)的 13.1.2：simple car、Reeds–Shepp car、Dubins car；再读[第 15 章](https://lavalle.pl/planning/ch15.pdf)的 15.3.1 Dubins Curves、15.3.2 Reeds–Shepp Curves。画出向前、倒车、原地旋转、横移四种动作在不同模型里是否存在。
3. 读 [R07：Nav2 humble 分支 Smac README](https://github.com/ros-navigation/navigation2/blob/humble/nav2_smac_planner/README.md)的 `Introduction`、`Features`、参数配置示例与调参说明；优先定位 `motion_model_for_search`、`angle_quantization_bins`、`minimum_turning_radius`，随后区分 2D、Hybrid、Lattice。

**先跳过：**LaValle 的微分几何、可控性证明、完整最优控制推导；Smac 的模板性能优化和 Lattice 原语生成器。先能说明模型差异，不需要从零重写 Hybrid-A*。

**理解问题：**本队底盘能横移，为什么 `DUBIN` 搜索仍不会产生直接横移原语？放宽最小转弯半径会不会增加可达状态？规划的 yaw 与底盘最终自旋是否必须一致？带姿态足迹检查与仅检查圆半径有何区别？

**离线小练习与验收：**画起点 `(0,0,0)` 到终点 `(0,1,0)` 的“保持朝向直接侧移”和一条前向曲线，标注可用动作；不要求手求最短 Dubins 曲线。交付动作约束表，指出两种路径适用的模型，禁止只按平面线长判算法对错。

**队内映射：**固定提交的配置是 `SmacPlannerHybrid`、`DUBIN`、64 个方向桶、最小转弯半径 `0.05 m`，见 R10。当前选择是否合适需实验判断；“底盘全向”不足以直接得出保留或更换插件的结论。

### D. 沿本队源码追一次全向速度

**前置与学时：**基础 B，能读 C++ 函数及 `Twist`；先看 [Nav2 证据页](../system/nav2-and-control-evidence.md)。额外阅读 2–3 h。

1. 读 [R11：OmniPidPursuitController](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_omni_pid_pursuit_controller/src/omni_pid_pursuit_controller.cpp)：`configure → computeVelocityCommands → getLookAheadDistance / getLookAheadPoint → applyCurvatureLimitation → applyApproachVelocityScaling`。
2. 同时读 [PID::calculate](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_omni_pid_pursuit_controller/src/pid.cpp)。逐句记录 `dt_`、积分更新、`i_out` 计算、积分限幅、最终输出限幅的顺序；不要只根据参数名判断功能。
3. 读 [R12：fake_vel_transform.cpp](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp)：先 `transformVelocity`，再 `cmdVelCallback → localPlanCallback → syncCallback → cmdSpinCallback`，画缓存与发布时序。

**先跳过：**插件注册、日志格式等样板；但不能跳过 `isCollisionDetected` 的调用位置、零速度分支和同步缓存。这些边界决定“控制器算出什么”是否等于“底盘收到什么”。

**理解问题：**`theta_dist=atan2(y,x)` 后为何可得到非零 `linear.y`？当前实现是不是 x/y 各一套 PID？`enable_rotation=false` 后最终 `angular.z` 为什么仍可能非零？收到零命令和没有收到命令是否相同？

**离线小练习与验收：**计算 `vx'=vx·cosψ+vy·sinψ`、`vy'=-vx·sinψ+vy·cosψ`。输入 `(0.2,0)`、`ψ=π/2` 应得约 `(0,-0.2)`；平移模长不变。输入全零、`spin=0.5` 时应预测输出 `wz=0.5`，并标为源码预测。

**队内映射：**P2 只验证数学和简化反馈；真实控制链还包括速度平滑、fake 同步、自旋、恢复行为和外部串口。生产停车是否可靠必须按 T7–T8 的完整接口与实车流程确认，不能用离线公式替代。

### E. 把 Costmap 当作输入系统来研究

**前置与学时：**T6 的地图、frame、足迹概念；不会点云也能先读代码。额外阅读 2–3 h。

1. 读 [R10：本队 reality/nav2_params.yaml](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml)，只看 `terrain_analysis → local_costmap / global_costmap → planner_server`。记清 `terrain_map`、frame、marking/clearing、intensity 阈值及膨胀参数。
2. 读同一来源包中的 [IntensityObstacleLayer](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/src/layers/intensity_obstacle_layer.cpp)：`onInitialize → pointCloud2Callback → updateBounds → raytraceFreespace → updateCosts`，在纸上区分标记障碍与清除自由空间。

**先跳过：**本次没有加载的 IntensityVoxelLayer，以及与当前数据链无关的其他传感器接入方式。

**理解问题：**地形点的 intensity 来自什么计算，为什么不应直接理解成雷达反射强度？低于阈值的点没有被标记，是否就说明原有障碍已被清除？膨胀半径改变的是车体尺寸还是规划代价？

**离线小练习与验收：**固定其余过滤条件有效，给六个点赋 intensity `[0.09,0.10,0.11,1.99,2.00,2.01]`，按源码默认 `[0.1,2.0]` 比较运算输出保留表。阈值边界判断应正确；用同一 float32 表示构造输入与阈值，避免把表示误差当成新算法结论。

**队内映射：**默认图层包括 StaticLayer、IntensityObstacleLayer、InflationLayer。来源点云、TF 或地形含义错误时，换 A* 或改 PID 不能修复输入。更完整的点云体检与真实数据验证仍按 T3、T6 完成。

## 第三层：研究进阶

### F. 在 Humble 上提出可证伪的算法比较

**前置与学时：**C、D；至少一个完整基线报告。额外阅读 4–6 h；实现比较另计。

1. 重读 R07 中 Smac2D、Hybrid、Lattice 的适用模型。把候选算法需要的 footprint、状态维数和原语文件列出来；暂不更改运行配置。
2. 读 [R08：Nav2 humble RPP README](https://github.com/ros-navigation/navigation2/blob/humble/nav2_regulated_pure_pursuit_controller/README.md)的 `Pure Pursuit Basics → Regulated Pure Pursuit Features → Configuration`，找前视距离、曲率/障碍减速、碰撞预测。原文明示可用于全向平台，但不能充分利用横向运动。
3. 读 [R09：Nav2 humble MPPI README](https://github.com/ros-navigation/navigation2/blob/humble/nav2_mppi_controller/README.md)的 `Overview → MPPI Description → Configuration`，先只看 `motion_model`、`model_dt`、`time_steps`、`batch_size`、`vy_max`、`vy_std` 和 critics；读懂“采样速度→前向预测→打分→更新控制”。

**先跳过：**MPPI 的随机最优控制证明、所有 critic 同时调参、自定义 GPU 实现，以及没有问题驱动的算法排行榜。

**理解问题：**选 `motion_model=Omni` 后，`vy` 的采样、限幅与实际底盘反馈是否一致？预测时域 `time_steps×model_dt` 多长，是否超出局部地图？更短路径是否会带来更大的跟踪误差？官方机器上的耗时能否代表本队设备？

**离线小练习与验收：**先算 `56×0.05=2.8 s`，再手画不同 `vy` 的三条全向候选轨迹；自己定义“终点误差+路径偏离”的简单分数，说明权重变化如何改变排序。它是采样评分教学模型，不称为已实现 MPPI。

**队内映射：**RPP、MPPI 都是候选学习对象，本队默认控制器仍为 OmniPid。算法比较应保留当前配置为 baseline，先消除坐标、数据与接口差异；未经隔离测试、回归和维护者评审，不替换生产算法。

**版本边界：**R07–R09 均链接 `humble` 分支；该分支仍可能回移修复，实验时记录实际 Nav2 包版本或源码 SHA。README 中跳转到现行文档的链接可能已更新，不能据此照抄 Rolling 的参数、插件名称分隔符或接口到 Humble。PythonRobotics 的 `master` 同样要在实验开始时记录下载版本。

## 三个可独立提交的选做项目

### P1：带权地图、启发式与最优代价

**目标与环境：**用 Python 标准库完成，4–6 h；接 T5。代码、输入与绘图数据均留在个人练习仓库。

**固定输入：**20×20 格，坐标 `x,y∈[0,19]`，四邻接；进入目标格的代价作为边权，起点本身不计费。所有格默认代价 1。

| 场景 | 起点 → 终点 | 改动 | 预先可验证的参照 |
|---|---|---|---|
| G0 | `(1,1)→(18,18)` | 无障碍 | 最优代价 34 |
| G1 | `(1,10)→(18,10)` | `x∈{9,10}, y∈[4,15]` 的格子代价 20 | 最优代价 29；可从 `y=16` 绕行 |
| G2 | 同 G1 | 在 G1 上将整列 `x=10` 设为不可通行 | 无解 |

1. 跑 Dijkstra / `h=0` 和 A* / 曼哈顿距离，固定相同邻居顺序、平局规则和终止条件。
2. 加 `f=g+w·h`，比较 `w=1,1.5,2`。记录允许重新入队/重新扩展的实现策略；不得把“更快”预填成结论。
3. 另外跑 T5 的非法起终点和相同起终点检查。画 G1 的低代价绕行与高代价直行，分别报告长度与总代价。

**指标：**成功/失败、总代价、路径格数、实际扩展次数、耗时中位数；成功时报告 `C/C_Dijkstra`。每场景每设置重复 10 次，计时关闭动画，说明是否包含输入构造。

**验收：**`w=1` 与 Dijkstra 代价一致，G0/G1 与表中参照一致；逐段验证邻接及通行，G2 能有限终止。`w>1` 即使没有变差也如实记录，不能据少数地图声称仍保证最优。交付 CSV、输入文件、命令、至少一个失败用例与解释。

### P2：全向 PID、速度饱和与坐标变换

**目标与环境：**Python 数值仿真，6–8 h；不启动 ROS、不连接底盘。模型只研究平移，yaw 是给定条件，自旋另做代数检查。

**固定输入：**从 `(0,0)` 出发，目标分别为 `(1,0)`、`(0,1)`、`(1,1)` m；每个目标测试固定 `yaw=0`、`π/2`。`dt=0.05 s`、每段 10 s，速度模长上限 `0.5 m/s`，每次重置控制器状态。

1. 先实现教学 P 基线 `v=min(1.0·d,0.5)`，沿世界坐标中的目标误差方向输出平移；当 `d=0` 时明确输出零。它不是仓库完整控制器。
2. 加一个标量距离 PID，再按方向分解成两分量；每次只改一项增益，保留全部值。另一种“x/y 各自 PID”可作为额外对照，但必须注明与本队实现不同。
3. 用 R12 的旋转公式转到车体速度，再用 T2 的正向旋转积分回世界位姿。固定 yaw 的两组世界轨迹应一致，侧向目标必须能出现 `vy≠0`。
4. 给速度执行模型加入 `τ=0.2 s` 的一阶滞后，另加持续世界 `+y` 方向 `0.03 m/s` 的扰动；比较无积分、有限积分与明确实现的 anti-windup。参考停止时也记录积分与残余速度，不只截取收敛前半段。

**指标：**最后 1 s 的平均位置误差、最终距离、首次进入并持续留在 0.05 m 范围的时间、最大速度模长、处于限幅的样本比例、积分状态最大绝对值。未收敛记为超时，不能删除失败组。

**验收：**无滞后/扰动的 P 基线在六组中最终误差均小于 0.01 m；同目标两种 yaw 的世界轨迹最大差小于 `1e-6 m`，旋转前后速度模长误差小于 `1e-9 m/s`。这些是理想计算门槛。扰动组不要求新控制器必胜，但要求用指标解释增益、限幅与误差的关系。

**单独的边界检查：**输入零平移、零角速度，设置 `spin=0.5`，代数输出必须是 `wz=0.5`；明确这一条没有验证 fake 节点缓存、消息断流或整车停车。项目结果不能直接转换为生产 PID 参数。

### P3：固定场景下的参数 / 规划器对照

**目标与环境：**已准备好的 Ubuntu 22.04 / ROS 2 Humble 训练环境，6–8 h；只调用 Planner，不启动控制器、恢复行为、串口或电机接口。完成环境准备后可断网运行。

**固定输入：**80×80 格、分辨率 `0.05 m`、原点 `(0,0,0)`，地图四周一格障碍墙，unknown 禁行，教学圆半径固定 `0.2 m`。冻结每张图、起终点、朝向、参数及其校验值。

| 场景 | 障碍定义 | 起点 → 终点；yaw 均为 0 |
|---|---|---|
| M0 开阔平移 | 只有边界墙 | `(1.0,1.0)→(1.0,2.0)` m |
| M1 双开口 | 整列 `x=40` 为墙，开口格 `y=12…25`、`52…65` 除外 | `(0.8,2.0)→(3.2,2.0)` m |
| M2 无解 | 同 M1，但封闭两处开口 | 同 M1 |

1. **基线组：**以本队 Hybrid/DUBIN 参数为来源，为教学地图建立独立配置；改动路径、frame 等适配项全部登记。先验证服务激活、TF 与起点无碰撞。
2. **参数组：**固定 Planner，分别测试 `inflation_radius=0.4/0.7/1.0 m`；保持 `cost_scaling_factor=4.0`、半径和其他设置一致。另做方向桶或转弯半径实验时另起一组，不混在同一次改动中。
3. **规划器扩展：**回到基线膨胀参数，仅比较 Hybrid/DUBIN 与 Humble Smac2D；教学圆形 footprint 条件保持一致。Lattice 只有在原语文件已核对并记录来源时才增加，不假设换 plugin 名称就完成配置。
4. 每图每设置先预热一次，再测 10 次；报告是否复用目标启发式缓存，不能把冷启动时间与缓存命中时间混为一组。所有超时和无解结果均保留。

**指标：**规划成功数、响应耗时中位数/最大值、路径米制长度、终点位置误差、路径中心到占据格边界的最小几何距离、碰撞检查结果。减去固定半径才可作为教学圆形足迹的余量；图中代价值不能直接当米制余量。

**验收：**M2 不得输出可通行成功路径；成功路径需独立检查，重采样间距不大于 `0.025 m`，并检查采样点间线段与圆形足迹扫掠区域。阈值在实验前冻结，不能缩小 footprint 换成功。报告至少一处路径变化或“没有变化”的证据及原因。

**解释边界：**这里只测规划成功率，不测到达率、闭环跟踪误差或动态避障能力。若未准备 ROS 环境，可先完成地图生成、校验和碰撞检查器，Nav2 部分标“待环境”；不得把纯 Python A* 的结果写成 Smac 对照结果。

## 交付与资源维护

每个项目按[作业统一格式](../assignments/README.md)交付，再补一页“baseline comparison”：原方案、唯一改动、数据与版本、所有指标、负面结果、适用范围、下一步验证。导师优先检查你能否解释一个反例，而不是引用了多少算法。

本页精选 R01–R12 共 12 组第一方材料：作者教程、作者教学代码、作者开放教材、Nav2 维护仓库与队伍源码；同一作者教材的章节/配套源码合为一组。英文资料均给出具体阅读入口与可跳过范围。

链接核验日期为 **2026-09-14**：Red Blob Games、PythonRobotics 页面及两个具体 demo 路径、LaValle 三个章节、Nav2 三份 `humble` README、队伍固定 SHA 的配置和四份源码均已访问核对。Murray 课程页可读；章节网页和 PDF 经直接 HTTP 请求确认返回 200，网页标题为 `PID Control - FBSwiki`，PDF 类型为 `application/pdf`。部分网页提取工具无法解析该站，不表示需要购买教材。

首次学习时保存来源 URL、访问日期、代码版本与必要页面/PDF，保留许可证和署名；链接迁移后优先回作者或项目官网找同章。这里只完成资料与静态源码核验，未声称运行本页项目、编译 Nav2 或验证实车。
