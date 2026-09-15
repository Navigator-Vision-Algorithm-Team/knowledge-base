# Debug 案例 2：发过零命令，旧速度为什么再次输出

本题适合 S2 算式与 S5 状态分析，建议 60–90 分钟，是[源码练习 R2](../assignments/reading-labs.md)的可执行版本。**故障和修复都在 Python 教学状态机中实际运行；不是队内事故复盘，也没有验证生产 ROS 节点或车体停车。** 本题只修复“零命令使旧缓存失效”这个契约，自旋与命令断流另行分析。

## 学生任务：零输出和缓存状态要分开观察

已知初始 yaw=0、spin=0。先非零、再零、再同步回调，零之后禁止再次输出取消前的缓存；收到新的非零命令后应能正常恢复。

先运行 broken，逐行写下输入、缓存、是否输出及输出值。重点比较 0.3、0.4、0.45 秒；不能只截取零命令那一行。提出至少三个解释，指出最小修复应改变什么状态，再验证修复没有吞掉后续正常命令。

从 `knowledge-base` 根目录运行；仅需 Python 3.10+ 标准库。Ubuntu 按环境使用 `python3`。

```bash
python training/cases/run_case.py stale-command --mode broken --input training/cases/inputs/stale-command.json --out-dir training/cases/runs/stale-broken-1 --check-contract
```

预期验收退出码为 1，并输出 `events.jsonl` 和 `report.json`。提交命令、退出码、原始输入及 SHA256、完整状态表、假设/排除、最小修改、原故障与正常输入回归、回滚方法，以及自旋和 watchdog 的边界解释。

## 导师解答：完整输入与初始假设

`training/cases/inputs/stale-command.json` 的完整内容：

```json
{
  "initial_yaw": 0.0,
  "initial_spin": 0.0,
  "events": [
    {"at": 0.0, "event": "local_plan"},
    {"at": 0.1, "event": "command", "twist": [0.2, 0.0, 0.0]},
    {"at": 0.2, "event": "sync", "yaw": 0.0},
    {"at": 0.3, "event": "command", "twist": [0.0, 0.0, 0.0]},
    {"at": 0.4, "event": "sync", "yaw": 0.0},
    {"at": 0.45, "event": "sync", "yaw": 0.0},
    {"at": 0.46, "event": "local_plan"},
    {"at": 0.47, "event": "command", "twist": [0.0, 0.1, 0.0]},
    {"at": 0.48, "event": "sync", "yaw": 0.0}
  ]
}
```

输入文件原始字节 SHA256 为 `1d542d4f5c6298712e52f2c57b3093334b68f27a0383d72bbb5db56515da14da`。`at` 是手工设定的逻辑秒数，不是采集到的时间戳；Twist 三分量依次为 `(vx m/s, vy m/s, wz rad/s)`。

初始化使用已知 yaw、空缓存、`last_plan=None`，明确表示尚未收到 local_plan。`sync` 表示已经选择执行一次同步回调，**不模拟消息过滤器配对，也不自动调用 localPlanCallback**；需要更新时间时单独输入 `local_plan`。源节点启动时的未初始化角度、真实时钟、线程竞争、TF、上游 Nav2 和输出消费者都不在模型内。这个事件顺序用于检验一条可能的缓存路径，不声称实际 ROS 一定采用相同顺序。

## 实际生成的证据

2026-09-14 在 Windows/Python 3.12.10 运行脚本，保存于 `training/cases/evidence/stale-command/{broken,fixed}/`。每行实际执行日志包含 `input`、`branch`、`cache_before`、`cache_after`、`output` 和 `stale_reissue`。**`output=null` 表示此回调没有发布，区别于发布 `[0,0,0]`。**

| 时间 / 输入 | broken 事件后缓存 | broken 输出 | fixed 事件后缓存 | fixed 输出 |
|---|---|---|---|---|
| 0.0 local_plan | 空 | 无发布 | 空 | 无发布 |
| 0.1 command `(0.2,0,0)` | `(0.2,0,0)` | 无发布 | `(0.2,0,0)` | 无发布 |
| 0.2 sync | `(0.2,0,0)` | `(0.2,0,0)` | `(0.2,0,0)` | `(0.2,0,0)` |
| 0.3 command `(0,0,0)` | **`(0.2,0,0)`** | `(0,0,0)` | **空** | `(0,0,0)` |
| 0.4 sync | `(0.2,0,0)` | **`(0.2,0,0)`** | 空 | 无发布 |
| 0.45 sync | `(0.2,0,0)` | **`(0.2,0,0)`** | 空 | 无发布 |
| 0.46 local_plan | `(0.2,0,0)` | 无发布 | 空 | 无发布 |
| 0.47 command `(0,0.1,0)` | `(0,0.1,0)` | 无发布 | `(0,0.1,0)` | 无发布 |
| 0.48 sync | `(0,0.1,0)` | `(0,0.1,0)` | `(0,0.1,0)` | `(0,0.1,0)` |

broken 在零命令后的首个同步事件原文：

```json
{"branch": "sync_cached", "cache_after": [0.2, 0.0, 0.0], "cache_before": [0.2, 0.0, 0.0], "index": 4, "input": {"at": 0.4, "event": "sync", "yaw": 0.0}, "output": [0.2, 0.0, 0.0], "stale_reissue": true}
```

fixed 同一事件原文：

```json
{"branch": "sync_no_cache", "cache_after": null, "cache_before": null, "index": 4, "input": {"at": 0.4, "event": "sync", "yaw": 0.0}, "output": null, "stale_reissue": false}
```

