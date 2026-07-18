已创建唯一的未评审草案：[2026-07-19-durable-order-archive-design.md](/workspace/fixture/docs/specs/2026-07-19-durable-order-archive-design.md)。

未创建 plan、未实施代码、未操作 task/thread。PRD 复验通过；46 个结果 ID、20 个保证 ID 均唯一；`git diff --check` 和现有基线测试通过。按要求未发起独立评审。

完整正文如下。

````markdown
---
document_type: design
topic: durable-order-archive
requirements_path: docs/requirements/2026-07-18-durable-order-archive.md
requirements_topic: durable-order-archive
requirements_scope: feature
requirements_understanding_confidence: 98
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: pending
independent_review: pending
---

# 持久订单归档技术规格

## 目标

1. 为本地订单 API 提供带乐观并发控制的同步保存：只有 `expectedRevision` 与当前修订一致的草稿才能落库；冲突请求不得改变服务端订单，客户端提交的草稿仍由客户端持有。
2. 将一次归档请求作为持久化后台作业接受，并在接受时保存一个不可变的完整订单快照。慢速序列化不得占用数据库事务或 SQLite 写锁。
3. 仅当发布事务开始时订单仍是该快照对应的当前完整修订，才原子地发布归档、更新该订单的最后完成归档指针并把作业置为成功。
4. 让客户端仅通过稳定的 HTTP 状态、错误码、可达时的 `currentRevision` 和终态作业状态，区分编辑冲突、过期归档、后台失败与成功完成。
5. 明确 SQLite 3.46 WAL 下的事务、锁、回滚、提交核对、进程恢复和自动化验证边界，使实现者无需自行选择一致性语义。

## 非目标

- 不增加订单删除、归档删除、归档取消、优先级、批量归档或远程对象存储。
- 不支持多个 API 进程、多个后台 worker 或由仓库之外的进程直接写同一 SQLite 文件；这些拓扑需要重新评审锁与恢复保证。
- 不定义操作者认证或授权。当前证据只规定本地 API；部署边界负责限制访问。
- 不为永久进程停机、永久磁盘不可达或 SQLite 数据库损坏承诺作业进度。在进程和数据库恢复可用后，本规格定义恢复和终态收敛行为。
- 不把技术规格批准当作实现授权，也不在本文中创建实施计划或提交代码。

## 当前证据

- `docs/requirements/2026-07-18-durable-order-archive.md` 已批准，主题为 `durable-order-archive`、范围为 `feature`，要求冲突保留草稿、只从当前完整快照发布归档，并且失败或过期尝试不能替换最后完成归档。
- `README.md` 固定了 Python 3.14、标准库 `sqlite3`、SQLite 3.46、WAL、一个本地 API 进程和一个进程内后台 worker，并给出 `PUT /orders/{orderId}`、`POST /order-archives` 与 `GET /order-archives/{jobId}` 三个接口。它还明确要求事务外慢速序列化，以及区分过期快照与本地持久化失败。
- `src/orders.py` 当前只有返回 `id`、`owner`、`status=created` 的最小内存模型；没有 API、修订、数据库或归档实现。
- `tests/test_orders.py` 使用标准库 `unittest`，只覆盖现有最小创建行为。仓库没有第三方 Web 或测试框架证据，因此新接口使用 Python 标准库 HTTP 服务，测试继续使用 `unittest`。
- `AGENTS.md` 要求规格经独立评审并获用户明确批准后才可生成计划。本草案的 `user_approval` 与 `independent_review` 均保持 `pending`。

## 行为与边界

### 订单与修订

- 当前订单的可编辑字段固定为 `owner` 和 `status`。`owner` 是去除首尾空白后 1 至 128 个 Unicode 字符；`status` 只能是 `created` 或 `complete`。只有 `complete` 可开始归档。
- `orderId` 只来自 URL 或归档请求的 `orderId` 字段，必须匹配 `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`。请求体不得另带 `id`，未知字段一律拒绝，避免不同客户端形成不同快照。
- `expectedRevision` 必须是 JSON 整数且不能是布尔值，范围为 0 至 `9223372036854775807`。不存在的订单只能用 0 创建，创建后的修订为 1；已存在订单必须精确匹配当前修订。
- 两个公开状态变更命令都必须携带 `expectedRevision`：`PUT` 用它执行订单 CAS，`POST` 用它选择归档来源。worker 的内部写入不接受新的客户端修订，而是同时使用作业中持久化的 `source_revision` 与作业状态 CAS。
- 每次内容实际变化的成功保存把修订恰好加 1。相同内容保存是成功无变化，不增加修订。修订达到 SQLite 有符号整数上限后拒绝再修改。
- 服务端冲突响应不回写请求体，也不把当前服务端内容当作客户端草稿返回；它只返回当前修订。客户端负责保留、合并并用新的 `expectedRevision` 再提交。

### 固定快照与可见归档

- 接受归档时，在同一写事务中读取订单、验证 `expectedRevision` 和 `status=complete`，再把规范化快照 JSON、快照 SHA-256 和来源修订写入作业。事务提交后，订单随后变化不会改变作业快照。
- 快照是 UTF-8 规范 JSON：键按字典序排列、无非必要空白、禁止 NaN/Infinity，内容为 `id`、`owner`、`status`、`revision`。哈希按这些精确字节计算。
- worker 只读取作业中保存的快照。归档字节是包含 `schemaVersion=1`、`orderId`、`sourceRevision` 和 `order` 快照的规范 JSON；序列化与 SHA-256 计算在事务外完成。
- 同一订单和来源修订最多有一个处于 `queued`、`running` 或 `succeeded` 的作业。重复开始请求返回现有作业，不创建副本。`failed` 作业不阻止同一当前修订的新重试作业。
- 归档只通过完成事务进入可见集合。该事务重新读取订单；修订不同、订单不存在或状态不再为 `complete` 时，作业进入 `stale`，不得插入归档或更新归档头。
- `succeeded`、`stale`、`failed` 是终态且不可逆。`queued` 和 `running` 是非终态。失败或过期作业永远不能替换 `order_archive_heads` 中最后一次成功结果。

### 进度边界

- 作业状态机在进程和数据库可用、且本地锁竞争最终消失的条件下收敛到终态。数据库持续不可读时，API 返回 503；不能伪造终态。
- 没有远程依赖、取消命令或业务级序列化超时。输入上限为 64 KiB，序列化是本地有界计算；数据库等待只受 `busy_timeout=5000` 毫秒约束。
- 同步 API 不自动重放状态变更。API 调用者只在结果矩阵允许时重试。worker 对 `SQLITE_BUSY`/`SQLITE_LOCKED` 和未持久化的终态标记拥有重试责任。

## 组件与控制流

### 组件职责

