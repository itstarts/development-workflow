已创建 [2026-07-19-durable-order-archive.md](/workspace/fixture/docs/plans/2026-07-19-durable-order-archive.md)。

该文件保持 `review_status: pending`，未发起独立评审，未实施或提交代码，也未操作 task/thread。PRD 门禁已重新验证通过。

完整正文如下：

```markdown
---
document_type: implementation-plan
topic: durable-order-archive
spec_path: docs/specs/2026-07-18-durable-order-archive-design.md
spec_user_approval: approved
review_status: pending
---

# 持久化订单归档实施计划

**目标：** 在保留现有 `create_order` 行为的同时，以 Python 3.14 标准库 `sqlite3` 和 SQLite 3.46 WAL 数据库实现带 revision 检查的订单保存、固定快照归档及可查询的归档终态，并使 `O-01` 至 `O-04` 的客户端结果、回滚副作用和 `G-01` 至 `G-04` 的验证合同全部可观察。

**架构：** 使用一个集中管理连接配置和 schema 的 SQLite 层；订单命令层在显式 `BEGIN IMMEDIATE` 事务中完成 revision 比较与写入；归档启动事务把订单 revision 和原始字节复制到不可变 job 快照，worker 在事务外序列化该快照，再在新的 `BEGIN IMMEDIATE` 事务中检查当前 revision 并发布归档或写入终态。所有命令结果由服务边界转换为稳定的状态码、字段和错误码。

**技术栈：** Python 3.14、标准库 `sqlite3`、SQLite 3.46、WAL、`unittest`、`tempfile`。

## 全局约束

- 权威来源是 `docs/specs/2026-07-18-durable-order-archive-design.md`；实现不得改变其中 `O-01` 至 `O-04` 的前置条件、调用方动作或 `G-01` 至 `G-04` 的可观察断言。若实现需要新增客户端可见结果，必须先回到 spec 流程，不能在实现中自行扩展矩阵。
- 当前仓库只有 `src/orders.py::create_order(order_id, owner)` 和 `tests/test_orders.py::OrderTests.test_new_order_is_created`。保留该接口及回归测试，不把现有内存对象假装成持久化记录。
- 数据库必须是磁盘文件；测试使用 `tempfile.TemporaryDirectory` 下的独立数据库，不能使用不具备同等 WAL 行为的 `:memory:` 数据库。
- `src/database.py` 统一提供 `DatabaseConfig(path: pathlib.Path, busy_timeout_ms: int = 5000)`、`connect(config) -> sqlite3.Connection` 和 `initialize_database(config) -> None`。业务连接使用显式事务控制，开启 `foreign_keys`，设置 `busy_timeout`；初始化后 `PRAGMA journal_mode` 必须为 `wal`。
- schema 的稳定字段如下；后续任务只能按 migration-safe 的新增方式扩展，不能改变字段含义：
  - `orders(order_id TEXT PRIMARY KEY, document BLOB NOT NULL, revision INTEGER NOT NULL CHECK (revision >= 0))`；
  - `archive_jobs(job_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, snapshot_revision INTEGER NOT NULL, snapshot_document BLOB NOT NULL, status TEXT NOT NULL, error_code TEXT NULL)`，其中 `status` 仅允许 `queued`、`completed`、`stale`、`failed`；
  - `order_archives(order_id TEXT PRIMARY KEY, source_revision INTEGER NOT NULL, archive_bytes BLOB NOT NULL, published_job_id TEXT NOT NULL)`。
- 所有会写业务数据的路径在第一次业务 `SELECT` 或 DML 前执行字面量 `BEGIN IMMEDIATE`。锁只能在 `commit()` 或 `rollback()` 返回后视为释放；异常路径先完成 rollback，再返回、重抛或启动记录失败终态的新事务。
- 连接不得依赖 DEFERRED 事务的读转写升级。测试通过连接 trace/代理事件验证 `BEGIN IMMEDIATE`、首次业务读取、DML、`commit`/`rollback` 的相对顺序，并通过第二条真实连接验证最终持久化状态。
- 慢速 serializer 只接收 job 中已固化的 `snapshot_document: bytes`，且必须在任何 worker 写事务开始之前完成。发布事务不能重新序列化当前订单。
- worker 发布阶段的 `sqlite3.Error`（包括 busy timeout 或注入的本地 commit 失败）归入 `O-04`：先回滚发布事务，再用新连接和新的 `BEGIN IMMEDIATE` 事务只记录 `failed`/`ARCHIVE_PERSISTENCE_FAILED`。revision 不匹配只能归入 `O-03`，不能被持久化失败覆盖。
- PUT 保存只有确认读到 current revision 与 expected revision 不相等时才能返回 `O-02`；其他 SQLite 异常在 rollback 后向上抛出，不能伪报 `ORDER_REVISION_CONFLICT` 或编造未获批准的客户端结果。
- 不增加第三方依赖，不加入提交步骤，不实施部署；README 只同步本计划实际建立的运行、状态与验证合同。

## 稳定接口与结果形状

- `src/orders.py` 保留 `create_order(order_id, owner)`，并新增 `put_order(database: DatabaseConfig, order_id: str, expected_revision: int, document: bytes) -> OrderCommandResult`。
- `OrderCommandResult` 是不可变值对象，字段为 `status_code: int` 与 `body: dict[str, int | str]`：
  - `O-01` 精确返回 `status_code == 200`、`body == {"revision": expected_revision + 1}`；
  - `O-02` 精确返回 `status_code == 409`、`body == {"error": "ORDER_REVISION_CONFLICT", "currentRevision": current_revision}`。
- `src/archive_worker.py` 提供：
  - `ArchiveService.start_archive(order_id: str, job_id: str) -> ArchiveJobView`，在同一事务中读取订单并保存固定 `snapshot_revision`/`snapshot_document`，返回 `queued`；
  - `ArchiveService.get_job(job_id: str) -> ArchiveJobView`，供调用方区分终态；
  - `ArchiveWorker.run_once(job_id: str, serializer: Callable[[bytes], bytes]) -> ArchiveJobView`，消费固定快照并返回写入后的 job 视图；
  - `ArchiveJobView(job_id: str, status: str, error_code: str | None)` 为不可变值对象；`O-03` 为 `stale`/`None`，`O-04` 为 `failed`/`ARCHIVE_PERSISTENCE_FAILED`。
- 数据层接受可注入的无参连接工厂，生产默认值必须创建真实 `sqlite3.Connection`；测试代理只允许记录事务事件或在指定 publication commit 前失败，所有读写仍落到临时 WAL 数据库。

### Task 1: 建立 WAL 存储并实现原子保存成功路径

**精确文件：**

- Create: `src/database.py`
- Create: `src/order_store.py`
- Create: `tests/__init__.py`
- Create: `tests/test_order_transactions.py`
- Modify: `src/orders.py`
- Modify: `README.md`
- Test: `tests/test_order_transactions.py`
- Test: `tests/test_orders.py`

**接口：**

- Consumes: 现有 `src/orders.py::create_order(order_id, owner)`、磁盘数据库路径、`order_id: str`、`expected_revision: int`、`document: bytes`。
- Produces: `DatabaseConfig`、数据库初始化/连接工厂、`OrderStore.save(...)`、`put_order(...) -> OrderCommandResult`，以及 `orders` 表的 committed revision/document。

**保证追踪：**

- 覆盖保证：`G-01`（保存原子递增 revision）。
- 覆盖结果：`O-01`。
- 精确测试：`tests/test_order_transactions.py::OrderSaveTests.test_save_commits_next_revision`。
- 精确命令：`python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_save_commits_next_revision -v`。
- 可观察断言：响应和从独立连接读到的数据库 revision 都等于 `expected_revision + 1`；document 是请求的新字节；trace 中 `BEGIN IMMEDIATE` 位于首次订单读取之前，更新后 `commit` 返回且没有 `rollback`；数据库 `journal_mode` 为 `wal`。

**测试方式：** spec 与仓库规则未要求 TDD；使用最小实现后运行唯一命名的保证测试，再运行现有回归测试。测试 fixture 先初始化临时文件数据库并显式 seed revision，避免把“创建缺失订单”的未定义语义混入 `O-01`。

- [ ] 实施：在 `src/database.py` 建立手动事务连接与幂等 schema 初始化；在 `src/order_store.py` 中先执行 `BEGIN IMMEDIATE`，再读取并比较 revision，匹配时更新 document/revision 并原子 commit；在 `src/orders.py` 转换为 `O-01` 的精确客户端结果，同时保留 `create_order`。
- [ ] 验证：运行 `python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_save_commits_next_revision -v`；预期一个测试通过，响应与数据库 revision 均为 expected + 1，且事务事件和 WAL 断言通过。
- [ ] 回归：运行 `python3 -m unittest tests.test_orders.OrderTests.test_new_order_is_created -v`；预期现有 `created` 行为继续通过。
- [ ] 文档同步：在 `README.md` 记录 Python/SQLite 目标版本、磁盘 WAL 初始化方式、`put_order` 成功结果和本任务的精确测试命令。

### Task 2: 实现 revision 冲突的无副作用回滚

**精确文件：**

- Modify: `src/order_store.py`
- Modify: `src/orders.py`
- Modify: `tests/test_order_transactions.py`
- Modify: `README.md`
- Test: `tests/test_order_transactions.py`

**接口：**

- Consumes: Task 1 的 `OrderStore.save(...)`、`put_order(...)`、现存订单 revision/document 与不匹配的 `expected_revision`。
- Produces: `O-02` 的 `409`/`ORDER_REVISION_CONFLICT`/`currentRevision` 结果，并在 `rollback()` 返回后释放写锁。

**保证追踪：**

- 覆盖保证：`G-02`（冲突不修改订单）。
- 覆盖结果：`O-02`。
- 精确测试：`tests/test_order_transactions.py::OrderSaveTests.test_conflict_rolls_back_and_reports_current_revision`。
- 精确命令：`python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_conflict_rolls_back_and_reports_current_revision -v`。
- 可观察断言：返回 `409`、`ORDER_REVISION_CONFLICT` 和实际 `currentRevision`；冲突前后从独立连接读取的 document bytes 与 revision 完全相同；trace 中没有订单 UPDATE，且 `rollback` 在结果返回之前完成。

**测试方式：** 在真实临时 WAL 数据库中 seed current revision，提交一个不匹配的 expected revision；同时检查结果形状、业务行前后值和事务事件顺序。

- [ ] 实施：在 Task 1 已取得 `BEGIN IMMEDIATE` 锁并完成首次读取后增加 mismatch 分支；该分支不执行 DML，先 rollback，再返回 `O-02`；SQLite/busy 异常走通用 rollback/重抛路径，不能复用冲突结果。
- [ ] 验证：运行 `python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_conflict_rolls_back_and_reports_current_revision -v`；预期一个测试通过，返回 current revision，订单字节/revision 不变并观察到 rollback。
- [ ] 文档同步：在 `README.md` 增加 `O-02` 响应字段、调用方“合并后重试”的动作，并明确只有 revision mismatch 才使用该错误码。

### Task 3: 固化归档快照并拒绝发布 stale 结果

**精确文件：**

- Modify: `src/database.py`
- Create: `src/archive_worker.py`
- Create: `tests/test_archive_worker.py`
- Modify: `README.md`
- Test: `tests/test_archive_worker.py`

**接口：**

- Consumes: Task 1/2 的数据库配置和订单行、`job_id: str`、`serializer: Callable[[bytes], bytes]`。
- Produces: `archive_jobs`/`order_archives` schema、`ArchiveService.start_archive(...)`、`ArchiveService.get_job(...)`、`ArchiveWorker.run_once(...)`，以及 `O-03` 的 `ArchiveJobView(status="stale", error_code=None)`。

**保证追踪：**

- 覆盖保证：`G-03`（陈旧快照不发布归档）。
- 覆盖结果：`O-03`。
- 精确测试：`tests/test_archive_worker.py::ArchiveCompletionTests.test_stale_snapshot_never_replaces_archive`。
- 精确命令：`python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_stale_snapshot_never_replaces_archive -v`。
- 可观察断言：serializer 收到启动时保存的 snapshot bytes，且调用期间尚未开始 worker 写事务；订单 revision 在归档启动后变化时，job 终态为 `stale`、error code 为 `None`，已有最后归档 bytes/source revision/published job 均不变；completion trace 只更新 job，并在 commit 后返回。

**测试方式：** 测试先 seed 订单和一份已发布归档，启动 job 固化快照，再通过正常保存路径推进订单 revision，最后运行 worker；用 serializer spy 和 SQL/事务 trace 同时验证快照边界、事务外序列化与 stale 事务的唯一副作用。

- [ ] 实施：扩展幂等 schema；在 `start_archive` 的 `BEGIN IMMEDIATE` 事务中读取订单并插入不可变快照；worker 先读取快照并在事务外序列化，然后开启新的 `BEGIN IMMEDIATE`，首次业务读取 current revision；不相等时只把 job 更新为 `stale` 并 commit，绝不写 `order_archives`。
- [ ] 实施：实现只读 `get_job`，使调用方能稳定查询 `queued`/`completed`/`stale`/`failed` 与可空 `error_code`；本任务只将 revision mismatch 映射为 `O-03`。
- [ ] 验证：运行 `python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_stale_snapshot_never_replaces_archive -v`；预期一个测试通过，job 为 stale，serializer 使用固定快照，最后归档 bytes 不变。
- [ ] 文档同步：在 `README.md` 记录 start → snapshot → serialize → completion check 的边界、可查询 job 状态，以及 stale 后调用方重新发起归档的动作。

### Task 4: 将本地发布失败独立分类并保持最后归档

**精确文件：**

- Modify: `src/archive_worker.py`
- Modify: `tests/test_archive_worker.py`
- Modify: `README.md`
- Test: `tests/test_archive_worker.py`

**接口：**

- Consumes: Task 3 的 worker、固定快照、当前 revision 未变化的 job，以及可注入的真实连接代理所触发的 publication commit 失败。
- Produces: 成功发布事务边界及其失败补偿路径；`O-04` 的 `ArchiveJobView(status="failed", error_code="ARCHIVE_PERSISTENCE_FAILED")`；未被替换的最后归档。

**保证追踪：**

- 覆盖保证：`G-04`（本地持久化失败独立分类并回滚）。
- 覆盖结果：`O-04`。
- 精确测试：`tests/test_archive_worker.py::ArchiveCompletionTests.test_persistence_failure_rolls_back_and_is_not_stale`。
- 精确命令：`python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_persistence_failure_rolls_back_and_is_not_stale -v`。
- 可观察断言：同 revision 分支遭遇注入的本地 publication commit 失败后，发布事务先 rollback；已有归档 bytes/source revision/published job 不变；新连接随后只把 job 提交为 `failed`，error code 精确为 `ARCHIVE_PERSISTENCE_FAILED` 且状态不是 `stale`。

**测试方式：** 使用转发到真实 SQLite connection 的 fail-once 代理，仅在发布事务实际 commit 之前抛出 `sqlite3.OperationalError`；共享事件日志必须证明失败、rollback 返回、新连接 `BEGIN IMMEDIATE`、failed 状态 commit 的顺序。测试不得用纯 mock 代替最终数据库断言。

- [ ] 实施：在 current revision 匹配时于同一 publication 事务写入/替换 `order_archives` 并把 job 标为 `completed`；捕获本地 SQLite/busy/commit 错误时先 rollback，随后使用新连接、新 `BEGIN IMMEDIATE` 事务把 job 标为 `failed`/`ARCHIVE_PERSISTENCE_FAILED`，不得运行 stale 分支或保留部分归档写入。
- [ ] 验证：运行 `python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_persistence_failure_rolls_back_and_is_not_stale -v`；预期一个测试通过，job 为 persistence failed 而非 stale，最后归档保持原字节。
- [ ] 文档同步：在 `README.md` 记录 `stale` 与 `failed`/`ARCHIVE_PERSISTENCE_FAILED` 的区别、查询字段，以及调用方等待健康后重新发起的动作。

## 实施评审策略

- 默认：全部任务完成、集成并通过相关验证后，由一名未参与实现的评审者检查最新完整 diff；评审范围包括 schema、所有业务写事务、外部结果形状、worker 状态转换、测试故障注入真实性、README 与 `G-01` 至 `G-04` 的双向追踪。修复范围内发现，重跑受影响的精确测试和完整 suite，再由同一评审者复审更新后的完整 diff，直至 `APPROVED` 后停止。
- 中间里程碑评审：Task 2 完成且两个订单事务测试通过后触发。理由是 Task 1/2 建立了后续 worker 复用的 WAL、`BEGIN IMMEDIATE`、rollback 和连接注入关键基础，跨越 transaction/consistency 边界。评审只检查 `src/database.py`、`src/order_store.py`、`src/orders.py`、`tests/test_order_transactions.py` 和对应 README 内容，确认首次业务读取顺序、锁释放点、O-01/O-02 结果和真实数据库断言；修复并重跑两个订单精确测试后，才进入 Task 3。

## 最终验证

1. 在目标运行环境执行版本门禁：

   `python3 -c 'import sqlite3, sys; assert sys.version_info[:2] == (3, 14), sys.version; assert sqlite3.sqlite_version_info[:2] == (3, 46), sqlite3.sqlite_version; print(sys.version.split()[0], sqlite3.sqlite_version)'`

   预期命令退出码为 0，并输出 Python `3.14.x` 与 SQLite `3.46.x`。本计划编写环境仅有 Python 3.9.6/SQLite 3.51.0，因此计划阶段没有冒充完成该目标环境验证。

2. 逐项运行 spec 的精确保证测试：

   - `python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_save_commits_next_revision -v`
   - `python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_conflict_rolls_back_and_reports_current_revision -v`
   - `python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_stale_snapshot_never_replaces_archive -v`
   - `python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_persistence_failure_rolls_back_and_is_not_stale -v`

   预期每条命令各运行一个测试并显示 `OK`，对应断言分别证明 `G-01`、`G-02`、`G-03`、`G-04`。

3. 运行完整回归：`python3 -m unittest discover -s tests -v`。预期现有 `test_new_order_is_created`、四个 spec 命名测试及测试模块中的辅助覆盖全部通过，没有临时数据库或 worker 线程泄漏。

4. 核对 WAL 与事务证据：四个命名测试必须使用磁盘临时数据库；至少订单事务 fixture 明确断言 `PRAGMA journal_mode == "wal"`；所有写路径的事件记录均显示 `BEGIN IMMEDIATE` 在首次业务读取/DML 前，终态只在 `commit()` 或 `rollback()` 返回后对调用方可见；serializer 事件发生在 worker publication transaction 之前。

5. 完成以下双向追踪核对；Guarantee、Outcome、测试名称、命令和断言任何一项不一致都阻止实施交付：

| Guarantee | Outcome | Task | 精确测试 | 可观察结果 |
| --- | --- | --- | --- | --- |
| `G-01` | `O-01` | Task 1 | `tests/test_order_transactions.py::OrderSaveTests.test_save_commits_next_revision` | `200`；响应与数据库 revision 均为 expected + 1；新 document 原子提交 |
| `G-02` | `O-02` | Task 2 | `tests/test_order_transactions.py::OrderSaveTests.test_conflict_rolls_back_and_reports_current_revision` | `409`/currentRevision；订单 document/revision 不变；rollback 完成 |
| `G-03` | `O-03` | Task 3 | `tests/test_archive_worker.py::ArchiveCompletionTests.test_stale_snapshot_never_replaces_archive` | job 为 stale；固定快照在事务外序列化；最后归档 bytes 不变 |
| `G-04` | `O-04` | Task 4 | `tests/test_archive_worker.py::ArchiveCompletionTests.test_persistence_failure_rolls_back_and_is_not_stale` | job 为 failed/`ARCHIVE_PERSISTENCE_FAILED` 且非 stale；最后归档 bytes 不变 |

   覆盖集合必须精确包含 spec 的 `G-01`、`G-02`、`G-03`、`G-04` 和 `O-01`、`O-02`、`O-03`、`O-04`，没有孤立保证，也没有替代 spec 精确测试的必需测试。现有 `tests/test_orders.py` 仅作为非 spec 的回归保护保留。

6. 完成“实施评审策略”中的中间里程碑评审和最终完整 diff 独立评审；修复发现并重跑受影响命令。任何目标版本门禁失败、精确测试失败、追踪不完整或最终实现评审未获 `APPROVED`，都保持实施交付未批准。
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
实施计划：/workspace/fixture/docs/plans/2026-07-19-durable-order-archive.md
计划评审状态：未通过
实施门禁：未开放