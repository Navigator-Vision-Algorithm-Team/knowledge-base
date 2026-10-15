# 导航 Debug 代码详解：零基础新人版

<small>整理与维护：24cst朱鑫鹏</small>

知识库适配日期：2026-10-10。命令工具面向 Ubuntu 22.04 / ROS 2 Humble / Bash；实机路径、参数和带读代码来自 2026-09 的本地化 PB2025 部署案例。

**本知识库主线是 Navigation-2027，源码审查基线为 `183a4109b0de2030bb8970a54654937c8b039ba9`。历史 PB2025 的本地修复没有被证明已进入该基线。** 先阅读 [环境与工程基础](../onboarding/environment.md)和[本队源码审查证据](../system/nav2-and-control-evidence.md)，登记实际工作空间、commit、命名空间、串口实现和地图。本文所有 `/home/ubuntu/navigation_2025/...`、独立 `/home/ubuntu/ros_ws` 路径及历史 PID/IP/地图名均为案例值，不是当前本队默认部署。

本次仅更新培训知识库，不修改 Navigation-2027 生产源码。通用命令可按实际名称使用；本地化专有参数/诊断话题不存在时先登记版本差异，不盲目添加。

阅读顺序：**先学本书，再使用 [导航 Debug 排查手册](runbook.md)**。本书解释检查命令的组成、输出字段、基础概念，以及配套采集脚本的代码；排查手册负责按具体故障查处理步骤。

文中的输出示例用于教学，不是机器人此刻的实测结果。现场必须看本次输出。我们保留此前验证过的情况，也标出尚未验证的结论。

## 0. 学习路线与动手约定

### 0.1 按什么顺序读

| 阶段 | 阅读章节 | 学完能做什么 |
| --- | --- | --- |
| 认识环境 | 1–3 | 找到正确终端、路径和工作空间，理解最常见命令符号 |
| 认识 ROS | 4 | 分清程序、数据、坐标和导航目标 |
| 看程序与数据 | 5–9 | 查重复实例、话题频率、TF 与时间 |
| 看 Goal 到底盘 | 10–12 | 确认目标是否到达、速度是否传给串口 |
| 看定位与避障 | 13–15 | 认识地图、代价地图和自旋参数 |
| 看环境与错误 | 16–18 | 读懂构建、日志、RViz 和 SSH 检查 |
| 看完整代码 | 19–20 | 理解两终端启动流程和采集脚本 |
| 做练习 | 21–22 | 用一段输出说明判断依据，再查排查手册 |

### 0.2 哪些终端可以运行这些命令

`bash` 代码块：在机器人 Linux 的终端执行，可以是在 Ubuntu 桌面打开的终端，也可以是已经 SSH 登录进去的终端。

`powershell` 代码块：在 Windows PowerShell 执行。

`text`、`yaml`、`xml`、`cpp` 代码块：主要是输出或代码教学示例；不要把它们直接粘贴到 Bash 提示符执行。第 20 节的 `bash` 片段也用于解释脚本结构，不是要求逐段粘贴执行。

这两种提示符表示不同环境：

```text
PS C:\Users\student>                              Windows PowerShell
ubuntu@ubuntu:~/navigation_2025/ros_ws$            已登录 Ubuntu 的 Bash
```

提示符不是命令的一部分。复制 `ubuntu@ubuntu:...$` 会导致终端把用户名等当成命令。

### 0.3 执行与停止

输入命令后按 Enter。提示符重新出现通常意味着命令已结束；连续输出命令要按 `Ctrl+C` 或等 `timeout` 自动结束。

在检查终端按 `Ctrl+C`，停止的是正在执行的检查。**在导航启动终端按 `Ctrl+C`，停止的是导航 launch。** 两者的按键相同，作用对象不同。

一次复制一个代码块，确认最后一行之后有换行，不要反复连着粘贴。此前出现的 `*.xmlcd`、`pb2025_nav_bringupcd`，就是上一条末尾与下一条开头连在一起。

### 0.4 看懂操作类型

| 标签 | 例子 | 会改变什么 |
| --- | --- | --- |
| 查看 | `ps`、`ros2 topic info`、`ros2 param get` | 主要读取状态；ROS 检查可能创建临时订阅/诊断节点 |
| 写报告 | `mkdir`、采集脚本、`view_frames` | 创建目录或报告文件 |
| 启停程序 | `ros2 launch`、`kill -INT`、`ros2 daemon stop` | 改变对应程序的运行状态 |
| 改文件/构建 | `mv`、`sed -i`、`colcon build` | 改文件位置、内容或安装产物 |

初学练习优先做“查看”。有运行中的机器人时，先知道自己操作的是哪个终端、哪个程序。

## 1. 路径、目录和工作空间

先把工作空间看作一套“源码→构建→安装→运行”的工具箱。终端当前在哪个目录，决定相对路径从哪里找；source 了哪套安装环境，决定 ROS 从哪里找包。例如你站在工作空间根目录，`install/setup.bash` 才是预期位置；站在 `src` 内，同样的写法会去找 `src/install/setup.bash`。所以先 `pwd`，再运行依赖相对路径的命令。

### 1.1 `cd` 是进入目录

```bash
cd /home/ubuntu/navigation_2025/ros_ws
```

| 部分 | 意思 |
| --- | --- |
| `cd` | change directory，改变当前目录 |
| `/home/ubuntu/...` | 从文件系统根目录开始的绝对路径 |
| `ros_ws` | 我们这个工作空间的目录名，本身不是命令 |

执行后可以检查：

```bash
pwd
```

`pwd` 显示当前所在目录。预期输出：

```text
/home/ubuntu/navigation_2025/ros_ws
```

`source install/setup.bash` 使用相对路径，依赖当前目录；`source /home/ubuntu/navigation_2025/ros_ws/install/setup.bash` 使用绝对路径，不依赖当前目录。

### 1.2 `~`、相对路径和绝对路径

| 写法 | 在 ubuntu 用户下的意义 |
| --- | --- |
| `~` | 当前用户的家目录，一般为 `/home/ubuntu` |
| `~/navigation_2025/ros_ws` | 家目录下的导航工作空间 |
| `install/setup.bash` | 当前目录下面的这个文件 |
| `.` | 当前目录 |
| `..` | 当前目录的上一层 |

`~/ros_ws` 与 `~/navigation_2025/ros_ws` 是两个不同目录。一个主要放串口/视觉相关程序，一个主要放导航程序，不能因为都叫 `ros_ws` 就混用。

### 1.3 工作空间的四个目录

| 目录 | 作用 | 新人要记住的事 |
| --- | --- | --- |
| `src` | 源码和配置 | 正式修改通常在这里做 |
| `build` | 编译中间结果 | 由构建工具生成 |
| `install` | 安装后的运行文件 | ROS 启动时常用的是这里的内容 |
| `log` | 构建工具日志 | 与 `/home/ubuntu/.ros/log` 中的 ROS 运行日志区分 |

“我改了 src 里的文件”与“运行程序已经用上改动”是两件事，后面第 16 节会教你核对。

## 2. 每个新终端为什么要 `source`

终端启动程序时，会把自己的环境变量交给它，类似给程序一张“到哪里找工具”的地址单。另一个终端有另一张地址单；第一个终端 source 成功，不会替第二个填写。比如同一个包在新终端提示找不到，在已 source 的终端却能查到 prefix，先比较环境来源，而不是立即重装包。

以下加载顺序属于历史双工作空间部署。Navigation-2027 的克隆工作空间通常是仓库下的 `ros_ws`，串口依赖另见环境登记；不要按案例路径覆盖已经验收的当前 overlay。

操作类型：加载当前终端的环境，不等于启动导航。

```bash
cd /home/ubuntu/navigation_2025/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source /home/ubuntu/ros_ws/install/setup.bash
source /home/ubuntu/navigation_2025/ros_ws/install/setup.bash
```

逐行解释：

| 行 | 做了什么 | 为什么需要 |
| --- | --- | --- |
| `cd ...` | 进入导航工作空间 | 后面的相对路径和构建位置明确 |
| `unset LD_LIBRARY_PATH` | 删除当前 shell 中这个变量的值 | 清掉以前可能干扰 ROS/PCL 的库路径 |
| `source /opt/ros/humble/setup.bash` | 在当前 shell 执行 Humble 环境脚本 | 让终端能找到 ROS 命令和基础包 |
| `source /home/ubuntu/ros_ws/install/setup.bash` | 加载串口/视觉工作空间 | 让终端能找到 `rm_serial_driver` 等包 |
| `source /home/ubuntu/navigation_2025/ros_ws/install/setup.bash` | 加载导航工作空间 | 让终端能找到导航包和本地覆盖版本 |

### 2.1 环境变量是什么

环境变量是程序启动时能读取的配置值，例如程序搜索路径、ROS 域编号等。查看指定变量：

```bash
printenv LD_LIBRARY_PATH
```

输出可能是多个用 `:` 分隔的目录。没有输出可能表示没有设置。`unset` 不会删除磁盘上的库文件；后续 `source` 会设置 ROS 需要的路径。

### 2.2 `source` 与 `bash 文件` 的区别

`source` 在**当前终端的 shell**里执行脚本，使里面的环境设置保留下来。

`bash /某个脚本.sh` 会启动一个新的 Bash 来执行文件。它适合运行采集脚本，但子 shell 里的环境修改一般不会回传到父终端。

`install/setup.bash` 通常还会加载构建时记录的父环境，所以此前只 `source install/setup.bash` 也能工作。若换了工作空间、安装状态或构建来源，完整的加载顺序更容易检查。

### 2.3 新开终端不会自动继承另一个终端刚做的设置

在终端 A source 后，终端 B 仍可能没有 ROS 环境。出现 `ros2: command not found` 时，先在当前终端执行上面的环境步骤。

## 3. Bash 命令里的符号与参数

这节先读懂符号，后面的长命令才有意义。

先区分“shell 帮你处理的符号”和“程序收到的参数”。例如 `|` 由 shell 连接两条命令，`--field header` 则交给 `ros2 topic echo` 解释。命令报错时，看它是在执行前就拼错了，还是 ROS 已执行却找不到接口；这能避免把粘贴错误当作机器人故障。

### 3.1 命令、选项、参数

```bash
ros2 topic info /red_standard_robot1/odometry -v
```

| 部分 | 分类 | 意思 |
| --- | --- | --- |
| `ros2` | 主命令 | 使用 ROS 2 命令行工具 |
| `topic` | 子命令 | 操作话题相关工具 |
| `info` | 操作 | 查询话题端点信息 |
| `/red_standard_robot1/odometry` | 参数 | 要查询的话题名 |
| `-v` | 选项 | verbose，显示详细信息 |

`-v`、`-n` 等选项的意思取决于**前面是哪一个程序**，不能把 `grep -n` 的含义套给所有命令。可用 `--help` 查看该命令支持的选项：

```bash
ros2 topic echo --help
```

### 3.2 管道 `|`

```bash
ros2 node list | sort | uniq -d
```

执行顺序：列出节点 → 把节点名排序 → 只显示重复的名字。

`|` 把左边命令的标准输出交给右边命令作为输入；它本身不表示多个 ROS 节点互相订阅。

### 3.3 `grep` 是筛选文字

```bash
ros2 action list -t | grep navigate_to_pose
```

`grep navigate_to_pose` 保留包含这个字符串的行。没有输出有可能是没匹配到，也可能左边命令就失败了，需看有没有错误。