- `src/orders.py`：订单字段校验、规范 JSON、修订规则与纯领域对象；保留现有 `create_order` 行为兼容性。
- `src/order_store.py`：连接工厂、SQLite 版本/PRAGMA 校验、schema v1 迁移、显式事务、错误码分类和提交核对。每个请求线程与 worker 使用自己的连接，连接不得跨线程共享。
- `src/order_api.py`：基于标准库 `http.server.ThreadingHTTPServer` 的 JSON 传输层、64 KiB 限制、HTTP/错误映射及三个公开路由。
- `src/order_archive.py`：持久作业领取、规范序列化、发布前新鲜度检查、提交核对、终态写入和启动恢复。
- SQLite 作业表是权威队列。进程内 `threading.Condition` 只用于提交后唤醒 worker；通知丢失不影响正确性，worker 还必须周期性扫描 `queued` 作业。

### 保存控制流

1. HTTP 层在事务外完成 JSON、大小、字段和类型校验，并为可能的实际写入生成内部 `save_token`。
2. 存储层执行 `BEGIN IMMEDIATE`，获得 SQLite 单一写者锁后才首次读取订单，因此不存在 deferred 读事务升级写事务的窗口。
3. 按不存在、冲突、修订耗尽、内容相同或内容变化分支处理。实际更新还使用 `WHERE order_id=? AND revision=?`，受影响行数必须为 1。
4. 内容相同分支用 `ROLLBACK` 结束无写事务并返回无变化。实际写入保存新修订与 `last_save_token` 后执行 `COMMIT`。
5. `COMMIT` 抛错时，关闭失败连接并用新连接按 `last_save_token` 核对：令牌匹配即按成功返回；前置状态仍存在即确认未应用；令牌不同且修订已前进即返回冲突；数据库不可读或状态矛盾即返回提交未知。不得盲目重放。

### 归档开始与完成控制流

1. `POST` 在事务外校验请求并预生成 `jobId`，然后执行 `BEGIN IMMEDIATE`。
2. 事务读取订单并按不存在、修订冲突和不完整分支拒绝；随后查找同一订单/修订的活动或成功作业。存在时结束事务并返回该作业。
3. 没有重复项时，在事务内生成并保存固定快照与哈希，插入 `queued` 作业并提交。只有提交成功后才通知 worker。
4. worker 用短 `BEGIN IMMEDIATE` 事务按 `created_at, job_id` 领取最早 `queued` 作业，通过 `UPDATE ... WHERE status='queued'` 比较交换为 `running/serializing` 并增加 `attempt_count`。
5. worker 提交领取事务，读取已持久化快照，在无数据库事务状态下验证哈希、生成归档字节和归档哈希。
6. worker 用一个短事务把阶段改为 `running/publishing`，预存 `candidate_archive_id` 与归档哈希；归档正文仍只在内存中。然后开启发布事务。
7. 发布事务以 `BEGIN IMMEDIATE` 开始，先读作业再读订单。只有作业仍为当前候选、订单修订等于 `source_revision` 且仍完整时，才插入不可变归档、更新归档头、把作业置为 `succeeded`；三项在一次 `COMMIT` 中原子生效。
8. 发布提交抛错时，不再执行发布 SQL。新连接按 `jobId`、`candidate_archive_id`、归档行和归档头核对；完整三元组表示已应用，无候选归档且作业仍在发布阶段表示确认未应用，任何部分可见组合表示完整性错误。数据库不可读时保留非终态并继续核对。

## API 与技术接口

所有响应使用 `application/json; charset=utf-8`。错误响应使用固定结构；字段存在但不可取得当前修订时为 `null`：

```json
{
  "error": {
    "code": "ORDER_REVISION_CONFLICT",
    "message": "stable, non-sensitive text",
    "retryable": true,
    "currentRevision": 7,
    "jobId": null
  }
}
```

`message` 只用于人类诊断，客户端分支必须依据 HTTP 状态和 `code`。响应和日志不得包含完整订单或归档正文。

三个路由只接受本文列出的 HTTP 方法。已知路由上的其他方法返回 405 `METHOD_NOT_ALLOWED`，未知路由返回 404 `ENDPOINT_NOT_FOUND`；两者均无数据库事务或副作用。

### `PUT /orders/{orderId}`

请求：

```json
{
  "expectedRevision": 6,
  "owner": "operator-1",
  "status": "complete"
}
```

- 新建返回 201；实际更新和相同内容无变化返回 200。
- 成功体固定为 `{"order":{"id":string,"owner":string,"status":string,"revision":integer},"changed":boolean}`。
- 400 `INVALID_REQUEST`：非 JSON、错误 Content-Type、超过 64 KiB、缺字段、未知字段或字段类型错误。
- 422 `INVALID_ORDER`：`orderId`、`owner`、`status` 或数值范围不合法。
- 404 `ORDER_NOT_FOUND`：不存在订单且 `expectedRevision` 非 0。
- 409 `ORDER_REVISION_CONFLICT`：订单存在但修订不匹配；必须返回可达的 `currentRevision`。
- 409 `ORDER_REVISION_EXHAUSTED`：当前修订已达上限；返回当前修订且不可重试同一内容变更。
- 503 `DATABASE_BUSY`、`ORDER_SAVE_PERSISTENCE_FAILED` 或 `ORDER_SAVE_COMMIT_UNKNOWN`：分别表示锁等待耗尽、确认未应用的本地持久化失败、无法核对提交状态。
- 500 `DATA_INTEGRITY_ERROR`：已校验输入仍触发约束或核对不变量矛盾；不可自动重试，也不得伪装成 409 编辑冲突。

### `POST /order-archives`

请求：

```json
{
  "orderId": "o-1",
  "expectedRevision": 7
}
```

- 新作业提交成功返回 202；活动或已成功的同修订作业返回 200 且复用其 `jobId`。
- 成功体固定为 `{"jobId":string,"orderId":string,"sourceRevision":integer,"status":string}`。
- 400 `INVALID_REQUEST` 或 422 `INVALID_ORDER_ID`：结构/类型或订单标识不合法。
- 404 `ORDER_NOT_FOUND`；409 `ORDER_REVISION_CONFLICT`；409 `ORDER_NOT_COMPLETE`。后两者返回当前修订。
- 503 `DATABASE_BUSY`、`ARCHIVE_START_PERSISTENCE_FAILED` 或 `ARCHIVE_START_COMMIT_UNKNOWN`。提交未知响应带预生成的 `jobId`，调用方先轮询该 ID；数据库恢复后若为 404，才以当前修订重新开始。
- 500 `DATA_INTEGRITY_ERROR`：去重分支之外发生约束或不变量错误；不创建作业，需运维介入。

### `GET /order-archives/{jobId}`

200 响应固定为：