两模式都是 9 个事件、1 条零命令、2 次零后同步、1 次正常恢复输出。broken 共输出 5 次、旧缓存重发 2 次，`contract_passed=false`；fixed 共输出 3 次、重发 0 次，`contract_passed=true`。判定同时要求出现零命令、后续同步和正常恢复，不以空输入或删除所有输出获得通过。

## 假设与根因定位

| 假设 | 实际证据 | 判断 |
|---|---|---|
| 零命令未到达 | 0.3 秒日志进入 `zero_immediate` 并输出全零 | 本模型中排除 |
| 自旋偏置造成再次非零 | 初始 spin=0，全部输入没有 spin 事件；再次输出的是 linear.x=0.2 | 不是本次重发原因 |
| 零之后收到新非零命令 | 0.3–0.45 秒只有两个 sync，下一条非零在 0.47 秒 | 排除该区间内的新命令 |
| 旧缓存没有失效 | 0.3 秒 `cache_after` 仍是 `(0.2,0,0)`，两个 sync 读取它 | 与重发构成完整因果链 |
| 真实同步器、DDS 或底盘再次发送 | 本模型没有这些组件 | 尚无运行证据，不能作外推结论 |

只读源码固定为 [Navigation-2027@183a410](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/tree/183a4109b0de2030bb8970a54654937c8b039ba9)，完整 SHA `183a4109b0de2030bb8970a54654937c8b039ba9`：

| 教学规则 | 源文件位置 |
|---|---|
| `EPSILON=1e-5`，local_plan 活动超时 0.5 秒 | [fake_vel_transform.cpp L23–24](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L23-L24) |
| 零/活动超时立即发布，否则缓存；零分支没有清缓存 | [cmdVelCallback L93–110](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L93-L110) |
| local_plan 更新活动时间；同步回调读缓存再发布 | [localPlanCallback / syncCallback L112–137](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L112-L137) |
| 自旋回调只改成员；旋转公式叠加 spin | [L80–83](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L80-L83)、[transformVelocity L147–156](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp#L147-L156) |

相关源码风险见[控制接口证据 R3/R4/R6/R7](../system/nav2-and-control-evidence.md)。`training/cases/run_case.py::CacheModel.step` 是这些规则的有意缩小版本，`run_stale` 执行输入并记录真实模型状态。源导航仓库保持只读。

## 最小修复与边界

本题契约是“收到按 EPSILON 判定的零命令后，取消之前缓存，直至新非零命令重新赋值”。教学脚本实际修复位于立即发布分支：

```python
if zero or inactive:
    if zero and self.mode == "fixed":
        self.cache = None
    # 随后按原公式立即输出当前输入
```

对应 C++ 的最小修改建议是在 `cmdVelCallback` 现有互斥锁保护下、求出 `is_zero_vel` 后增加以下三行。**这是审查用建议，不是已经修改、编译或验证的生产补丁。**

```diff
+ if (is_zero_vel) {
+   latest_cmd_vel_.reset();
+ }
  if (
    is_zero_vel ||
    (rclcpp::Clock().now() - last_controller_activate_time_).seconds() > CONTROLLER_TIMEOUT) {
```

清缓存保留原来的零输入立即发布与正常命令路径。以下问题仍独立存在，不能因本题通过就声称完整停止链成立：

- spin=0.5 时，全零输入仍输出角速度 0.5；`spin` 事件只改成员，不立即发布。yaw=π/2、输入 `(0.2,0,0)`、spin=0.5 时，输出约 `(0,-0.2,0.5)`。
- `CONTROLLER_TIMEOUT` 使用 local_plan 活动年龄且比较为 `>0.5`。活动刚好过去 0.5 秒时非零仍走缓存；`sync` 不检查命令年龄。测试中 at=0 更新 plan、at=0.5 缓存 `(0.2,0,0)`、at=9 直接调用 sync，仍输出该缓存。这是回调级边界测试，不是实际消息配对复现。
- 三个分量绝对值都严格小于 `1e-5` 才按零处理；`1e-6` 清缓存，但仍按原值立即变换；恰好 `1e-5` 不按零处理。
- 没有后续发布不等于消费者停止，串口缓存、固件 watchdog、取消与控制权协议需要各自的实测和验收。

## 同输入回归、正常功能与回滚

```bash
python training/cases/run_case.py stale-command --mode fixed --input training/cases/inputs/stale-command.json --out-dir training/cases/runs/stale-fixed-1 --check-contract
python -m unittest discover -s training/cases -p 'test_*.py' -v
```

fixed 验收退出 0。共享案例套件共 10 个行为测试，缓存相关测试覆盖零后两次同步无重发、后续侧移正常、旋转缓存、近零/阈值边界、旋转加自旋、spin 不立即发布、local_plan 超时边界，以及不接受倒序时间和非有限速度。两模式都会在测试中执行，broken 的已知重发应被检出。

恢复故障时以新目录 `training/cases/runs/stale-rollback-1` 重跑首条 broken 命令，应再次得到 2 次旧缓存重发、退出 1；再以 fixed 和新目录恢复通过。输出目录已存在会返回 2，程序不会覆盖旧记录。没有必要改动源导航仓库来完成回滚练习。

若推进真实 ROS 修复，需要另外记录原节点的输入、local_plan、同步 odometry、最终输出和回调顺序，在不连接驱动的独立环境先复现，再测试上述停止协议。当前[验证状态](../training/validation.md)中，生产节点编译/同步复现/物理停止仍为待验证。