| 选项 | 意思 |
| --- | --- |
| `-n` | 显示文件内行号 |
| `-i` | 忽略大小写 |
| `-E` | 使用扩展正则表达式，支持 `A\|B` 等写法 |
| `-R` | 递归搜索目录，GNU grep 会跟随遇到的符号链接 |

`grep -RniE` 是把 `-R`、`-n`、`-i`、`-E` 合在一起。

### 3.4 同样的 `|`，在引号里也可能是正则“或者”

```bash
grep -nE 'inflation_radius|cost_scaling_factor|footprint_padding' /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml
```

引号内的 `|` 被传给 grep，表示匹配三种关键词中的任意一种；引号外的 `|` 才是 shell 管道。

示例：

```text
423:        inflation_radius: 0.60
```

`423` 是文件行号，`0.60` 是参数值。文件修改后行号会变化，不用死记行号。

### 3.5 通配符与正则不要混淆

| 写法 | 谁处理 | 意思 |
| --- | --- | --- |
| `/dev/ttyACM*` | Bash 文件名展开 | 匹配这个路径下以 ttyACM 开头的名字 |
| `'component_container.*nav2_container'` | grep 的正则 | 两段文字中间允许有任意数量字符 |
| `'^/'` | grep 的正则 | 只匹配以 `/` 开头的行 |
| `'[r]m_serial_driver'` | grep 的正则 | 匹配 rm_serial_driver，同时通常避开 grep 自身的命令行 |

`*` 在文件通配符中和在正则中规则不同。正则中的 `.` 表示任意一个字符，`.*` 表示任意数量字符。

### 3.6 引号、变量和空格

```bash
PARAM=/home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml
grep -n 'inflation_radius' "$PARAM"
```

第一行把路径存到名为 `PARAM` 的变量；第二行的 `$PARAM` 取出变量值。变量赋值时 `=` 两边不加空格。

单引号 `'...'` 通常原样保留里面的字符；双引号 `"..."` 允许展开变量，并将展开后的字符串保留为一个参数。给文件路径变量加双引号，可以避免空格把路径拆成多个参数。

### 3.7 多行续写 `\` 和连接命令 `&&`

```bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py \
  slam:=True \
  use_robot_state_pub:=True \
  use_rviz:=True
```

前三行末尾的 `\` 表示当前命令还没结束，下一行接着读。`\` 必须紧挨换行，后面不要追加空格、文字或注释。最后一行不需要 `\`。

`&&` 表示前一条命令成功后再执行下一条，例如 `cd ... && colcon build ...`。新人排查时逐行执行更容易发现哪一步失败。

`:=` 是 ROS launch 参数或 ROS remap 中使用的语法，不等于 Bash 的变量赋值 `=`。

### 3.8 输出重定向

| 符号 | 意思 | 例子用途 |
| --- | --- | --- |
| `>` | 把标准输出写入文件，覆盖原内容 | 创建报告 |
| `>>` | 把标准输出追加到文件末尾 | 累积不同检查结果 |
| `2>` | 重定向错误输出 | 保存或隐藏错误 |
| `2>/dev/null` | 丢弃错误输出 | 搜不存在的可选目录时减少杂音 |
| `2>&1` | 让错误输出去当前标准输出所在位置 | 把正常输出与错误都记入报告 |

文件描述符 `1` 是标准输出，`2` 是标准错误。重定向顺序有意义：`> report.txt 2>&1` 才能先将标准输出设到文件，再让错误输出跟过去。

隐藏错误只改变你看到的输出，不会修好问题。新人第一次检查路径时，可以先不加 `2>/dev/null`，看清具体失败原因。

### 3.9 `head`、`tail`、`sort`、`uniq`

| 命令 | 意思 |
| --- | --- |
| `head -n 25` | 只显示前 25 行 |
| `tail -n 80` | 只显示后 80 行 |
| `sort` | 对文本行排序 |
| `uniq -d` | 只打印相邻的重复行，因此节点排查先 sort |

`tail` 可以保留报错尾部，但可能漏掉真正触发问题的第一条错误。需要完整时回到原日志文件。

### 3.10 `timeout` 与退出码

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/odometry
```

| 部分 | 意思 |
| --- | --- |
| `timeout` | 给后面的检查程序设置运行时限 |
| `--signal=INT` | 达到时限时先发 SIGINT，类似按 Ctrl+C |
| `--kill-after=2s` | 若收信号后还不退出，再等 2 秒后强制结束这次检查 |
| `6s` | 正常采样时长 6 秒 |
| `ros2 topic hz ...` | 实际要运行的检查命令 |

它针对自己启动的检查进程，不是自动关闭已经运行的导航 launch。连续检查到时退出时，退出码 `124` 常见；被强制终止或提前失败会有其他码。

紧跟一条命令后可以读取：

```bash
echo $?
```

`$?` 是上一条命令的退出码。通常 `0` 为成功，但意义仍取决于程序：grep 无匹配会返回 `1`，不等于导航程序崩溃。执行别的命令之后 `$?` 就已经换成新的结果。

## 4. ROS 里的八个基础名词

一台机器人里可以有很多程序：传感器程序发数据，定位程序处理数据，导航程序接受任务，串口程序交给硬件。ROS 的这些名词，就是描述“谁工作、通过什么接口、使用什么坐标、现在处于什么状态”的共同语言。下面每个词都要能落到一条检查命令，后面才有办法把故障缩小到某一段。

### 4.1 包、程序、进程、节点

| 名词 | 意思 | 本项目例子 |
| --- | --- | --- |
| 包 package | 用来组织和安装代码、资源、启动文件的单位 | `pb2025_nav_bringup` |
| 可执行程序 executable | 可启动的程序文件 | `pointlio_mapping` |
| 进程 process | 操作系统正在运行的一个程序实例 | `ps` 中带 PID 的一行 |
| 节点 node | ROS 图中的计算/通信单位 | `/red_standard_robot1/point_lio` |

一个程序可以创建多个 ROS 节点；一个容器进程可以运行多个组件节点。所以“只有一个进程”不代表“只有一个节点”。

### 4.2 话题与消息

话题 topic 是数据通道的名字，例如 `/red_standard_robot1/odometry`。

消息 message 是每次发送的数据，例如里程计的位置、姿态、速度。消息类型定义字段结构，例如 `nav_msgs/msg/Odometry`。

发布者 publisher 向话题发送，订阅者 subscriber 从话题接收。话题名相同但类型不匹配，或 QoS 不兼容，都可能无法形成你期望的数据通路。

### 4.3 命名空间 namespace

```text
/red_standard_robot1/odometry
 └─ 命名空间             └─ 话题名
```

命名空间帮助区分机器人或不同模块。节点相对名字 `odometry` 在这个命名空间下可解析成完整路径；开头带 `/` 的名字是绝对 ROS 名字。

文件系统路径与 ROS 名字是两套系统：`/home/ubuntu/...` 是磁盘路径，`/red_standard_robot1/...` 是 ROS 图中的名字。

### 4.4 TF、frame 和变换

frame 是坐标系的名字；TF 描述两个坐标系之间的位置与朝向关系。

```text
map → odom → base_footprint → 其他机器人坐标系 → front_mid360
```

箭头表示坐标变换关系，不是速度数据正在沿箭头传输。真实中间关节以当前 TF 树为准。

### 4.5 Action、Service、Topic

| 通信方式 | 适合什么 | 例子 |
| --- | --- | --- |
| Topic | 持续数据流 | 雷达点云、速度、里程计 |
| Service | 一次请求、一次回应 | 查询节点/设置相关服务 |
| Action | 持续任务，有接收、反馈、结果，可取消 | NavigateToPose 导航目标 |

点一次 Goal 是提出一项导航任务；不是直接让电机执行固定速度。

### 4.6 生命周期 lifecycle

部分 ROS 节点先被创建，再配置，再激活，最后清理和退出。节点出现在列表里，可能仍未激活工作。

Nav2 常见节点 `bt_navigator`、`planner_server`、`controller_server` 使用 lifecycle。

### 4.7 参数 parameter

参数是一个节点的设置，例如 `use_sim_time`、膨胀半径、控制频率。

YAML 是磁盘上写好的配置；运行参数是程序此刻登记的值；某些内部变量又可能通过话题改变。这三者不一定完全同步。

### 4.8 组件 component 与容器 container

组件是能装进容器进程的 ROS 节点实现。容器相当于把多个节点放在同一个进程中运行。

`ros2 component list` 查容器装了什么。列表前面的 `1`、`2` 是容器内的组件 ID，不是操作系统 PID。

在本队 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py][guide-components] 中，`LoadComposableNodes` 把 loam_interface、sensor_scan_generation、fake_vel_transform 等列进同一个目标容器。源码说明“准备加载哪些组件”，现场 `component list` 才说明“此刻真正装了哪些”；比较两者时尤其留意重复组件与启动条件。

## 5. 怎么读“是否重复启动”的命令

对应排查手册第 3 节。

重复启动的危险在于两个来源可能交替送入下游：一个里程计认为 x=1 米，另一个认为 x=3 米，消费者看到的就像位置突然跳了 2 米。这个示意解释了为何要同时看进程、节点与端点，不能只凭“终端里只有一个 launch”排除后台或其他电脑的来源。

### 5.1 `ps`：看本机进程

操作类型：查看。

```bash
ps -eo pid,ppid,stat,etimes,args | grep -E '[r]m_navigation_reality_launch|[c]omponent_container.*nav2_container|[p]ointlio_mapping|[l]ivox_ros_driver2_node|[r]m_serial_driver'
```

| 部分 | 意思 |
| --- | --- |
| `ps` | 显示进程状态 |
| `-e` | 查看本机所有进程 |
| `-o ...` | 指定显示哪些列以及列顺序 |
| `pid` | 当前进程编号 |
| `ppid` | 父进程编号 |
| `stat` | 进程状态 |
| `etimes` | 已运行的时间，单位秒 |
| `args` | 进程启动时的完整命令和参数 |
| `grep -E ...` | 只保留导航、雷达、串口等相关进程 |

教学输出：

```text
3199 2784 Sl 120 /usr/bin/python3 ... ros2 launch ... world:=final2 slam:=False
6196 3199 Sl 103 .../livox_ros_driver2_node ...
6198 3199 Sl 103 ... component_container_isolated ... __node:=nav2_container
```

`6196`、`6198` 的 PPID 都是 `3199`，说明它们由这个父进程启动。`slam:=False` 说明这条 launch 用的是导航模式，`world:=final2` 显示它选的地图参数。

常见状态：`R` 运行，`S` 可中断睡眠/等待，`D` 不可中断等待，`T` 停止，`Z` 僵尸；后面 `l` 常表示多线程。`Sl` 很常见，并不等于程序卡住。

### 5.2 重名节点检查

```bash
ros2 node list | sort | uniq -d
```

教学输出：

```text
/red_standard_robot1/loam_interface
/red_standard_robot1/sensor_scan_generation
```

这意味着 ROS 图里这些名字重复了，不是意味着“这里只运行了两个节点”。没有输出时，先确认 `ros2 node list` 本身成功。

`ps` 只看本机；ROS 图也可能发现同一 ROS 域中其他电脑的节点。因此重名时还要查组件列表与话题发布端点。

### 5.3 组件列表

```bash
ros2 component list
```

教学输出：

```text
/red_standard_robot1/nav2_container
  1 /red_standard_robot1/loam_interface
  2 /red_standard_robot1/sensor_scan_generation
  15 /red_standard_robot1/loam_interface
  16 /red_standard_robot1/sensor_scan_generation
```

同一容器内出现相同名字的组件，才有了“同一容器重复加载”的直接证据。操作系统仍可能只显示一个容器 PID。