```json
{
  "jobId": "uuid",
  "orderId": "o-1",
  "sourceRevision": 7,
  "status": "queued|running|succeeded|stale|failed",
  "phase": "queued|serializing|publishing|terminal",
  "archiveId": null,
  "currentRevision": 7,
  "error": null
}
```

- `archiveId` 只在 `succeeded` 时非空。`error` 只在 `stale` 或 `failed` 时为 `{"code":string,"retryable":boolean}`。
- `stale` 使用 `ARCHIVE_SNAPSHOT_STALE`，调用方读取 `currentRevision` 后为当前完整修订创建新作业。
- `failed` 至少区分 `ARCHIVE_SERIALIZATION_FAILED`、`ARCHIVE_PERSISTENCE_FAILED`、`ARCHIVE_WORKER_INTERRUPTED` 和 `ARCHIVE_INTEGRITY_ERROR`。
- `currentRevision` 由同一只读快照中对订单的读取获得；订单或数据库不可达时为 `null`。404 使用 `ARCHIVE_JOB_NOT_FOUND`，数据库不可用使用 503 `ARCHIVE_STATUS_UNAVAILABLE`。
- `GET` 没有持久化副作用。客户端轮询不得推动作业状态。

## 命令结果与失败矩阵

| 结果 ID | 命令或异步完成阶段 | 前置条件 | 结果类型 | 客户端可见结果 | 事务、回滚与副作用 | 调用方动作 | 保证 ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `O-01` | `PUT /orders/{orderId}` | 订单不存在，合法 `expectedRevision=0` | 成功 | 201，修订 1，`changed=true` | `BEGIN IMMEDIATE` 中插入并提交；只产生一个订单版本 | 接受新修订 | `G-02`, `G-16`, `G-17` |
| `O-02` | `PUT /orders/{orderId}` | 修订匹配且内容变化 | 成功 | 200，新修订，`changed=true` | 条件更新恰好一行并提交 | 用返回修订继续编辑 | `G-02`, `G-16`, `G-17` |
| `O-03` | `PUT /orders/{orderId}` | 修订匹配且规范内容相同 | 无变化 | 200，原修订，`changed=false` | `ROLLBACK` 结束无写事务；不使归档快照过期 | 停止 | `G-02`, `G-16` |
| `O-04` | `PUT /orders/{orderId}` | 请求结构、Content-Type、大小或类型非法 | 校验 | 400 `INVALID_REQUEST`，`currentRevision=null` | 事务外拒绝，无副作用 | 修正请求 | `G-01`, `G-16` |
| `O-05` | `PUT /orders/{orderId}` | 字段值非法 | 校验 | 422 `INVALID_ORDER`，`currentRevision=null` | 事务外拒绝，无副作用 | 修正订单 | `G-01`, `G-16` |
| `O-06` | `PUT /orders/{orderId}` | 订单不存在且预期修订非 0 | 状态 | 404 `ORDER_NOT_FOUND` | 回滚，无订单写入 | 改为创建或停止 | `G-02`, `G-16` |
| `O-07` | `PUT /orders/{orderId}` | 当前修订不匹配 | 冲突 | 409 `ORDER_REVISION_CONFLICT`，带当前修订 | 回滚；服务端订单及客户端草稿均未被替换 | 客户端合并后重试 | `G-02`, `G-16` |
| `O-08` | `PUT /orders/{orderId}` | 匹配修订已达整数上限且内容变化 | 状态 | 409 `ORDER_REVISION_EXHAUSTED`，带当前修订 | 回滚，无副作用 | 停止并运维处理 | `G-02`, `G-16` |
| `O-09` | `PUT /orders/{orderId}` | `BEGIN IMMEDIATE` 在 5000 ms 内未获锁 | 超时/冲突 | 503 `DATABASE_BUSY`，`retryable=true` | 无事务或回滚活动事务；新连接可读时带当前修订 | 调用方退避并用同一预期修订重试 | `G-03`, `G-17` |
| `O-10` | `PUT /orders/{orderId}` | 写入/提交失败，核对确认令牌未应用且前置状态未变 | 持久化 | 503 `ORDER_SAVE_PERSISTENCE_FAILED`，`retryable=true`；可读时带当前修订 | 回滚；确认没有该保存副作用 | 调用方退避后可重试 | `G-03`, `G-16` |
| `O-11` | `PUT /orders/{orderId}` 创建 | `COMMIT` 抛错但新连接读到匹配 `last_save_token` | 核对成功 | 201，修订 1，`changed=true` | 不重放；把已提交创建作为唯一结果 | 接受新修订 | `G-04`, `G-16` |
| `O-45` | `PUT /orders/{orderId}` 更新 | `COMMIT` 抛错但新连接读到匹配 `last_save_token` | 核对成功 | 200，新修订，`changed=true` | 不重放；把已提交更新作为唯一结果 | 接受新修订 | `G-04`, `G-16` |
| `O-12` | `PUT /orders/{orderId}` | 提交后数据库不可读或核对状态矛盾 | 未知 | 503 `ORDER_SAVE_COMMIT_UNKNOWN`，`retryable=false`，修订可不达 | 不重放、不声称回滚；保留数据库实际状态 | 数据库恢复后以原预期修订探测；冲突则合并 | `G-04`, `G-16` |
| `O-13` | `POST /order-archives` | 当前修订匹配、完整且无重复作业 | 成功 | 202，`status=queued` | 固定快照与作业在一个事务中提交，随后才唤醒 worker | 轮询 `jobId` | `G-05`, `G-16`, `G-19` |
| `O-14` | `POST /order-archives` | 同修订已有活动或成功作业 | 无变化 | 200，返回已有作业 | 回滚无写事务，不创建重复作业 | 轮询已有 `jobId` | `G-05`, `G-16` |
| `O-15` | `POST /order-archives` | 请求结构、大小或类型非法 | 校验 | 400 `INVALID_REQUEST`，`currentRevision=null` | 事务外拒绝，无作业 | 修正请求 | `G-01`, `G-06`, `G-16` |
| `O-39` | `POST /order-archives` | `orderId` 值不合法 | 校验 | 422 `INVALID_ORDER_ID`，`currentRevision=null` | 事务外拒绝，无作业 | 修正订单标识 | `G-01`, `G-06`, `G-16` |
| `O-16` | `POST /order-archives` | 订单不存在 | 状态 | 404 `ORDER_NOT_FOUND` | 回滚，无作业 | 停止或先创建订单 | `G-06`, `G-16` |
| `O-17` | `POST /order-archives` | 修订不匹配 | 冲突 | 409 `ORDER_REVISION_CONFLICT`，带当前修订 | 回滚，无快照、无作业 | 读取当前修订并决定是否重试 | `G-06`, `G-16` |
| `O-18` | `POST /order-archives` | 修订匹配但订单不是 `complete` | 状态 | 409 `ORDER_NOT_COMPLETE`，带当前修订 | 回滚，无作业 | 完成并保存订单后重试 | `G-06`, `G-16` |
| `O-19` | `POST /order-archives` | 写锁等待耗尽 | 超时/冲突 | 503 `DATABASE_BUSY`，`retryable=true`；可读时带当前修订 | 无事务或回滚，无作业 | 调用方退避重试 | `G-06`, `G-17` |
| `O-20` | `POST /order-archives` | 写入/提交失败且核对确认预生成 `jobId` 不存在 | 持久化 | 503 `ARCHIVE_START_PERSISTENCE_FAILED`，`retryable=true`；可读时带当前修订 | 回滚；确认没有该作业 | 调用方用当前修订重试 | `G-06` |
| `O-21` | `POST /order-archives` | `COMMIT` 抛错但核对找到预生成的该 `jobId` | 核对成功 | 202，返回本作业 | 不重复插入或唤醒；已提交快照保持唯一 | 轮询返回的作业 | `G-07`, `G-16` |
| `O-44` | `POST /order-archives` 提交核对 | 候选 `jobId` 未应用，但同修订权威活动/成功作业已存在 | 无变化/核对成功 | 200，返回权威重复作业 | 不插入候选作业、不再次唤醒 | 轮询返回的作业 | `G-05`, `G-07`, `G-16` |
| `O-22` | `POST /order-archives` | 提交后无法读取核对 | 未知 | 503 `ARCHIVE_START_COMMIT_UNKNOWN`，带候选 `jobId`，`retryable=false` | 不重放、不声称未创建 | 数据库恢复后先 GET 候选 ID；404 后再重试 | `G-07`, `G-16` |
| `O-23` | worker 领取 | 最早作业仍为 `queued` | 成功 | GET 可见 `running/serializing` | 条件更新并提交，`attempt_count+1`；领取事务结束 | worker 继续；客户端轮询 | `G-08`, `G-17` |
| `O-24` | worker 领取 | 另一领取/恢复已改变 `queued` 状态，CAS 受影响 0 行 | 无变化/冲突 | 权威作业保持另一执行者已提交的状态 | 回滚无写事务；不发生重复领取 | worker 重扫，客户端继续轮询 | `G-08` |
| `O-40` | worker 领取 | SQLite busy/locked | 超时/冲突 | 作业保持原状态；数据库不可读时 GET 为 503 | 回滚，无重复领取 | worker 退避并重扫，客户端继续轮询 | `G-08`, `G-17` |
| `O-25` | worker 序列化 | 快照哈希有效 | 成功 | 仍为 `running` | 事务外只产生内存字节与哈希，不改归档头 | worker 进入发布阶段 | `G-08`, `G-19` |
| `O-26` | worker 序列化/终态写入 | 快照哈希有效，但 serializer 抛出受控异常 | 失败 | 终态 `failed`，`ARCHIVE_SERIALIZATION_FAILED`，无 `archiveId` | 独立短事务写失败状态；不插入归档、不改头 | 客户端修正订单后新建作业；终态写忙由 worker 重试 | `G-09`, `G-16`, `G-20` |
| `O-27` | worker 发布新鲜度检查 | 订单不存在、修订变化或不再完整 | 状态 | 终态 `stale`，`ARCHIVE_SNAPSHOT_STALE`，带可达当前修订 | 同一事务只写过期终态；不插入归档、不改头 | 客户端为当前完整修订新建作业 | `G-10`, `G-16`, `G-20` |
| `O-28` | worker 发布提交 | 作业候选匹配，订单仍是当前完整快照 | 成功 | 终态 `succeeded`，返回 `archiveId` | 归档行、归档头、成功状态一次原子提交 | 客户端停止轮询 | `G-11`, `G-19`, `G-20` |
| `O-29` | worker 发布/重复核对 | 作业已成功且归档、头、候选三者一致 | 无变化/核对成功 | 保持 `succeeded` | 不重复插入或移动归档头 | 停止 | `G-11`, `G-13` |
| `O-30` | worker 发布或终态事务 | SQLite busy/locked | 超时/冲突 | 作业保持 `running`；GET 仍可轮询 | 回滚本次尝试，不丢内存完成意图 | worker 指数退避并重试；客户端不重发 | `G-12`, `G-17` |
| `O-31` | worker 发布提交 | 非 busy 持久化失败，核对确认发布未应用，失败终态可落库 | 持久化 | 终态 `failed`，`ARCHIVE_PERSISTENCE_FAILED`，`retryable=true` | 发布事务回滚；另一个事务只写失败状态，头不变 | 客户端可为仍当前的修订创建新作业 | `G-12`, `G-16`, `G-20` |
| `O-32` | worker 发布提交 | `COMMIT` 抛错且数据库暂不可读 | 未知 | 保持 `running/publishing`；数据库不可读时 GET 503 | 不重放发布，不报告失败或成功 | worker 独占核对责任；客户端继续轮询 | `G-13`, `G-16` |
| `O-33` | worker 提交核对 | 归档、头和成功作业完整匹配候选 ID | 核对成功 | 终态 `succeeded` | 认定原提交已应用，不再写归档 | 客户端停止轮询 | `G-13`, `G-20` |
| `O-34` | worker 提交核对 | 无候选归档且作业仍在发布阶段 | 确认未应用 | 终态 `failed`，`ARCHIVE_PERSISTENCE_FAILED` | 只提交失败状态，头保持原值 | 客户端按当前修订决定新作业 | `G-13`, `G-20` |
| `O-35` | worker 终态持久化 | 数据库不可写，失败/过期终态暂不能提交 | 未知 | 保持非终态，或 GET 503；不得伪造终态 | worker 保留终态意图并重试；所有失败事务回滚 | 客户端继续轮询；worker 负责重试 | `G-14`, `G-16`, `G-20` |
| `O-36` | 启动恢复 | `running/serializing` 且尝试次数小于 3 | 恢复 | 作业回到 `queued` | 启动恢复事务执行条件更新；快照不变 | worker 重新领取；客户端继续轮询 | `G-14` |
| `O-37` | 启动恢复 | `running/publishing` 核对确认候选发布未应用 | 失败 | 终态 `failed`，`ARCHIVE_WORKER_INTERRUPTED` | 只写失败终态，既有归档头不变 | 客户端可新建作业 | `G-14`, `G-16`, `G-20` |
| `O-46` | 启动恢复 | `running/serializing` 且 `attempt_count` 已达 3 | 失败 | 终态 `failed`，`ARCHIVE_WORKER_INTERRUPTED` | 只写失败终态，固定快照和既有归档头不变 | 客户端可新建作业 | `G-14`, `G-16`, `G-20` |
| `O-38` | 任一发布核对 | 归档、头、作业出现 SQLite 原子性不允许的部分组合或哈希不符 | 完整性失败 | 作业 `failed`（可写时）且 `ARCHIVE_INTEGRITY_ERROR`；服务健康检查失败 | 不修复、不删除、不移动头，停止该作业及后续发布 | 运维介入；客户端不得自动重试 | `G-15`, `G-16`, `G-20` |
| `O-41` | `PUT /orders/{orderId}` | 已校验输入触发意外 `SQLITE_CONSTRAINT` 或核对发现不变量矛盾 | 完整性失败 | 500 `DATA_INTEGRITY_ERROR`，`retryable=false` | 回滚并停止该写路径；不得把错误归类为编辑冲突 | 运维介入，客户端不得自动重试 | `G-15`, `G-16` |
| `O-42` | `POST /order-archives` | 去重分支之外触发意外 `SQLITE_CONSTRAINT` 或不变量矛盾 | 完整性失败 | 500 `DATA_INTEGRITY_ERROR`，`retryable=false` | 回滚，不创建作业、不唤醒 worker | 运维介入，客户端不得自动重试 | `G-06`, `G-15`, `G-16` |
| `O-43` | worker 领取或阶段持久化 | 非 busy 本地写失败，核对确认控制状态未应用 | 持久化 | 数据库恢复后终态 `failed`，`ARCHIVE_PERSISTENCE_FAILED`；落终态前保持原非终态或 GET 503 | 不进入/不继续发布；独立事务写失败终态，若该事务也失败则转 `O-35` | worker 负责终态收敛；客户端继续轮询 | `G-14`, `G-16`, `G-20` |

