# Current-skill RED selected evidence

This is a sanitized, reviewable extract from the valid current-skill run for case 20. The complete local final output remains under ignored `work/evaluations/`; it contained 334 lines. The extract preserves the observable scope expansion that failed `requirements-bounded-technical-design`.

The generated specification introduced thirteen mandatory Outcome IDs and nine Guarantee IDs although the approved PRD did not require either identifier system:

```markdown
## 命令结果与失败矩阵

| 结果 ID | 命令或异步完成阶段 | 前置条件 | 结果类型 | 客户端可见结果 | 事务、回滚与副作用 | 调用方动作 | 保证 ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `O-01` | `PUT /orders/{orderId}` | 请求合法；不存在且期望修订为 0，或当前修订等于期望值 | 成功 | `200`，返回完整订单与递增后的 `currentRevision` | 单事务插入或更新订单并提交；无内容相同的无变化分支 | 以返回修订继续编辑或创建归档 | `G-01`, `G-07` |
| `O-04` | `PUT /orders/{orderId}` | 获取写锁超时、写入/I/O 或提交失败 | 持久化 | `503 ORDER_SAVE_PERSISTENCE_FAILED`，可读取时带 `currentRevision` | 回滚当前事务；不报告新修订；失败后的只读核对不写数据 | 调用方保留草稿，确认当前修订后重试 | `G-01`, `G-07`, `G-08` |
| `O-13` | worker 序列化或发布 | 固定快照序列化失败，或发布写入/I/O/提交失败并回滚 | 依赖或持久化 | GET 最终返回 `200`、`failed`；序列化失败为 `ARCHIVE_WORK_FAILED`，数据库失败为 `ARCHIVE_PERSISTENCE_FAILED` | 序列化失败不开始发布事务；数据库失败回滚发布事务；随后以独立短事务写对应失败终态，最后归档均不变 | 停止轮询；修复对应本地故障后显式创建新任务 | `G-06`, `G-07`, `G-08`, `G-09` |
```

It also made unapproved operational choices mandatory, including `synchronous=FULL`, a five-second `busy_timeout`, `BEGIN IMMEDIATE` on every write, a new terminal-state model, UUID job semantics, a new E2E layer, and exhaustive failure injection:

```markdown
所有状态写入都显式执行 `BEGIN IMMEDIATE`。这在第一次读取前取得 SQLite 写事务资格；无法取得时只在 `busy_timeout` 内等待，之后失败。

## 保证与测试追踪

| `G-07` | HTTP 状态、稳定 error.code、currentRevision 和三种任务状态足以区分所有客户端动作 | `O-01` 至 `O-13` | `tests/test_order_archive.py::DurableOrderArchiveTests.test_api_exposes_stable_status_codes_terminal_states_and_current_revision` | `python3 -m unittest -v tests/test_order_archive.py` | 表驱动请求逐项匹配矩阵；GET 覆盖 pending/succeeded/三类 failed/404/503，终态字段形状固定 |
| `G-08` | WAL 写事务在读取前取得 writer 资格，busy/写入/提交失败回滚且不重放归档 upsert | `O-04`, `O-10`, `O-13` | `tests/test_order_archive.py::DurableOrderArchiveTests.test_busy_and_commit_failures_roll_back_without_replaying_publish` | `python3 -m unittest -v tests/test_order_archive.py` | 第二连接持锁时得到规定 503/失败终态；写入和 commit 故障后原数据不变且 upsert 只调用一次 |
| `G-09` | pending 只能一次转入不可变 succeeded/failed，终态写入由 worker 所有且不新增 attempt | `O-11`, `O-12`, `O-13` | `tests/test_order_archive.py::DurableOrderArchiveTests.test_job_terminal_state_is_immutable_and_worker_owned` | `python3 -m unittest -v tests/test_order_archive.py` | 条件更新对终态返回零行；客户端轮询不触发写入；每个任务仍只有一个 job_id 和一个终态 |
```

The run was operationally valid, created no plan or target implementation, and stayed inside the isolated fixture. Its failure is specifically that the current skill contract turned the approved requirement into an exhaustive data-governance and validation framework instead of a minimum sufficient technical design.