### 5.4 为什么三个检查要一起用

| 工具 | 回答的问题 |
| --- | --- |
| `ps` | 本机启动了几套程序，参数是什么 |
| `ros2 node list` | ROS 图里有哪些节点名，有没有重名 |
| `ros2 component list` | 一个容器里面是否装了重复组件 |

我们此前的完整问题是：桌面登录自动启动旧 `final2` 导航，又手动启动建图。仅看正在操作的建图终端，看不到后台旧导航；这就是先查程序来源的原因。

## 6. 自启动、PID 和停止命令怎么读

对应排查手册第 3 节。以下涉及停止程序或移动文件，执行前先核对对象。

自启动配置是“下次从哪里启动”，PID 是“这次哪个程序正在运行”。移走桌面启动项不能停止已运行进程；停止 PID 也不能防止下次登录又启动。历史案例需要这两层都处理，所以本节先找当前对象，再查长期启动来源。

### 6.1 查指定 PID

```bash
ps -p 3199 -o pid,ppid,stat,args
```

`-p 3199` 只检查这个 PID。`3199` 是历史教学值；**必须替换成当前旧导航进程的 PID**。重启后进程号会变化，同一个数字可能已经属于别的程序。

### 6.2 发停止信号

```bash
kill -INT 3199
```

`kill` 用来给进程发信号，名字并不意味着每次都强制杀死。`-INT` 是 SIGINT，给程序机会进行正常退出和保存。

发出信号不表示进程已经退出，要再次用 ps 检查。建图可能在正常退出时写 PCD，所以不要连续重复 Ctrl+C 或直接强杀代替完整退出。

### 6.3 查开机自启动文字

```bash
grep -RniE 'nav_test|rm_navigation_reality_launch|start_nav_tuned|world:=final2' /home/ubuntu/.config/autostart /etc/xdg/autostart 2>/dev/null
```

两个路径分别是该用户的桌面自启动目录和系统桌面自启动目录。`2>/dev/null` 隐藏不存在目录等错误。

教学输出：

```text
/home/ubuntu/.config/autostart/nav_test.desktop:4:Exec=/home/ubuntu/start_nav_test.sh
```

依次是文件路径、第 4 行、行内容。`Exec=` 表示这个桌面启动项运行哪一个程序。

### 6.4 移出自启动目录

```bash
mkdir -p /home/ubuntu/.config/autostart-disabled
mv -i /home/ubuntu/.config/autostart/nav_test.desktop /home/ubuntu/.config/autostart-disabled/nav_test.desktop
```

第一行：建立备份目录；`-p` 允许创建中间目录，目录存在时也可以继续。

第二行：`mv` 将源文件移动到目标路径；`-i` 在目标已存在时询问是否覆盖。不是删除启动文件。

移走启动项会影响以后桌面登录，不能停止它此前已经启动的程序。

### 6.5 其他自动启动来源

```bash
systemctl --user list-units --all | grep -Ei 'nav|robot|ros'
systemctl list-units --all | grep -Ei 'nav|robot|ros'
crontab -l
```

`systemctl` 查询 systemd 服务；`--user` 是当前用户的服务，没带则查询系统服务；`--all` 包含非活动项。grep 只筛名字，名字匹配仍需核对具体服务内容。

`crontab -l` 列出当前用户的定时任务。`no crontab` 可能只是没有配置，不是导航故障。

## 7. 话题、端点、QoS 和频率详解

对应排查手册第 5、7、9、12 节。

数据通路要依次满足：两端名称一致、类型一致、QoS 兼容、发送回调真的执行。`list` 看登记，`info` 看连接条件，`echo/hz` 看当前检查者是否收到数据。比如 Topic 存在且发布数为 1，echo 仍超时，这些证据并不矛盾：publisher 可以创建后一直等待输入。本队 [ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp][guide-loam-endpoints] 就在构造时创建端点，数据发布发生在后续回调中。

### 7.1 `topic list -t`

```bash
ros2 topic list -t
```

`list` 列出话题；`-t` 同时列消息类型。例如：

```text
/red_standard_robot1/odometry [nav_msgs/msg/Odometry]
/red_standard_robot1/cmd_vel [geometry_msgs/msg/Twist]
```

看到话题名说明图中发现了相关端点，不能证明消息一直在发送。

### 7.2 `topic info -v`

```bash
ros2 topic info /red_standard_robot1/aft_mapped_to_init -v
```

示例字段：

```text
Type: nav_msgs/msg/Odometry
Publisher count: 1
Subscription count: 4
Node name: point_lio
Node namespace: /red_standard_robot1
Endpoint type: PUBLISHER
GID: ...
QoS profile:
  Reliability: RELIABLE
  Durability: VOLATILE
```

| 字段 | 解释 |
| --- | --- |
| `Type` | 这个话题的消息结构 |
| `Publisher count` | 发现的发布端点数量 |
| `Subscription count` | 发现的订阅端点数量 |
| `Node name` 与 `Node namespace` | 该端点所属节点的名字与命名空间 |
| `Endpoint type` | 当前列出的这一段是发布者还是订阅者 |
| `GID` | 中间件中的端点标识，帮助区分不同实例，不用背内容 |
| `QoS profile` | 通信的可靠性、持久性等规则 |

`Publisher count: 1` 可能只是程序创建了 publisher，实际回调仍没跑；继续用 hz/echo 确认有数据。

订阅数 `4` 可以来自四个不同消费者，也可以来自重复实例；必须看下面逐个端点属于谁。运行诊断 echo/hz 自身也会增加订阅数。

### 7.3 QoS 用最少的规则理解

| 项目 | 常见取值 | 新人如何理解 |
| --- | --- | --- |
| Reliability | `RELIABLE`、`BEST_EFFORT` | 可靠传输要求与尽力发送 |
| Durability | `VOLATILE`、`TRANSIENT_LOCAL` | 是否可向后加入的订阅者提供发布者缓存的历史样本 |
| History/Depth | KEEP_LAST 等、队列深度 | 保留多少历史数据的规则 |

发布者只提供 BEST_EFFORT，而订阅者要求 RELIABLE，可能不兼容。发布者提供 RELIABLE、订阅者只要求 BEST_EFFORT，在这一项上通常兼容。持久性等其他条件也需要匹配。

点云诊断使用 `--qos-reliability best_effort`，是让这个检查订阅者使用相应规则，不是在修改雷达驱动的发布设置。

### 7.4 `topic hz`：测收到的更新频率

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic hz /red_standard_robot1/odometry
```

教学输出：

```text
average rate: 19.994
min: 0.000s max: 0.100s std dev: 0.03137s window: 102
```

| 字段 | 含义 |
| --- | --- |
| `average rate` | 这个检查订阅者收到消息的平均频率，单位 Hz |
| `min` | 消息到达间隔的最小值，单位秒 |
| `max` | 消息到达间隔的最大值 |
| `std dev` | 间隔的标准差，越大说明间隔变化越明显 |
| `window` | 当前统计窗口里的间隔样本数 |

`20 Hz` 表示每秒大约 20 次，平均间隔约 `0.05 s`。`0.100 s` 最大间隔表示某次收到更新相隔约 100 毫秒；不能仅靠这一项断言底盘必定掉线。

初始 `topic does not appear to be published yet`，随后有稳定频率，可能只是发现端点需要时间。一直没频率时要结合 info、QoS 和节点日志。

`hz` 统计接收频率的含义也可对照 [ROS 2 Humble 话题入门](https://docs.ros.org/en/humble/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)。

### 7.5 为什么要查多个话题

| 话题后缀 | 在这套工程中主要代表 |
| --- | --- |
| `livox/lidar/pointcloud` | 驱动发布的点云 |
| `livox/imu` | 驱动发布的 IMU |
| `aft_mapped_to_init` | Point-LIO 估计的运动状态 |
| `cloud_registered` | Point-LIO 已配准点云 |
| `lidar_odometry` | loam_interface 转接后的里程计 |
| `registered_scan` | loam_interface 转接后的点云 |
| `odometry` | 后续导航使用的里程计 |

例如原始点云 `20 Hz`，但最后 odometry 无数据：雷达的那一段有输出，还不能证明整条链成功。需要从上向下查到第一次断开的位置。

### 7.6 `node info`：一个节点接了什么

```bash
ros2 node info /red_standard_robot1/sensor_scan_generation
```

重点读 `Subscribers`、`Publishers`，分别表示它的输入和输出。参数/服务等辅助端点可能很多，先找到你正在排查的数据通道。

同名节点重复存在时，node info 的结果可能含混，先做去重排查。

## 8. TF 检查命令与输出逐项解释

对应排查手册第 4、8、13 节。

TF 回答的是“同一个东西，在另一套坐标尺里在哪里”。雷达读到前方 1 米的桌腿，车体参考原点却可能在雷达后方 0.2 米，不能原样把 1 米当作桌腿到底盘原点的距离。先检查安装变换，再检查机器人在地图中的变换；两者任何一段缺失或时间不匹配，点云都可能无法放到正确位置。

### 8.1 三个坐标系和雷达坐标系

| frame | 含义 |
| --- | --- |
| `map` | 地图坐标系，保存地图和全局目标使用它 |
| `odom` | 连续的局部里程计坐标系，长期可能漂移 |
| `base_footprint` | 本项目中的车体底部参考坐标系，实际定义以机器人模型为准 |
| `front_mid360` | 雷达相关坐标系 |
| `gimbal_yaw` 等 | 云台或项目自定义坐标系，不能仅看名字推断真实运动 |

有了 TF，程序才能把“雷达坐标里的桌腿”换算为“地图里哪里是障碍”。

### 8.2 拆解完整命令

```bash
timeout --signal=INT --kill-after=2s 8s ros2 run tf2_ros tf2_echo odom base_footprint --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

| 部分 | 意思 |
| --- | --- |
| `timeout ... 8s` | 采样 8 秒，超时结束检查 |
| `ros2 run` | 运行一个包里的可执行程序 |
| `tf2_ros` | 提供这个工具的包 |
| `tf2_echo` | 输出指定两帧之间的变换 |
| `odom base_footprint` | 查看 base_footprint 相对 odom 的位置和朝向 |
| `--ros-args` | 后面开始给这个程序传 ROS 通用参数 |
| `-r` | remap，重映射一个 ROS 名字 |
| `/tf:=/red_standard_robot1/tf` | 让检查工具去本项目的动态 TF 话题收数据 |
| `/tf_static:=/red_standard_robot1/tf_static` | 静态 TF 同样接到本项目的话题 |

remap 改的是**这次启动的检查工具**使用的名字，不是把全系统的 TF 改名。

这里 `odom` 和 `base_footprint` 是 frame 名；`/red_standard_robot1/tf` 是传 TF 数据的话题名。两类名字不能混着写。

### 8.3 读变换数值

教学输出：

```text
At time 1789989051.224270105
- Translation: [-0.079, -0.049, -0.002]
- Rotation: in Quaternion [-0.015, -0.010, 0.746, 0.666]
- Rotation: in RPY (radian) [-0.034, 0.009, 1.683]
- Rotation: in RPY (degree) [-1.966, 0.522, 96.436]
```

| 行 | 解释 |
| --- | --- |
| `At time` | 该变换的时间戳，不是检查耗时 |
| `Translation [x,y,z]` | 目标 frame 原点在参考 frame 中的位置，单位米 |
| `Quaternion [x,y,z,w]` | 四元数表示的旋转，不是四个角度 |
| `RPY (radian)` | roll、pitch、yaw 的弧度数值 |
| `RPY (degree)` | 同一组角度换算为度，初学时更直观 |