取消和远程依赖结果不在矩阵中，因为本功能没有取消入口或远程调用。业务超时也不适用；实际等待超时已由 `O-09`、`O-19`、`O-40` 和 `O-30` 覆盖。`GET` 是只读查询，其 200/404/503 契约由 `G-16` 单独验证。

## 数据模型与实体关系

schema 版本为 1，使用 SQLite `STRICT` 表。以下字段与约束是实现契约；时间均为注入时钟产生的 UTC RFC 3339 字符串。

### `orders`

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `order_id` | TEXT PRIMARY KEY | 路径标识 |
| `owner` | TEXT NOT NULL | 已规范化所有者 |
| `status` | TEXT CHECK `created|complete` | 当前可编辑状态 |
| `revision` | INTEGER, 1..最大有符号整数 | 单调修订 |
| `last_save_token` | TEXT NOT NULL | 仅供提交异常核对的服务端 UUID |
| `updated_at` | TEXT NOT NULL | 最近实际内容变更时间；无变化保存不更新 |

### `archive_jobs`

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `job_id` | TEXT PRIMARY KEY | 服务端预生成 UUID |
| `order_id` | TEXT NOT NULL, FK `orders` RESTRICT | 所属订单 |
| `source_revision` | INTEGER NOT NULL | 接受时的固定修订 |
| `snapshot_json` / `snapshot_sha256` | TEXT NOT NULL | 固定规范快照及 64 位小写十六进制哈希 |
| `status` | TEXT CHECK `queued|running|succeeded|stale|failed` | 公开状态 |
| `phase` | TEXT CHECK `queued|serializing|publishing|terminal` | 可恢复内部阶段 |
| `attempt_count` | INTEGER NOT NULL DEFAULT 0 | 成功领取次数 |
| `candidate_archive_id` | TEXT NULL | 进入发布前生成的 UUID |
| `archive_sha256` | TEXT NULL | 发布候选哈希 |
| `archive_id` | TEXT NULL | 只在成功终态设置 |
| `error_code` | TEXT NULL | 只在过期/失败终态设置 |
| `created_at` / `updated_at` | TEXT NOT NULL | 排序与诊断时间 |

