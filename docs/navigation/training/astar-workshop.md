# A* 两步练习：先补框架，再独立写出规划器

<small>整理与维护：24cst朱鑫鹏</small>

先不用写代码。看蓝色搜索怎样绕过墙，最后留下从起点到终点的一条路。

<div data-nav-visuals="查看A*搜索动图"></div>

![A星逐格搜索并绕墙到达目标的教学动图](../visuals/assets/astar.gif)

<iframe src="../../visuals/playground.html?scene=astar" title="A星搜索单步与播放演示" width="100%" height="620" loading="lazy" style="border:0;border-radius:12px"></iframe>

[单独打开演示](../visuals/playground.html?scene=astar)。先按几次「单步」，再换「无路可走地图」：能解释它什么时候该停止，就可以开始下面的小程序练习了。

**今天先做到这里：** 动画用来认过程；下面会换成更小的 3×3 地图，先手算 6 步，再运行 `detour` 核对。不同地图的路径步数不一样。框架填空和独立实现分两次完成。

<link rel="stylesheet" href="../../visuals/reader.css">
<script src="../../visuals/reader.js" defer></script>
<div data-nav-fold></div>

## 这次练习怎么安排

这节课接在[规划与代价地图](../planning/README.md)后面，目标是把 `f=g+h` 变成可运行、可验收的代码。先用一张九格地图手算，再补齐三个核心函数；第二步在个人仓库从空文件实现相同接口，仍用同一批输入检查。