常见机器人轴约定是 x 向前、y 向左、z 向上，具体传感器/模型还需核对。roll 绕 x、pitch 绕 y、yaw 绕 z。

上例 yaw 约 `96°` 是朝向，不意味着车体倾斜 `96°`。判断车体斜不斜看 roll/pitch，并结合真实地面。

### 8.4 Matrix 是什么

```text
 1.000  0.000  0.000  0.000
 0.000  1.000  0.000  0.000
 0.000  0.000  1.000  0.000
 0.000  0.000  0.000  1.000
```

这是单位变换：没有平移、没有旋转。一般 4×4 变换矩阵左上 3×3 表示旋转，最右列前三个值是平移，最后一行通常为 `[0,0,0,1]`。初学排查不需要手算矩阵，可以先看 Translation 和 RPY。

### 8.5 静态与动态 TF

静态 TF 用于固定安装关系；动态 TF 用于随时间变化的运动/关节关系。

`At time 0.0` 可能是静态变换的显示形式。我们此前建图模式的 `map → odom` 是静态单位变换，所以它不变化可以正常；导航模式应核对全局定位发布者。

`odom → base_footprint` 是运动关系，不能为了去掉报错人为固定它。云台会独立转动的关系也不能用假的固定角度代替。

### 8.6 错误文字怎么读

| 输出 | 先理解为 |
| --- | --- |
| `Invalid frame ID ... does not exist` | 监听器还不知道这个 frame |
| `two or more unconnected trees` | 两帧存在，但没有完整连接路径 |
| `extrapolation into the future` | 请求时间晚于可用 TF 数据 |
| `earlier than all the data ...` | 请求时间比缓存最早数据还早 |

第一条启动警告后若开始连续输出，说明需要看最终结果；持续整个检查都失败才按故障继续查。

本队有两种值得对比的失败路径：[ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp][guide-loam-tf] 在首次安装 TF 查询失败时 return，不发这次里程计；[ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp][guide-scan-tf] 的 `getTransform` 则记录警告并返回单位变换。因此“没有输出”和“有输出但坐标错误”都可能来自 TF，必须连日志与数值一起看。

### 8.7 画出树

```bash
mkdir -p /home/ubuntu/nav_debug_tf
cd /home/ubuntu/nav_debug_tf
ros2 run tf2_tools view_frames --ros-args -r /tf:=/red_standard_robot1/tf -r /tf_static:=/red_standard_robot1/tf_static
```

第一行建立输出目录；第二行进入目录；第三行监听 TF 并生成图文件。`.gv` 是图描述文件，PDF 是可看的图；绘图需要 `dot` 工具。

这条命令会写图文件，但不会把图里的连线加到机器人 TF 系统。

## 9. 时间戳、点云消息头和队列

对应排查手册第 6 节。

一条点云既有“何时到达终端”，也有“何时采集”的 stamp。TF 应匹配采集时刻；只用此刻的姿态变换旧点云，会把机器人后来移动的距离误加到障碍位置。示意：车以 0.5 m/s 前进，点云落后 0.2 秒，两者已经差出 0.1 米。这个数字解释了为什么时间问题会表现为点云错位，而不只是日志多几行警告。

### 9.1 读当前时间

```bash
date +%s
```

`date` 是日期时间工具；`+%s` 输出 Unix 时间戳的整秒部分。它表示从 1970-01-01 UTC 开始计数的秒，不是当天运行了多少秒。

### 9.2 读一条消息头

```bash
timeout --signal=INT --kill-after=2s 8s ros2 topic echo /red_standard_robot1/registered_scan sensor_msgs/msg/PointCloud2 --qos-reliability best_effort --field header --once
```

| 部分 | 意思 |
| --- | --- |
| `topic echo` | 订阅并打印收到的消息 |
| `sensor_msgs/msg/PointCloud2` | 明确写出要接收的消息类型 |
| `--qos-reliability best_effort` | 为当前检查订阅设置可靠性规则 |
| `--field header` | 只打印消息头，不打印巨大点云数组 |
| `--once` | 收到第一条满足条件的消息后退出 |

教学输出：

```text
stamp:
  sec: 1789988456
  nanosec: 225700000
frame_id: odom
```

真实时间约为 `sec + nanosec / 1000000000`。`nanosec` 是这一秒中的小数部分，单位纳秒；`frame_id` 表示这批点在什么坐标系中。

例如观察时系统时间约 `1000 s`，原始点云时间约 `999.9 s`，注册点云约 `985 s`：后者可能在处理中积压。这里的 1000/985 是教学数字，判断需考虑两条命令执行间隔。

### 9.3 `use_sim_time`

```bash
ros2 param get /red_standard_robot1/point_lio use_sim_time
```

`param get` 读取这个节点登记的参数。`false` 通常表示使用系统时间；`true` 表示节点的 ROS 时钟使用仿真 `/clock`。

实机各模块不应一部分使用真实时间、一部分在等无效仿真时钟。相差非常大的时间值可能是不同时间基准，而不仅是程序运行慢。

### 9.4 为什么队列满未必是队列太小

接收到点云后，程序可能需要等待对应时间的 TF 才能处理。一直没有 TF，旧点云就排队；队列满了只能丢数据。

因此看到 `queue is full` 先查 TF 与时间，再查处理能力。扩大 queue 容量可能让程序保留更多过时数据。

### 9.5 CPU、内存和时钟状态

```bash
top -b -n 1 | head -n 25
free -h
timedatectl status
```

| 命令片段 | 解释 |
| --- | --- |
| `top -b` | 用适合输出到文本的批处理模式查看负载 |
| `-n 1` | 只刷新一次 |
| `head -n 25` | 保留最前面的 25 行 |
| `free -h` | 用 MiB/GiB 等便于阅读的单位显示内存 |
| `timedatectl status` | 查看系统时间、时区、同步相关状态 |

看 free 时重点结合 `available`，不能把缓存占用都当成无法使用的内存。top 中多线程进程的 CPU 使用率可能超过 100%，也不能只凭一个截图断言程序永久堵塞。

## 10. Action 与 lifecycle 命令详解

对应排查手册第 7 节。

Action 像一张持续执行的任务单：有人接收、报告进度，最后给结果；lifecycle 像执行者是否已备妥工具、进入工作状态。执行者 active 但本次任务被拒绝，和任务已执行后 ABORTED，是不同断点。下面检查时把 server 状态与本次 UUID 分别记录，才不会用旧成功结果解释新目标。

### 10.1 Action 列表和详细信息

```bash
ros2 action list -t | grep navigate_to_pose
ros2 action info /red_standard_robot1/navigate_to_pose
```

第一行列出 Action 名和类型，再筛导航到一个目标的 Action。第二行查看是谁作为 client/server 连接它。

教学输出：

```text
Action: /red_standard_robot1/navigate_to_pose
Action clients: 5
Action servers: 1
```

clients 是提出任务的一方，server 是执行任务的一方。RViz、手柄节点等都可能成为 client；client 多不等于重复导航。应确认唯一预期 server 通常属于 bt_navigator。

存在 server 不等于它已经准备好执行，下一步看 lifecycle。

### 10.2 读 lifecycle 状态

```bash
ros2 lifecycle get /red_standard_robot1/bt_navigator
ros2 lifecycle get /red_standard_robot1/planner_server
ros2 lifecycle get /red_standard_robot1/controller_server
```

| 输出 | 含义 |
| --- | --- |
| `unconfigured [1]` | 未完成配置 |
| `inactive [2]` | 已配置，但未激活工作 |
| `active [3]` | 激活状态 |
| 节点/服务不可达 | 节点不存在、未发现，或查询环境不一致 |

这三个节点 active 只是必要检查，不能证明本次 Goal 已收到，也不能证明串口或底盘能动。

### 10.3 Goal 状态话题

```bash
ros2 topic echo /red_standard_robot1/navigate_to_pose/_action/status action_msgs/msg/GoalStatusArray --qos-durability transient_local --qos-reliability reliable
```

`_action/status` 是 Action 的状态通道。`GoalStatusArray` 表示一条消息中可以有多个目标状态。

`--qos-durability transient_local` 请求可接收发布者缓存的样本；所以刚打开 echo 就看到的状态可能属于之前的 Goal。

| 数字 | 英文 | 中文 |
| --- | --- | --- |
| `0` | UNKNOWN | 状态未知 |
| `1` | ACCEPTED | 已接受 |
| `2` | EXECUTING | 执行中 |
| `3` | CANCELING | 取消中 |
| `4` | SUCCEEDED | 成功 |
| `5` | CANCELED | 已取消 |
| `6` | ABORTED | 失败中止 |

每个目标有 UUID，作为目标标识；读数组时结合 UUID、时间和本次操作。看到旧目标的 `4`，不能证明刚点的新目标成功。

`goal_pose` 是一个可能被转发的目标话题；RViz 也可能直接向 Action 发目标。所以只检查 goal_pose 是不完整的。

## 11. `Twist` 消息、速度链和少量 C++ 源码

对应排查手册第 7、11、12 节。

导航目标给的是“去哪里”，Twist 给的是“这一刻以什么速度动”。同一条速度经过平滑与坐标转换后，数字可能改变；其中任意一级有输出都不等于车已执行。例如 yaw=π/2 时，本队转换公式将输入 `(0.2,0,0)` 变成约 `(0,-0.2,spin)`，要先知道每一级坐标含义，再判断方向是否正确。

### 11.1 读取速度

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel geometry_msgs/msg/Twist
```

教学输出：

```text
linear:
  x: 0.20
  y: 0.00
  z: 0.00
angular:
  x: 0.00
  y: 0.00
  z: 0.80
```

`linear` 是线速度，通常单位 m/s；`angular` 是角速度，通常单位 rad/s。这个工程的底盘常用 `linear.x`、`linear.y`、`angular.z`。

`angular.z=0.8 rad/s` 约为 `45.8°/s`，如果实际恒定实现该速度，转一圈约 `2π/0.8=7.85 s`。它仍是请求值，实际速度要看反馈与物理运动。

左右/前后方向依赖消息实际使用的坐标约定。本项目涉及云台/虚拟 frame 和 fake_vel_transform，不要未经确认把每一级的 x 都叫作“实际底盘正前方”。

### 11.2 `--field` 读单个字段

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel geometry_msgs/msg/Twist --field angular.z
```

点号 `.` 是访问嵌套字段：先找到 angular，再读它的 z。输出只剩数字，例如 `0.8`。

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /red_standard_robot1/cmd_vel geometry_msgs/msg/Twist --field linear
```

这里会输出 linear 里的 x/y/z。`Invalid field 'angular.zvvvvvv'` 就是字段拼错了，和底盘电控无关。

### 11.3 三个速度话题分属不同环节

| 后缀 | 本项目此前使用的环节 |
| --- | --- |
| `cmd_vel_controller` | 路径控制器原始输出 |
| `cmd_vel_nav2_result` | 速度平滑后或恢复行为输出 |
| `cmd_vel` | fake_vel_transform 转换后、串口接收前 |

读某一级有非零速度，只能确认到这一层。机器人空闲、到达、取消目标时，零速度可能完全正常。

三段名称可在 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py][guide-velocity-remap] 对上控制器和 smoother 的 remap；最后的缓存/同步和旋转公式在 [ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp][guide-velocity-callbacks]。用相同时间区间读三段，才能区分“上游决定停止”和“转换环节改变了输出”。

### 11.4 看懂发布与订阅源码

这里带读的是历史独立 `rm_serial_driver` 的接口。Navigation-2027 克隆中未发现同名完整包，另有 Python/C++ 串口实现，详见[接口差异与风险 R1–R2](../system/nav2-and-control-evidence.md)。不得把这些实现当成已经验证等价。

若要从当前基线练习同一类语法，打开 [standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp][guide-serial-subscription] 的 `createSubscription`，逐项读消息类型、相对 `cmd_vel`、深度 10 和回调绑定。它与下面历史摘录的绝对名不同，最后完整名称要结合 namespace/remap 确认。这一小差异正是[名称错配案例](case-topic-mismatch.md)训练的内容。

下面是教学摘录，解释 C++ 中的典型写法，不作为终端命令执行：

```cpp
nav_cmd_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
  "/red_standard_robot1/cmd_vel", 10,
  std::bind(&RMSerialDriver::sendNavigationCmd, this, std::placeholders::_1));