部分唯一索引 `(order_id, source_revision) WHERE status IN ('queued','running','succeeded')` 实现开始请求去重。检查约束要求：`succeeded` 必须有 `archive_id` 且无错误；`stale|failed` 必须有 `error_code` 且无 `archive_id`；非终态两者都为空。

### `order_archives` 与 `order_archive_heads`

- `order_archives` 是不可变表：`archive_id` 主键，`job_id` 唯一且外键指向作业，`order_id` 外键指向订单，另含 `source_revision`、`content` BLOB、`content_sha256`、`created_at`。`(order_id, source_revision)` 唯一，防止同修订多次发布。
- `order_archive_heads` 每个 `order_id` 恰有至多一行，含 `archive_id`、`source_revision`、`published_at`，两个 ID 均为外键。只允许发布事务更新；新 `source_revision` 不得小于现有值。
- 作业保存快照，归档保存输出，两者都不引用可变订单内容来重建历史。没有删除级联；当前功能也没有删除入口。

## 数据库事务与锁语义

### 引擎与连接配置

- 权威运行时是 Python 3.14 标准 `sqlite3` 驱动和 SQLite 3.46.x。启动必须检查 `sqlite3.sqlite_version`；不满足 3.46.x 时拒绝启动，不能静默降级保证。
- 数据库是文件而不是 `:memory:`。bootstrap 在事务外执行 `PRAGMA journal_mode=WAL` 并要求返回 `wal`。每个连接设置 `PRAGMA foreign_keys=ON`、`PRAGMA synchronous=FULL`、`PRAGMA busy_timeout=5000`，随后读回验证。
- 连接使用显式事务模式（`isolation_level=None`），所有写路径显式发送 `BEGIN IMMEDIATE`、`COMMIT`、`ROLLBACK`。请求线程和 worker 不共享连接。
- SQLite 没有行锁。`BEGIN IMMEDIATE` 在首次读取前取得数据库级写保留锁，所有写路径的锁顺序统一为“SQLite 写者锁 → 作业行 → 订单行 → 归档行/归档头”。不使用 deferred 读后升级，因此避免 `SQLITE_BUSY_SNAPSHOT` 型升级竞争。

### 持锁与可见性

- 保存事务只包含订单读取、条件写入和提交；归档开始事务只包含订单读取、去重、快照复制和作业插入；领取与阶段事务只更新作业；发布事务只做新鲜度读取与三项原子发布。
- JSON 请求解析、字段校验、慢速归档序列化、归档正文哈希、HTTP I/O、退避等待和提交后核对均不得在数据库事务内进行。归档开始事务可以对刚读取且最大 64 KiB 的订单生成固定快照 JSON 及快照哈希；这段有界复制是开始命令原子捕获快照的一部分，不得调用慢速 serializer。
- WAL 读者在写者提交期间可继续读取。每个 GET 在一个显式只读事务内读取作业和订单修订，看到该事务首次 SELECT 时的一致已提交快照；不会看到发布事务的部分结果。
- 写锁在 `COMMIT` 或 `ROLLBACK` 完成时释放。所有异常路径在 `connection.in_transaction` 为真时尝试回滚，再关闭连接。回滚错误只增加诊断信息，不能把未知结果错误标成确认未应用。

