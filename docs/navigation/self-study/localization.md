# 定位方向自学：从坐标变换走到 Point-LIO 与 small_gicp

适合对照[系统链路](../system/README.md)和[传感器与定位课](../sensor-lio/README.md)、希望进一步读懂算法的同学。S2 可先学第一段坐标变换；完整方向学习建议在 S3 后开始。这里的“必学”只表示**选择定位方向后的核心内容**，不是给所有新人新增一套入队门槛。不会矩阵或概率也可以从第一段开始，不必先完整读完一本 SLAM 书。

本队代码统一对应 `Navigation-2027@183a4109b0de2030bb8970a54654937c8b039ba9`；所有队内源码链接固定在该提交。外部资料核查日期为 **2026-09-14**。本文给出学习和实验要求，没有声称已运行本队 LIO、完成 bag 复现或验证实车性能。

建议顺序：**矩阵与坐标 → 概率与滤波 → 点云几何 → small_gicp → Point-LIO 源码 → 论文对照**。核心部分约 25～37 小时；按每周额外 2～3 小时可分约 9～19 周学习，时间充裕时每周 4～6 小时、约 5～10 周完成。先选一个小实验即可，不要求一学期读完全部；选学和进阶另算。下文时间均为包含笔记和实验的教学估计，不是视频长度或作者承诺。

## 1. 只保留这 11 组材料

先按后面的路线学习，这张表用于找回具体入口。英文页面可先读代码、图和公式，再对照正文；课程视频不可用时，3Blue1Brown 的文字课和 Modern Robotics 的 Transcript 仍可阅读。