```

| 部分 | 意思 |
| --- | --- |
| `nav_cmd_sub_ =` | 保存创建出的订阅对象 |
| `this->` | 在当前节点对象上调用功能 |
| `create_subscription<...>` | 创建指定消息类型的订阅 |
| `geometry_msgs::msg::Twist` | C++ 中消息类型的名字 |
| 话题字符串 | 要订阅哪个话题 |
| `10` | 这里用来构造订阅 QoS 的历史深度 |
| `sendNavigationCmd` | 收到消息后要调用的处理函数，即回调 |
| `_1` | 将收到的第一个回调参数传给这个函数 |

`::` 是 C++ 名字空间/作用域分隔符，不是 ROS launch 的 `:=`。

此后串口回调中有：

```cpp
packet.vx = msg->linear.x;
packet.vy = msg->linear.y;
packet.wz = msg->angular.z;
```

`msg` 指向收到的消息；`->` 访问指向对象中的字段；`packet` 是准备发送的串口数据包。三行将 ROS 的速度字段填到数据包里。

因此 `angular.z` 与 `linear.z` 不能交换使用。此前另一个工程有从 linear.z 读取 wz 的片段，需由该实际消费者的维护者核对，不能只看发布端就判断字段正确。

### 11.5 命令值、发送成功和物理执行

```text
ROS 消息非零 → 串口函数被调用 → 数据已发出 → 电控接收/允许执行 → 真实车体运动
```

每个箭头都需要证据。串口 `send` 成功表示调用完成，不等于电控认可数据，也不等于电机已经动作。

## 12. 串口设备检查逐条详解

对应排查手册第 9 节。

串口是软件数据走向硬件的边界。设备文件存在只能说明系统识别了设备；程序打开它、写入数据、电控收到并允许执行，还要各自证明。比如 `/dev/ttyACM0` 存在、却被旧程序占用，导航速度再正常也不能解释为规划器故障。下面先查设备与占用，再查消费者和反馈。

### 12.1 设备文件

```bash
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/serial/by-id/* 2>/dev/null
```

| 部分 | 意思 |
| --- | --- |
| `ls` | 列出文件/目录信息 |
| `-l` | 显示权限、所属用户/组等详细信息 |
| `/dev/ttyACM*` | 查 ACM 类型串口设备 |
| `/dev/ttyUSB*` | 查 USB 转串口设备 |
| `/dev/serial/by-id/*` | 查按设备标识建立的链接 |

Linux 用设备文件作为操作硬件的接口。`ttyACM0` 拔插后可能变成 `ttyACM1`；编号不保证固定。

如果链接稳定且确实对应这个硬件，by-id 可以帮助识别设备；能否用于驱动参数还需结合实际设备与启动配置。

### 12.2 当前驱动打开哪个设备

```bash
ros2 param get /rm_serial_driver device_name
```

读取串口节点登记的设备路径，接下来的 fuser/lsof 用这个路径，而不是盲目使用历史 ttyACM0。

### 12.3 `sudo`、`fuser` 和 `lsof`

```bash
sudo fuser -v /dev/ttyACM0
```

`sudo` 用管理员权限执行紧跟着的命令；`fuser` 查谁在使用这个文件；`-v` 输出详细信息。输入 sudo 密码时终端通常不显示星号，这是正常行为。

```bash
sudo lsof /dev/ttyACM0
```

`lsof` 列出打开这个文件的进程，关注 COMMAND、PID、USER、NAME。它没安装时先用 fuser。

两个独立串口程序打开同一硬件，不代表它们能各自获得完整回包。我们曾遇到导航串口驱动和视觉工程串口程序同时占用，需要按实际运行职责保留一套。

### 12.4 返回诊断话题

这两项只属于历史修改过的驱动；不是本队源码基线保证提供的标准接口。话题缺失时先登记实际串口版本与回包来源。

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /serial/chassis_enabled std_msgs/msg/UInt8
```

```bash
timeout --signal=INT --kill-after=2s 6s ros2 topic echo /serial/chassis_velocity_feedback geometry_msgs/msg/Twist
```

`UInt8` 是一个 0–255 范围的无符号整数消息，这里转发电控的字段。必须按协议解释具体取值/位，不能把所有非零值一概认作“允许导航”。

第二条用于看驱动收到的底盘速度回包。两者属于此前添加的诊断功能，旧驱动可能没有这些话题。

### 12.5 设备重连日志

```bash
sudo journalctl -k -b --no-pager | grep -Ei 'ttyACM|ttyUSB|usb|disconnect|reset' | tail -n 60
```

| 选项 | 意思 |
| --- | --- |
| `journalctl` | 查询系统日志 |
| `-k` | 查看内核相关日志 |
| `-b` | 只看本次开机 |
| `--no-pager` | 直接输出，不进入分页阅读器 |
| grep 与 tail | 保留 USB/串口关键词附近匹配行的最后 60 行 |

`disconnect`、重新枚举等证据提示检查线缆、供电和设备路径，不是让你改控制器速度参数。

### 12.6 权限字段怎么读

`ls -l` 中形如 `crw-rw----` 的开头：`c` 表示字符设备，后面的权限分给所属用户、所属组和其他用户。查看自己所属组可用：

```bash
id
```

权限不足时先核对驱动用户与设备组，由管理员按实验室规则设置，不用给所有人都开放的权限来掩盖问题。

## 13. 地图、定位参数与配置文件阅读

对应排查手册第 8、13、15 节。

地图是定位与规划共同使用的参照。二维图说“哪里占据”，三维点云说“空间结构长什么样”，YAML 说“图片上的像素怎么换成米”。例如分辨率 0.05 m/格时，20 格代表 1 米；原点改变后，同一像素的世界位置也会改变。所以文件存在只是入口检查，真正验收还要看实际加载路径与几何重合。

### 13.1 三类地图文件

| 扩展名 | 装了什么 | 用在哪里 |
| --- | --- | --- |
| `.yaml` | 图片路径、分辨率、原点、占据阈值等元信息 | 二维地图加载 |
| `.pgm` | 二维栅格地图图片 | Nav2 规划与代价地图相关输入 |
| `.pcd` | 三维先验点云 | 本工程重定位匹配 |

它们需要对应同一次建图。名字相同不代表内容必然配套；`ls` 看到文件非零也不等于地图与当前场地正确对应。

### 13.2 `ls -lh` 文件检查

```bash
ls -lh /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/map/reality/lab_20260826_01.yaml /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/map/reality/lab_20260826_01.pgm /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/pcd/reality/lab_20260826_01.pcd
```

`-l` 是长格式，`-h` 将大小写成 K/M/G 等便于读的单位。核对文件是否存在、大小是否合理、时间是否对应。地图名必须替换成当前使用的名字。

### 13.3 实际加载的地图

```bash
ros2 param get /red_standard_robot1/map_server yaml_filename
ros2 param get /red_standard_robot1/small_gicp_relocalization prior_pcd_file
ros2 param get /red_standard_robot1/small_gicp_relocalization auto_initialize
```

前三个参数依次回答：二维地图 YAML 在哪里、重定位 PCD 在哪里、是否开启自动初始化。

建图模式可能没有这些导航模式节点，查询不到不能直接判定建图坏了。

### 13.4 YAML 的缩进和点号参数

教学片段：

```yaml
controller_server:
  ros__parameters:
    progress_checker:
      required_movement_radius: 0.15
      movement_time_allowance: 7.0
```

YAML 用缩进表达层级。冒号左边是名字，右边是值；同层字段对齐。`#` 开始的是注释，不参与实际参数值。

上面两项在该节点中通常按点号组合成：

```text
progress_checker.required_movement_radius
progress_checker.movement_time_allowance
```

点号表示参数层级，不是说要在 Linux 目录里找名为 progress_checker 的文件夹。

### 13.5 GICP 初始化日志

以下 `auto_initialize` 和日志来自历史本地修改；不能推断 Navigation-2027 基线也能开机从任意位置自动重定位。本队初始化入口与条件以[传感器与重定位专题](../sensor-lio/README.md)及实际运行参数为准。

`Auto-initialized at the map origin...` 表示从地图原点开始了自动初始化；不表示已经在全场找到真实位置。

`GICP did not converge` 表示这轮匹配没收敛；`Rejected GICP jump` 表示这轮校正超过限幅被拒绝。先查地图、点云、TF 和起点，再决定是否调参数。

当前基线可直接带读 [ros_ws/src/pb2025_sentry_nav/small_gicp_relocalization/src/small_gicp_relocalization.cpp][guide-gicp]: `loadGlobalMap` 检查 PCD，`performRegistration` 在不收敛时返回，只有收敛结果才更新匹配结果。`Rejected GICP jump` 属于上面的历史修订日志，不能期待本队基线也打印这一句。读代码时把“本版本有哪些失败分支”列出来，再到本次日志里逐项找证据。

稳定错位也属于定位错误。除了看 TF 数值连续，还要对照实物位置、地图与点云是否正确重合。

### 13.6 安装倾角与实际车体倾斜

`base_footprint → front_mid360` 的 roll `-30°` 可以表示真实安装关系。`odom → base_footprint` 的 roll/pitch 表示车体参考系相对里程计的姿态。

真实雷达倾斜就应有对应外参；不能为了让显示平整把真实角度改为零。雷达在会动的云台上，还需要真实关节运动反馈。

## 14. 代价地图、足迹、膨胀与恢复参数

对应排查手册第 10、11 节。

避障至少有四步：看见障碍、保留障碍、把它标进 costmap、用真实车体外形判断运动是否能通过。膨胀属于后面的代价表达，无法修补前面丢掉的桌腿。示意：长 0.60 m、宽 0.45 m 的矩形车，角点到中心约 0.375 m；只用半径 0.2 m 的圆表达它，转弯时角点就可能超出被检查的区域。

### 14.1 认识 costmap

地图表示保存/建出的环境；代价地图 costmap 在地图与实时观测基础上，为每个区域赋予通行代价。

全局 costmap 常用于整体路径；局部 costmap 关注机器人附近，供控制与相关行为使用。

看到点云有桌腿，还要确认 terrain_map 保留了它、costmap 标记了它。每一步都可能过滤或变换数据。

### 14.2 为什么节点名里 local_costmap 写了两遍

```bash
ros2 param get /red_standard_robot1/local_costmap/local_costmap inflation_layer.inflation_radius
```

这是节点的完整名字，前一个 local_costmap 可作为附加命名空间，后一个是节点名。不要为“去重复”手动删掉其中一个，先用 node list 确认。

最后 `inflation_layer.inflation_radius` 是该节点内的参数名字，与节点路径分开。

### 14.3 `footprint` 与 padding

教学参数：

```yaml
footprint: "[[-0.30, -0.225], [-0.30, 0.225], [0.30, 0.225], [0.30, -0.225]]"
footprint_padding: 0.03
```

footprint 是车体平面外形多边形，每个点是 `[x,y]`，单位米。如果原点在底盘中心，x 从 -0.30 到 0.30 表示长 0.60 m，y 从 -0.225 到 0.225 表示宽 0.45 m。

padding 为足迹增加余量。还必须确认足迹跟随的 frame 真正代表底盘，不能只确认数字正确。

### 14.4 膨胀两个参数

```yaml
inflation_radius: 0.60
cost_scaling_factor: 4.0
```

`inflation_radius` 决定障碍周围建立代价影响的半径；`cost_scaling_factor` 决定代价衰减的快慢。

增大半径可以扩大已识别障碍的影响范围，但不保证车自动离障碍增加同样的距离；较高衰减因子通常让代价更快下降。路径还受规划器权重、足迹和通道宽度影响。

雷达没看见的障碍不会凭膨胀参数出现。对于非圆底盘旋转，角点扫掠也要考虑。

### 14.5 观测源

```bash
ros2 param get /red_standard_robot1/local_costmap/local_costmap obstacle_layer.observation_sources
ros2 param get /red_standard_robot1/local_costmap/local_costmap obstacle_layer.terrain_map.topic
```

第一行查障碍层配置了哪些观测源；第二行查 terrain_map 这个观测源实际订阅的话题。

本工程此前障碍层直接用 terrain_map 点云。因此只看 obstacle_scan 有更新，不能证明 costmap 正在正确使用它。

本队 [ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml][guide-costmap] 的 local/global 障碍层也声明 `terrain_map`，同时有强度与高度门限。先在有效参数中核对这些值，再把 RViz 里的输入点与 costmap 标记对照；“雷达看见了”与“障碍层接受了”是两个步骤。上面的矩形 footprint 是教学/历史尺寸示例，基线 YAML 的 `robot_radius: 0.2` 不应被误读成已经验收的实际底盘外形。

### 14.6 碰撞检查开关

以下是历史自定义扩展。Navigation-2027 审查基线的控制器有不同的碰撞采样逻辑与边界，见[风险 R8](../system/nav2-and-control-evidence.md)；参数不存在是版本差异，不能由此断言当前控制器完全不检查碰撞。

```bash
ros2 param get /red_standard_robot1/controller_server FollowPath.enable_collision_guard
```

这是本地控制器曾添加的开关。`false` 表示该可选检查没有开启，不是说整个 Nav2 没有任何代价地图功能；也不能因为规划器有地图就认定最后的完整运动轨迹都已检查。

如果参数不存在，先核对实际控制器插件和源码版本。不要直接把网上其他插件的参数加进 YAML 就认为生效。

### 14.7 进展检查的距离和时间

```bash
ros2 param get /red_standard_robot1/controller_server progress_checker.required_movement_radius
ros2 param get /red_standard_robot1/controller_server progress_checker.movement_time_allowance
```

`required_movement_radius` 是判断产生平移进展所需的距离；`movement_time_allowance` 是允许完成这段进展的时间。

SimpleProgressChecker 比较相对基准位置的位移，不是轮子转了多少圈，也不是往返累计走了多少米。原地旋转或短距离来回，仍可能被判定没进展。

此前试验为 `0.15 m / 7 s`。7 秒比 10 秒等待更短，所以更容易达到超时。

### 14.8 行为树 XML 与后退参数

下面只讲 XML 属性语法和历史试验值。Navigation-2027 的 `BackUp` 可能装载自定义 `BackUpFreeSpace`，会搜索自由方向，并不保证沿车体正后方直退；见[Nav2 与控制链](../nav2/README.md)和源码风险 R9。

教学片段：

```xml
<BackUp backup_dist="0.50"
        backup_speed="0.20"/>
```

`BackUp` 是行为节点名；后面是属性。距离 0.50 m，速度 0.20 m/s。这描述行为树具有怎样的后退行为，不是本次运行必定执行了它。

读实际树路径：

```bash
ros2 param get /red_standard_robot1/bt_navigator default_nav_to_pose_bt_xml
```

找源文件里的片段：

```bash
grep -nE 'BackUp|backup_dist|backup_speed' /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml
```

实际运行可能使用 install 或其他路径。源文件、已安装文件、当前选择的行为树三个层次要对应。

## 15. 云台、自旋与参数运行值

对应排查手册第 12 节。

一个参数可以只是启动时装入成员变量的初值，运行中 Topic 又可以改变这个成员。示意：启动 `init_spin_speed=0.5`，随后收到 `cmd_spin=0`，参数仍可能显示 0.5，实际公式已使用 0。先读 [ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp][guide-spin] 的初始化读取与 `cmdSpinCallback`，再读[同文件的 transformVelocity][guide-velocity-formula]；查实际旋转要用前后级速度差支持判断。

```bash
ros2 topic info /red_standard_robot1/cmd_gimbal_joint -v
ros2 param get /red_standard_robot1/fake_vel_transform init_spin_speed
```

第一行问“这个云台命令话题由谁发、谁收”，第二行问“速度转换节点登记的初始化速度是多少”。

`Subscription count: 0` 表示这个 ROS 话题没有发现消费者；即使有发布者，也没有形成该话题到硬件的通路。不能猜消息字段直接发布云台命令。

### 15.1 历史修订的自旋逻辑与本队基线的区别

下面的平移条件是历史部署后来增加的修改。**Navigation-2027 审查基线无此条件，始终叠加 spin_speed；全零输入可能仍输出非零角速度。** 确切代码与停止路径风险见[源码证据](../system/nav2-and-control-evidence.md)和[旧速度案例](case-stale-command.md)，不能把下方带读代码当作本队已经完成的修复。

```cpp
const bool is_translating = std::hypot(twist->linear.x, twist->linear.y) >= EPSILON;
aft_tf_vel.angular.z = twist->angular.z + (is_translating ? spin_speed_ : 0.0);
```

| 部分 | 意思 |
| --- | --- |
| `std::hypot(x,y)` | 计算平面线速度大小，类似 sqrt(x²+y²) |
| `>= EPSILON` | 大于等于一个很小的阈值，判定是否平移 |
| `bool` | true/false 真假值 |
| `条件 ? A : B` | 条件为真取 A，否则取 B |
| `spin_speed_` | 节点内部保存的附加旋转速度 |

含义是：有平移请求时，将附加旋转加到 angular.z；没有平移时不额外加这部分旋转。

这段逻辑没有发送云台命令，也没有直接检查 Goal 是否执行。前进、后退或其他经过同一通路的平移，都可能触发它。

### 15.2 为什么 `param get` 还不够

`init_spin_speed` 是初始值；此前代码的 `/cmd_spin` 回调会直接改内部 spin_speed_。内部变量可能变了，但参数读数没同步变。

所以判断实际加了多少旋转，要对比转换前后的 angular.z；判断云台真实是否跟随，要看硬件、接口和关节反馈。

“云台在世界坐标保持方向”只是待验证原因之一。此前还没有完整确认云台控制通路，本书不把它当成已经修好的功能。

## 16. 构建、安装路径与配置修改语法

对应排查手册第 15 节。

把“改了却没效果”拆成四站：源码改了吗、安装产物更新了吗、启动时选了它吗、现有进程重新读取了吗。比如 src 的膨胀值是 0.60，prefix 却指向旧工作区，构建这份 src 无法改变旧进程。下面从 prefix 开始查，最后用运行参数闭合，避免不断重建却始终用错版本。

### 16.1 查实际包位置

```bash
ros2 pkg prefix pb2025_nav_bringup
```

`pkg` 操作包相关信息；`prefix` 显示 ROS 当前找到的这个包的安装前缀。若指向旧工作空间，说明当前环境选择的版本不是预期版本。

### 16.2 列出源工作空间的包

```bash
cd /home/ubuntu/navigation_2025/ros_ws
colcon list | grep pb2025_nav_bringup
```

`colcon list` 从当前工作空间发现源码包。它和 pkg prefix 回答不同问题：一个问源码包在哪里，一个问当前 ROS 环境选中了哪个安装包。

### 16.3 构建命令

操作类型：生成/更新构建与安装文件。

```bash
colcon build --symlink-install --packages-select pb2025_nav_bringup
```

| 部分 | 意思 |
| --- | --- |
| `colcon build` | 构建并安装工作空间中的包 |
| `--symlink-install` | 对适合的安装产物使用符号链接，便于开发 |
| `--packages-select` | 仅选明确列出的包进行构建，不自动等同于所有依赖包 |
| `pb2025_nav_bringup` | 本次要构建的包名 |

教学输出：

```text
Starting >>> pb2025_nav_bringup
Finished <<< pb2025_nav_bringup [0.18s]
Summary: 1 package finished [0.45s]
```

说明本次选中的包完成构建。若 `Summary: 0 packages finished` 并出现 unknown package，就没构建目标包。

配置包构建很快可能正常。修改 fake_vel_transform 的 C++ 后，只构建 bringup 不会自动编译那个 C++ 包。

构建完还要 source 安装环境，相关正在运行的进程通常要重启才能读新的启动配置。

### 16.4 命令替换 `$(...)`

```bash
grep -nE 'init_spin_speed|required_movement_radius|movement_time_allowance|inflation_radius' "$(ros2 pkg prefix pb2025_nav_bringup)/share/pb2025_nav_bringup/config/reality/nav2_params.yaml"
```

Bash 先执行 `$(...)` 里的命令，用输出替代这一段，再拼接后面的文件路径。

例如 prefix 输出 `/某个install/pb2025_nav_bringup`，最终 grep 就读取该安装位置下的 share 配置文件。外面的双引号保留完整路径。

前提是 pkg prefix 成功；如果失败，最终拼出来的路径可能错误，所以新人可以先单独查 prefix。

### 16.5 `cp`、`sed -i`、`cmp` 怎么读

以下是修改语法教学，**不是要求现在再次调参**。需要修改时先按排查结论确定目标值，并退出相关 launch。

```bash
cp -a -i /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml.bak_newcomer
```

`cp` 复制文件；`-a` 尽可能保留属性，符号链接按链接处理；`-i` 目标存在时询问。源配置若本来就是符号链接，这种备份也可能保留链接关系，需要先确认 `ls -l`，不能一概当作独立内容备份。

```bash
sed -i -E 's/^([[:space:]]*inflation_radius:).*/\1 0.60/' /home/ubuntu/navigation_2025/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml
```

| 片段 | 意思 |
| --- | --- |
| `sed` | 文本处理工具 |
| `-i` | 原地修改文件，会写入内容 |
| `-E` | 使用扩展正则 |
| `s/旧模式/新文本/` | 替换命令 |
| `^` | 从行首匹配 |
| `[[:space:]]*` | 匹配行首的空白缩进 |
| `( ... )` | 捕获括号中的内容 |
| `.*` | 匹配行内余下字符，包括旧值/尾部注释 |
| `\1` | 在替换中放回第一组捕获内容 |
| `0.60` | 放入的新值 |

它会修改所有符合模式的行，所以局部和全局两处可能一起变化；也会去掉该行旧值后面的尾部注释。执行后必须 grep 检查，不凭 sed 没报错就断定预期改动完成。

`cmp -s 文件A 文件B` 比较文件内容；`-s` 不打印区别，以退出码区分。`0` 表示相同，`1` 表示不同，其他值可能是读取错误。文件相同不代表旧进程已经重新读取它。

## 17. 日志、RViz、daemon 和崩溃输出

对应排查手册第 6、14、15、16 节。

日志要先按“谁写的、什么时候、是在运行还是退出”读。先出现 TF 缺失，后出现队列满，可能是前者造成后者；先按 Ctrl+C，后出现 -9，可能是退出超时被强制终止。看到最后一行 ERROR 就改对应模块，会错过真正的首个异常。RViz、CLI 和导航进程各有自己的失败，下面逐层区分。

### 17.1 日志等级

| 标签 | 意义 |
| --- | --- |
| `INFO` | 普通运行信息，不保证任务成功 |
| `WARN` | 警告，要看是否持续、是否影响后续 |
| `ERROR` | 错误，需要对应具体节点与操作 |

先记录发生时间、模式和哪个节点报错，再找首次错误。后续“TF 失败”可能只是上游已经退出的结果。

### 17.2 日志列表

```bash
ls -lt /home/ubuntu/.ros/log | head -n 12
```

`-l` 长格式，`-t` 按修改时间排序，默认较新的在前，head 保留前 12 行。

`/home/ubuntu/.ros/log/latest` 常是链接到最近某个运行日志目录。后来单独启动 RViz，latest 就可能指到 RViz 那次运行，不能默认它是当前导航日志。

```bash
readlink -f /home/ubuntu/.ros/log/latest
```

`readlink -f` 解析链接，显示规范化后的目标路径。它不改动链接。

### 17.3 搜日志

```bash
grep -RniE 'Failed to make progress|BackUp|Collision|collision|abort' /home/ubuntu/.ros/log/latest 2>/dev/null | tail -n 80
```

递归搜指定日志目录，再保留最后的匹配行。无输出表示这批文件没找到匹配，不能证明机器人没有错误，也不能证明没有执行恢复。

### 17.4 进程退出码与信号

| 输出 | 能确定什么 | 不能直接确定什么 |
| --- | --- | --- |
| ROS launch 中 `exit code -11` | 子进程收到 SIGSEGV | 不能仅凭数字判断驱动为什么崩溃 |
| `exit code -9` | 子进程被 SIGKILL 结束 | 可能是退出超时强杀，也可能别的来源 |
| `failed to terminate ... SIGKILL` | launch 在停止过程中升级了终止方式 | 不一定是此前正常运行阶段的原始故障 |
| 检查命令退出 `124` | GNU timeout 达到时限的常见结果 | 不等于导航进程崩溃 |

launch 的负值表示信号来源，与 shell 的 `$?` 显示方式可能不同，不要直接按数字对照。

### 17.5 内存与库检查

```bash
sudo journalctl -k -b --no-pager | grep -Ei 'out of memory|oom|killed process|segfault' | tail -n 60
```

查内核是否记录内存不足杀进程或段错误。OOM 是内存不足；它与正常关机过程中的 launch SIGKILL 不同。

```bash
ldd /home/ubuntu/navigation_2025/ros_ws/install/point_lio/lib/point_lio/pointlio_mapping | grep -Ei 'not found|pcl|usb|MVS'
```

`ldd` 查看已知本地可执行文件需要的动态库及解析路径。`not found` 表示相关库没有找到；路径指向意外的第三方目录时继续查环境。仅看名字出现 PCL/USB 不表示它们有错。

### 17.6 CLI daemon 是什么

ROS CLI daemon 用来帮助命令行工具查询 ROS 图信息。它不是 planner_server，也不是串口程序。

```bash
ros2 daemon stop
ros2 daemon start
```

两行分别停止和启动这个辅助 daemon。此前 `RuntimeError: !rclpy.ok()` 的 CLI 故障用这两行恢复过。

重启它不会替你停止重复导航，也不会补出丢失的 odom TF。输入了错误字段名时也不用重启它。

### 17.7 RViz 软件渲染的语法

```bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch pb2025_nav_bringup rviz_launch.py namespace:=red_standard_robot1
```

开头 `变量=值 命令` 给这次命令及其子进程设置环境变量。这里要求尝试软件 OpenGL 渲染。

启动的是单独 RViz 的 launch，不是再启动一整套导航。软件渲染可能更吃 CPU；画面恢复后仍需确认数据没有积压。

白色模型、GLSL 报错属于显示线索。机器人不动仍要查 Goal/速度/串口，而不是凭模型颜色作结论。

## 18. SSH 检查命令与网络输出

对应排查手册第 17 节。

SSH 先找到主机，再建立 TCP 连接，最后认证用户。失败信息是在告诉你走到哪一步：端口可达却 Permission denied，重点已从路由转向认证；一直超时，则用户名是否正确还没得到检验。下面的网络命令用来定位这个边界，与 ROS 的 Topic 通信检查分开记录。

### 18.1 Linux 地址与监听端口

```bash
hostname -I
ip -br addr
sudo ss -lntp | grep ':22'
sudo ufw status verbose
```

| 命令/选项 | 解释 |
| --- | --- |
| `hostname -I` | 列出主机地址，可能同时有多个网卡/网桥 |
| `ip -br addr` | 用简洁格式显示接口、状态与地址 |
| `ss` | 查询套接字/连接状态 |
| `-l` | 监听中的套接字 |
| `-n` | 使用数字显示地址和端口 |
| `-t` | TCP |
| `-p` | 显示关联进程，需要权限才能看到完整信息 |
| `grep ':22'` | 筛选包含这个端口文字的行，仍要核对实际列值 |
| `ufw status verbose` | 查看 UFW 防火墙状态 |

`LISTEN ... 0.0.0.0:22 ... sshd` 表示 sshd 在该机器的 IPv4 地址上监听 22 端口；它不保证 Windows 到该机器的网络可达。

### 18.2 Windows 测端口

```powershell
Test-NetConnection 192.168.1.50 -Port 22
```

只在 Windows PowerShell 执行。目标地址换成当前 Linux 可达网卡的地址。

| 输出字段 | 意思 |
| --- | --- |
| `RemoteAddress` | 本次实际测试的远端地址 |
| `SourceAddress` | 本次使用的 Windows 本地地址 |
| `InterfaceAlias` | 本次使用的接口，例如 WLAN |
| `PingSucceeded` | Ping 是否收到回复 |
| `TcpTestSucceeded` | TCP 端口连接是否成功 |

Ping 成功/失败与 TCP 22 可达不是完全相同的事。看 SSH 连接问题时重点结合 TcpTestSucceeded 与错误类型。

### 18.3 抓包命令

```bash
sudo tcpdump -ni any 'tcp port 22 and host 192.168.1.64'
```

| 部分 | 解释 |
| --- | --- |
| `tcpdump` | 查看经过网络接口的数据包 |
| `-n` | 不将地址/端口换成名称 |
| `-i any` | 监听可用接口 |
| 引号里的表达式 | 只看 TCP 22 且涉及指定主机的包 |

把 `.64` 换成 Windows 本次实际源地址，然后在 Windows 发起一次 SSH 测试。抓包没有任何输出之前，先确认过滤地址确实正确。

### 18.4 网络错误分类

| 错误 | 检查方向 |
| --- | --- |
| `Could not resolve hostname` | SSH 别名或名称解析 |
| `Connection timed out` | 地址、路由、过滤或回程网络 |
| `Connection refused` | 通常收到了拒绝，核对监听和服务 |
| `Permission denied` | 已进入认证，核对用户、密钥等 |
| `TtlExpired` | 可能是路由循环，不等于 sshd 服务没开 |

历史地址不能当作永远有效。雷达网络、无线网络、Docker 网桥都可能出现在 hostname -I 输出里，需要按当前接口确认。

## 19. 历史双终端启动语法：先登记，再采用

两个终端的分工是让串口与导航各有独立日志和退出对象，不是要求多启动一套机器人。建图与先验导航互为模式选择：前者制作地图，后者消费已有地图。先确认本次目的，再选一条 launch；否则重复输入和 TF 会让后面的诊断失去唯一来源。

此节保留历史双工作空间案例的逐行教学，不是当前 Navigation-2027 可直接照抄的完整启动方案。当前入口不自动补齐串口依赖；先按[环境登记](../onboarding/environment.md)及[实车流程](README.md)确认实际 launch、停止路径和地图，再由负责人安排启动。

对应排查手册第 18 节。以下会启动程序；先按第 5 节确认没有已经运行的同一套导航/串口。

### 19.1 终端 1：串口

```bash
cd /home/ubuntu/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch rm_serial_driver serial_driver.launch.py
```

前四行是进入串口工作空间、清理旧库路径、加载基础环境、加载该工作空间。最后一行从 rm_serial_driver 包读取 serial_driver.launch.py，启动串口相关节点。

该终端保持运行。不要因为没有不断刷屏，就再启动第二个串口程序。

### 19.2 终端 2：建图

```bash
cd /home/ubuntu/navigation_2025/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py slam:=True use_robot_state_pub:=True use_rviz:=True
```

| 部分 | 意思 |
| --- | --- |
| `ros2 launch` | 执行一个启动文件，可能启动多个节点/组件 |
| `pb2025_nav_bringup` | 启动文件所在包 |
| `rm_navigation_reality_launch.py` | 实机启动入口 |
| `slam:=True` | 请求进入建图模式 |
| `use_robot_state_pub:=True` | 请求启动机器人状态/模型 TF 相关发布 |
| `use_rviz:=True` | 同时打开 RViz |

这些 launch 参数的实际作用由本工程启动文件定义。`True` 不代表所有硬件状态已经验证正确。

### 19.3 终端 2：导航，和建图二选一

```bash
cd /home/ubuntu/navigation_2025/ros_ws
unset LD_LIBRARY_PATH
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch pb2025_nav_bringup rm_navigation_reality_launch.py world:=lab_20260826_01 slam:=False use_robot_state_pub:=True use_rviz:=True
```

`slam:=False` 选导航/定位模式；`world:=lab_20260826_01` 指定本工程构造地图路径使用的名称，不是要求你创建同名文件夹。地图换了就换成那次建图的名字。

两条模式命令不要同时启动。另开诊断终端只是查看数据，不是再运行一条建图/导航 launch。

## 20. 一键采集脚本代码详解

采集脚本把手工检查封装成有时间、命令和退出码的快照，让导师能复核“哪条检查取得了什么”。它没有把诊断自动变成结论：查询失败可以继续下一项，报告文件写完也不代表机器人健康。先懂一个检查，再看脚本怎样保存证据，才能读懂其中的循环与函数。

下载 [只读采集脚本](assets/collect_navigation_debug.sh)。仓库相对路径与源码蓝色入口是 [docs/navigation/debug-real/assets/collect_navigation_debug.sh][guide-collector]。本次仓库版增加了显式工作空间参数，默认使用当前终端环境，不自动加载历史实验室路径。

**本节代码片段用于带读，不要逐段粘贴执行。** 实际运行用完整脚本，先查看帮助：

```bash
bash docs/navigation/debug-real/assets/collect_navigation_debug.sh --help
```

在已加载正确 ROS 环境的终端，从知识库根目录进行快速观察：

```bash
bash docs/navigation/debug-real/assets/collect_navigation_debug.sh --namespace /red_standard_robot1
```

`--full` 加入连续频率与 TF 采样；不会主动发 Goal。需要脚本加载工作空间时，使用经登记的真实绝对路径传入 `--nav-workspace` 和可选 `--serial-workspace`。`--serial-node` 可以指定实际串口节点，不能默认所有工程都叫 rm_serial_driver。

### 20.1 首行、变量与路径

```bash
#!/usr/bin/env bash
nav_workspace=${NAV_WORKSPACE:-}
robot_namespace=${ROBOT_NS:-/red_standard_robot1}
report_root=${NAV_DEBUG_REPORT_ROOT:-"$HOME/nav_debug_reports"}
```

第一行选择 Bash。变量赋值的等号两边没有空格。`${变量:-默认值}` 在未设置或为空时取默认值，不是在修改原环境变量。

导航工作空间默认空值，表示不猜部署路径；命名空间有示例默认值，可由选项覆盖。HOME 只用于读取当前用户的家目录，脚本不重新定义 HOME。

### 20.2 参数循环、case 与 shift

```bash
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) full_mode=1; shift ;;
    --help) usage; exit 0 ;;
  esac