### busy、错误分类与重试

- 只依据 `sqlite_errorcode`/扩展码分类，不解析异常文本。`SQLITE_BUSY`、`SQLITE_BUSY_SNAPSHOT`、`SQLITE_LOCKED` 是竞争/等待耗尽；输入已校验后的 `SQLITE_CONSTRAINT` 是实现或完整性错误；`SQLITE_IOERR`、`SQLITE_FULL`、`SQLITE_CANTOPEN`、`SQLITE_READONLY` 等是本地持久化失败；`SQLITE_CORRUPT`/`SQLITE_NOTADB` 触发健康失败。
- 单个 SQLite 数据库只有一个写者锁，所有写路径锁顺序相同，因而没有应用级锁环和死锁；竞争表现为 busy/locked，而不是等待环。
- 同步 HTTP 写在 5000 ms 驱动等待后不做服务端自动重试。worker 对 busy/locked 以 50 ms 起步、加倍至最多 1 秒的退避无限重试，直到竞争消失、作业终态、进程停止或出现非竞争错误。
- 非 busy 发布错误不得盲目重放。必须先按内部令牌或候选 ID 在新连接核对，再选择成功、确认未应用或未知结果。

## 状态转换、迁移边界与一致性

### 状态转换

```text
不存在订单 --PUT(expectedRevision=0)--> revision 1
revision N --PUT(内容变化, expectedRevision=N)--> revision N+1
revision N --PUT(内容相同, expectedRevision=N)--> revision N

queued --> running/serializing --> running/publishing --> succeeded
                                      |                  --> stale
                                      |                  --> failed
running/serializing --进程恢复且 attempt_count<3--> queued
running/publishing --恢复核对--> succeeded 或 failed
```

- 修订只增不减；不存在把订单恢复到旧修订的路径。因此一旦作业因更高修订而过期，同一作业不可能重新变为当前。
- `order_archives` 行、`order_archive_heads` 指针和 `archive_jobs.succeeded` 在同一事务中可见或均不可见，提供 SQLite 数据库内的原子一致性。
- 归档开始提交与后续保存之间允许竞争：开始事务先提交则获得固定快照，随后保存会使其在发布时过期；保存先提交则开始请求按旧 `expectedRevision` 冲突。两种顺序都不会发布非当前快照。
- 相同内容保存不增加修订，因此不会仅因重复请求使在途归档过期。
- 两个不同修订的作业可先后存在，但只有完成时仍为当前修订的作业能移动归档头。失败、过期、未知和恢复路径均不更新头。

### migration 与启动恢复

1. bootstrap 先配置并验证 WAL，然后执行 `BEGIN IMMEDIATE`，读取 `PRAGMA user_version`。
2. `user_version=0` 时一次性创建四张表、外键、检查约束和索引，设置 `user_version=1` 并提交。任何失败全部回滚，不得留下部分 schema。
3. `user_version=1` 时验证必需表、索引和 `PRAGMA quick_check`。其他版本、缺对象或检查失败均拒绝启动；本功能不自动降级或猜测迁移。
4. schema 就绪后，在一个恢复事务中扫描非终态作业。`running/serializing` 且 `attempt_count<3` 回到 `queued`；达到 3 次则失败。`running/publishing` 先按候选 ID 核对：完整发布视为成功，确认未发布视为失败，部分组合使服务健康失败。终态不重开。
5. 恢复事务提交后启动唯一 worker；worker 先扫描持久队列，再等待条件通知。进程在归档开始提交后、通知前崩溃也不会丢作业。

## 错误与不确定性

- 本规格没有遗留给实施阶段选择的材料性一致性分支。订单字段采用当前仓库已有的 `id/owner/status` 最小模型，并把 PRD 的“完整”明确映射为 `status=complete`；增加新订单字段或状态会改变快照与校验契约，需先变更并重新批准规格。
- `currentRevision` 只能在新的、成功的只读事务中获得。失败事务里先前读到的值不能在提交未知后冒充当前值；无法可靠读取时必须返回 `null`。
- `save_token`、候选归档 ID 和哈希只解决本地提交核对，不向客户端承诺跨进程崩溃的 exactly-once HTTP 交付。断线客户端以原 `expectedRevision` 重试时，成功落库会表现为当前修订前进而不是重复写入。
- 事务外序列化不得读取订单表或重新计算“当前”内容，只能消费作业快照。发布事务必须重新检查当前订单，不能信任开始时或序列化前的检查。
- 日志可记录 Outcome ID、错误码、订单/作业标识、SQLite 主/扩展错误码和修订，不记录 `owner`、快照 JSON、归档正文或完整错误请求。
- 64 KiB 请求上限、严格字段集、规范 JSON 与哈希校验构成本功能的数据完整性边界。认证、传输加密和操作者权限属于本地部署边界，当前仓库没有证据可定义它们。

## 保证与测试追踪

所有 SQLite 一致性测试必须使用临时目录中的真实文件数据库、真实 WAL 和至少两个独立连接；高风险保证不能只靠 mock。故障注入包装连接的 `BEGIN`、写入、`COMMIT` 和 serializer 边界，但提交后的核对必须读取真实 SQLite 文件。

