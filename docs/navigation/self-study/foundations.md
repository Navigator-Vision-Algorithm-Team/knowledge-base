# 基础自学：学到能读节点、改小代码为止

适合 S0–S2，也可在 T9 前补缺。已会的部分用交付证明跳过；完全没有编程经验时，前两周只做最小程序，不强行与有竞赛编程基础的同学同速。页面中的时间是教学估算，包含指定练习，不包含系统安装和网络排障。

## F1：终端、文件与进程（必学，3–5 小时）

先读队内 [Linux 基础](../../Linux教学/2.0Linux基础.md)，再选 MIT Missing Semester 的 [The Shell](https://missing.csail.mit.edu/2020/course-shell/) 中路径、管道和重定向，以及 [Shell Tools and Scripting](https://missing.csail.mit.edu/2020/shell-tools/) 中查找文件、搜索内容与 shell 函数。用 Bash 练习，不将命令直接贴到 PowerShell。

**做什么**：在个人练习目录建立 `src/config/reports`，编写一个脚本输出日期、所在目录、Git commit 和 `ROS_DISTRO`；允许目录名含空格。将日志写入文件，用 `rg -n` 定位错误文本；比较标准输出和标准错误。脚本不采集口令、token 或整份环境变量。

**过关**：换一个工作目录仍可定位文件；故意给不存在的路径时能识别非零退出状态；能解释 `>` 覆盖和 `>>` 追加。暂不要求熟练 Vim、复杂正则或 shell 花式语法。

学有余力再读 [Command-line Environment](https://missing.csail.mit.edu/2020/command-line/) 的进程/信号、终端复用与 SSH：在教学程序上区分 Ctrl+C、后台运行、进程仍存在。回到[实车页](../debug-real/README.md)解释“终端退出”和“底盘停止”为何不是同一个检查项。

## F2：Git 变更与恢复（必学，3–4 小时）

官方中文 Pro Git 指定阅读：[2.2 记录更新](https://git-scm.com/book/zh/v2/Git-%E5%9F%BA%E7%A1%80-%E8%AE%B0%E5%BD%95%E6%AF%8F%E6%AC%A1%E6%9B%B4%E6%96%B0%E5%88%B0%E4%BB%93%E5%BA%93)、[2.4 撤消操作](https://git-scm.com/book/zh/v2/Git-%E5%9F%BA%E7%A1%80-%E6%92%A4%E6%B6%88%E6%93%8D%E4%BD%9C)、[3.2 分支的新建与合并](https://git-scm.com/book/zh/v2/Git-%E5%88%86%E6%94%AF-%E5%88%86%E6%94%AF%E7%9A%84%E6%96%B0%E5%BB%BA%E4%B8%8E%E5%90%88%E5%B9%B6)。先看工作区、暂存区、commit 和冲突；历史重写暂缓。

**做什么**：在练习仓库两个分支改同一参数说明，制造并解决冲突；保留双方有用内容。提交一次错误数值，再用 `git revert` 生成恢复提交；对比恢复前后文件。给自己的 PR 写清问题、修改、验证命令。

**过关**：口头解释为什么 `git diff` 和 `git diff --cached` 不同；展示提交图与恢复结果；`.gitignore` 排除 `build/install/log` 和大数据。不要在共享比赛分支练习强制推送或丢弃未提交文件。

## F3：C++ 最小语法与读代码顺序（必学，分散 8–12 小时）

零编程基础先在 [LearnCpp 目录](https://www.learncpp.com/) 按标题读第 1 章变量/初始化/输入输出，第 2 章函数/参数/多文件，以及第 8 章 if、for、while。先写“读入 x/y，输出距离”的命令行程序，再进入下表；不要直接跳到智能指针例子。

| 读哪部分 | 读完马上做什么 | 对应本队代码与停止条件 |
|---|---|---|
| [0.5 编译器、链接器和库](https://www.learncpp.com/cpp-tutorial/introduction-to-the-compiler-linker-and-libraries/)、[2.11 头文件](https://www.learncpp.com/cpp-tutorial/header-files/) | 把距离函数拆成 `.hpp/.cpp/main.cpp`，分别制造漏声明、漏实现两类错误 | 能分辨编译错误与链接错误，停止刷编译器原理 |
| [12.6 const 引用传参](https://www.learncpp.com/cpp-tutorial/pass-by-const-lvalue-reference/)；不熟指针先补同章 12.3–12.8 | 对一个点数组分别按值/const 引用传入；说明哪种允许修改和可能复制 | 看懂回调参数与只读消息，不要求实现容器内存管理 |
| [14.2 类](https://www.learncpp.com/cpp-tutorial/introduction-to-classes/)、[14.10 初始化列表](https://www.learncpp.com/cpp-tutorial/constructor-member-initializer-lists/) | 写 `Pose2D`，构造时初始化 x/y/yaw；列出对象创建到销毁顺序 | 读 `LoamInterfaceNode` 构造函数，找到成员、参数和 pub/sub |
| [16.2 std::vector](https://www.learncpp.com/cpp-tutorial/introduction-to-stdvector-and-list-constructors/) | 读入若干路点，空路径返回明确错误；检查索引范围 | 为 T5 路径容器与 T9 空输入处理做准备 |
| [20.7 Lambda captures](https://www.learncpp.com/cpp-tutorial/lambda-captures/)；先看页面前置 lambda 入门 | 写一个捕获阈值的函数，比较按值和按引用修改后的输出 | 能说明回调捕获对象是否仍存活，不要求复杂泛型 lambda |
| [22.5 unique_ptr](https://www.learncpp.com/cpp-tutorial/stdunique_ptr/)、[22.6 shared_ptr](https://www.learncpp.com/cpp-tutorial/stdshared_ptr/) | 画消息、订阅对象、节点成员的所有权关系，解释为何不用裸 `new/delete` 管理每个对象 | 读 `make_unique`、`SharedPtr/ConstSharedPtr`，先理解生命周期，再学多线程 |

本队并非统一使用最新 C++：例如 [loam_interface CMake](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/CMakeLists.txt) 指定 C++14，[pb_nav2_plugins CMake](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb_nav2_plugins/CMakeLists.txt) 指定 C++17。教程中的 C++20/23 写法不自动适用；以所改包和真实编译命令为准。

**综合小作业**：给 `Pose2D` 数组实现路径长度函数，输入 `(0,0),(3,4),(3,8)` 应得 `9`；单点得 `0`，空输入按自己写明的接口处理。使用 `-Wall -Wextra` 构建并解释警告。不要将“教程例子全能运行”当作读懂本队异步回调。

## F4：CMake 到 ament/colcon 的桥梁（必学，3–4 小时）

使用 CMake 3.22 教程的 [Step 1](https://cmake.org/cmake/help/v3.22/guide/tutorial/A%20Basic%20Starting%20Point.html)、[Step 2](https://cmake.org/cmake/help/v3.22/guide/tutorial/Adding%20a%20Library.html)、[Step 3](https://cmake.org/cmake/help/v3.22/guide/tutorial/Adding%20Usage%20Requirements%20for%20a%20Library.html)，重点是目标、源文件、链接库和头文件使用要求。后续打包、生成器表达式、交叉编译按需查阅。

**做什么**：把 F3 函数构建为一个库和一个可执行文件；从新的构建目录编译。然后回到 [S0 小包](../onboarding/environment.md)，在教学包里添加 executable、ament 依赖与 install 规则。再读 `loam_interface` 的 `ament_auto_add_library` 和 `rclcpp_components_register_node`，解释它为什么还可以作为组件加载。

**过关**：在构建日志找到真实的编译命令；说清 `package.xml` 依赖声明、CMake 目标、`colcon` 工作区构建的分工。能定位“找不到头文件”“undefined reference”“ros2 run 找不到 executable”的不同处理位置。无需背完整 CMake 命令表。

## F5：Python 阅读与实验工具（必学最小部分，3–5 小时）

Python 官方教程面向已有一些编程基础的读者。先完成 F3 的函数与循环，再读 Python 3.10 中文版 [第 4 章](https://docs.python.org/zh-cn/3.10/tutorial/controlflow.html) 的 for/range/函数定义、[第 5 章](https://docs.python.org/zh-cn/3.10/tutorial/datastructures.html) 的列表和字典、[第 7 章](https://docs.python.org/zh-cn/3.10/tutorial/inputoutput.html) 的文件读写、[第 8 章](https://docs.python.org/zh-cn/3.10/tutorial/errors.html) 的异常。需要 import/类时再查[目录](https://docs.python.org/zh-cn/3.10/tutorial/index.html)第 6、9 章。

**做什么**：用 Python 标准库读取 CSV，列为 `stamp_s,x_m,y_m`，输出每段 dt 和平面速度。固定样本为 `(0,0,0),(1,3,4),(1,3,4),(0.5,3,4)`：第一段速度为 `5 m/s`，后两段应报告重复/回跳并按写明策略处理，不输出无穷大或偷偷取绝对值。

**对应代码**：读 [reality launch](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/rm_navigation_reality_launch.py) 的函数、字典、路径组合和 `LaunchConfiguration`。区分普通 Python 字符串与 launch 在运行上下文求值的对象；能找到参数默认值、传递位置和覆盖点。数据分析工具以后再加，不为读 launch 先学完整科学计算栈。

## F6：从日志到调试器（了解到进阶，3–6 小时）

读 [Missing Semester Debugging and Profiling](https://missing.csail.mit.edu/2020/debugging-profiling/) 的调试、日志和性能测量部分。用自己的路径长度程序练习：断点停在入口→查看实参→单步到计算→检查调用栈。让空数组触发自己定义的错误，展示错误发生位置。

初学停止于“能定位到出问题的函数和数据”；需要处理节点卡顿、内存或回调阻塞时进入 [ROS2 系统专题](ros2-systems.md)。优化前先保存测量基线，不能凭 CPU 高就重写算法。

## 完成基础补课之后

拿 [源码练习 R1](../assignments/reading-labs.md) 检验自己能否读出一个真实节点的接口。还不能解释智能指针或回调，就只补对应 F3 行；不重新从整本 C++ 第一页开始。概念笔记应包含英文名、一个例子和本队文件路径，方便下次遇到直接查。

以上资源均有免费正文；本页按 2026-09-14 可见标题核对。课程页章节会调整，以链接标题和自己保存的学习记录为准。