done
```

这是缩略结构，完整脚本还处理带路径的选项与未知参数。`$#` 是剩余参数个数；`$1` 是第一个参数；case 按选项分支处理；shift 移走已处理参数，避免无限循环。

带值的选项需要检查后面是否真的提供了值；完整脚本对空路径、缺失路径、非法命名空间先报错，不默默套用旧路径。`--help` 只显示用法，不采集、不建报告目录。

### 20.3 if、返回码和程序存在性

```bash
if ! command -v ros2 >/dev/null 2>&1; then
  printf 'ROS 2 CLI is unavailable. Source your verified environment first.\\n' >&2
  exit 1
fi
```

command -v 查能否找到程序；! 反转成功条件；if/then/fi 围住一个分支。printf 输出文字，\\n 换行；>&2 将文字写到错误输出；exit 1 表示提前失败。

是否存在工作空间先用 `[[ -f "$setup_file" ]]` 检查 install/setup.bash。只有显式提供路径时才 source，该检查不意味着包与硬件依赖已经全部齐备。

### 20.4 创建不覆盖的报告目录

```bash
report_stamp=$(date +%Y%m%d_%H%M%S)
report_directory=$(mktemp -d "$report_root/${report_stamp}_XXXXXX") || exit 1
report_file="$report_directory/report.txt"
```

