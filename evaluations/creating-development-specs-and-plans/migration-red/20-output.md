已创建唯一的未评审规格草案：[2026-07-18-durable-order-archive-design.md](/workspace/fixture/docs/specs/2026-07-18-durable-order-archive-design.md:1)。

未启动独立评审，未创建 plan、实现代码或 task/thread。PRD 复验通过，现有测试 1/1 通过，文档格式检查通过。

完整正文如下：

```markdown
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

# 持久化订单归档技术规格

## 目标

- 为 PUT /orders/{orderId} 定义同步、可观察且基于 expectedRevision 的乐观并发保存契约；任一冲突或持久化失败均不覆盖数据库中的现有订单，也不要求客户端放弃其提交草稿。
- 为 POST /order-archives 创建持久化后台任务，并由同一 API 进程中的单一后台 worker 从固定订单快照生成归档。
- 仅当固定快照在发布事务中仍与当前完整订单一致时，原子地发布归档并把任务置为 completed。
- 让 GET /order-archives/{jobId} 以稳定状态、错误码和可读取时的当前 revision 区分排队、执行、成功、快照过期、序列化失败和本地数据库持久化失败。
- 明确数据库 schema、事务、锁、回滚、进程恢复、校验和故障注入测试边界，使实现无需自行决定并发与一致性语义。

## 非目标

- 不新增订单读取、删除、归档下载、归档历史列表、任务取消或任务重试 API。
- 不定义 UI 如何保存本地草稿。服务端的责任是冲突时不写入失败草稿、不返回会替换草稿的服务端订单正文，并提供 currentRevision；客户端继续持有原请求正文。
- 不新增身份认证、授权、多租户隔离或公网部署能力。当前服务仍是单机本地 API，默认只绑定 loopback。
- 不支持多个 API 进程、多个后台 worker、远程队列或 SQLite 之外的存储。
- 不为 POST 增加幂等键。一次已提交但响应丢失的请求可能留下客户端未知的任务；后续独立请求会创建新 job。
- 不在本规格中生成实施计划、实现代码、提交或用户可见 task/thread。

## 当前证据

- docs/requirements/2026-07-18-durable-order-archive.md 已通过仓库检查器验证：topic 为 durable-order-archive、scope 为 feature，需求理解确认、用户批准和独立评审均为 approved，specification_gate 为 open。
- AGENTS.md 要求规格经过独立评审和用户明确批准后才能生成计划；本草案的 user_approval 与 independent_review 因而均保持 pending。
- README.md 固定运行栈为 Python 3.14、标准库 sqlite3、SQLite 3.46 WAL、一个本地 API 进程和一个进程内后台 worker；同时固定三个端点、每个写命令携带 expectedRevision、固定快照在事务外进行慢序列化，以及 stale 与本地持久化失败必须分开。
- src/orders.py 只有 create_order(order_id, owner)，其当前可见订单字段为 id、owner 和值为 created 的 status；尚无 HTTP、持久化、revision 或归档实现。
- tests/test_orders.py 只验证 create_order 返回 created；仓库当前使用标准库 unittest，尚无并发、SQLite 或 API 测试基础设施。
- 当前历史只有 fixture 初始提交，工作树在本规格创建前无改动；没有可兼容的既有数据库 schema 或线上迁移证据。

## 行为与边界

### 订单与 revision

- orderId 是服务端实体标识，必须匹配 [A-Za-z0-9][A-Za-z0-9._-]{0,127}。路径解码后再校验；空值、斜杠、控制字符和超长值均无效。
- 订单正文是 JSON object，持久化时采用规范 JSON 字节。id 和 revision 是服务端字段，不得出现在 order object 中。
- expectedRevision 必须是 JSON integer，不能是 boolean，范围为 0 至 9223372036854775806。
- expectedRevision = 0 仅表示“当订单不存在时创建”。创建成功后的 revision 为 1。
- 已存在订单仅在 expectedRevision 与当前 revision 完全相等时保存；每次成功保存（包括正文未变化）都把 revision 加 1。归档任务的创建、状态变化和归档发布均不改变订单 revision。
- 不存在的订单配合正 expectedRevision 返回 order_not_found；已存在的订单配合 expectedRevision = 0 或任意不相等 revision 返回 revision_conflict。

### 可编辑正文与可归档完整性

- 保存校验允许草稿不完整：owner 和 status 可以缺失或为 null。若存在非 null owner，它必须是最多 256 个 Unicode code point 的 string；若存在非 null status，它必须是最多 64 个 Unicode code point 的 string。
- 未知业务字段允许存在并按原值保存及归档，但所有值必须是标准 JSON 类型；拒绝 NaN、Infinity、重复 object key 和无法编码为 UTF-8 的输入。
- 完整订单必须同时满足：owner 是去除首尾空白后长度为 1 至 256 的 string，且 status 严格等于 created。该规则以当前 create_order 的唯一已知完整形态为依据。
- order object 的规范编码使用 UTF-8、按 key 排序、无非必要空白、禁止 NaN/Infinity；规范编码不得超过 1,048,576 bytes。owner 原值和未知字段不会因完整性检查而被改写。
- PUT 只执行结构校验并可保存不完整草稿；POST 和 worker 发布前都执行完整性校验。因此不完整草稿可同步保存，但不能产生已发布归档。

### 同步保存

1. HTTP 层完成路径、媒体类型、body 大小、JSON、重复 key、expectedRevision 和 order 结构校验；校验失败前不得开启写事务。
2. command service 在独立连接上执行 BEGIN IMMEDIATE，取得 SQLite writer reservation 后读取订单。revision 比较和 INSERT/UPDATE 位于同一事务。
3. 创建或更新成功后先 COMMIT，再返回 201 或 200。任何成功响应都表示 revision 已持久化。
4. revision 不匹配时显式 ROLLBACK，返回 409 revision_conflict 和事务内读到的 currentRevision；不得写入订单、job 或 archive。
5. 任意 sqlite3 错误或 COMMIT 错误走失败协调流程：若事务仍活动则尝试 ROLLBACK；回滚失败时关闭该连接；再用新连接尽力读取 currentRevision。响应不得声称成功。
6. 对提交结果不确定的错误不猜测结果。返回 503 persistence_unavailable；客户端可用原 expectedRevision 重试，若前次实际提交，重试将稳定得到 revision_conflict 和新 revision。
7. handler 不修改传入的 order object，冲突响应不携带当前服务端 order 正文。这样持久化状态保持胜出版本，调用方仍持有其原草稿。

### 创建归档任务

1. POST 请求完成通用校验后执行 BEGIN IMMEDIATE，并在同一事务内读取 orderId 对应订单、比较 expectedRevision、校验当前正文完整性、复制规范 snapshot JSON 和 sourceRevision，再插入一个 status = queued 的 archive_jobs 行。
2. 订单不存在返回 404；revision 不匹配返回 409；当前订单不完整返回 422。三种情况都回滚且不创建 job。
3. jobId 使用 UUID v4 小写标准文本。每个成功接受的 POST 恰好插入一行；本规格不合并同 revision 的多个请求。
4. 只有 job 行 COMMIT 成功后才返回 202 并唤醒 worker。进程内唤醒不是事实来源；唤醒丢失时，worker 的启动扫描和每轮扫描仍会发现 queued 行。
5. job snapshot 和 sourceRevision 插入后不可修改。后续 PUT 只产生新订单 revision，不会改变已存在 job 的输入。

### 后台执行与发布

1. 单一 worker 在短 BEGIN IMMEDIATE 事务中按 created_at、job_id 顺序选择一个 queued job，并用 WHERE status = 'queued' 的条件更新为 running。COMMIT 后把 snapshot、sourceRevision 和 jobId 留在内存。
2. worker 在没有任何 SQLite transaction 或开放 cursor 的情况下执行 serialize_archive。慢序列化不得阻塞 API 的读事务或 writer reservation。
3. 归档格式是以下 envelope 的规范 JSON UTF-8 bytes，并作为 BLOB 保存：

~~~json
{"document":{"owner":"user-1","status":"created"},"orderId":"o-1","revision":1}
~~~

4. worker 对最终 bytes 计算小写十六进制 SHA-256。相同 orderId、sourceRevision 和 snapshot 必须得到相同 bytes 与 digest。
5. 序列化异常不进入发布事务；worker 把 running job 终结为 failed，error.code = archive_serialization_failed，且不触碰已发布归档。
6. 序列化成功后，worker 执行新的 BEGIN IMMEDIATE，在同一事务内重新读取 job 与当前订单，并要求：
   - job 仍为 running，sourceRevision 与内存值一致；
   - 当前订单存在且 revision 等于 sourceRevision；
   - 当前规范 document_json 与 job snapshot byte-for-byte 相等；
   - snapshot 仍通过完整性校验。
7. 当前订单不存在、revision 不同或相同 revision 下正文不同，任务在该事务中变为 stale，error.code = archive_snapshot_stale；不得插入或替换 published_order_archives。
8. snapshot 与当前正文相同但不再通过完整性校验表示数据库不变量被破坏，任务变为 failed，error.code = archive_snapshot_invalid；该情况不得伪装成 stale。
9. 条件全部满足时，在一个事务中 upsert published_order_archives，并把 job 更新为 completed。两项必须一起 COMMIT；任何观察者都不能看到新归档配 running/failed job，或 completed job 配旧归档。
10. 发布事务持有 writer reservation，所以在最终比较与 COMMIT 之间 PUT 不能改变订单。若发布先提交，随后保存可产生更高 revision；若保存先提交，发布必须观察到新 revision 并标记 stale。

### 任务恢复与终态

- queued、running 是非终态；completed、stale、failed 是终态。终态不可转换，所有状态更新都用当前 status 作为 compare-and-set 条件并检查 rowcount = 1。
- 进程启动完成 schema 校验后，先在一个事务中把遗留 running job 置为 failed，error.code = archive_worker_interrupted，再启动 worker。已提交的 completed、stale、failed 不变；queued 继续执行。
- 正常关闭停止领取新 job，并允许当前 job 在关闭期限内写入终态；强制终止留下的 running job 由下一次启动按上一条规则终结。
- worker 捕获每个 job 的 Exception，完成终态写入后才领取下一个 job。意外 BaseException 使进程健康检查失败并触发进程退出，不允许 API 在没有 worker 的情况下继续长期接受任务。
- 若失败终态本身暂时无法写入，job 在数据库中保持 running，worker 保留“待终结”意图并只重试该终态写入，不领取后续 job。数据库可写后才持久化 failed。
- 若进程在“检测到失败但尚未写入 failed”的窗口退出，下一次启动使用 archive_worker_interrupted。无额外持久化介质时无法保留更细的原始错误码；该边界不得被实现为 stale 或 completed。

## 组件与控制流

### 组件职责

- HTTP adapter：使用 Python 标准库 ThreadingHTTPServer，默认绑定 127.0.0.1；负责路由、JSON 边界、HTTP 状态与稳定响应 envelope，不包含 revision 或事务决策。
- Order command service：实现 PUT 的校验后 CAS 保存，并把 repository 结果映射为成功、conflict、not-found 或 persistence failure。
- Archive command/query service：实现 POST 的原子 snapshot 捕获和 GET 的一致状态读取。
- SQLite connection factory：每个请求线程和 worker 各自创建并只在所属线程使用一个连接；统一配置 WAL、foreign_keys、synchronous、busy_timeout 和显式 transaction。
- Schema bootstrap：在 HTTP server 和 worker 启动前创建或校验 schema version 1，并完成遗留 running job 的恢复终结。
- Archive worker：从 SQLite 扫描及 claim job、在事务外调用 serializer、再执行 stale 检查或原子发布。threading.Condition 只用于降低扫描延迟，SQLite job 行是唯一事实来源。
- Serializer：纯函数式接收固定 snapshot envelope，返回确定性 bytes；不得自行读取数据库、当前时间或可变全局状态。
- Clock/ID provider：生产环境提供 UTC 时间和 UUID v4，测试可注入确定值；不得影响并发正确性。

### 控制流不变量

- HTTP 请求、worker claim、worker completion 各使用不同的短 transaction；跨 transaction 的 worker 输入只来自 archive_jobs 中已提交的 immutable snapshot。
- 所有订单状态判断都发生在取得 BEGIN IMMEDIATE writer reservation 之后；不得先在 autocommit SELECT 中判断，再另开写事务。
- GET 使用一个显式只读 transaction 读取 job、当前订单 revision 和最新归档引用，确保一个响应来自同一 SQLite snapshot。
- API response 只能在 COMMIT 成功或失败结果已分类后构建；不得在 transaction 尚未结束时向 socket 写成功状态。

## API 与技术接口

所有 response 使用 application/json; charset=utf-8。错误 message 可用于人工阅读但不是稳定契约；HTTP status、error.code、currentRevision 字段名和 job status 是稳定契约。

### PUT /orders/{orderId}

请求：

~~~json
{
  "expectedRevision": 0,
  "order": {
    "owner": "user-1",
    "status": "created"
  }
}
~~~

- body 必须恰好包含 expectedRevision 和 order。
- 创建成功返回 201；更新成功返回 200：

~~~json
{
  "orderId": "o-1",
  "revision": 1,
  "order": {
    "owner": "user-1",
    "status": "created"
  }
}
~~~

### POST /order-archives

请求：

~~~json
{
  "orderId": "o-1",
  "expectedRevision": 1
}
~~~

- body 必须恰好包含 orderId 和 expectedRevision。
- 接受成功返回 202：

~~~json
{
  "jobId": "00000000-0000-4000-8000-000000000000",
  "orderId": "o-1",
  "sourceRevision": 1,
  "status": "queued",
  "terminal": false,
  "currentRevision": 1,
  "archive": null,
  "error": null
}
~~~

### GET /order-archives/{jobId}

- jobId 必须是规范 UUID 文本。已知 job 返回 200；终态失败仍返回 200，因为请求本身成功读取了 job。
- queued 或 running 的 terminal 为 false；completed、stale、failed 的 terminal 为 true。
- completed response 的 archive 包含 sourceRevision、sha256 和 publishedAt，不返回 archive bytes。publishedAt 取该 job 的 finished_at，因此后续归档替换 latest row 后仍可查询；若该 job 仍是该订单最新发布归档，isLatest 为 true，否则为 false。
- stale 或 failed response 的 archive 为 null，error 包含稳定 code；currentRevision 是本次只读 transaction 中读取的当前值。

completed 示例：

~~~json
{
  "jobId": "00000000-0000-4000-8000-000000000000",
  "orderId": "o-1",
  "sourceRevision": 1,
  "status": "completed",
  "terminal": true,
  "currentRevision": 1,
  "archive": {
    "sourceRevision": 1,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "publishedAt": "2026-07-18T15:00:00.000Z",
    "isLatest": true
  },
  "error": null
}
~~~

stale 示例：

~~~json
{
  "jobId": "00000000-0000-4000-8000-000000000000",
  "orderId": "o-1",
  "sourceRevision": 1,
  "status": "stale",
  "terminal": true,
  "currentRevision": 2,
  "archive": null,
  "error": {
    "code": "archive_snapshot_stale",
    "message": "The archived snapshot is no longer current."
  }
}
~~~

### 命令错误 envelope

所有 PUT/POST 错误都返回相同结构。只要 orderId 有效且新连接可读取数据库，currentRevision 必须是当前 integer；订单不存在或读取不可用时为 null。

~~~json
{
  "error": {
    "code": "revision_conflict",
    "message": "The expected revision does not match.",
    "currentRevision": 2
  }
}
~~~

稳定 HTTP 映射：

| HTTP | error.code | 适用边界 |
| --- | --- | --- |
| 400 | invalid_request | 非法路径参数、缺失/多余字段、无效 JSON、重复 key 或 expectedRevision 类型/范围错误 |
| 404 | order_not_found | 正 expectedRevision 指向不存在订单，或 POST 指向不存在订单 |
| 404 | archive_job_not_found | GET 的 jobId 格式有效但不存在 |
| 409 | revision_conflict | 当前订单存在但 expectedRevision 不匹配 |
| 413 | request_too_large | HTTP body 或规范 order JSON 超过 1,048,576 bytes |
| 415 | unsupported_media_type | 写请求不是 application/json |
| 422 | invalid_order | PUT 的 order 结构或字段类型非法 |
| 422 | order_not_archiveable | POST 读取到的当前 snapshot 不满足完整性规则 |
| 503 | persistence_unavailable | SQLite busy/locked 超时、读写/commit/rollback 故障，或 schema 不可用 |
| 500 | internal_error | 非 sqlite3 的未预期同步服务错误 |

GET 无法读取 SQLite 时返回 503 persistence_unavailable；其 currentRevision 为 null。未知路由和不支持的方法分别使用 404 route_not_found 与 405 method_not_allowed。

## 数据模型与实体关系

SQLite schema version 1 包含以下表；所有 timestamp 是 UTC RFC 3339 文本，精度到毫秒并以 Z 结尾。

### orders

| 列 | 约束与含义 |
| --- | --- |
| order_id | TEXT PRIMARY KEY，已校验的 orderId |
| document_json | TEXT NOT NULL，规范 JSON；不得由归档流程修改 |
| revision | INTEGER NOT NULL CHECK revision >= 1 |
| updated_at | TEXT NOT NULL |

### archive_jobs

| 列 | 约束与含义 |
| --- | --- |
| job_id | TEXT PRIMARY KEY，UUID v4 |
| order_id | TEXT NOT NULL，REFERENCES orders(order_id) ON DELETE RESTRICT |
| source_revision | INTEGER NOT NULL CHECK source_revision >= 1 |
| snapshot_json | TEXT NOT NULL，创建后 immutable |
| status | TEXT NOT NULL，限定 queued/running/completed/stale/failed |
| error_code | TEXT NULL，仅 stale/failed 非 null |
| archive_sha256 | TEXT NULL，仅 completed 非 null |
| observed_revision | INTEGER NULL，终结时看到的 revision；订单不存在时可为 null |
| created_at | TEXT NOT NULL |
| started_at | TEXT NULL，仅 running 或终态允许 |
| finished_at | TEXT NULL，仅终态非 null |

- CHECK 约束必须保证非终态没有 finished_at/error_code/archive_sha256；completed 有 finished_at/archive_sha256 且 error_code 为 null；stale/failed 有 finished_at/error_code 且 archive_sha256 为 null。
- (status, created_at, job_id) index 支持 worker 扫描。snapshot_json 和 source_revision 没有更新路径。

### published_order_archives

| 列 | 约束与含义 |
| --- | --- |
| order_id | TEXT PRIMARY KEY，REFERENCES orders(order_id) ON DELETE RESTRICT |
| job_id | TEXT NOT NULL UNIQUE，REFERENCES archive_jobs(job_id) |
| source_revision | INTEGER NOT NULL |
| archive_blob | BLOB NOT NULL |
| archive_sha256 | TEXT NOT NULL，64 位小写 hex |
| published_at | TEXT NOT NULL |

- 每个订单只保留一个当前发布归档。只有 completed transaction 可 INSERT/UPDATE 此表。
- archive_jobs 保存每次尝试及其终态；published_order_archives 只指向最后一次成功发布。stale 或 failed 不得删除、插入或替换已有行。
- 发布 transaction 要求表中的 job_id、source_revision、digest 与被置为 completed 的 job 完全一致。

## 状态转换、迁移边界与一致性

### 合法状态转换

| 起始 | 目标 | 触发条件 |
| --- | --- | --- |
| queued | running | worker 成功 claim |
| running | completed | snapshot 仍 current、完整，归档与 job 原子提交 |
| running | stale | 当前订单缺失、revision 改变或 snapshot bytes 不同 |
| running | failed | 序列化失败、snapshot 不变量破坏、本地持久化失败或进程恢复 |

除此之外的转换均为实现错误。条件 UPDATE 未影响恰好一行时必须回滚并记录内部错误，不能继续发布。

### SQLite 配置与 transaction

- schema bootstrap 在对外监听前执行。新库以一个 transaction 创建三张表、约束和 index，并设置 PRAGMA user_version = 1。
- user_version = 0 且没有本功能表时可初始化；user_version = 1 时逐项校验所需表/列；更高版本、半存在 schema 或不匹配约束使启动失败，禁止删除或猜测迁移。
- 初始化时设置并验证 PRAGMA journal_mode = WAL。每个连接设置 PRAGMA foreign_keys = ON、PRAGMA synchronous = FULL、PRAGMA busy_timeout = 1000，并使用 isolation_level = None 以便显式控制 transaction。
- sqlite3 connection 不跨线程共享。API request transaction、GET read transaction、worker claim 和 completion 都在所属线程内创建、提交/回滚和关闭。
- 所有写路径使用 BEGIN IMMEDIATE。transaction 中只执行有界 SQL、规范 JSON 比较和状态决定；HTTP I/O、慢序列化、sleep 和重试等待均在 transaction 外。
- API 依赖 SQLite busy_timeout 等待最多 1000 ms，不在 handler 内自动重放整个命令；超时返回 503。
- worker claim 遇到 SQLITE_BUSY/SQLITE_LOCKED 时保持 job 为 queued 并稍后扫描。completion 遇到这两类错误时保留已序列化 bytes，最多执行四次 completion attempt；前三次失败后依次在 transaction 外退避 50 ms、100 ms、200 ms。每次新 transaction 都重新检查 current snapshot；第四次仍失败后按 archive_persistence_failed 终结。
- completion 的其他 sqlite3 错误立即回滚并按 archive_persistence_failed 终结。不得把任何 sqlite3 exception、busy timeout 或回滚失败分类为 archive_snapshot_stale。

### COMMIT 不确定性与回滚

- 每个 repository operation 追踪 transaction 是否活动；失败时只对活动 transaction 调用 ROLLBACK。ROLLBACK 也失败则关闭连接，后续协调使用新连接。
- PUT/POST 的 COMMIT 抛错一律返回 503，不把内存中的新 revision/job 当作事实；新连接读取仅用于填充 currentRevision。
- worker completion 的 COMMIT 抛错后，先用新连接协调读取：
  - 若 job 已是 completed，且 published_order_archives 的 job_id、source_revision 和 digest 全部匹配，则把原 transaction 视为已提交，不再写 failed。
  - 若 job 仍为 running 且 published row 未指向该 job，则尝试持久化 failed/archive_persistence_failed。
  - 任何部分组合都表示不变量损坏，停止 worker、使进程不健康，禁止用补写猜测修复。
- archive upsert 与 completed job update 位于同一 transaction，因此正常 SQLite 原子性下不存在可提交的部分组合；协调分支用于检测 wrapper、磁盘或 schema 故障。

### 一致性保证

- 订单保存提供单行线性化 CAS：两个相同 expectedRevision 的并发 PUT 最多一个成功。
- job 创建在线性化点捕获已提交 order snapshot。接受响应中的 sourceRevision 与 archive_jobs 中 snapshot 属于同一 transaction。
- 归档发布相对于订单 PUT 线性化：completion transaction 的 COMMIT 是发布点；只有该点前最后一个订单 revision 与 snapshot 一致才可成功。
- WAL reader 可以与事务外序列化并发；任何长时间 serializer 都不持有 read snapshot 或 writer lock。
- failed/stale 的 transaction 不改变 published_order_archives；已有成功归档在任意后续失败后保持 byte-for-byte 不变。
- GET 的 status、currentRevision 和 isLatest 来自同一个 read snapshot，不组合不同时刻的数据。

## 错误与不确定性

### 后台稳定错误码

| job status | error.code | 分类规则 |
| --- | --- | --- |
| stale | archive_snapshot_stale | 数据库读取成功，且明确观察到当前订单缺失、revision 不同或 document bytes 不同 |
| failed | archive_serialization_failed | serializer 对有效固定 snapshot 抛出异常 |
| failed | archive_snapshot_invalid | 固定 snapshot 或同 revision 当前正文违反完整性/规范 JSON 不变量 |
| failed | archive_persistence_failed | completion/terminal write 的本地 SQLite 持久化错误，且不是可协调的已提交结果 |
| failed | archive_worker_interrupted | 启动时发现前一进程留下的 running job |

- 对外仅保存和返回稳定 error.code 与通用 message；不得返回 exception 文本、SQL、文件路径、order body 或 archive bytes。
- 日志可记录 jobId、orderId、sourceRevision、SQLite 主错误码和堆栈，但不得记录完整 snapshot/archive；日志不是客户端判断结果的必要条件。
- completed job 后续遇到更高订单 revision 仍保持 completed，因为它在自己的发布点有效；GET 通过 currentRevision 和 isLatest 表示当前关系。
- job 终态写入需要 SQLite 可写。在完全不可读写期间，API 只能返回 503；在“可读但暂不可写”期间，job 可能暂时显示 running，直到 worker 持久化失败终态。实现不得提前返回未持久化的 terminal 状态。

### 权限与数据边界

- 服务默认绑定 loopback；本功能不新增认证。若未来允许非本机访问，必须先通过独立需求定义认证与授权，不能仅修改绑定地址。
- 归档包含完整订单 document，因此 archive_blob 不通过当前 API 返回，且 snapshot/blob 不写入日志或错误 response。
- 数据库文件、WAL 和 SHM 使用进程现有运行账户权限；本规格不定义跨账户共享。

### 已知限制

- 仓库没有既有 HTTP 框架或数据库 schema；本规格选用 Python 标准库 HTTP server 和 schema version 1。更换框架不能改变这里的 API、transaction 或错误语义。
- 当前证据只定义 owner 与 created status 的完整订单形态。新增业务必填字段或其他可归档 status 是产品/领域契约变化，需要更新已批准需求与本规格，而不是在实现中静默放宽。
- POST 没有幂等键。HTTP 响应在 commit 后丢失时，已创建 job 仍会执行；当前 API 无法按客户端请求键找回该 job。

## 测试与文档

### 自动化策略

- 延续 unittest；数据库集成测试使用每个测试独立的真实临时文件，不能使用 :memory:，以覆盖 WAL、独立连接和锁竞争。
- HTTP contract 测试在 loopback 随机端口启动真实 adapter；repository/worker 测试可直接调用 service，但不能只 mock 掉 SQLite transaction。
- 并发测试使用 threading.Barrier 或 Event 建立确定的交错，不使用任意 sleep 判断正确性。等待均设置明确 timeout，超时即失败。
- connection factory、serializer、clock 和 commit 边界提供测试注入点，以制造 SQLITE_BUSY、序列化异常、archive upsert 后异常、commit 后抛错和 terminal write 暂时失败；生产分支不通过错误字符串分类。

### 必测行为

1. 校验矩阵：非法 orderId、缺失/多余字段、boolean/负数/溢出 revision、重复 JSON key、NaN/Infinity、非 object order、字段类型错误、超限 body；断言稳定 HTTP/error.code 且三张表无变化。
2. 保存 CAS：expectedRevision = 0 创建 revision 1；匹配 revision 更新并加 1；不存在配正 revision 返回 404；已存在配 0 或 stale revision 返回 409 和准确 currentRevision。
3. 并发保存：两个连接用相同 expectedRevision 同时 PUT；断言恰好一个成功、一个 revision_conflict，最终 revision 只增加 1，失败请求的 order object 未被 handler 修改。
4. API 锁超时：一个连接持有 BEGIN IMMEDIATE，另一个 PUT/POST 在约 1000 ms 后得到 503；释放锁后用同 expectedRevision 重试可由实际提交状态确定性成功或 conflict。
5. job 捕获：POST 对 missing/conflict/incomplete 分别返回 404/409/422 且无 job；成功时 job 的 sourceRevision 与 snapshot bytes 精确匹配同一订单版本。
6. 事务外序列化：serializer 用 Event 阻塞时，并发 PUT 能完成；释放 serializer 后旧 job 必须 stale，且已有 published archive 不变。这也证明无长 read transaction。
7. 反向竞争：completion 先取得 writer reservation 并发布后，PUT 再保存；job completed，PUT revision 增加，旧归档仍是一次合法完成且 GET 反映新的 currentRevision。
8. 原子发布：预置旧 published archive，在 archive upsert 与 job completed update 之间注入异常；断言整个 transaction 回滚、旧 archive byte-for-byte 不变、job 最终 failed/archive_persistence_failed。
9. COMMIT 协调：真实 commit 完成后由 wrapper 抛错；协调读取必须识别 matching completed job 与 published row，不得改成 failed 或重复发布。
10. stale 与 persistence 分类：revision 变化只产生 archive_snapshot_stale；SQLite 写异常只产生 archive_persistence_failed；两者都不能替换旧 archive。
11. 序列化与 snapshot 故障：serializer 异常产生 archive_serialization_failed；直接种入不满足不变量的 snapshot 产生 archive_snapshot_invalid；均为 terminal failed。
12. 恢复：启动扫描处理 queued；遗留 running 被原子终结为 archive_worker_interrupted；所有既有终态保持不变，completed 对应 published row 保持一致。
13. 多 job：同 revision 的多个已接受 job 各自有独立 jobId；只有 completion 时仍 current 的 job 可发布，任何后到 stale/failed job 都不覆盖最新成功归档。
14. GET 一致性：覆盖五种 status、terminal、error、archive、currentRevision、isLatest，未知 job 404 和数据库不可读 503；用并发保存/发布确认单个 response 不混合两个 SQLite snapshot。
15. schema/config：新库创建 version 1；连接确认为 wal、foreign_keys=1、synchronous=FULL、busy_timeout=1000；未来 version、半 schema 和错误约束均使启动失败而不改库。

实现完成后的统一验证命令为：

~~~text
python3 -m unittest discover -s tests -v
~~~

测试环境必须报告 Python 3.14 和 SQLite 3.46.x；版本不满足时验证失败，不以 skip 伪装通过。

### 文档影响

- 实现时同步更新 README.md，记录三个 endpoint 的 request/response、expectedRevision 语义、job 状态、稳定错误码、loopback 边界和验证命令。
- schema version、归档格式或稳定 API/error code 的后续变化必须先修改已批准规格并重新经过独立评审与用户批准。
- 本草案本身不创建 plan；只有当前文件完成真实独立评审并由用户明确批准后，才可进入计划阶段。

## 验收标准

- 使用相同 expectedRevision 的并发保存最多一个成功；失败保存既不改变数据库订单，也不改变调用方提交的草稿对象，并返回 409 revision_conflict 与 currentRevision。
- POST 只从事务内验证过的当前完整订单创建 queued job，响应 jobId/sourceRevision 对应数据库中不可变 snapshot。
- serializer 运行期间没有 SQLite transaction 或开放 cursor；同期保存能在测试 timeout 内完成。
- completion 在一个 BEGIN IMMEDIATE transaction 内完成当前 snapshot 校验、归档发布和 completed 状态提交；不存在部分发布。
- 订单在 snapshot 捕获后先被保存时，job 终态为 stale/archive_snapshot_stale，最后成功归档保持不变。
- 序列化或本地 SQLite 持久化故障分别产生 terminal failed 的稳定错误码，且永不误报 stale、永不替换最后成功归档。
- API 的所有写成功只在 commit 后返回；所有失败执行规定的 rollback/协调，并在可读取时返回 currentRevision。
- 进程重启会继续 queued job、把遗留 running job 终结为 archive_worker_interrupted，并保留所有已有终态与发布归档。
- GET 对已知 job 始终返回一致 snapshot 中的 status、terminal、currentRevision、archive/error；客户端无需读取日志即可区分进行中、成功、stale 和 failed。
- 全部 unittest 在真实临时 SQLite WAL 文件上通过，并包含确定性交错与故障注入；README 与最终行为一致。
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
技术规格用户批准：待批准
技术规格独立评审：待评审
实施计划：尚未创建
计划评审状态：未开始
实施门禁：未开放