练习借鉴了 [AIM 2025–26 导航入队考核](https://github.com/unnc-aim/aim-2526-navigation-final-assessment)中“纯算法与 ROS 接入分开、启发式/主循环/回溯三处 TODO”的安排。本页的二进制小图、代码和检查器由本队课程重新编写；独立实现与同一接口复验是本页增加的第二步。

## 1. 先把地图和答案说清楚

把机器人暂时看成一个点。每次只能走到上、下、左、右的相邻格，每步代价为 1；障碍格不能走，不能斜着穿过去。这个简化模型让我们先判断算法正确性，机器人尺寸和转弯约束留到后面的真实 Planner 阅读。

这里采用图像式行列方向：左上角是 `(x=0,y=0)`，`x` 向右增加，`y` 随行号向下增加。坐标写 `(x,y)`，读取却是 `grid[y][x]`。它不是 ROS 的世界坐标；不能把行号直接当作地图中的米。

```text
       x=0  x=1  x=2
y=0     S    #    G
y=1     .    #    .
y=2     .    .    .

S=(0,0), G=(2,0), #=1 障碍, .=0 通行
```

输入就是 `[[0,1,0],[0,1,0],[0,0,0]]`。起终点之间直线只有 2 格，但中间有墙，合法路径必须下到第三行绕过去。数边得到代价 6，数路径上的点得到 7；把这两个数字混淆，是第一次作业最常见的错误之一。

所有实现都保留同一个入口：

```python
plan(grid, start, goal) -> dict
```

`grid` 是非空、等宽、只含整数 `0/1` 的二维列表或元组；`start/goal` 是两个整数构成的列表或元组。输入不包含 unknown；出现 `-1` 就明确拒绝，导入真实地图时须先另行规定 unknown 策略。

| 返回字段 | 本课约定 | 小图的结果 |
|---|---|---|
| `status` | `ok` 找到路径；`no_path` 合法输入但不可达；`invalid` 输入非法 | `ok` |
| `path` | 从起点到终点的有序 `[[x,y], ...]`；失败时 `[]` | 7 个点 |
| `cost` | 四邻接单位代价之和；失败时 `None`（JSON 为 `null`） | `6` |
| `expanded` | 实际处理过的不同通行格数，包含取出的终点；不计堆中旧条目 | `7` |

非法输入在搜索前结束，返回 `invalid, [], None, 0`。起终点是同一个通行格，返回 `ok, [[x,y]], 0, 1`；如果同一个格是障碍，仍是非法输入。`plan` 不得改动输入地图。

## 2. 手算：启发式为什么可以“猜”

`g(n)` 是已经走到格子 `n` 的最小已知代价；`h(n)` 是从 `n` 到目标的估计剩余代价；`f(n)=g(n)+h(n)` 是本次优先级。A* 从候选队列中取出 `f` 最小的格子处理，而不是每次只选离目标最近的邻居。

四邻接单位成本使用曼哈顿距离：

```text
h(n) = |x - goal_x| + |y - goal_y|
```

目标在 `(2,0)`，起点的 `h=2`。它忽略墙，所以会低估真实的 6 步；这样的低估可以用来引导搜索。沿上图唯一的合法路线，先在纸上填出下表，再用计算器核对。

| 取出的格子 | `g` | `h` | `f` | 新发现的后继 |
|---|---:|---:|---:|---|
| `(0,0)` | 0 | 2 | 2 | `(0,1)` |
| `(0,1)` | 1 | 3 | 4 | `(0,2)` |
| `(0,2)` | 2 | 4 | 6 | `(1,2)` |
| `(1,2)` | 3 | 3 | 6 | `(2,2)` |
| `(2,2)` | 4 | 2 | 6 | `(2,1)` |
| `(2,1)` | 5 | 1 | 6 | `(2,0)` |
| `(2,0)` | 6 | 0 | 6 | 终点，结束 |

在 `(0,1)`，距离目标反而比起点更远，但绕墙必须先这样走。只按 `h` 做局部贪心，无法解释这一步；A* 保留候选队列和已知 `g`，允许暂时远离目标。

曼哈顿距离在本课条件下还满足一致性：每次移动一格，`h` 最多下降 1，因此 `h(n) <= 1+h(neighbor)`。配合正确的代价更新，取出终点时可以结束搜索。本课参考实现用这个条件管理已处理集合；更改运动规则或启发式后，不能直接假定仍成立。

如果以后允许对角移动且代价为 `sqrt(2)`，曼哈顿距离可能高估：`(0,0)` 到 `(1,1)` 的曼哈顿距离为 2，实际可以是约 1.414。先重新规定运动、代价和启发式，再讨论八邻接；本课检查仍只接受四邻接。

## 3. 第一步：下载框架，完成三个 TODO

配套文件都在本知识库的 `docs/navigation/training/assets/`。下面是实际文件的相对下载链接，克隆仓库后也可直接打开；它们尚未发布到远程 `main`，所以这里不编造 GitHub 新文件链接。

- [下载待补模板 astar_starter.py](assets/astar_starter.py)：先读 `plan` 和 `valid_input`，再依次补 `heuristic`、`search`、`reconstruct_path`。
- [下载固定输入 astar_cases.json](assets/astar_cases.json)：地图、起终点和手工预期状态/代价都在里面。
- [下载参考与检查器 astar_reference.py](assets/astar_reference.py)：先独立尝试，再读 `plan` 的堆循环和 `check_result` 的路径检查。
- [下载回归测试 test_astar_workshop.py](assets/test_astar_workshop.py)：读 `independent_distance` 和 128 幅小图测试，理解答案如何独立复算。

需要 Python 3.10 或更新版本，只用标准库，不需要先安装 ROS 或绘图库。以下命令从**知识库根目录**运行，使用 Ubuntu 常见的 `python3`；Windows 已安装 Python 时可换成自己的 Python 可执行文件或 `py -3`。

先运行参考小图，确认地图与手算一致：

```bash
python3 docs/navigation/training/assets/astar_reference.py --case detour
```

应看到下面这些字段；`case` 是命令行附加的案例名，不属于 `plan` 必须返回的四个字段。

```json
{
  "case": "detour",
  "status": "ok",
  "path": [[0,0],[0,1],[0,2],[1,2],[2,2],[2,1],[2,0]],
  "cost": 6,
  "expanded": 7
}
```

把模板复制进自己的作业目录，保留教学资产原样。下面的相邻目录只是位置示例，可换成个人仓库路径。

```bash
mkdir -p ../my-astar-homework
cp docs/navigation/training/assets/astar_starter.py ../my-astar-homework/my_astar.py
python3 ../my-astar-homework/my_astar.py
```

第一次运行会在标准错误中给出 `unfinished: TODO 1...`，退出码为 1。这是模板明确提示未完成。不要把异常删掉、直接返回空路径冒充完成；也不要把三个 TODO 的故意缺实现当作参考程序测试失败。

### 3.1 `heuristic`：先保证单位和下界

填完函数后，手动检查 `(0,0)` 到 `(2,0)` 是 2，`(0,2)` 到 `(2,0)` 是 4，目标到自己是 0。这里的单位是“步”，不是米、欧氏距离平方或带方向的差值。

### 3.2 `search`：队列里存什么，什么时候更新

框架已经准备了四个容器：`frontier` 放待处理格，`g_score` 记最小已知代价，`parent` 记前驱，`closed` 记已处理的格。堆条目是 `(f,g,插入序号,(x,y))`；同 `f` 时参考先比 `g`，再按入队顺序决定，保证可重复。

用 `heapq.heappop` 取出候选格，跳过已经处理或 `g` 已过期的旧条目。确认这是新处理格后计数，再判断它是不是终点。发现终点邻居就立即结束，会在更一般的加权搜索中留下错误习惯；本课在终点被取出时结束。

对上下左右邻居，先查边界，再读 `grid[ny][nx]`，最后计算 `candidate_g=g+1`。只有 `candidate_g` 更小时，才同时改 `g_score`、`parent` 并压入新条目。Python 堆不需要原地删掉旧条目，下一次取出时识别过期即可。

候选队列耗尽表示合法地图上没有路，返回 `no_path`、空路径、`None` 代价和已处理数。别写无限的 `while True` 等待不存在的终点。

### 3.3 `reconstruct_path`：沿父指针回家

如果 `parent[(2,0)]=(2,1)`，说明当前最便宜的已知路线最后一段从 `(2,1)` 走来。由终点不断找前驱会得到“终点到起点”，最后反转才是需要发布和绘制的顺序。

起点没有父节点，因此回溯包含它之后就停止。起终点相同会直接得到一个点；不能为了让数组看起来像一条线而重复添加起点。

三个函数完成后，先运行自己的小图，再检查所有固定输入：

```bash
python3 ../my-astar-homework/my_astar.py
python3 docs/navigation/training/assets/astar_reference.py --check ../my-astar-homework/my_astar.py
```

检查器会导入文件并调用 `plan`，所以把演示运行放在 `if __name__ == "__main__":` 下；不要在模块导入时启动节点或等待键盘输入。检查器在同一进程中调用算法，不能自动终止学生的死循环；若卡住，用终端中断，再检查无解分支的退出条件。

## 4. 边界验收：成功、无路、非法输入分别看

| 固定案例名 | 想抓住的问题 | 参考 `status / cost` |
|---|---|---|
| `detour` | 绕障，检查父指针顺序与路径步数 | `ok / 6` |
| `no_path` | 墙完全隔开，候选耗尽后结束 | `no_path / null` |
| `out_of_bounds`、`goal_out_of_bounds` | 起点负索引、终点超出右边界 | `invalid / null` |
| `occupied`、`goal_occupied` | 起点或终点位于障碍 | `invalid / null` |
| `same`、`same_occupied` | 同一点时先检查通行性 | `ok / 0`、`invalid / null` |
| `narrow` | 只能沿单格宽折线前进，不能斜穿 | `ok / 16` |
| `empty`、`ragged`、`unknown` | 空图、行宽不齐、未定义的 `-1` 输入 | `invalid / null` |

任选一项复验，案例名必须与上表一致：

```bash
python3 docs/navigation/training/assets/astar_reference.py --case no_path
python3 docs/navigation/training/assets/astar_reference.py --case narrow
python3 docs/navigation/training/assets/astar_reference.py --case empty
```

命令行退出码也有明确含义：`--case` 找到路或确认无路返回 0，非法地图返回 2；未知案例名、学生文件不存在或导入失败也返回 2。`--check` 学生结果不合格返回 1，通过返回 0。模板直接运行未完成返回 1。

`--all` 会检查参考实现，`--check FILE.py` 会检查指定学生模块；两者都包含 12 个固定案例和 128 幅三乘三小图。固定案例中的预期非法输入是需要正确处理的测试，因此它们通过时整套检查仍返回 0，而不是 2。

```bash
python3 docs/navigation/training/assets/astar_reference.py --all
python3 -m unittest discover -s docs/navigation/training/assets -p test_astar_workshop.py -v
```

整套参考检查预期 `passed=true, fixed_cases=12, small_maps=128, failures=[]`；回归测试预期 14 项通过。路径合法性检查逐段核对边界、障碍、端点和相邻性，再核对 `cost=len(path)-1` 以及最优代价；跳格路径、错误代价或不可能的扩展数不能通过。

## 5. 为什么还要拿 BFS 对照

这批小图每条边代价一样，BFS 按距离逐层展开，因此能给出独立的最少步数。检查器的 `bfs_cost` 使用普通先进先出队列，不调用 A* 的启发式、回溯或优先队列；测试文件也单独写了 `independent_distance`。

三乘三网格有九格，固定两个对角端点通行，剩余七格各有通行/占据两种取值，共 `2^7=128` 幅图。每幅图都比较 A* 的状态和代价，成功时还验路径；这比只在一张看起来顺眼的图上画线更能发现更新条件和结束条件的错误。

BFS 与 A* 的路径形状可以不同，只要合法且代价相同就能通过。扩展数受同优先级的处理顺序影响，检查器按本课“不同处理格”的定义检查它的范围，不要求学生所有案例都与参考数字完全相同。

这些有限小图能证明当前案例上的行为，不能替代所有地图的算法推理。解释曼哈顿下界、一致性、严格改善 `g` 和终点取出条件，仍是口头验收的一部分。

## 6. 第二步：个人仓库从空文件独立实现

第一步通过后，暂时关上模板与参考，在个人仓库新增 `my_astar_independent.py`。自己决定容器与函数拆分，保留 `plan(grid,start,goal)` 和本课返回契约；不用沿用参考的函数名或固定扩展顺序。

先写出地图规则与结束条件，再实现搜索和回溯；给 `no_path`、`same`、非法起终点各留一个自己的回归用例。完成后从知识库根目录复验：

```bash
python3 docs/navigation/training/assets/astar_reference.py --check ../my-astar-homework/my_astar_independent.py
```

交付包含手算表、第一步补全版、第二步独立版、固定输入版本和检查结果。口头讲清“候选队列里可能有旧条目”“为什么回溯要反转”“无路和输入非法有什么区别”；再给导师一张自己新增的地图，由双方独立算出最优代价。

T5 还要记录耗时。`plan` 的四个返回字段不包含计时，可在自己的调用处用 `perf_counter` 测量一次搜索，单位从秒转成毫秒；文件读取、打印和画图放在计时区间之外：

```python
from time import perf_counter
started = perf_counter()
result = plan(grid, start, goal)
elapsed_ms = (perf_counter() - started) * 1000
```

固定地图与端点，记录重复次数、各次耗时和运行环境。小图耗时很短，系统调度和计时开销会占较大比例；先保证路径与代价正确，再解释耗时，不能凭一次小数排名判断算法优劣。

如果只把参考文件改名，检查器能验证数值，但无法证明独立实现过程。第二步的代码说明、自己的测试和现场改图解释，需要与输出一起评估。此练习接入 S4；阶段门槛仍以[作业与验收](../assignments/README.md)为准。

## 7. 接回本队 Planner，ROS 接入留作拓展

本队现用配置在主导航仓库的 [`nav2_params.yaml / GridBased` L468–503](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml#L468-L503)，固定审查提交为 `183a4109b0de2030bb8970a54654937c8b039ba9`。它选择 `nav2_smac_planner/SmacPlannerHybrid`、`DUBIN` 运动模型和 64 个朝向桶，状态还要考虑朝向和运动约束；不能把本课点机器人的二维 A* 直接等同于它。

完成离线两步后，可以再做独立的 ROS 拓展：读 `OccupancyGrid`，明确 unknown/阈值策略，将输入转为本课行列方向；把输出格中心按 resolution、origin 和 origin yaw 转成地图坐标，再封装为 `nav_msgs/Path`。图像行向下与 ROS 栅格方向的转换，须先用三个已知格中心核对，不能只在 RViz 看外观。

拓展还需提交真实 Topic 类型、frame、时间戳、地图输入、路径输出和 RViz 结果；确认非法输入/无路时不继续发布旧成功路径。需要 ROS2 Humble 和对应运行环境才能另行验收。本页资产只验证纯 Python 搜索与数值契约，**没有运行 ROS Path 接入或实车跟踪**；离线通过不会自动算作这两项通过。