| 编号 | 免费材料与具体入口 | 在本路线中的用途 |
|---|---|---|
| R1 | 3Blue1Brown：[第 3 章矩阵与线性变换](https://www.3blue1brown.com/lessons/linear-transformations/)、[第 4 章矩阵乘法与复合](https://www.3blue1brown.com/lessons/matrix-multiplication/) | 理解矩阵的列、变换顺序；作者文字课，不依赖付费课程 |
| R2 | 3Blue1Brown：[第 14 章特征向量与特征值](https://www.3blue1brown.com/lessons/eigenvalues/) | 建立点云局部平面、协方差方向的直觉 |
| R3 | Northwestern / Lynch、Park：[Modern Robotics 3.2.1 Rotation Matrices，Part 1](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-2-1-rotation-matrices-part-1-of-2/) | SO(3)、旋转矩阵约束；页面目录可接着读 Part 2 |
| R4 | 同一作者课程：[3.3.1 Homogeneous Transformation Matrices](https://modernrobotics.northwestern.edu/nu-gm-book-resource/3-3-1-homogeneous-transformation-matrices/) | SE(3)、变换求逆、坐标系下标消去规则 |
| R5 | Simo Särkkä：[Bayesian Filtering and Smoothing，2013 作者授权在线版](https://users.aalto.fi/~ssarkka/pub/cup_book_online_20131111.pdf) | 第 2、4 章与 5.1–5.2；下文编号对应第一版，不能套用到第二版 |
| R6 | PCL 官方：[VoxelGrid 下采样教程](https://pointclouds.org/documentation/tutorials/voxel_grid.html) | 体素尺度、质心代表点、输入输出点数 |
| R7 | PCL 官方：[How to use iterative closest point](https://pointclouds.org/documentation/tutorials/iterative_closest_point.html) | source/target 方向、配准矩阵与最小可运行 C++ 例子 |
| R8 | Kenji Koide：[small_gicp 官方 README 的 C++ 用法](https://github.com/koide3/small_gicp#usage-c) | 重点看 Using PCL interface 中直接使用 Registration 模板的示例 |
| R9 | 同一作者：[src/example/basic_registration.py](https://github.com/koide3/small_gicp/blob/master/src/example/basic_registration.py) | `example_numpy1`、`example_numpy2`；用于合成点云实验 |
| R10 | HKU MARS：[Point-LIO 官方说明](https://github.com/hku-mars/Point-LIO#readme) | §1 输入注意事项、§5.2 外参/IMU、§5.3 点时间、§6 数据集说明 |
| R11 | Xu 等：[FAST-LIO2 原作者 arXiv 正文](https://arxiv.org/html/2107.06829v1) | §III、§IV-A/B 与 §V-A；理解另一种 LIO 组织方式并对照差异 |

R5 的 PDF 是作者在学校网站发布、允许个人阅读的版本；链接学习即可，不把整本书复制进知识库。R6/R7 核查时页面为 PCL 1.15.1-dev 文档，API 教程不代表本队机器安装了该版本。R8/R9 为上游可变化的页面，复现时记录版本；本队对应实现见下面的固定链接。

## 2. 第一段：矩阵、坐标与外参（必学，5～7 小时）

**先修：** 会三角函数、三维向量加法，能运行一个 Python/NumPy 脚本。还不会编程时先手算第一组数据，再请同伴帮助把公式写成数组运算。

**按这个范围读：** R1 两课先看变换图，再完成各自正文中的小题；R3 读 Description 和 Transcript，记住旋转矩阵三列的意义；R4 读完整 Transcript，亲自推一次求逆与复合。R2 选学 1～2 小时，只读 An example、3d rotational axis、Working in an eigenbasis；第一次可跳过末尾 Fibonacci 数列谜题。机器人动力学、机械臂逆运动学不属于这次先修。

笔记统一写 `T_A_B` 表示“把 B 坐标中的数值转换到 A 坐标”。对列向量有 `p_A = R_A_B p_B + t_A_B`，齐次形式为 `p_A = T_A_B p_B`。先在草稿上写出输入、输出 frame，再写乘法；不要根据变量名中的 `to` 猜矩阵方向。

**理解问题：** 为什么 `T_A_B T_B_C` 可以直接相乘，反过来通常不行？`R` 的转置为什么等于逆，而整个 `T` 的转置通常不等于逆？雷达相对云台固定，为什么雷达相对底盘仍可能变化？修改消息的 `frame_id` 为什么不能完成坐标转换？

**小实验 A：把方向错误变成一个会失败的数值检查。** 不需要 ROS、雷达或 bag。

1. 定义 `R_B_L = Rz(90°)`、`t_B_L = [1,2,0]`，以及雷达点 `p_L=[1,0,0]`。手算应得 `p_B=[1,3,0]`；代码角度使用弧度。
2. 定义 `T_O_B` 为单位旋转、平移 `[2,0,0]`，计算 `T_O_L=T_O_B T_B_L`。检查逐级计算和一次计算均得到 `p_O=[3,3,0]`。
3. 用 `T_L_B=[R_B_L^T, -R_B_L^T t_B_L; 0,1]` 把 `p_B` 变回 `p_L`；检查 `R^T R=I`、`det(R)=1`、`T T^-1=I`，双精度最大绝对误差要求小于 `1e-10`。
4. 故意交换两矩阵顺序；它仍是合法刚体变换，却得到另一个位置。保存这个反例。再把协方差 `diag(0.04,0.01,0.0025)` 按 `R Σ R^T` 旋转，观察 x、y 方向方差交换。

**交付：** `transforms.py`、一张三坐标系草图、检查输出、200 字错误解释。这里的误差界用于无噪声合成计算，不是实车精度指标。

**回到本队：** 顺着 [loam_interface.cpp 的里程计变换][team-loam]标注每个矩阵的输入/输出 frame；再到 [sensor_scan_generation.cpp][team-scan]找动态 TF 查询。区别 [UIC 机器人模型中的雷达安装][team-model]和 [Point-LIO 的雷达—IMU 外参参数][team-config]：前者属于机器人模型链，后者进入估计器计算，不能仅因都叫“外参”就混用。

## 3. 第二段：从不确定性走到滤波（必学，6～9 小时）

**先修：** 第一段；知道均值、方差、条件概率。条件概率不熟时先读 R5 §2.3–2.4，再读附录 A.1 的高斯分布；多元微积分薄弱时先理解雅可比是一阶局部近似，不急着推流形上的全部公式。

**按这个范围读：** R5 §3.6 看状态空间模型的例子；§4.1–4.3 是必学；§5.1 先看一阶 Taylor 展开，§5.2 先看加性噪声 EKF。对应书内页码约 39、51–61、64–74，PDF 阅读器页码另有前置页。二阶 EKF、UKF、粒子滤波、平滑和参数学习先跳过；有余力再补 §8.2 的 RTS smoother，另计 2～3 小时。

每次看公式先写清 `x` 是待估计状态、`z` 是测量、`P` 是状态估计协方差、`Q` 是过程噪声协方差、`R` 是测量噪声协方差。此处 `R` 与上一段的旋转矩阵同字母但不同语境，笔记可写 `R_meas`。会背卡尔曼增益却说不出矩阵维度，暂时不要继续读 LIO。

**理解问题：** 只有位置测量为什么能逐渐估计速度？增大测量噪声后，更新更信模型还是测量？小协方差能否证明模型正确？滤波为什么只用当前与过去测量，而平滑能使用未来测量？

**小实验 B：一维运动的“自信但错误”。** 使用 NumPy，固定随机种子 2027，生成 100 步数据，`dt=0.1 s`；真实初值 `p=0 m`、`v=1 m/s`，第 50 步开始每步先加 `v += 0.1`，再做 `p += v*dt`。

1. 测量为 `z=p+N(0,0.2²)`。估计器采用匀速状态 `[p,v]`，`F=[[1,dt],[0,1]]`、`H=[[1,0]]`，初始估计 `[0,0]`、`P=diag(1,1)`。
2. 使用教学中的离散随机加速度模型，`G=[dt²/2,dt]^T`、`Q=σ_a² GG^T`；基准取 `σ_a=0.5`、`R_meas=0.2²`。每步完成预测、创新、增益和更新；标出每个矩阵的维度。
3. 保持同一份测量，分别把 `R_meas` 乘 100、把 `Q` 乘 0.01。画真实/测量/估计位置、速度，以及位置误差与 `±2 sqrt(P[0,0])`，报告加速前后的 RMSE。不要预填“调大一定更好”的结论。
4. 选学：固定一个状态，用中心差分核对 `h(p,v)=p²` 的雅可比 `[2p,0]`；说明在 `p≈0` 时仅用这一测量会遇到什么问题。暂不把它替换进完整 LIO。

**交付：** `kalman_1d.py`、包含三个设置的误差表和曲线、对第 50 步模型失配的解释。保留随机种子、噪声标准差与协方差的区别；一次实验中误差落在 2σ 外不自动证明程序有错。

**回到本队：** 打开 [common_lib.h][team-state]列出 `state_input` 与 `state_output` 的字段；再读 [Estimator.cpp 的状态导数和过程噪声][team-models]。本队有 24 维和 30 维的滤波分支，不是把这个二维玩具滤波器复制进去；其中旋转状态还需专门的扰动表示。

## 4. 第三段：点云几何与 ICP（必学，4～6 小时）

**先修：** 前两段；会数组索引和欧氏距离。C++ 尚不熟也可以先用 NumPy 完成下采样与协方差，随后再读 PCL 例子。

**按这个范围读：** R6 的 The code、The explanation；R7 的同名两节，重点是 `setInputSource`、`setInputTarget`、`align`、`getFinalTransformation`。需要运行 C++ 时才读 Compiling and running。教程提供的数据可选下载；核心实验用自己生成的点，环境无网时也能继续。

**理解问题：** 体素中的质心和体素几何中心是否相同？下采样分辨率为什么影响配准速度与细节？最近邻不等于真实对应点，迭代为何可能配错？一面没有边界的平墙能否约束所有平移和旋转？

先做两个十分钟练习：给同一体素放入三个不对称点，手算质心；然后生成带微小 z 噪声的 xy 平面，计算中心化协方差和特征向量，检查最小特征值方向是否接近法向。法向 `n` 与 `-n` 表示同一平面，不能仅因符号相反判错。

**交付：** 点数/体素尺寸表、局部平面三个特征值、法向示意图，以及 `point-to-point` 和 `point-to-plane` 各约束什么的解释。将这些函数保留，继续用于实验 C；不用为这一段准备 bag。

**回到本队：** [small_gicp_relocalization.cpp 的地图预处理与扫描预处理][team-gicp]分别做下采样、协方差估计和 KD-tree 构建。再读 [normal_estimation.hpp 的 CovarianceSetter][team-cov]：这里会按特征向量构造经过处理的协方差，不能把返回值直接当作雷达厂家给出的测量噪声。地形点云 `intensity` 的离地高度语义另见[传感器课](../sensor-lio/README.md)，不是本段几何配准使用的额外观测。

## 5. 第四段：small_gicp 从示例到本队封装（必学，5～7 小时）

**先修：** 第三段，理解 source/target 和 4×4 变换。选 Python 或 C++ 一条路线即可；不要同时花时间搭建两套运行环境。

**按这个范围读：** R9 的 `example_numpy1` 理解整体接口，`example_numpy2` 理解预处理复用；本队保存的[同名示例固定版本][team-example]可用于核对差异。R8 读 Using PCL interface 中 `Registration<GICPFactor, ParallelReductionOMP>` 的段落。选学读同目录 `03_registration_template.cpp`，进阶才读并行 reduction、VGICP 与性能 benchmark。Open3D 可视化和 KITTI odometry 不作为完成本段的前置。

**小实验 C：配准成功标志与真实误差分开验收。** 安装已核对版本的 small_gicp 后，只生成数组并调用 R9 接口，不启动 ROS 导航。没有该库时可先完成造点、变换和误差计算，明确标为“配准待运行”。

1. 用随机种子 2027 在地面 `z=0, x∈[0,4], y∈[0,3]`、墙 `x=0, y∈[0,3], z∈[0,2]`、墙 `y=0, x∈[0,4], z∈[0,2]` 上各采样 600 点，作为 target。补 300 个位于非对称小立方体表面的点，立方体范围为 `[2.4,2.9]×[1.0,1.6]×[0,0.8]`。
2. 设真实 `R=Rz(15°)`、`t=[0.3,-0.2,0.1] m`。若每一行存一个点，用 `source=(target-t) @ R` 造 source，检查 `source @ R.T + t` 恢复 target；随后给 source 加标准差 0.005 m 的独立高斯噪声。
3. 调 `small_gicp.align(target, source, ...)`，使用 `registration_type="GICP"`、下采样 0.1 m、最大对应距离 1.0 m；先用真值附近初值（在真值平移加 `[0.02,0,0]`），再用单位初值。保存结果与耗时；这里的数值只是教学参数。
4. 计算平移误差 `||t_est-t_true||`；旋转误差取 `acos(clip((trace(R_est R_true^T)-1)/2,-1,1))`，转成度；同时保存 `converged`、`iterations`、`num_inliers`。结果方向用“估计后 source 是否贴合 target”核对。
5. 每次只改一项：初始 yaw 偏差改为 60°；随机仅保留 source 的 30%；体素改成 0.4 m；最后移除墙和立方体，仅保留平面。记录哪些条件失败、哪些有较大误差；有限平面的边缘可能提供额外约束，不能预设它必定失败。
6. 进阶再读 [GICPFactor::linearize][team-factor]，对照最近邻、组合协方差、残差、`J^T W J`。看清小特征值方向与退化现象，再决定是否研究求解器；另计 2～4 小时。

**交付：** `registration_synthetic.py`、真值/估计 4×4 矩阵、参数与误差 CSV、一张对齐图、一张失败场景图。基准的真值附近初值组可先以平移小于 0.03 m、角度小于 1°为教学检查目标；达不到先检查方向、单位、数据、版本，不调整到“刚好通过”。这是合成任务目标，不能用于实车验收。

**理解问题：** GICP 中协方差如何改变不同方向残差的权重？为什么 `converged=true` 也可能位于错误的局部解？没有对应点、初值很差和地图不重叠是否能靠统一调大阈值解决？为什么缓存 target 预处理结果有用？

**本队源码阅读顺序：** [同一文件][team-gicp]的构造函数 → `loadGlobalMap` → `registeredPcdCallback` → `performRegistration` → `initialPoseCallback` → `publishTransform`。给每一步写一行“输入、缓存/计算、输出、失败后行为”，重点核对：

- 本队实例化的是 `GICPFactor`，不要因上游支持 VGICP 就写成本队启用了 VGICP。
- `registered_scan` 累加后配准，`previous_result_t_` 是初值；失败时直接返回，成功后才清空累计点云。
- YAML 的 `max_dist_sq=4.0` 是平方距离阈值；它不能原样填到 Python 的 `max_correspondence_distance`。坐标以米计时，前者对应 2 m 的距离上限。[参数与实现][team-config]
- 500 ms 配准定时器和 50 ms TF 定时器是两件事；初值为单位变换、TF 发布只检查是否全零，所以有 `map→odom` 不证明已经配准成功。[发布条件][team-gicp]

## 6. 第五段：Point-LIO 的每个测量如何进入估计器（核心源码必学，5～8 小时）

**先修：** 前四段。若尚不能解释实验 B 的创新与实验 C 的坐标方向，先补这两点；本段会同时使用状态、残差、雅可比、点时间和多个坐标系。

**按这个范围读：** R10 §1 的输入注意事项、§5.2、§5.3 和 §6 的数据说明。首次不照搬上游安装/启动命令，也不必逐个运行激烈运动数据集。理论进阶时沿 R10 §1.2 到原作者 Point-LIO 论文，先看 §3 System Overview 与 Figure 1，再沿图找到模型、传播与更新；论文入口的访问情况见文末。

队内代码按下面顺序读，每读完一行就在自己的流程图补一条边，避免从一千行主循环的第一行一路向下翻。

| 顺序 | 精确文件入口 | 必须留下的笔记 |
|---|---|---|
| 1 | [parameters.cpp][team-parameters] + [reality 参数][team-config] | `use_imu_as_input`、`mapping.imu_en`、`mapping.extrinsic_est_en` 各控制什么；区分默认值和运行值 |
| 2 | [preprocess.cpp][team-preprocess] | 找 Livox CustomMsg 处理分支；`offset_time / 1e6` 写到 `curvature` 后单位为 ms；这里的 curvature 不是几何曲率 |
| 3 | [common_lib.h 的状态定义][team-state] | `state_output` 相比 `state_input` 增加了哪些状态，位置/姿态/速度/偏置在哪个块 |
| 4 | [Estimator.cpp][team-estimator] | 从 `get_f_output` 到 `h_model_output`、`h_model_IMU_output`，标出状态传播、点到面残差、IMU 残差 |
| 5 | [laserMapping.cpp 主循环][team-loop] | 在 `!use_imu_as_input` 分支追踪 `predict`、IMU 更新、点更新的时间顺序 |
| 6 | [laserMapping.cpp 发布函数][team-output] | 算法内部更新时间与消息发布时间的区别；`camera_init/body` 如何接上导航的 `odom` 链 |

**理解问题：** `use_imu_as_input=False` 为什么仍可使用 IMU？没有邻近平面时，哪一项更新会缺失？点的时间偏移丢失后为什么不能简单“用整帧时间代替”？运行输出 20 Hz 是否能证明内部估计只更新 20 次？雷达—IMU 外参关闭在线估计后，是不是就不再需要正确的外参？

**纸面实验与交付：** 画一条 10 ms 时间轴，放 IMU 测量于 0、5、10 ms，雷达点于 2、4、7 ms。按源码输出状态分支标出相邻事件的传播 `dt`、IMU 更新与点到面更新；再故意把三个雷达点都记作 10 ms，说明丢掉了哪些时序信息。这是理解练习，不是在声称本队设备使用这些采样率。

另外交一页“测量到代码”表：变量、单位、时间来源、frame、源码函数，至少覆盖一个雷达点和一条 IMU。手算取平面 `z=0`、点变换后 `z=0.05` 时的点到面残差，再对照 `h_model_output` 中 `ekfom_data.z` 的负号约定。第一遍可跳过 MTK 宏展开、模板细节与被注释掉的试验代码。

**与本队参数核对：** 该固定版本 reality 配置为 `use_imu_as_input=False`、`mapping.imu_en=True`、`mapping.extrinsic_est_en=False`。在 [IMU 观测函数][team-estimator]可以找到角速度与加速度残差，在 [主循环][team-loop]可以找到实际调用；据此解释“IMU 作为观测”，不要把参数名称翻译成“关闭 IMU”。是否运行这些值仍要在训练机查运行参数。

## 7. 第六段：论文是对照表，不是本队功能清单（进阶，4～6 小时）

**先修：** 已能讲清第五段数据流，最好独立完成实验 B/C。阅读 R11 §III System Overview、§IV-A Kinematic Model、§IV-B 的 Propagation / Residual Computation / Iterated Update；先看状态和几何意义，再补推导。§V-A Map Management 用来认识局部地图维护，§V-D/F 的重建与复杂度分析、所有 benchmark 表格首次可跳过。

**理解问题：** FAST-LIO2 为何要把扫描内点变换到扫描结束时刻？它与 Point-LIO 逐点处理的思路有什么差别？论文中的算法吞吐率、ROS topic 频率、控制闭环带宽为何不能当作同一个数？不同雷达、运动条件与处理器的实验结果为何不能直接当作本队指标？

**交付：** 一张三列对照表“FAST-LIO2 论文 / Point-LIO 原作者说明或论文 / 本队固定源码”，至少比较更新粒度、IMU 角色、地图索引、外参估计、发布接口。未知项就写“待读/待运行”，不要用一个项目的宣传图替代另一个项目的事实。

这里有一项可以直接核对：R11 的地图结构是 ikd-Tree；本队 [Estimator.cpp][team-estimator]通过 `ivox_->GetClosestPoint` 搜索，[laserMapping.cpp][team-ivox]创建 IVox。读 ikd-Tree 的思想有价值，但不能据此写成本队目前采用了 ikd-Tree。同理，本队重定位节点的 GICP 与 Point-LIO 内部点到面更新，是不同位置的算法模块。

## 8. 有数据之后怎么接上，没数据如何结课

三个合成实验和源码笔记已经构成完整的离线路线；只需提前准备学习材料与软件依赖，运行不依赖网络、bag 或实车。拿到团队已登记的数据后，再按[传感器课的输入体检与隔离重跑](../sensor-lio/README.md)扩展，不用为做完本页先采一套实车数据。

R10 §6 的作者示例数据可以作为进阶材料，但本次只核对到官方说明，没有下载验证云盘。上游示例使用 `roslaunch` 和 ROS 1 消息环境，本队是 ROS 2 Humble 与 `livox_ros_driver2/msg/CustomMsg`；不能仅给 topic 改名就宣称兼容。转换前逐项记录：bag 容器、消息定义、点时间字段及单位、IMU 单位/量程、外参方向、时间基准、初始化状态。缺失的逐点时间不能靠转换工具自动恢复。

R10 明确对 `racing_drone.bag` 的非静止启动和 `PULSAR.bag` 的 IMU 量程给出单独设置。这些是作者数据的条件，不是本队 MID360 应统一照搬的参数。R8 中 KITTI 示例学习的是点云匹配流程，也不能据此推断数据已满足本队 Point-LIO 的输入契约。

结课时交三个实验脚本和结果、坐标图、滤波噪声对照表、源码函数表。能够解释一个错误方向、一个模型失配、一个错误配准，比“看完十一组资料”更能证明进步；实车定位性能仍由另外的受控实验验收。

## 9. 材料核查与维护说明

- R1–R4 已打开具体文字课/课程 Transcript，核对章节名和阅读入口；R5 已打开作者 PDF，核对第一版目录、§4.3、§5.1–5.2 和个人使用说明。
- R6/R7 已核对教程代码、解释与构建段；R8/R9 已核对上游示例路径，并与本队 `small_gicp/src/example/basic_registration.py` 及重定位封装交叉阅读。
- R10 已打开官方 README，核对外参定义、点时间要求、ROS 1 示例与数据集特殊设置；其 §1.2 指向 DOI `10.1002/aisy.202200459`。检索可核对到作者机构存档及论文 §3 / Figure 1，但此次直接打开 Wiley/HKU 全文失败，因此原论文只列为进阶补读，不作为核心路线的必需入口。
- R11 已打开原作者 arXiv v1 正文，核对 §III、IV、V 的真实标题。以上是材料/源码核查记录，不是课程实验已经完成的证明；上游页面变动后要复核路径与版本。

[team-loam]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp#L43-L98
[team-scan]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp#L38-L157
[team-model]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_robot_description/resource/xmacro/uic2025_sentry_robot.sdf.xmacro#L15-L22
[team-config]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L1-L174
[team-state]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/include/common_lib.h#L18-L41
[team-models]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/Estimator.cpp#L26-L110
[team-gicp]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/small_gicp_relocalization/src/small_gicp_relocalization.cpp#L26-L221
[team-cov]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/small_gicp/include/small_gicp/util/normal_estimation.hpp#L28-L91
[team-factor]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/small_gicp/include/small_gicp/factors/gicp_factor.hpp#L24-L72
[team-parameters]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/parameters.cpp#L54-L196
[team-preprocess]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/preprocess.cpp#L80-L160
[team-estimator]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/Estimator.cpp#L55-L385
[team-loop]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/laserMapping.cpp#L573-L677
[team-output]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/laserMapping.cpp#L182-L293
[team-ivox]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/point_lio/src/laserMapping.cpp#L311-L323
[team-example]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/small_gicp/src/example/basic_registration.py#L10-L68
