已创建唯一的 [spec 草案](/workspace/fixture/docs/specs/2026-07-21-durable-order-archive-design.md:1)。

未创建实施计划、未实施代码、未操作 task/thread，也未提交。PRD 复验通过，`git diff --check` 通过，现有 1 项测试通过。按要求未发起独立评审，草案仍待评审、待用户批准。状态尾注中的计划路径只是工作流预解析的默认候选位置，该文件并未创建。

完整正文如下：

```markdown
---
文档类型: 技术规格
主题: durable-order-archive
需求文档: docs/requirements/2026-07-18-durable-order-archive.md
需求主题: durable-order-archive
需求范围: 功能
需求理解置信度: 98
需求理解确认: 已确认
需求文档用户批准: 已批准
需求文档独立评审: 已通过
技术规格门禁: 已开放
技术规格用户批准: 待批准
技术规格独立评审: 待评审
---

# 持久订单归档技术规格

## 目标

- `PUT /orders/{orderId}` 以 `expectedRevision` 原子保存可编辑订单；版本冲突不改变服务端订单，也不要求调用方丢弃其待保存草稿。
- `POST /order-archives` 为指定订单启动一个后台归档 job；`GET /order-archives/{jobId}` 让调用方仅凭稳定状态和错误码判断继续轮询、处理版本冲突、重试失败工作或确认完成。
- 归档只在序列化所用快照仍是当前完整订单时发布。陈旧或失败的 job 保留上一份已完成归档。
- 在 SQLite WAL 的单写者约束下，将慢序列化移出数据库事务，并用短写事务确定保存与归档发布的线性化结果。

## 非目标

- 不提供归档历史、归档取消、自动重新归档或多版本下载；每个订单只保留最后一次成功发布的归档。
- 不支持多进程或多 worker 协调、跨进程崩溃恢复、分布式队列或通用重试/恢复框架。
- 不新增 `attemptId`、`archiveId` 等持久身份；除既有 `orderId` 外，只使用 API 已要求的 `jobId`。
- 不引入独立于本功能的通用状态机。归档 job 仅有调用方动作不同所必需的 `in_progress`、`completed`、`failed` 三种状态。
- 不在本规格中发明订单“完整”的产品字段或改变所有权/权限规则；归档入口与发布检查复用同一个订单域完整性判定。

## 当前证据

- 已批准 PRD `docs/requirements/2026-07-18-durable-order-archive.md` 要求：保存冲突保留操作员草稿；只从当前完整快照发布归档；陈旧或失败尝试不得替换上一份完成归档；客户端无需日志即可区分冲突、后台失败和完成。
- `README.md` 已确认 Python 3.14、标准库 `sqlite3`、SQLite 3.46 WAL、单个本地 API 进程和单个进程内归档 worker，并确认慢序列化、版本检查及本地数据库持久化失败是本规格必须覆盖的边界。
- `src/orders.py` 目前只有内存态 `create_order`，没有持久化、HTTP 或 worker 实现；因此本规格定义初始持久化边界，不承担既有生产数据迁移。
- `tests/test_orders.py` 目前只验证新订单状态。基线命令 `python3 -m unittest discover -s tests -v` 于 2026-07-21 通过 1 项测试。
- 根目录 `AGENTS.md` 要求规格先经真实独立评审并由用户明确批准，之后才能生成计划；本文件因此保持待评审、待批准。

## 行为与边界

### 保存订单

1. PUT 请求携带完整的可编辑订单内容和整数 `expectedRevision`。尚未持久化的订单以 `expectedRevision: 0` 创建，成功后修订号为 `1`；既有订单只有在当前修订号等于 `expectedRevision` 时才被替换，并将修订号恰好加一。
2. 成功响应只在事务提交后返回 `200`，并给出提交后的 `revision`。
3. 不匹配返回 `409 / ORDER_REVISION_CONFLICT` 和可读取的 `currentRevision`。服务端订单、当前归档和调用方提交的草稿均不被该失败路径替换；调用方保留原请求内容，读取当前版本后自行合并并以新 `expectedRevision` 重试。
4. 保存事务未提交时不得报告成功。本地数据库写入失败回滚整个保存，并返回 `503 / ORDER_PERSISTENCE_FAILED`；回滚后能读取订单时附带 `currentRevision`，否则该字段为 `null`。

### 启动并查询归档

1. POST 请求体为 `{ "orderId": ..., "expectedRevision": ... }`。入口在一个短事务内确认订单存在、修订号匹配且满足统一的完整性判定，然后插入一个 `in_progress` job。成功提交后返回 `202`、`jobId`、`status: "in_progress"` 和接受时的 `currentRevision`。
2. 修订号不匹配沿用 `409 / ORDER_REVISION_CONFLICT`；订单不存在返回 `404 / ORDER_NOT_FOUND`；当前订单不完整返回 `422 / ORDER_INCOMPLETE`。这些结果均不创建 job，也不改变已有归档。
3. GET 在 job 可读取时返回 `200`。`in_progress` 表示继续轮询；`completed` 同时返回 `sourceRevision`；`failed` 同时返回稳定的 `failureCode`。响应在订单可读取时包含实时 `currentRevision`，否则为 `null`。
4. `ARCHIVE_STALE_SNAPSHOT` 表示 job 的固定快照已不是当前完整订单，调用方应基于当前修订重新发起归档。`ARCHIVE_WORK_FAILED` 合并序列化失败和本地归档持久化失败：两者对调用方都是稍后新建 job 重试，且都不得改变上一份完成归档。该合并不免除实现对数据库失败执行回滚的责任。
5. GET 找不到 job 时返回 `404 / ARCHIVE_JOB_NOT_FOUND`。数据库不可读取时返回 `503 / ARCHIVE_STATUS_UNAVAILABLE`，不得把未知结果伪装成 `failed` 或 `completed`。

### 固定快照与发布

1. 单 worker 在一个短只读事务中按 job 的 `orderId` 读取订单内容和修订号，重新确认它等于 job 的 `expectedRevision` 且订单完整。检查通过时，将该不可变副本留在内存后结束事务；POST 提交后至此次读取前若订单已变化、不存在或不再完整，则不执行序列化，并用短写事务记录 `failed / ARCHIVE_STALE_SNAPSHOT`。
2. 慢归档序列化只读取该内存副本，并在没有数据库事务和写锁的情况下执行。
3. 发布使用一个短写事务再次读取当前订单。只有当前订单仍完整且修订号仍等于快照修订号时，才可原子替换该订单的当前归档并把 job 置为 `completed`。
4. 若最终检查发现修订号变化、订单不存在或不再完整，则同一短事务只把 job 置为 `failed / ARCHIVE_STALE_SNAPSHOT`；不得写归档。
5. 序列化或发布持久化失败时，把 job 置为 `failed / ARCHIVE_WORK_FAILED`。归档写入和 `completed` 状态必须同一事务提交；任一语句或提交失败都回滚两者，因此上一份完成归档保持不变。若数据库暂时连失败终态也无法写入，GET 返回 `503`，worker 只允许重试该既有 job 的失败终态落盘，不重新发布、不重新序列化、不创建额外 attempt 身份。

## 组件与控制流

- **订单 API 边界**：校验 `expectedRevision`，调用订单存储事务，并把领域结果映射为固定 HTTP 状态、错误码和修订号；冲突响应不得用服务端内容覆盖调用方草稿。
- **订单存储边界**：维护订单内容及单调递增的修订号；所有条件保存都在 SQLite 写事务内完成。
- **归档 API 边界**：在短事务内验证归档前置条件并持久化 job，返回 `jobId`；查询时只投影 job 状态、失败码和可读取的当前修订号。
- **单个进程内 worker**：按 `jobId` 取得固定快照、在事务外调用序列化器、再调用发布事务。单 worker 已足以满足当前仓库约束，不需要租约、claim token 或多 worker 竞争协议。
- **归档存储边界**：按 `orderId` 保存唯一的当前完成归档，并在同一发布事务中更新 job 终态。

控制流为：保存或确认完整订单 → POST 条件创建 job → worker 短读复制固定快照 → 无事务序列化 → 短写事务校验当前修订并发布或记录陈旧终态 → GET 返回稳定结果。

## API 与技术接口

### `PUT /orders/{orderId}`

- 请求：可编辑订单字段加 `expectedRevision: integer >= 0`。
- `200`：`{ "orderId": string, "revision": integer }`。
- `409`：`{ "error": { "code": "ORDER_REVISION_CONFLICT", "currentRevision": integer } }`。
- `503`：`{ "error": { "code": "ORDER_PERSISTENCE_FAILED", "currentRevision": integer | null } }`。

### `POST /order-archives`

- 请求：`{ "orderId": string, "expectedRevision": integer >= 1 }`。
- `202`：`{ "jobId": string, "status": "in_progress", "currentRevision": integer }`。
- `409`：`ORDER_REVISION_CONFLICT`，附 `currentRevision`。
- `404`：`ORDER_NOT_FOUND`，`currentRevision: null`。
- `422`：`ORDER_INCOMPLETE`，附 `currentRevision`。
- `503`：`ARCHIVE_JOB_PERSISTENCE_FAILED`，`currentRevision` 在可读取时为整数，否则为 `null`。

### `GET /order-archives/{jobId}`

- 进行中：`{ "jobId": string, "orderId": string, "status": "in_progress", "currentRevision": integer | null }`。
- 完成：`{ "jobId": string, "orderId": string, "status": "completed", "sourceRevision": integer, "currentRevision": integer | null }`。
- 失败：`{ "jobId": string, "orderId": string, "status": "failed", "failureCode": "ARCHIVE_STALE_SNAPSHOT" | "ARCHIVE_WORK_FAILED", "currentRevision": integer | null }`。
- job 可读时，包括失败终态在内均返回 `200`；资源不存在返回 `404 / ARCHIVE_JOB_NOT_FOUND`，状态库不可读返回 `503 / ARCHIVE_STATUS_UNAVAILABLE`。

所有错误响应使用同一 `error.code` 字段。只有以上公开码属于本功能契约；内部 SQLite 或 Python 异常文本不得透传给调用方。

## 关键结果与失败边界（按需）

| 需求或已确认风险依据 | 触发条件 | 可观察结果 | 数据或一致性影响 | 调用方动作 | 最小充分验证 |
| --- | --- | --- | --- | --- | --- |
| 保存冲突保留草稿；每次写入携带预期修订号 | PUT 或 POST 的 `expectedRevision` 与当前值不符 | `409 / ORDER_REVISION_CONFLICT` 和 `currentRevision` | 订单、job、归档均无变化 | 保留草稿，读取/合并当前订单后以新修订号重试 | API 集成测试断言响应、提交草稿副本未被改写及数据库无副作用 |
| 只归档完整订单 | POST 时当前订单不完整 | `422 / ORDER_INCOMPLETE` | 不创建 job，不改变归档 | 补全并成功保存订单后重试 | 组件测试断言无 job、无归档写入 |
| 后台执行且客户端可轮询 | job 已提交但尚无终态 | `202` 或 GET `200`，状态为 `in_progress` | 当前归档尚无变化 | 使用同一 `jobId` 继续轮询 | API 测试断言稳定状态形状 |
| 成功完成可由客户端确认 | 固定完整快照在发布事务中仍为当前版本 | GET `200`，状态为 `completed` 且给出 `sourceRevision` | 新归档和完成终态原子提交 | 停止轮询并使用完成结果 | 真 HTTP、worker 与 WAL 数据库的最小关键 E2E |
| 陈旧尝试不得覆盖完成归档 | 序列化期间订单修订号改变或不再完整 | GET `200`，状态为 `failed / ARCHIVE_STALE_SNAPSHOT` | 上一份完成归档不变 | 基于 `currentRevision` 新建 job | 带同步屏障的 WAL 集成测试，证明编辑可先提交且发布被拒绝 |
| 失败后台工作不得覆盖完成归档 | 序列化失败，或归档写入/提交失败 | GET `200`，状态为 `failed / ARCHIVE_WORK_FAILED`；状态库不可读期间为 `503` | 归档与 `completed` 一并回滚，上一份完成归档不变 | 服务恢复后新建 job；状态不可读时稍后查询 | 序列化异常测试与针对归档写事务的局部失败测试；不建设通用故障注入框架 |
| SQLite WAL 单写者风险 | 保存与归档发布竞争写锁 | 获得写锁者先线性化；另一方在短事务后按当时修订号成功或冲突 | 不出现部分保存、部分发布或长序列化持锁 | 按返回修订号/状态继续 | 真实 WAL 并发集成测试断言序列化暂停期间 PUT 仍可完成 |

## 数据模型与实体关系

- `orders`：以 `order_id` 为主键，保存现有所有权字段、可编辑订单内容和 `revision`。`revision` 从 1 开始，仅成功保存时递增，job 状态变化和归档发布不改变它。
- `archive_jobs`：以 API 必需的 `job_id` 为主键，保存 `order_id`、`expected_revision`、`status` 和可空 `failure_code`。`status` 只允许 `in_progress`、`completed`、`failed`；`failure_code` 只在 `failed` 时出现。完成版本由 `expected_revision` 得出，不另设 attempt 或 snapshot 身份。
- `order_archives`：以 `order_id` 为唯一键，保存 `source_revision` 和序列化结果。每个订单最多一行，因此成功发布是对“最后完成归档”的原子替换。
- 一个订单可关联多个可查询 job，但最多有一个当前完成归档。job 只引用订单和预期修订号；固定订单内容仅在 worker 内存中存在，不复制为额外持久快照实体。

当前仓库没有数据库实现或生产数据。本功能只需创建上述初始 schema 并启用 WAL；不定义历史数据回填、在线迁移或第二套存储。

## 事务与并发边界（按需）

- API 请求线程与 worker 使用各自的 `sqlite3` 连接；数据库初始化为 WAL。连接不跨线程共享。
- PUT、POST job 创建、job 终态更新和归档发布均使用短写事务；需要先读后写的路径使用 `BEGIN IMMEDIATE`，在作出版本判断前取得 SQLite 写入保留权，避免把陈旧读取升级为写入。
- worker 的快照读取使用短只读事务；复制订单值后立即结束。序列化期间不得持有事务、游标或数据库锁。
- 最终发布在 `BEGIN IMMEDIATE` 后重新检查 `orders.revision` 与完整性。若 PUT 先取得写入权并提交，发布看到新修订号并失败为陈旧；若发布先提交，随后 PUT 可基于其 `expectedRevision` 正常保存。两种顺序都保证归档在其发布线性化点来自当前完整快照。
- `order_archives` 替换与 job `completed` 必须同事务提交。陈旧路径只提交 job `failed`。数据库异常回滚当前事务；SQLite 锁等待超过连接的有界等待策略后按对应持久化失败处理，不做无界透明重试。
- 只有一个 worker，因此不增加 job claim、租约、幂等 attempt 或并行发布协议。多个相同订单的 job 依次执行，并各自以其 `expected_revision` 接受或判陈旧。

## 状态转换、迁移边界与一致性

- job 唯一允许的转换是 `in_progress → completed` 或 `in_progress → failed`；两者均为终态，不允许从终态重新进入执行。重试由调用方创建新的 `jobId`。
- `completed` 只能与对应 `order_archives` 行在同一提交中出现。观察到 `completed` 即表示归档已持久化；观察到 `failed` 不会改变上一份完成归档。
- `ARCHIVE_STALE_SNAPSHOT` 的终态写入与最终修订检查在同一写事务中完成。`currentRevision` 不冗余存入 job，而由 GET 在可达时读取当前订单。
- 初始 schema 建立之外无迁移或回填。未来若要保留历史归档、多 worker 或跨重启恢复，必须回到需求范围重新批准，不能通过实施计划扩展。

## 错误与不确定性

- 输入缺少或使用非法 `expectedRevision` 时按现有 API 参数校验返回 `400`；该路径不进入数据库事务，也不增加领域错误状态。
- 订单完整性是已批准行为的前置条件，但仓库没有字段级产品规则。本规格固定其调用点和一致性要求，实施不得自行增加产品字段；应使用同一个订单域判定覆盖 POST 初检、worker 取快照和最终发布检查。
- 对可处理的序列化或本地归档写失败，公开结果合并为 `ARCHIVE_WORK_FAILED`，因为调用方动作和归档一致性影响相同；内部异常仍须区分数据库失败并执行事务回滚。
- 整个 API 进程退出、数据库长期不可达及跨重启接管不在批准范围内。本规格不以额外身份、队列或恢复状态机掩盖该未批准范围。

## 需求与验证追踪

| 需求或风险依据 | 最小技术保证 | 验证方式 | 命令或证据 | 可观察通过条件 |
| --- | --- | --- | --- | --- |
| 保存冲突保留操作员草稿 | 条件写失败不修改服务端订单，并返回稳定冲突码和当前修订号 | API 集成测试 | `python3 -m unittest discover -s tests -v`；具体测试名在实施计划阶段确定 | 冲突为 409；请求草稿副本与三类持久数据均未被改写 |
| 只发布当前完整订单快照 | 入口、快照读取和最终发布使用同一完整性判定；发布前复核修订号 | 组件测试 + 关键 E2E | 同上 | 不完整请求无 job；成功归档的 `sourceRevision` 等于发布时订单修订号 |
| 陈旧或失败尝试不替换上一份完成归档 | 归档替换与完成终态原子提交；陈旧/失败路径不写归档 | WAL 集成测试 | 同上；用测试内同步屏障暂停序列化 | 订单并发编辑后 job 为 stale，归档字节和版本保持旧值 |
| 客户端可区分冲突、后台失败和成功 | 固定 HTTP 状态、`error.code`、job `status`、`failureCode` 和可达的 `currentRevision` | API 契约测试 | 同上 | 不读取服务端日志即可为每类结果选择规定动作 |
| 慢序列化不得扩大 SQLite 写锁窗口 | 快照短读、事务外序列化、短事务最终发布 | 真实 SQLite WAL 并发集成测试 | 同上 | 序列化被暂停时，PUT 可提交；释放后 job 按修订号确定完成或陈旧 |
| 本地归档持久化失败必须回滚 | 归档与 completed 同事务；失败后上一归档不变并记录失败终态 | 聚焦存储集成测试 | 同上；仅在归档写边界触发局部失败 | GET 返回 work failed，且无部分归档/完成状态 |

## 验收类型与证据

| 验收项 | 验收类型 | 执行者 | 环境与步骤 | 可观察通过条件 | 留存证据 |
| --- | --- | --- | --- | --- | --- |
| 完整快照成功归档闭环 | 关键 E2E | 自动化测试执行者；独立评审者核对结果 | 发布候选本地进程、真实 HTTP API、单 worker、临时 SQLite WAL；保存完整订单，POST job，轮询 GET | 最终为 `completed`，`sourceRevision` 正确，数据库当前归档与该修订一致 | 测试输出和失败时的去敏诊断日志 |
| 序列化期间编辑的陈旧闭环 | 关键 E2E | 自动化测试执行者；独立评审者核对结果 | 同一环境；先建立旧归档，启动新 job 并在序列化处暂停，PUT 新版本后释放并轮询 | PUT 可在暂停期间完成；job 最终为 `failed / ARCHIVE_STALE_SNAPSHOT`；旧归档未变 | 测试输出和数据库断言 |

本功能没有视觉、文案或主观易用性判断，因而不设置目标用户人工验收；API 契约、并发和持久化结果均由上述自动化证据及更低层测试覆盖。

## 测试与文档

- 保留并扩展现有 `unittest` 测试层次：纯修订与状态转换用单元测试，HTTP 映射用 API 组件测试，真实 SQLite WAL 下的事务、回滚和并发用集成测试，仅上述两个跨层闭环作为关键 E2E。
- 并发测试使用测试内事件/屏障控制序列化时点，不依赖时间睡眠；失败测试只替换归档写边界或序列化器，不建设通用故障注入系统。
- 所有测试继续由 `python3 -m unittest discover -s tests -v` 执行。实现后该命令必须包含现有创建订单回归，并稳定覆盖成功、冲突、陈旧和归档工作失败结果。
- 更新 `README.md`，同步三条 API 的请求/响应形状、job 三态、公开错误码、WAL 短事务边界和“只保留最后完成归档”的约束。无需新增运维恢复手册或多 worker 文档。

## 验收标准

- 使用匹配 `expectedRevision` 保存订单会原子提交并将修订号加一；使用旧修订号返回稳定 409 和当前修订号，服务端数据及调用方草稿不被冲突路径替换。
- 完整订单可创建一个 `in_progress` job；调用方通过 GET 最终观察到 `completed` 或带稳定失败码的 `failed`，无需读取服务端日志。
- 成功归档的内容来自固定快照，且该快照在发布事务中仍是当前完整订单；`completed` 与归档数据不存在部分提交。
- 序列化期间发生订单编辑时，编辑无需等待整个序列化过程，job 最终为 `ARCHIVE_STALE_SNAPSHOT`，上一份完成归档保持不变。
- 序列化或本地归档持久化失败时，job 为 `ARCHIVE_WORK_FAILED`，归档替换与完成状态均不提交；状态库不可达时 API 明确返回 503 而不报告虚假终态。
- 测试套件在真实 SQLite WAL 上证明保存冲突、入口完整性、事务外序列化、发布竞争顺序、回滚和稳定 API 投影，且不引入额外持久身份、恢复框架或并行 worker 状态。
```

需求文档：/workspace/fixture/docs/requirements/2026-07-18-durable-order-archive.md
需求主题：durable-order-archive
需求范围：功能
需求理解置信度：98
需求理解确认：已确认
需求文档用户批准：已批准
需求文档独立评审：已通过
技术规格门禁：已开放
技术规格：/workspace/fixture/docs/specs/2026-07-21-durable-order-archive-design.md
技术规格用户批准：待批准
技术规格独立评审：待评审
实施计划：/workspace/fixture/docs/plans/2026-07-21-durable-order-archive.md
计划评审状态：未通过
实施门禁：未开放