| 保证 ID | 保证或失败契约 | 对应结果 ID 或状态 | 精确测试文件与名称 | 精确命令 | 可观察断言 |
| --- | --- | --- | --- | --- | --- |
| `G-01` | 非法请求在事务前拒绝且不产生订单或作业 | `O-04`, `O-05`, `O-15`, `O-39` | `tests/test_order_api.py::InputValidationTests.test_invalid_write_requests_have_stable_errors_and_no_rows` | `python3.14 -m unittest tests.test_order_api.InputValidationTests.test_invalid_write_requests_have_stable_errors_and_no_rows` | 各 HTTP 状态/错误码固定，四张表行数和 `user_version` 外数据不变 |
| `G-02` | 创建、更新、无变化、缺失、冲突与耗尽严格遵守修订 CAS，冲突不覆盖草稿 | `O-01`, `O-02`, `O-03`, `O-06`, `O-07`, `O-08` | `tests/test_order_api.py::OrderSaveContractTests.test_save_revision_cas_and_noop_preserve_conflicting_draft` | `python3.14 -m unittest tests.test_order_api.OrderSaveContractTests.test_save_revision_cas_and_noop_preserve_conflicting_draft` | 修订序列为 1、2、2；冲突/耗尽后数据库内容不变且响应带当前修订 |
| `G-03` | save 的 busy 与确认未应用错误完整回滚并可安全按契约重试 | `O-09`, `O-10` | `tests/test_order_transactions.py::SaveFailureTests.test_busy_and_confirmed_persistence_failure_do_not_apply_save` | `python3.14 -m unittest tests.test_order_transactions.SaveFailureTests.test_busy_and_confirmed_persistence_failure_do_not_apply_save` | 真实写锁保持超过 5000 ms 时为 `DATABASE_BUSY`；注入失败后修订、内容、令牌均不变 |
| `G-04` | save 提交异常按 `last_save_token` 区分已应用与未知，绝不重复创建或增加修订 | `O-11`, `O-45`, `O-12` | `tests/test_order_transactions.py::SaveFailureTests.test_commit_exception_reconciliation_never_duplicates_revision` | `python3.14 -m unittest tests.test_order_transactions.SaveFailureTests.test_commit_exception_reconciliation_never_duplicates_revision` | 已提交创建/更新异常返回对应一次成功且修订只前进一次；核对不可读返回 commit unknown 且无重放 SQL |
| `G-05` | 归档开始原子保存当前完整固定快照，并在正常与提交核对路径去重活动/成功作业 | `O-13`, `O-14`, `O-44` | `tests/test_order_archive_api.py::ArchiveStartTests.test_start_captures_fixed_snapshot_and_deduplicates_revision` | `python3.14 -m unittest tests.test_order_archive_api.ArchiveStartTests.test_start_captures_fixed_snapshot_and_deduplicates_revision` | 快照字节/哈希匹配接受时订单；正常或核对重复请求返回同一权威 ID 且作业数为 1 |
| `G-06` | 归档开始的输入、缺失、冲突、不完整、busy、确认未应用和完整性失败均不创建作业 | `O-15`, `O-39`, `O-16`, `O-17`, `O-18`, `O-19`, `O-20`, `O-42` | `tests/test_order_archive_api.py::ArchiveStartTests.test_start_rejections_and_failures_create_no_job` | `python3.14 -m unittest tests.test_order_archive_api.ArchiveStartTests.test_start_rejections_and_failures_create_no_job` | 每个稳定错误码正确，`archive_jobs` 行数不变，冲突/不完整带当前修订 |
| `G-07` | 归档开始提交异常按候选 `jobId` 核对已应用、权威重复或未知 | `O-21`, `O-44`, `O-22` | `tests/test_order_archive_transactions.py::ArchiveStartCommitTests.test_start_commit_exception_is_reconciled_by_job_id` | `python3.14 -m unittest tests.test_order_archive_transactions.ArchiveStartCommitTests.test_start_commit_exception_is_reconciled_by_job_id` | 已提交异常返回唯一作业；并发重复返回权威作业；不可读时返回候选 ID 且不执行第二次插入 |
| `G-08` | worker 只 CAS 领取一次，领取 busy 不重复执行，并且整个慢速序列化期间没有活动事务或写锁 | `O-23`, `O-24`, `O-40`, `O-25` | `tests/test_order_archive_worker.py::WorkerClaimTests.test_claim_is_cas_and_serialization_holds_no_database_transaction` | `python3.14 -m unittest tests.test_order_archive_worker.WorkerClaimTests.test_claim_is_cas_and_serialization_holds_no_database_transaction` | 两个竞争领取尝试仅一个成功；busy 后没有双领取；阻塞 serializer 时另一连接可 `BEGIN IMMEDIATE` 并提交保存 |
| `G-09` | serializer 异常只产生失败终态，不产生可见归档 | `O-26` | `tests/test_order_archive_worker.py::WorkerFailureTests.test_serialization_failure_marks_failed_without_publication` | `python3.14 -m unittest tests.test_order_archive_worker.WorkerFailureTests.test_serialization_failure_marks_failed_without_publication` | 状态/错误码为 failed/serialization，归档表为空，既有头不变 |
| `G-10` | 发布前修订或完整性变化必定转为 stale 且不发布 | `O-27` | `tests/test_order_archive_concurrency.py::ArchiveFreshnessTests.test_save_during_serialization_makes_job_stale_without_publication` | `python3.14 -m unittest tests.test_order_archive_concurrency.ArchiveFreshnessTests.test_save_during_serialization_makes_job_stale_without_publication` | barrier 后并发保存先提交，作业终态 stale，返回新修订，归档头保持旧值 |
| `G-11` | 当前完整快照的归档、归档头与成功状态一次原子提交，重复完成无变化 | `O-28`, `O-29` | `tests/test_order_archive_transactions.py::ArchivePublishTests.test_publish_is_atomic_and_repeated_completion_is_noop` | `python3.14 -m unittest tests.test_order_archive_transactions.ArchivePublishTests.test_publish_is_atomic_and_repeated_completion_is_noop` | 单次提交后三表相互匹配；重复调用后行数、头和作业不变 |
| `G-12` | 完成阶段 busy 由 worker 重试，确认的非 busy 失败回滚发布并记录失败 | `O-30`, `O-31` | `tests/test_order_archive_transactions.py::ArchivePublishFailureTests.test_busy_retries_and_confirmed_failure_preserves_head` | `python3.14 -m unittest tests.test_order_archive_transactions.ArchivePublishFailureTests.test_busy_retries_and_confirmed_failure_preserves_head` | 释放真实写锁后同一作业成功；注入确认未应用错误时作业失败且候选归档/头均未变化 |
| `G-13` | 发布提交未知在核对前不报告终态，核对只得出完整成功或确认未应用 | `O-29`, `O-32`, `O-33`, `O-34` | `tests/test_order_archive_transactions.py::ArchivePublishFailureTests.test_unknown_commit_reconciliation_never_reports_false_failure` | `python3.14 -m unittest tests.test_order_archive_transactions.ArchivePublishFailureTests.test_unknown_commit_reconciliation_never_reports_false_failure` | 核对不可读期间状态非终态；恢复后已应用为 succeeded、未应用为 failed，均无第二次发布 |
| `G-14` | 控制状态或终态无法写入时不伪造状态；启动恢复按阶段和三次上限收敛 | `O-35`, `O-36`, `O-37`, `O-46`, `O-43` | `tests/test_order_archive_recovery.py::WorkerRecoveryTests.test_inflight_jobs_recover_by_phase_and_attempt_limit` | `python3.14 -m unittest tests.test_order_archive_recovery.WorkerRecoveryTests.test_inflight_jobs_recover_by_phase_and_attempt_limit` | 阶段写失败最终为 persistence failure；serializing 作业被重新排队；publishing 未应用及第三次中断作业失败；所有既有头不变 |
| `G-15` | 意外约束、SQLite 原子性矛盾或哈希不符时 fail closed，不伪装成业务冲突、不自动修复或移动头 | `O-38`, `O-41`, `O-42` | `tests/test_order_archive_integrity.py::IntegrityFailureTests.test_constraints_partial_publication_and_hash_mismatch_fail_closed` | `python3.14 -m unittest tests.test_order_archive_integrity.IntegrityFailureTests.test_constraints_partial_publication_and_hash_mismatch_fail_closed` | 同步接口返回 data integrity；发布健康检查失败，作业为 integrity（可写时），所有头保持原值 |
| `G-16` | 客户端仅凭 HTTP/错误码/修订/作业终态即可区分全部公开结果 | `O-01`, `O-02`, `O-03`, `O-04`, `O-05`, `O-06`, `O-07`, `O-08`, `O-09`, `O-10`, `O-11`, `O-45`, `O-12`, `O-13`, `O-14`, `O-15`, `O-39`, `O-16`, `O-17`, `O-18`, `O-19`, `O-20`, `O-21`, `O-44`, `O-22`, `O-26`, `O-27`, `O-28`, `O-29`, `O-30`, `O-31`, `O-32`, `O-33`, `O-34`, `O-35`, `O-36`, `O-37`, `O-46`, `O-38`, `O-41`, `O-42`, `O-43` 及 GET | `tests/test_order_archive_api.py::ArchiveStatusTests.test_status_and_error_contract_distinguishes_conflict_stale_failed_and_success` | `python3.14 -m unittest tests.test_order_archive_api.ArchiveStatusTests.test_status_and_error_contract_distinguishes_conflict_stale_failed_and_success` | 响应 schema 固定；公开分支无需日志即可判别；冲突/状态/可核对失败在可靠可读时含 currentRevision，预事务校验或数据库不可达时为 null |
| `G-17` | SQLite 3.46 WAL、FULL、5000 ms busy、`BEGIN IMMEDIATE` 和一致锁序得到规定可见性 | `O-01`, `O-02`, `O-09`, `O-13`, `O-19`, `O-23`, `O-40`, `O-28`, `O-30` | `tests/test_sqlite_contract.py::SQLiteTransactionContractTests.test_wal_begin_immediate_busy_timeout_and_reader_visibility` | `python3.14 -m unittest tests.test_sqlite_contract.SQLiteTransactionContractTests.test_wal_begin_immediate_busy_timeout_and_reader_visibility` | PRAGMA/版本读回精确；一个写者等待，读者仍见完整旧或新提交且从不见部分发布 |
| `G-18` | schema v0 到 v1 原子迁移；未知或损坏 schema 拒绝启动 | migration/启动 | `tests/test_order_archive_migration.py::SchemaMigrationTests.test_version_zero_migrates_atomically_and_unknown_versions_fail` | `python3.14 -m unittest tests.test_order_archive_migration.SchemaMigrationTests.test_version_zero_migrates_atomically_and_unknown_versions_fail` | 成功后四表/索引/约束及 user_version 完整；注入失败无部分对象；版本 2 启动失败 |
| `G-19` | 固定快照和归档正文采用唯一规范字节并在读取/发布时验证哈希 | `O-13`, `O-25`, `O-28` | `tests/test_order_archive_serialization.py::ArchiveSerializationTests.test_snapshot_and_archive_bytes_are_canonical_and_hash_verified` | `python3.14 -m unittest tests.test_order_archive_serialization.ArchiveSerializationTests.test_snapshot_and_archive_bytes_are_canonical_and_hash_verified` | 不同键顺序输入得到相同字节/哈希；篡改任一字节不能发布 |
| `G-20` | 失败、过期、未知、恢复和完整性错误均不替换最后完成归档 | `O-26`, `O-27`, `O-28`, `O-31`, `O-33`, `O-34`, `O-35`, `O-37`, `O-46`, `O-38`, `O-43` | `tests/test_order_archive_concurrency.py::ArchiveHeadTests.test_only_successful_current_completion_moves_archive_head` | `python3.14 -m unittest tests.test_order_archive_concurrency.ArchiveHeadTests.test_only_successful_current_completion_moves_archive_head` | 预置头在所有非成功分支保持同一 archive ID；仅当前成功事务一次移动到新 ID |