命令替换 $() 先执行 date/mktemp，再把输出放进变量。`%m` 是月份，`%M` 是分钟。`mktemp -d` 创建随机后缀的新目录；|| 表示前一条失败时退出，因此同秒多次采集也不覆盖旧报告。

### 20.5 函数 run_probe

```bash
run_probe() {
  local probe_label=$1
  local probe_duration=$2
  shift 2
  timeout --signal=INT --kill-after=2s "$probe_duration" "$@" >> "$report_file" 2>&1
  local probe_status=$?
  printf '[command exit=%s]\\n' "$probe_status" >> "$report_file"
  return 0
}
```

这是实际函数的主体摘录。local 声明函数内部变量；前两个参数是标题/时长；shift 2 移走它们；"$@" 将剩余参数保持边界传给 timeout。直接记录 $?，避免被下一条命令覆盖。

return 0 使采集继续下一项，**不代表这项诊断成功**；真实退出码在 report 中。连续采样退出 124 可正常，参数缺失、查询超时则按手册分辨。

调用 `run_probe 'Composable components' 10s ros2 component list` 可读成“这项叫组件检查，运行最多 10 秒，执行后面这条命令”。

### 20.6 命令组与报告

`{ ... } >> "$report_file"` 将多条输出一起追加到报告。`>` 覆盖，`>>` 追加；`2>&1` 将错误输出也写进去。

