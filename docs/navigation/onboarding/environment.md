# S0：环境与工程基础

目标：在普通开发机建立最小可工作的 ROS2 环境，并能读懂项目如何构建。前置：会安装软件和打开终端。本页命令面向 **Ubuntu 22.04 / ROS2 Humble / Bash**，不是 Windows PowerShell 命令。Windows 可用虚拟机完成基础课；网口雷达、串口、Gazebo 图形性能和 DDS 跨机发现需要在队伍批准的 Linux 环境单独验证。

## 1. 先建立最小环境

沿用[Linux 基础](../../Linux教学/2.0Linux基础.md)、[配套练习](../../Linux教学/2.1Linux基础配套练习.md)、[SSH](../../Linux教学/3.ubuntu-ssh-guide.md)与[Git](../../git教学/1.git下载和如何使用github.md)。原 Ubuntu 安装占位页已转为本课入口；准确安装步骤见下方官方版本文档。

ROS 安装按[官方 Humble 安装文档](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)进行，若网页无法访问可读[官方 Humble 文档源码](https://github.com/ros2/ros2_documentation/blob/humble/source/Installation/Ubuntu-Install-Debs.rst)。操作系统、软件源和依赖版本以安装日官方说明为准；不混装其他 ROS 发行版来绕过错误。

安装完成后，在新终端检查：

```bash
cat /etc/os-release
source /opt/ros/humble/setup.bash
echo "$ROS_DISTRO"
command -v ros2
ros2 --help
ros2 pkg prefix demo_nodes_cpp
ros2 run demo_nodes_cpp talker
```

另开终端，同样 source 后执行 `ros2 run demo_nodes_py listener`，应持续收到递增数据。ROS2 CLI 不应靠 `ros2 --version` 判断发行版；看 `ROS_DISTRO`、包版本和环境报告。需要完整报告时使用已安装的 `ros2 doctor --report`。

## 2. 小工作区先于完整比赛工程

安装开发工具后创建自己的练习包：

```bash
sudo apt install build-essential cmake git python3-colcon-common-extensions python3-rosdep
mkdir -p ~/nav_training_ws/src
cd ~/nav_training_ws/src
ros2 pkg create --build-type ament_cmake nav_training --dependencies rclcpp std_msgs
cd ~/nav_training_ws
colcon build --symlink-install --packages-select nav_training
source install/setup.bash
ros2 pkg prefix nav_training
```

此时是空包骨架，T1 再添加可运行节点。能说明 `src`、`build`、`install`、`log` 的作用；`source /opt/ros/humble/setup.bash` 是基础环境，`source install/setup.bash` 是本工作区 overlay。修改参数文件后既要确认源文件，也要确认 launch 实际读取的安装路径。

## 3. 获取并检查本队工程

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027.git
cd Navigation-2027
git rev-parse HEAD
git status --short
git submodule status --recursive
cd ros_ws
colcon list
```

记录实际 commit，并与[审查基线](../README.md)比较。新人练习用自己的分支；不要把生产机器拉到最新主分支来试错。`colcon list` 只证明包能被发现，不证明依赖完整或能编译。

初始化 rosdep 数据库只需由环境维护者执行一次 `sudo rosdep init`；之后普通用户执行 `rosdep update`。在工作区使用：

```bash
rosdep check --from-paths src --ignore-src --rosdistro humble
rosdep install --from-paths src --ignore-src --rosdistro humble -y
```

这只覆盖已声明且有规则的依赖。未解析的键、源码库和模型资源必须记录，不使用一长串 `--skip-keys` 将错误隐藏。环境齐备后才尝试 `colcon build --symlink-install --packages-up-to pb2025_nav_bringup`，保留第一处失败日志；完成后 source 安装目录，用 `ros2 pkg prefix pb2025_nav_bringup` 确认包来源。**这是一条构建检查路径，本次未在 ROS 环境验证可成功构建。**

## 4. 当前代码不能当作开箱即用教学包

| 静态审查事项 | 新人应做的检查 | 负责人需要补齐 |
|---|---|---|
| README 要求 `rm_serial_driver`，当前导航树中未找到该包 | `colcon list` 和 `ros2 pkg prefix rm_serial_driver`；确认来自哪个 overlay | 实际自瞄/串口仓库 commit、启动命令、消息协议与 Topic |
| 根目录还有 `small_gicp`、`standard_robot_pp_ros2-main` 等，不能假设 `ros_ws/src` 会自动发现 | 查看目录、CMake 查找和实际安装来源 | 按各依赖文档建立单独可复现安装步骤；不能把不同串口实现随意互换 |
| 默认 world 与 README 示例不保证有完整地图 | 同时检查 YAML、图像、PCD 的真实路径和坐标关系 | 一套有版本、校验值、采集说明的地图包 |
| 已有仿真包，但有外部模型/PCD/版本依赖 | 阅读[仿真章节](../simulation/README.md) | 由老成员维护统一环境，避免新人各自搭一套 |
| reality YAML 与最终参数存在 launch 替换 | 用 `--show-args`、`ros2 param dump` 和包来源比较 | 发布一份实际运行命令及有效参数快照 |

基础学习不要因完整比赛工程的缺包而停住。继续 T0–T2、A* 和静态源码追踪，待训练材料齐备再做完整链路。

## 5. 编程只学本周用得到的部分

具体章节、预计投入、停止条件与带数值答案的小练习见[基础自学手册 F1–F6](../self-study/foundations.md)。按[周任务单](weekly-plan.md)逐步补齐，不要求先刷完整套 C++ 或 Python 课程。

| 能力 | 必须能做的事 | 对应代码阅读 |
|---|---|---|
| C++ | 读懂类、构造函数、引用、容器、智能指针、lambda/std::bind、回调；知道对象生命周期 | `loam_interface.cpp` 的订阅、发布和 TF 查询 |
| CMake | 添加 executable、ament 依赖、install 目标，说明头文件与库链接错误 | 小练习包→真实 package.xml/CMakeLists.txt |
| Python | 读参数、函数、类和脚本入口，不必先学完整语言课程 | reality launch 的参数与 IncludeLaunchDescription |
| Git | diff→分支→commit→push→PR；冲突时保留双方意图；用 revert 回退已共享提交 | 一项文档修订或隔离实验配置修改 |
| 工程观察 | 读第一条编译错误、保存命令、定位包来源、查看日志/CPU/内存/磁盘 | 后续所有任务 |

## 验收与常见错误

完成 [T0](../assignments/README.md)：同伴在新终端按 README 能复现；提交不包含 build/install/log、密钥或大 bag；能解释一次 source/包来源错误。常见失败是打开新终端未 source、在错误目录编译、混用多个工作区、改了源码配置但运行另一份安装。先确认这些，再处理算法问题。

下一步：[S1–S2 ROS2、TF、时间与运动](../ros2-tf/README.md)。
