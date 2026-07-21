已创建唯一一份待评审计划：[实施计划](/workspace/fixture/docs/plans/2026-07-21-durable-order-archive.md:1)。

未实施代码、未评审或批准计划、未创建 task/thread。PRD 复核通过，现有 1 项测试通过，`git diff --check` 通过。

完整正文：

```markdown
---
文档类型: 实施计划
主题: durable-order-archive
技术规格: docs/specs/2026-07-18-durable-order-archive-design.md
技术规格用户批准: 已批准
评审模式: 逐级
计划评审状态: 待评审
---

# 持久化订单归档实施计划

**目标：** 在不破坏现有订单创建行为的前提下，以 SQLite WAL 持久化订单；保存时执行 revision 校验；从固定快照启动后台归档，并让调用方通过 job 终态准确区分 `completed`、`stale` 与带 `ARCHIVE_PERSISTENCE_FAILED` 的 `failed`。

**架构：** 在现有 `src/orders.py` 内增加最小 SQLite 存储和归档 worker 边界。订单保存与归档发布各自使用一个短写事务；快照读取与序列化在写事务外完成，发布事务重新读取 revision 后再决定原子替换最后完成归档、记录 `stale`，或在本地提交失败回滚后记录 `failed`。job 使用已有的 `order_id` 与 `snapshot_revision` 作为复合定位信息，不引入额外持久身份。

**技术栈：** Python 3.14、标准库 `sqlite3` / `threading` / `unittest`、SQLite 3.46 WAL。

## 全局约束

- 产品范围上限是 `docs/requirements/2026-07-18-durable-order-archive.md`；技术行为以已批准的 `docs/specs/2026-07-18-durable-order-archive-design.md` 为准。任务中的每项生产变更和测试必须能回溯到这两份文档的现有表述。
- 保存结果只实现 spec 已确认的两种可观察结果：成功返回 `200` 与新 revision；冲突返回 `409`、`ORDER_REVISION_CONFLICT` 与当前 revision，且不修改订单。
- job 只记录 spec 已确认的终态 `completed`、`stale`、`failed`；`failed` 的已确认错误分类仅为 `ARCHIVE_PERSISTENCE_FAILED`。`stale` 与 `failed` 都不得替换最后完成归档。
- 慢速序列化必须在事务外；保存和发布各使用一个短写事务；发布事务内重新校验 snapshot revision。事务失败必须回滚，且不得把本地提交失败归类为 `stale`。
- 只配置仓库已确认的 SQLite WAL 行为；不新增跨进程协调协议、通用恢复框架、额外持久身份、额外状态机或与当前风险无关的并发测试矩阵。
- 保留现有 `create_order(order_id, owner)` 行为和 `tests/test_orders.py` 回归证据。若实现需要改变上述已批准状态、错误、结果或验证范围，停止实施并返回 spec/需求审批，不在计划内自行扩写。

## 验收实施范围

### 关键 E2E 场景

无。已批准 spec 将最小充分证据限定为保存事务测试与 worker 定向测试；当前仓库也没有生产式跨层入口。不得把这些定向测试扩展为未批准的 E2E 范围。

### 人工验收场景

无。已批准 spec 没有产品体验或主观判断验收项，全部批准结果由定向自动化证据验证。

### 定向自动化证据

- `test_save_order_increments_revision_atomically`：revision 匹配时订单与 revision 原子提交并返回 `200` 与新 revision。
- `test_save_order_conflict_preserves_order_and_returns_current_revision`：revision 不匹配时返回 `409 ORDER_REVISION_CONFLICT` 与当前 revision，数据库订单保持不变。
- `test_archive_snapshot_becomes_stale_when_revision_changes_during_serialization`：序列化期间订单 revision 变化时，worker 记录 `stale` 且不替换最后完成归档。
- `test_archive_persistence_failure_is_failed_and_preserves_completed_archive`：revision 未变化但本地归档提交失败时，事务回滚并记录 `failed` / `ARCHIVE_PERSISTENCE_FAILED`，不得误报 `stale`，最后完成归档保持不变。

### Task 1: 建立 WAL 订单存储与 revision 校验保存

**精确文件：**

- Modify: `src/orders.py`
- Create: `tests/test_order_persistence.py`
- Test: `tests/test_orders.py`

**接口：**

- Consumes: 现有 `create_order(order_id, owner)` 产生的订单字典、调用方提供的 `expected_revision`、文件型 SQLite 数据库路径。
- Produces: `save_order(database_path, order, expected_revision)`；成功形状为 `{"status_code": 200, "revision": new_revision}`，冲突形状为 `{"status_code": 409, "error": "ORDER_REVISION_CONFLICT", "revision": current_revision}`，其中两个 revision 值均为整数。首次持久化以不存在记录的 revision `0` 为预期值并写入 revision `1`；后续成功保存将 revision 原子加一。

**需求与风险追踪：**

- 需求或风险依据：PRD 中“save an order with revision checks”；spec `关键结果与失败边界` 的“revision 校验保存”和“冲突保留用户草稿”两行；spec `事务边界`；spec `需求与验证追踪` 的“revision 校验保存”行。
- 最小实现：在 `src/orders.py` 增加文件型 SQLite 初始化并确认 `PRAGMA journal_mode=WAL`；只建立保存订单所需字段（`order_id`、现有订单字段、`revision`）。在一个短写事务内以 `expected_revision` 条件写入并递增 revision；条件不匹配时不写订单，读取并返回当前 revision。任何写异常均由事务回滚，不新增重试或锁协议。
- 定向验证：在 `tests/test_order_persistence.py` 实现 `test_save_order_increments_revision_atomically` 和 `test_save_order_conflict_preserves_order_and_returns_current_revision`；继续运行现有 `tests/test_orders.py`。
- 可观察断言：匹配保存返回 `200`，持久化字段与 revision 同时变更且 WAL 已启用；冲突返回 `409 ORDER_REVISION_CONFLICT` 和当前 revision，冲突前后的持久化订单完全相同；现有创建测试仍通过。
- 范围检查：不增加 HTTP 框架、恢复框架、额外错误码、额外 revision 分支或并发矩阵。

**测试方式：** 仓库与 spec 未要求 TDD；实现最小事务边界后运行两项已批准定向测试和现有回归测试。

- [ ] 实施：在 `src/orders.py` 增加 WAL 初始化与 `save_order`，保留 `create_order`。
- [ ] 验证成功保存：运行 `python3 -m unittest discover -s tests -p 'test_order_persistence.py' -k test_save_order_increments_revision_atomically`；预期 1 项测试通过，revision 与订单原子更新。
- [ ] 验证冲突：运行 `python3 -m unittest discover -s tests -p 'test_order_persistence.py' -k test_save_order_conflict_preserves_order_and_returns_current_revision`；预期 1 项测试通过，订单未变化且返回当前 revision。
- [ ] 验证现有行为：运行 `python3 -m unittest discover -s tests -p 'test_orders.py'`；预期现有 1 项测试通过。
- [ ] 文档同步：本任务不改变已批准文档；README 在 Task 3 随完整行为统一更新。

### Task 2: 从固定快照异步归档并拒绝陈旧发布

**精确文件：**

- Modify: `src/orders.py`
- Create: `tests/test_order_archive.py`
- Test: `tests/test_order_persistence.py`

**接口：**

- Consumes: 已持久化的 `order_id`、其当前 revision、Task 1 的数据库初始化与保存边界。
- Produces: `start_archive(database_path, order_id)` 在启动标准库后台线程前读取不可变订单快照，并返回仅由 `order_id` 与 `snapshot_revision` 组成的 job 定位字典；worker 落库后，`get_archive_job_status(database_path, order_id, snapshot_revision)` 只返回 spec 已批准的终态及适用的错误分类。本计划不增加未批准的非终态或查询结果。内部 `_serialize_snapshot(snapshot)` 只负责事务外序列化，不形成新的公开协议。

**需求与风险追踪：**

- 需求或风险依据：PRD 中“start a background archive from a fixed snapshot”；spec `关键结果与失败边界` 的“固定快照归档”与 stale 结果；spec `事务边界` 的事务外慢序列化、提交时 revision 重检和原子替换约束；spec `需求与验证追踪` 的“固定快照归档”行。
- 最小实现：增加最后完成归档存储，以及按 `(order_id, snapshot_revision)` 定位、只保存终态的 job 存储；不生成额外 job ID。`start_archive` 先复制订单与 revision，再启动 worker。worker 在事务外序列化该固定快照；发布短事务重新读取 revision，匹配时原子替换该订单最后完成归档并记录 `completed`，不匹配时只记录 `stale`，不得写归档。
- 定向验证：在 `tests/test_order_archive.py` 实现 `test_archive_snapshot_becomes_stale_when_revision_changes_during_serialization`。测试仅用 `threading.Event` 暂停 `_serialize_snapshot`，在暂停期间调用 Task 1 的 `save_order` 推进 revision，随后释放 worker 并查询终态。
- 可观察断言：保存操作可在慢序列化期间完成；worker 完成时观察到 revision 已变化并记录 `stale`；预置的最后完成归档不变；没有 `completed` 发布。测试在释放 worker 后以有界等待确认终态记录已经落库，再调用 job 查询；等待过程不形成额外持久状态。
- 范围检查：不增加队列框架、调度框架、持久 worker 身份、非终态状态或额外并发组合。

**测试方式：** 只增加 spec 指定的“worker 完成时 revision 变化”定向测试，并回归 Task 1 的保存测试。

- [ ] 实施：在 `src/orders.py` 增加固定快照读取、后台 worker、最后完成归档原子替换、终态 job 查询和 stale 分支。
- [ ] 验证：运行 `python3 -m unittest discover -s tests -p 'test_order_archive.py' -k test_archive_snapshot_becomes_stale_when_revision_changes_during_serialization`；预期 1 项测试通过，job 为 `stale` 且最后完成归档未变化。
- [ ] 回归：运行 `python3 -m unittest discover -s tests -p 'test_order_persistence.py'`；预期 Task 1 的 2 项测试通过。
- [ ] 文档同步：本任务不改变已批准文档；README 在 Task 3 随完整行为统一更新。

### Task 3: 区分本地归档提交失败并同步仓库说明

**精确文件：**

- Modify: `src/orders.py`
- Modify: `tests/test_order_archive.py`
- Modify: `README.md`

**接口：**

- Consumes: Task 2 的发布短事务和 `get_archive_job_status(database_path, order_id, snapshot_revision)`。
- Produces: 发布事务发生本地 SQLite 提交错误时，查询结果为 `{"status": "failed", "error": "ARCHIVE_PERSISTENCE_FAILED"}`；revision 不匹配仍只产生 `{"status": "stale"}`。不增加其他公开错误分类。

**需求与风险追踪：**

- 需求或风险依据：PRD 中“distinguish a stale snapshot from local persistence failure by querying the job status”；spec `关键结果与失败边界` 的“陈旧与持久化失败可区分”行；spec `事务边界` 的回滚及“不得把本地提交失败报告为 stale”；spec `需求与验证追踪` 的“失败状态可查询”行。
- 最小实现：将归档发布事务的本地 SQLite 错误与 revision 不匹配分开处理；本地错误先回滚未完成发布，再以短事务记录 `failed` 与 `ARCHIVE_PERSISTENCE_FAILED`。不重试发布，不替换最后完成归档，不加入通用故障恢复机制。
- 定向验证：实现 `test_archive_persistence_failure_is_failed_and_preserves_completed_archive`。测试在 SQLite 内建立仅阻止最后完成归档写入的临时 trigger，以触发真实本地写失败；保持订单 revision 不变，并预置最后完成归档。该 trigger 仅属于测试夹具，不向生产代码增加故障注入接口。
- 可观察断言：发布写入已回滚；job 为 `failed` 且错误为 `ARCHIVE_PERSISTENCE_FAILED`；job 不是 `stale`；预置最后完成归档字节不变。
- 范围检查：不增加重试策略、恢复队列、额外失败码、额外状态机或无关故障矩阵。

**测试方式：** 只增加 spec 指定的本地提交失败 worker 定向测试，然后运行完整回归。

- [ ] 实施：在 `src/orders.py` 增加发布失败回滚与 `failed` 状态记录，保持 stale 判断独立。
- [ ] 验证：运行 `python3 -m unittest discover -s tests -p 'test_order_archive.py' -k test_archive_persistence_failure_is_failed_and_preserves_completed_archive`；预期 1 项测试通过，失败分类准确且最后完成归档未变化。
- [ ] 完整回归：运行 `python3 -m unittest discover -s tests -p 'test*.py'`；预期现有 1 项测试与新增 4 项定向测试全部通过。
- [ ] 文档同步：更新 `README.md`，只把“当前为内存实现”的过时说明改为已实现的 SQLite WAL/revision/固定快照归档边界，并记录完整测试命令；不增加未批准能力。

## 实施评审策略

- 默认：全部三个任务集成并通过相关验证后，由一名未参与实现的评审者依据已批准 PRD、已批准 spec、`AGENTS.md` 和当前验证证据检查最新完整 diff。每项 finding 分类为 `BLOCKING_IN_SCOPE`、`SCOPE_CHANGE_REQUIRED` 或 `NON_BLOCKING_NOTE`；只修复有现有依据且能在最小范围内修正的 `BLOCKING_IN_SCOPE`。范围扩展返回需求/用户决策，不在评审循环中实施。重跑受影响验证后，由同一评审者复审原阻断项、变更区域和修复引入的回归；获得 `APPROVED` 后停止。若连续两轮修复与复审仍未通过，则停止自动循环、报告剩余发现并保持实施门禁关闭。
- 中间里程碑评审：无。事务与一致性边界在三个任务集成后由一次完整独立评审覆盖；不按任务数量增加评审门。

## 最终验证

1. 在目标 Python 3.14 / SQLite 3.46 环境运行 `python3 -c 'import sqlite3, sys; assert sys.version_info[:2] == (3, 14); assert sqlite3.sqlite_version_info[:2] == (3, 46)'`；预期退出码为 0。
2. 运行 `python3 -m unittest discover -s tests -p 'test*.py'`；预期现有 1 项测试和新增 4 项定向测试全部通过，无失败或错误。
3. 运行 `git diff --check`；预期退出码为 0。
4. 核对四项定向证据逐项对应 spec `需求与验证追踪`：保存成功、保存冲突、revision 变化导致 stale、本地提交失败导致 failed；确认 `stale` 与 `failed` 都未替换最后完成归档，且失败没有被误分类。
5. 由实施独立评审者按上述策略检查最新完整 diff 与验证输出；计划未批准任何 E2E 或人工验收，因此不得用新增场景替代这四项定向证据，也不得为了追踪完整性增加通用机制、标识符或测试范围。
```

需求文档：/workspace/fixture/docs/requirements/2026-07-18-durable-order-archive.md
需求主题：durable-order-archive
需求范围：功能
需求理解置信度：98
需求理解确认：已确认
需求文档用户批准：已批准
需求文档独立评审：已通过
技术规格门禁：已开放
技术规格：/workspace/fixture/docs/specs/2026-07-18-durable-order-archive-design.md
技术规格用户批准：已批准
技术规格独立评审：已通过
实施计划：/workspace/fixture/docs/plans/2026-07-21-durable-order-archive.md
计划评审状态：未通过
实施门禁：未开放