## 测试与文档

- 保留 `tests/test_orders.py` 作为现有行为回归，并新增追踪表列出的测试模块。总验证命令为 `python3.14 -m unittest discover -s tests -p 'test_*.py'`。
- 并发测试使用 `threading.Barrier` 或事件把保存精确放在序列化与发布之间；禁止依赖 `sleep` 猜测时序。busy 测试用第二个真实连接持有 `BEGIN IMMEDIATE`，并测量等待至少接近 5000 ms 后返回稳定错误。
- 提交核对测试分别注入“SQLite 已提交但 Python `commit()` 抛错”“提交前失败”“核对连接不可读”三类 seam，并断言 SQL 调用计数，证明没有盲目重放。
- 每个测试创建独立临时数据库并断言 `journal_mode=wal`、SQLite 版本 3.46.x、`foreign_keys=1`、`synchronous=2`（FULL）和 `busy_timeout=5000`。内存数据库不得用于 WAL/锁保证。
- 更新 `README.md`，记录请求/响应 schema、错误码、状态机、单进程/单 worker 拓扑、数据库文件与启动恢复。文档不得宣称规格、计划或实现已批准。

## 验收标准

1. 合法创建、更新和相同内容保存分别得到 201/200/200，修订严格为 1、N+1、N；错误预期修订得到 409 和当前修订，数据库内容不变。
2. 归档开始只接受当前 `complete` 修订，在提交时持久保存规范快照；同修订重复请求复用作业，失败作业允许显式新重试。
3. 可控阻塞 serializer 时，另一连接仍能保存订单，证明慢工作无活动事务；随后旧作业终态为 `stale`，既有归档头不变。
4. 未发生并发修改时，归档行、归档头和作业 `succeeded` 在一个提交中同时可见，且归档哈希匹配固定快照。
5. serializer、SQLite busy、确认未应用持久化错误、提交已应用但抛错、核对不可达和进程恢复各自命中矩阵中的独立结果，不出现重复修订、重复作业、重复归档或虚假失败。
6. `GET` 能稳定区分 `queued/running/succeeded/stale/failed`，成功含 `archiveId`，过期/失败含稳定错误码，可读时含当前修订；无需查看服务端日志。
7. 所有失败、过期、未知、恢复和完整性错误分支均证明不会替换预先存在的最后完成归档。
8. 真实 SQLite 3.46 文件测试证明 WAL、FULL、5000 ms busy、`BEGIN IMMEDIATE` 锁顺序、读者可见性、回滚和原子迁移契约；完整 `unittest` 命令通过。
````

需求文档：/workspace/fixture/docs/requirements/2026-07-18-durable-order-archive.md
需求主题：durable-order-archive
需求范围：功能
需求理解置信度：98
需求理解确认：已确认
需求文档用户批准：已批准
需求文档独立评审：已通过
技术规格门禁：已开放
技术规格：/workspace/fixture/docs/specs/2026-07-19-durable-order-archive-design.md
技术规格用户批准：待批准
技术规格独立评审：待评审
实施计划：尚未创建
计划评审状态：未开始
实施门禁：未开放