完整函数用 `printf ' %q' "$@"` 记录可辨认的命令参数，仅写日志，不重新解释执行字符串。脚本没有 eval。

### 20.7 节点列表先保留原始结果

先把 node list 写到 nodes.txt，并保存退出码。成功后使用：

```bash
grep '^/' "$node_file" | sort | uniq -d
```

只取以 / 开头的节点名，排序后找重复，避免将警告文字参与统计。失败/超时不能把空结果当作没有重复。

topics.txt 同样记录这次发现的完整话题名和消息类型。订阅检查会产生临时诊断端点，但不会发送控制消息。

### 20.8 循环、数组、read 和 here-string

`for topic_suffix in ...; do ...; done` 依次替换话题后缀。`"$robot_namespace/$topic_suffix"` 拼成完整话题名。

`parameter_checks=( ... )` 是 Bash 数组；`"${parameter_checks[@]}"` 逐项取出完整字符串，不因里面的空格丢失边界。

`read -r node_suffix parameter_name <<< "$parameter_check"` 从字符串读取两个字段：here-string <<< 给 read 输入，-r 保留反斜杠本身。TF 的两帧也按同样规则拆分。

### 20.9 消息类型与可选接口

串口、云台、自动初始化相关端点在各版本中不同。脚本记录类型发现结果；读取可选状态时使用图中发现的类型，不把所有“云台状态”都当作 Twist。

未知/缺失接口被记录，不被包装成成功，也不会因此向该话题发布一个猜测格式的消息。克隆 Navigation-2027 不自动拥有历史独立串口包或新加的诊断话题。

### 20.10 报告怎么读

```text
===== Received frequency: odometry =====
average rate: 20.0
[command exit=124]
```

以上是教学输出：收到了频率数据，并按时限结束。只有 124 而没有统计时，要检查实际端点/QoS/发现延迟。

脚本默认快速模式；--full 的多段采样是顺序进行，不能当作严格同步的控制实验。空闲时零速度正常，记录采集时机器人处于空闲还是 Goal 执行中。

报告还列出当前 ROS 环境、节点/组件、运行参数、可选串口状态和 latest 日志路径。源文件参数与运行值分开看；latest 可能属于 RViz 或另一条 launch。

脚本语法与离线模拟检查由本次知识库更新验证，真实机器人运行仍需现场验证。运行报告完成不等于导航验收通过。脚本不停止进程、不改变参数、不重启 daemon，也不主动 sudo；唯一直接写入是诊断报告。

## 21. 新人练习：只查看，不改参数

练习的产出是一次有边界的判断。每段输出写“证明了什么、没有证明什么、下一步检查什么”；如果说“有 20 Hz，所以导航正常”，导师应追问 Goal、地图与底盘执行的证据。下面的题目让你把基础词汇变成能指导下一条命令的推理。

前提：由熟悉设备的同学确认机器人已经按需要启动。练习不用额外发 Goal，也不用启动第二套导航。

### 练习 A：说清楚程序与节点的区别

执行 `ps`、`ros2 node list`、`ros2 component list` 三类检查，回答：

1. 本机有几个相关 launch？参数是建图还是导航？
2. 哪些节点在同一容器里？组件编号是不是 PID？
3. 节点有重名时，是哪些证据支持重复实例，而不只是名字相似？

### 练习 B：读懂一个话题

```bash
ros2 topic info /red_standard_robot1/odometry -v
```

记录消息类型、发布者是谁、订阅者有哪些。再运行 6 秒 hz，记录有没有真实数据、平均频率和最大间隔。

不要只写“正常”，写“一个预期发布者，收到约 20 Hz 更新；这还没验证 map 定位和底盘执行”。

### 练习 C：读一个 TF

查看 odom → base_footprint，记录 Translation 单位、roll/pitch/yaw，以及时间是否前进。

如果第一次报 frame 不存在，随后正常输出，应该记录启动阶段发现延迟；如果全程树断开，转排查手册第 4 节。

### 练习 D：目标不动时沿链说明

假设有如下教学结果：Action 正在执行，cmd_vel_controller 非零，cmd_vel_nav2_result 非零，cmd_vel 非零，但没有预期串口订阅者。

可以得出的结论是“导航速度已到 cmd_vel，预期串口消费者缺失”；不能说“规划算法坏了”，也不能说“电机肯定坏了”。接着查串口节点与订阅名称。

### 练习 E：读这四种输出

| 教学输出 | 应回答 |
| --- | --- |
| 一个容器列出了两次 loam_interface | 有同容器重复加载证据 |
| 全部 lifecycle active，但新 Goal 直接 ABORTED | 请求到达后失败，需要运行日志，不是自动判定没发出 Goal |
| Point-LIO 里程计 1000 Hz | 高频本身不证明重复发布，查 publisher 端点与算法配置 |
| 地图稳定、点云稳定，但都对应错位置 | 稳定不等于定位正确 |

完成练习后再使用排查手册按现象找章节。

## 22. 从代码详解跳到排查手册

本页按工具学习，手册按症状查询。遇到现场问题时，先用下面的表找到对应工具说明，再回手册执行检查与复查。例如“点了目标不动”，先复习 Action/lifecycle/Twist，再沿手册第 7 节定位断点；不要按本页章节从头执行所有命令。

| 新人版学习内容 | 排查手册章节 |
| --- | --- |
| 环境、路径、Bash 符号：1–3 | 1、15 |
| ROS 基础与数据链：4、7 | 2、5 |
| 重复启动和自启动：5–6 | 3 |
| TF 和安装姿态：8、13 | 4、8、13 |
| 时间与队列：9 | 6 |
| Action、lifecycle、Twist：10–11 | 7、11 |
| 串口：12 | 9 |
| 地图与自动定位：13 | 8 |
| 避障与恢复参数：14 | 10、11 |
| 云台与自旋：15 | 12 |
| 构建、日志、显示、daemon：16–17 | 14、15、16 |
| SSH：18 | 17 |
| 两终端启动：19 | 18 |
| 一键采集脚本：20 | 19 |

### 给负责带新人的同学

先让新人解释一条命令和一段输出，再让他提出下一条检查。判断能力的重点是：**知道命令看了哪一层、知道结果能证明什么、知道还缺什么证据。** 不要求第一次就会修改 C++ 或调全套导航参数。

学习资料中的历史参数不能替代现场参数；文档中的历史 PID、IP、地图名也不能直接作为当前运行对象。

### 资料依据

本文主要依据我们保存的工程源码、Linux 输出和配套排查手册。工具语法与基础概念可对照以下官方资料；Nav2 rolling 文档中较新的参数不直接套用到 Humble。

- [Humble TF2 调试说明](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.rst)：对应 TF 工具和 frame/时间错误。
- [Humble ros2 topic echo 源码](https://github.com/ros2/ros2cli/blob/humble/ros2topic/ros2topic/verb/echo.py)：对应 field、once、QoS 等选项。
- [Humble 话题入门](https://docs.ros.org/en/humble/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)：对应 topic info 与 topic hz 的含义。
- [Humble SimpleProgressChecker 源码](https://github.com/ros-navigation/navigation2/blob/humble/nav2_controller/plugins/simple_progress_checker.cpp)：对应平移进展判断。
- [Nav2 Inflation Layer 参数说明](https://docs.nav2.org/rolling/configuration_and_development/configuration_guide/core_servers/costmap_2d/costmap_plugins/inflation/)：对应本文使用的 inflation_radius、cost_scaling_factor。

[guide-components]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L253-L286
[guide-loam-endpoints]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp#L43-L60
[guide-loam-tf]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/loam_interface/src/loam_interface.cpp#L63-L97
[guide-scan-tf]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/sensor_scan_generation/src/sensor_scan_generation.cpp#L62-L100
[guide-velocity-remap]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/launch/navigation_launch.py#L160-L236
[guide-velocity-callbacks]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L93-L154
[guide-serial-subscription]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/standard_robot_pp_ros2-main/src/standard_robot_pp_ros2.cpp#L103-L111
[guide-gicp]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/small_gicp_relocalization/src/small_gicp_relocalization.cpp#L95-L167
[guide-costmap]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L368-L450
[guide-spin]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L31-L82
[guide-velocity-formula]: https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L147-L154
[guide-collector]: https://github.com/Navigator-Vision-Algorithm-Team/knowledge-base/blob/main/docs/navigation/debug-real/assets/collect_navigation_debug.sh#L106-L225
