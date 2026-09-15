# 可执行 Debug 教学案例

Python 3.10+，仅标准库，从 `knowledge-base` 根目录执行。这里的事件日志由明确的教学输入生成；没有 ROS、DDS、串口或实车运行记录。

```bash
python training/cases/run_case.py topic-mismatch --mode broken --out-dir training/cases/runs/topic-broken-1 --check-contract
python training/cases/run_case.py topic-mismatch --mode fixed --out-dir training/cases/runs/topic-fixed-1 --check-contract
python training/cases/run_case.py stale-command --mode broken --out-dir training/cases/runs/stale-broken-1 --check-contract
python training/cases/run_case.py stale-command --mode fixed --out-dir training/cases/runs/stale-fixed-1 --check-contract
python -m unittest discover -s training/cases -p 'test_*.py' -v
```

加 `--check-contract` 时 broken 返回 1、fixed 返回 0；故障模式的 1 是教学验收失败，不是程序崩溃。不加该选项时，两种有效实验均返回 0。无效输入或已存在的输出目录返回 2。每次换新的输出目录，旧证据不会被覆盖。删除故障模式命令后不能声称做过回归。

- [Topic 题目及导师解答](../../docs/navigation/debug-real/case-topic-mismatch.md)：普通相对名拼接 namespace、绝对名保留根位置；按解析后的字符串相等投递。没有实现完整 ROS 名称语法、remap、发现、QoS 或网络。
- [缓存题目及导师解答](../../docs/navigation/debug-real/case-stale-command.md)：将回调调用顺序列为输入，观察零命令前后缓存。known yaw、`last_plan=None` 是明确教学初始条件；不模拟源代码初始化、线程调度、消息同步器或真实时间。
- `inputs/`：完整固定输入；`events.jsonl` 每行一个实际执行事件，`report.json` 包含输入原始字节 SHA256、源代码参考 SHA、验收结果。`null` 输出表示该事件没有发布，不表示发布零。
- `evidence/<case>/<mode>/`：2026-09-14 在 Windows/Python 3.12.10 实际生成的四组基线，不是 ROS 输出。使用相同输入文件字节和脚本可生成相同内容。运行机版本记录在本 README，报告不含不确定墙钟值。
- `tests/`：10 个行为测试。最初运行因 `ModuleNotFoundError: run_case` 失败；实现后 10/10 通过。测试同时验证 broken 的故障存在与 fixed 的契约成立，不能把“测试全绿”误读为 broken 没故障。

| 案例 | 模式 | 实际基线 |
|---|---|---|
| Topic | broken | 发送 5，接收 0，contract=false |
| Topic | fixed | 发送 5，接收 5，contract=true |
| 缓存 | broken | 9 个事件，5 次输出，零命令后旧缓存重发 2 次，正常恢复输出 1 次 |
| 缓存 | fixed | 9 个事件，3 次输出，旧缓存重发 0 次，正常恢复输出 1 次 |

课程联系的只读源代码版本为 Navigation-2027 `183a4109b0de2030bb8970a54654937c8b039ba9`。`run_case.py` 的缓存状态机与公式改编自 [fake_vel_transform.cpp](https://github.com/Navigator-Vision-Algorithm-Team/Navigation-2027/blob/183a4109b0de2030bb8970a54654937c8b039ba9/ros_ws/src/pb2025_sentry_nav/fake_vel_transform/src/fake_vel_transform.cpp)，保留原作者 Copyright 2025 Lihan Chen 归属，按 [Apache-2.0](../LICENSE) 提供。修改包括：以 Python 显式事件替代 ROS 回调、加入 fixed 分支与输出记录。Topic 路由模型和输入是本教学包新建内容，亦采用该许可证。源导航仓库未被修改。
