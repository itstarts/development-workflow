已创建唯一规格草案：[2026-07-19-direct-chapter-writing-design.md](</workspace/fixture/docs/specs/2026-07-19-direct-chapter-writing-design.md>)。

PRD 已重新验证通过；草案完成作者自检，33 个结果和 12 个保证均有唯一编号及测试追踪，现有 1 项基线测试通过。未派发 reviewer，独立评审和用户批准均保持待定；未创建计划、未实施代码、未操作 task/thread。

完整正文如下：

```markdown
---
文档类型: 技术规格
主题: direct-chapter-writing
需求文档: docs/requirements/2026-07-19-direct-chapter-writing.md
需求主题: direct-chapter-writing
需求范围: 功能
需求理解置信度: 98
需求理解确认: 已确认
需求文档用户批准: 已批准
需求文档独立评审: 已通过
技术规格门禁: 已开放
技术规格用户批准: 待批准
技术规格独立评审: 待评审
---

# 直接章节写作技术规格

## 目标

1. 写作者创建作品后，系统原子地创建空白第一章并直接打开该章编辑器；这条路径不依赖设定集或大纲。
2. 章节保存采用显式版本比较，过期版本不得覆盖较新内容；冲突时同时保留服务器版本和本地草稿，使写作者能够明确选择并继续编辑。
3. 编辑中的本地草稿在服务器确认保存前持续保留；保存结果不确定、浏览器刷新或冲突均不得静默丢弃草稿。
4. 写作辅助结果与章节正文隔离，只有写作者明确插入后才进入草稿，并仍通过同一版本保存契约持久化。
5. 以自动化技术验证和目标写作者人工验收分别证明跨层闭环、入口可发现性、冲突理解、辅助内容质量以及编辑器视觉层级与专注感。

## 非目标

- 本功能不新增设定集、大纲、多人实时协作、自动冲突合并或章节历史版本浏览能力。
- 本功能不自动把写作辅助结果写入正文，也不把辅助生成成功等同于正文保存成功。
- 本功能不选择具体的写作辅助供应商或模型；发布候选环境必须配置满足本规格超时、数据处理和流式结果契约的供应商。
- 本功能不改造现有订单示例域，不迁移既有写作数据；当前仓库没有可迁移的作品或章节实体。
- 本功能不定义原生移动端、离线跨设备同步、计费或账号体系改造。

## 当前证据

- 已批准需求来自 `docs/requirements/2026-07-19-direct-chapter-writing.md`，其受检主题为 `direct-chapter-writing`、范围为 `feature`、理解置信度为 98，需求用户批准和独立评审均已通过。
- `README.md` 将产品描述为浏览器写作产品，具有小型 API 和本地持久化层；单元、组件和 API 测试是主要回归层，浏览器 E2E 仅用于最小发布关键跨层路径。
- `README.md` 同时确认目标用户是长篇小说写作者，产品负责人能够组织主持式验收并留存任务记录、参与者判断和截图。
- 仓库当前仅有无关的 `src/orders.py` 示例和 `tests/test_orders.py`；`python3 -m unittest discover -s tests -v` 基线通过 1 个测试，尚无作品、章节、编辑器、API、数据库迁移或写作辅助实现可复用。
- 当前执行环境的 `python3` 为 3.9.6、SQLite 为 3.51.0，但仓库没有版本清单。为使并发保证可验证，本规格要求运行时 SQLite `>=3.35.0`，并由启动检查和集成测试把实际版本、WAL 模式及同步级别记录为权威运行证据；不得把当前工作站版本当作部署证明。
- 仓库规则要求规格经真实独立评审且由用户明确批准后才能生成计划。本文件保持用户批准待定、独立评审待定。

## 行为与边界

### 创建作品并直接进入第一章

1. 已认证写作者在创建页提交标题。标题去除首尾空白后必须为 1 到 200 个 Unicode 字符。
2. 一次创建事务同时写入作品和序号为 1 的章节。第一章标题固定为 `第一章`，正文为 `""`，修订号为 `0`。
3. 创建响应包含稳定的 `editorUrl`。浏览器只在收到已确认的成功或幂等重放结果后跳转到 `/works/{workId}/chapters/{chapterId}`。
4. 编辑器首屏把正文编辑区作为主操作区，展示保存状态和写作辅助入口；不得要求先访问或完成设定集、大纲页面。
5. 创建校验、权限、忙碌、持久化或未知提交失败时保留创建页输入，并显示可操作的错误；未知提交状态必须先核对，不得直接再创建一个作品。

### 编辑、草稿与保存

1. 编辑器加载服务器章节后读取同一用户、同一章节的 IndexedDB 草稿。若草稿的 `localVersion` 更新或其内容不同，展示“发现未保存草稿”恢复条，不自动覆盖服务器内容。
2. 每次正文变化都令编辑器进入 `dirty` 状态，并在 500 ms 防抖窗口内把最新内容写入 IndexedDB；`pagehide` 时发起一次尽力写入。只有 IndexedDB 事务完成后才能显示“草稿已保存在此设备”。
3. “保存”按钮和 `Ctrl/Cmd+S` 调用同一保存接口，提交唯一 `operationId`、当前 `baseRevision` 和完整正文。正文 UTF-8 编码后不得超过 2 MiB。
4. 服务器仅在 `baseRevision` 等于当前修订号时写入。内容变化时修订号恰好加 1；内容相同返回无变化结果且不增加修订号。
5. 服务器确认保存后，客户端仅在“当前编辑器内容仍等于该请求提交内容”时清除对应本地草稿。请求期间继续输入的较新草稿不得被旧响应清除。
6. `409 CHAPTER_REVISION_CONFLICT` 返回当前服务器修订号和正文。界面必须同时呈现服务器内容与本地草稿，并要求写作者明确选择“以服务器版本继续”或进入合并区后选择“采用此合并稿”；选择前不得再次发起保存。
7. 冲突后的本地草稿至少保留到合并稿成功保存，或写作者通过带二次确认的“放弃本地草稿”动作明确删除。关闭对话框、刷新或导航不得隐式删除。
8. 网络中断、超时或客户端取消发生在提交之后时，客户端把结果视为未知，保留草稿并按 `operationId` 核对；确认已应用、确认未应用和仍未知必须展示为不同状态。
9. IndexedDB 配额、权限或事务失败时显示持续可见的本地恢复能力降级提示，保留内存中的编辑内容并提供“复制全文”；不得显示虚假的本地已保存状态。

### 写作辅助

1. 写作辅助面板支持 `continue`、`rewrite`、`brainstorm` 三种意图；请求携带当前服务器 `baseRevision`、用户指令和可选选区。
2. 服务器只在请求修订号仍为当前版本时调用辅助供应商。发送范围限于当前章节正文、选区、意图和用户指令，不发送其他作品、设定集或大纲；应用日志不得记录正文、选区、指令或生成内容。
3. 供应商连接必须使用 TLS，部署配置必须禁止用请求内容训练并采用零保留或产品批准的等效数据处理条款。配置不满足时写作辅助保持不可用，章节编辑和保存仍可用。
4. 辅助结果流式显示在独立面板中；部分流、失败、超时或取消均不得改变正文或服务器修订号。
5. 只有写作者点击“插入到正文”后，结果才进入编辑器并触发普通本地草稿写入；之后仍需按章节保存契约持久化。
6. 单次请求 30 秒未出现完成事件即超时。用户可取消；超时、取消或连接丢失后允许以新的 `requestId` 重试，但不得把不完整结果标记为完成。

### 权限与数据边界

- API 从已有认证会话取得 `writerId`，不接受客户端提交的所有者 ID。作品、章节、变更回执和辅助请求均按该所有者限定。
- 对不属于当前写作者的作品或章节返回同一 `404 RESOURCE_NOT_FOUND`，避免暴露资源是否存在；未认证请求返回 `401 AUTH_REQUIRED`。
- 浏览器草稿按 `[writerId, chapterId]` 命名空间隔离，只允许当前会话读取当前用户键。作品正文属于用户内容，不写入遥测、错误消息或普通日志。
- 服务器章节是跨会话权威版本；IndexedDB 草稿是单设备恢复副本，不能宣称已同步到服务器。

## 组件与控制流

### 组件职责

| 组件 | 预期位置 | 职责 |
| --- | --- | --- |
| 创建页控制器 | `web/direct-writing/create-work.js` | 校验标题、生成幂等键、提交创建请求、处理核对并导航到 `editorUrl`。 |
| 编辑器控制器 | `web/direct-writing/editor-controller.js` | 管理 `clean/dirty/saving/conflict/unknown` 状态、保存快捷键、响应竞态与显式冲突解决。 |
| 草稿存储 | `web/direct-writing/draft-store.js` | 封装 IndexedDB v1 的写入、读取、核对和条件清除，不决定服务器保存状态。 |
| 辅助面板 | `web/direct-writing/assistant-panel.js` | 发起与取消流式请求、隔离部分结果、在明确操作后把完成结果插入编辑器。 |
| HTTP 适配层 | `src/writing/api.py` | 认证、输入/输出映射、HTTP 状态和稳定错误码，不包含并发决策。 |
| 写作服务 | `src/writing/service.py` | 创建作品、章节 CAS 保存、幂等和提交后核对的用例编排。 |
| SQLite 仓储 | `src/writing/repository.py` | 执行迁移、事务、锁、条件更新、回执读取和所有者范围查询。 |
| 辅助适配器 | `src/writing/assistant.py` | 构造最小上下文、实施 30 秒超时、规范化流式完成和供应商错误。 |
| 初始迁移 | `src/writing/migrations/001_direct_chapter_writing.sql` | 创建 `works`、`chapters` 和 `mutation_receipts` 及约束、索引。 |

### 控制流

1. 创建页生成 UUIDv4 幂等键并调用创建 API；服务在一个 `BEGIN IMMEDIATE` 事务中检查回执、创建作品与第一章并写入回执，提交成功后返回编辑器地址。
2. 编辑器并行加载服务器章节和本地草稿，按内容及本地版本决定展示空白正文或恢复条；任何自动选择都不得覆盖一方内容。
3. 输入先更新内存模型，再排队持久化草稿；保存请求携带读取时的服务器修订号。服务在写事务中执行修订号比较和写入。
4. 保存成功响应与当前内存内容匹配时清草稿；不匹配时只更新已知服务器基线并继续保留较新草稿。
5. 保存冲突时进入阻塞式冲突状态，展示双版本；显式选择或合并产生新的本地草稿和新的 `baseRevision`，随后才能再次保存。
6. 辅助请求先验证所有权和修订号，再调用供应商；完整结果停留在侧栏。明确插入只触发本地编辑流程，不直接调用数据库。

## API 与技术接口

所有 JSON 错误采用 `{ "error": { "code": string, "message": string, "retryable": boolean, "operationId"?: string, "reconcileUrl"?: string } }`。响应不得包含堆栈、SQL、供应商原始错误或其他用户正文。成功的章节响应包含 `ETag: "chapter-{chapterId}-r{revision}"`。

### `POST /api/works`

- 认证：必需。
- 请求头：`Idempotency-Key` 的值为 UUIDv4 字符串，同一写作者和命令内唯一。
- 请求体：`{ "title": string }`。
- 首次成功：`201` 与 `{ "outcome": "created", "operationId": string, "work": { "id": string, "title": string }, "chapter": { "id": string, "ordinal": 1, "title": "第一章", "content": "", "revision": 0 }, "editorUrl": string }`。
- 同键同请求重放：`200`，原结果不变且 `outcome` 为 `replayed`。同键不同请求返回 `409 IDEMPOTENCY_KEY_REUSED`。

### `GET /api/works/{workId}/chapters/{chapterId}`

- 认证和所有权校验后返回 `200` 与 `{ "id", "workId", "ordinal", "title", "content", "revision", "lastOperationId", "updatedAt" }`。
- 不存在或不属于当前写作者统一返回 `404 RESOURCE_NOT_FOUND`。读取不改变持久状态。

### `PUT /api/works/{workId}/chapters/{chapterId}`

- 认证：必需。
- 请求体：`{ "operationId": string, "baseRevision": integer, "content": string }`；`operationId` 必须是 UUIDv4，`baseRevision` 必须是非负整数。
- 写入成功：`200` 与 `{ "outcome": "saved", "operationId", "revision", "updatedAt" }`；相同正文返回 `{ "outcome": "unchanged", ... }`。
- 同 `operationId` 同请求重放原结果；同 ID 不同请求返回 `409 IDEMPOTENCY_KEY_REUSED`。
- 版本冲突：`409 CHAPTER_REVISION_CONFLICT`，并返回 `{ "operationId", "submittedBaseRevision", "currentChapter": { "content", "revision", "updatedAt" } }`。冲突响应不写章节或成功回执。

### `GET /api/mutations/{operationId}`

- 只允许原写作者查询。已应用返回 `200` 与保存的命令类型、`outcome`、资源 ID、修订号或 `editorUrl`；强一致的新连接查询返回 `404 MUTATION_NOT_APPLIED` 时表示确认未提交。
- 数据库不可读时返回 `503 COMMIT_STATE_UNKNOWN`。客户端在获得确定结果前不得换新操作 ID重复同一意图。

### `POST /api/works/{workId}/chapters/{chapterId}/assistance`

- 请求体：`{ "requestId": string, "baseRevision": integer, "intent": "continue" | "rewrite" | "brainstorm", "instruction": string, "selection"?: string }`；`requestId` 必须是 UUIDv4，`baseRevision` 必须是非负整数。指令 1 到 2000 字符，选区不超过 20000 字符。
- 成功响应为 `text/event-stream`；事件仅允许 `chunk`、`complete`、`error`。只有一个 `complete` 是完整成功，且包含 `requestId` 和完整结果摘要哈希。
- 修订号过期返回 `409 ASSISTANCE_REVISION_STALE`；供应商失败为 `502 ASSISTANCE_UNAVAILABLE`；30 秒超时为 `504 ASSISTANCE_TIMEOUT`。建立流后的终止错误使用 `error` 事件传递相同稳定码。
- 该接口和用户取消均不改变 `works`、`chapters` 或 `mutation_receipts`。

### 浏览器草稿接口

IndexedDB 数据库名为 `direct-chapter-writing`、版本为 1，对象仓库为 `drafts`，主键为 `[writerId, chapterId]`。记录形状为 `{ writerId, workId, chapterId, content, baseRevision, localVersion, updatedAt, conflictServerRevision? }`。`localVersion` 每次本地内容变化单调加 1；清除操作必须同时匹配主键、预期 `localVersion` 和已确认服务器内容哈希，防止旧响应删除新草稿。

## 命令结果与失败矩阵

| 结果 ID | 命令或异步完成阶段 | 前置条件 | 结果类型 | 客户端可见结果 | 事务、回滚与副作用 | 调用方动作 | 保证 ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `O-01` | `POST /api/works` | 已认证；标题和新幂等键有效 | 成功 | `201 created`，含空白第一章和 `editorUrl` | 作品、第一章、回执同一事务提交 | 导航到编辑器 | `G-01`, `G-02`, `G-12` |
| `O-02` | `POST /api/works` | 同一用户、键和请求哈希已有成功回执 | 无变化 | `200 replayed`，结果与首次一致 | 不新增作品或章节 | 使用原 `editorUrl` | `G-02` |
| `O-03` | `POST /api/works` | 标题或幂等键无效 | 校验 | `422 VALIDATION_ERROR` | 事务前拒绝，无副作用 | 修正输入 | `G-11` |
| `O-04` | `POST /api/works` | 未认证 | 状态 | `401 AUTH_REQUIRED` | 无事务、无副作用 | 重新认证 | `G-09` |
| `O-05` | `POST /api/works` 或章节保存 | 操作 ID 已存在但请求哈希不同 | 冲突 | `409 IDEMPOTENCY_KEY_REUSED` | 回滚且不改变原回执或资源 | 生成新 ID 后仅提交新的真实意图 | `G-02`, `G-11` |
| `O-06` | `PUT .../chapters/{chapterId}` | 所有权、版本和输入有效；正文变化 | 成功 | `200 saved` 与新修订号 | 章节修订号加 1，保存回执同事务提交 | 条件清除匹配的本地草稿 | `G-03`, `G-04`, `G-12` |
| `O-07` | `PUT .../chapters/{chapterId}` | 版本有效且正文与当前内容相同 | 无变化 | `200 unchanged`，修订号不变 | 仅提交幂等回执，不改章节 | 标记已保存并条件清草稿 | `G-05` |
| `O-08` | `PUT .../chapters/{chapterId}` | 同一操作 ID 和请求哈希已有结果 | 无变化 | `200` 重放原 `saved` 或 `unchanged` | 不再次增加修订号 | 按原结果完成 | `G-02`, `G-04` |
| `O-09` | `PUT .../chapters/{chapterId}` | 修订号、操作 ID 或正文无效 | 校验 | `422 VALIDATION_ERROR` | 事务前拒绝或回滚，无章节变化 | 修正输入 | `G-11` |
| `O-10` | 章节保存或辅助请求 | 资源不存在或不属于当前写作者 | 状态 | `404 RESOURCE_NOT_FOUND` | 无写入；不泄露存在性 | 停止并返回作品列表 | `G-09` |
| `O-11` | `PUT .../chapters/{chapterId}` | `baseRevision` 落后于当前修订号 | 冲突 | `409 CHAPTER_REVISION_CONFLICT`，含服务器版本 | 回滚；不写章节或成功回执；本地草稿不受影响 | 显式选择服务器版本或合并 | `G-03`, `G-08` |
| `O-12` | 创建或保存事务的 `BEGIN IMMEDIATE` | 写锁在 500 ms 内不可得 | 持久化 | `503 STORE_BUSY`，`retryable: true` | 未开始写事务，无部分写入 | 保留同一操作 ID，退避后重试 | `G-06`, `G-12` |
| `O-13` | 创建或保存的提交前阶段 | SQL、磁盘或完整性错误发生在 `COMMIT` 前 | 持久化 | `500 PERSISTENCE_FAILED`，`retryable: false` | 显式回滚；原状态完整保留 | 保留输入并停止自动重试 | `G-06`, `G-12` |
| `O-14` | `COMMIT` 异常后的新连接核对 | 回执存在且请求哈希匹配 | 成功核对 | 返回原成功结果并标记 `reconciled: true` | 已提交状态保持，不重复写 | 按成功完成 | `G-04`, `G-07` |
| `O-15` | `COMMIT` 异常后的新连接核对 | 数据库可读且回执确认不存在 | 确认未应用 | `503 MUTATION_NOT_APPLIED`，`retryable: true` | SQLite 原子提交保证资源变更也不存在 | 用同一操作 ID重试 | `G-06`, `G-07` |
| `O-16` | 提交后连接丢失、取消、超时或核对失败 | 无法读取回执 | 未知 | `503 COMMIT_STATE_UNKNOWN` 与 `reconcileUrl` | 不声称提交或回滚；状态保持未知 | 保留草稿并轮询，确定前不重发变更 | `G-07` |
| `O-17` | IndexedDB `putDraft` | 数据库可用且 `localVersion` 更新 | 成功 | “草稿已保存在此设备” | 单记录事务原子替换为新版本 | 可继续编辑或保存 | `G-08` |
| `O-18` | IndexedDB `putDraft` | 内容哈希和 `localVersion` 已持久化 | 无变化 | 保存状态不变 | 不写 IndexedDB | 无动作 | `G-08` |
| `O-19` | IndexedDB `putDraft` | 配额、权限或事务中止 | 持久化 | 持续降级提示和“复制全文” | 旧记录原子保留；内存内容不清除 | 复制内容或修复存储后重试 | `G-08`, `G-11` |
| `O-20` | IndexedDB 写入中页面终止后的加载核对 | 重新读取到预期 `localVersion` 和内容哈希 | 成功核对 | 展示完整的新草稿 | 新记录已原子提交 | 提供恢复或继续编辑 | `G-08` |
| `O-21` | IndexedDB 写入中页面终止后的加载核对 | 数据库可读但只存在旧记录或不存在记录 | 确认未应用 | 展示完整旧草稿或明确提示无设备草稿 | 中断写入未应用，旧记录保持完整 | 恢复旧稿或使用服务器版本 | `G-08` |
| `O-22` | IndexedDB 写入中页面终止后的加载核对 | IndexedDB 仍不可读 | 未知 | 持续降级提示，不声称存在或不存在新草稿 | 不改变内存或服务器状态 | 复制当前内容；存储恢复后再次核对 | `G-08`, `G-11` |
| `O-23` | IndexedDB `clearDraft` | 服务器已确认且本地版本、内容哈希均匹配 | 成功 | 编辑器为 `clean` | 原子删除匹配记录 | 无动作 | `G-08` |
| `O-24` | IndexedDB `clearDraft` | 本地版本或内容哈希不匹配 | 无变化 | 编辑器保持 `dirty` | 不执行删除，较新记录完整保留 | 继续编辑或保存较新草稿 | `G-08` |
| `O-25` | IndexedDB `clearDraft` | 匹配后删除事务失败 | 持久化 | 显示设备草稿清理失败，不宣称 `clean` | 记录保留，不影响已确认的服务器成功 | 下次加载核对后重试清理 | `G-08`, `G-11` |
| `O-26` | 辅助流完成 | 所有权、修订号、输入和供应商均有效 | 成功 | 唯一 `complete` 事件；完整结果在侧栏 | 不改变章节、回执或草稿 | 明确插入或丢弃结果 | `G-10` |
| `O-27` | 辅助请求开始前 | `requestId`、意图、指令或选区无效 | 校验 | `422 VALIDATION_ERROR` | 不调用供应商，不改变正文 | 修正输入 | `G-11` |
| `O-28` | 辅助请求开始前 | `baseRevision` 落后于当前修订号 | 冲突 | `409 ASSISTANCE_REVISION_STALE` | 不调用供应商，不改变正文 | 刷新服务器基线后重新决定 | `G-11` |
| `O-29` | 辅助请求开始前 | 未认证 | 状态 | `401 AUTH_REQUIRED` | 无供应商调用和持久副作用 | 重新认证 | `G-09` |
| `O-30` | 辅助调用或流式阶段 | 供应商拒绝、不可达或流内错误 | 依赖 | `502 ASSISTANCE_UNAVAILABLE` 或 `error` 事件 | 丢弃不完整结果；正文和修订号不变 | 可用新 `requestId` 重试 | `G-10`, `G-11` |
| `O-31` | 辅助调用 30 秒截止 | 未收到完整完成事件 | 超时 | `504 ASSISTANCE_TIMEOUT` 或 `error` 事件 | 取消上游；正文和修订号不变 | 可用新 `requestId` 重试 | `G-10`, `G-11` |
| `O-32` | 用户取消辅助流 | 请求仍在运行 | 取消 | 侧栏显示“已取消” | 中止上游；部分文本不插入，正文不变 | 修改指令或重试 | `G-10` |
| `O-33` | 辅助流连接丢失 | 未观察到 `complete` | 未知 | 侧栏显示“不完整结果”，不得标为完成 | 部分文本仅在易失侧栏；正文和服务器状态不变 | 丢弃或重试，不得插入部分结果 | `G-10`, `G-11` |

## 数据模型与实体关系

### SQLite

- `works(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL)`。
- `chapters(id TEXT PRIMARY KEY, work_id TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE, ordinal INTEGER NOT NULL CHECK(ordinal >= 1), title TEXT NOT NULL, content TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision >= 0), last_operation_id TEXT, updated_at TEXT NOT NULL, UNIQUE(work_id, ordinal))`。
- `mutation_receipts(owner_id TEXT NOT NULL, operation_id TEXT NOT NULL, command TEXT NOT NULL, request_hash TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner_id, operation_id))`。回执只保存资源 ID、结果、修订号和地址，不保存正文；当前范围不删除作品，因此回执不设自动过期，用于幂等和核对。未来若增加删除或清理，必须先定义与客户端最大核对窗口一致的保留契约。
- 所有 ID 使用服务端生成或验证的 UUIDv4；时间使用 UTC RFC 3339。`owner_id` 来自认证上下文。
- 一个作品拥有多个章节；本功能只在创建时生成序号 1。作品和第一章必须同生共灭，章节保存不得改变作品所有权或章节序号。

### 浏览器

- IndexedDB 草稿是服务器章节的一份按用户和章节隔离的可恢复候选，不是服务器实体的复制事务参与者。
- `baseRevision` 记录草稿从哪个服务器修订号派生；`localVersion` 仅用于同设备写入排序，不可作为服务器并发版本。
- 写作辅助运行和结果不在服务器持久化；明确插入后作为普通草稿内容处理。

## 数据库事务与锁语义

- 实际引擎要求为 SQLite `>=3.35.0`，通过 CPython 标准库 `sqlite3` 驱动访问。每个连接设置 `PRAGMA journal_mode=WAL`、`PRAGMA synchronous=FULL`、`PRAGMA foreign_keys=ON` 和 `PRAGMA busy_timeout=500`；启动时读取 `sqlite_version()` 及这些 PRAGMA，任一不匹配即拒绝写流量并输出不含用户内容的配置证据。
- 创建和保存均以 `BEGIN IMMEDIATE` 开始。写锁在首次读取前获取，因此不存在先读后写的锁升级；SQLite 的单写者预留锁是唯一物理写锁，不存在多行锁循环等待。
- 创建事务的首次读取是按 `operation_id + owner_id` 查询回执，首次写入是 `works`；随后依次写 `chapters`、`mutation_receipts`。保存事务的首次读取是回执，其次读取带所有者约束的章节；首次写入是条件更新章节或无变化回执，最后写回执。
- 锁从 `BEGIN IMMEDIATE` 成功起持有到 `COMMIT` 或 `ROLLBACK` 返回。事务内不得调用辅助供应商、访问网络或等待浏览器；正文哈希在事务前计算。
- WAL 读者使用各自读事务快照；写事务内的修订号检查和更新处于同一快照及单写者边界。其他写者在 `busy_timeout` 最多等待 500 ms，之后归类为 `STORE_BUSY`。不做应用层隐式重试；浏览器持有原操作 ID并负责退避重试。
- SQLite 不产生行锁死锁；锁竞争统一归为 busy。提交前异常显式 `ROLLBACK`。`COMMIT` 抛错时关闭原连接，并以新连接强一致查询回执：存在为已应用，不存在为确认未应用，新连接不可读才为未知。
- 集成测试必须在两个独立连接和真实临时 SQLite 文件上制造竞争、busy、提交前故障及三类提交核对结果；内存数据库或 mock 不能作为这些保证的唯一证据。

## 状态转换、迁移边界与一致性

### 状态转换

- 创建：`absent -> creating -> created(work + chapter@0)`；任何确认失败回到 `absent`，未知提交进入 `reconciling`，核对后转为 `created`、`absent` 或继续 `unknown`。
- 编辑器：`clean@rN -> dirty@rN -> saving@rN -> clean@rN+1`；请求期间新输入使成功响应转为 `dirty@rN+1` 而不是清稿。
- 冲突：`saving@rN -> conflict(server@rM, local@rN)`，其中 `M > N`；只有显式采用服务器版本或采用合并稿才能转为 `dirty@rM` 或 `clean@rM`。
- 辅助：`idle -> streaming -> completed | failed | timed-out | cancelled | incomplete`；只有 `completed -> explicit-insert` 会触发 `dirty`，其他终态不改变编辑器内容。

### 迁移与一致性

- `001_direct_chapter_writing.sql` 是新增 schema；当前仓库无写作表，因此没有数据回填或双写阶段。迁移必须在接受写流量前完整成功，否则服务保持不可写。
- 首次发布前可在空环境删除新表回退。任何真实作品数据产生后不得用降级脚本删除表；回退版本必须保持数据库文件并进入只读/导出模式，直到兼容版本恢复。
- 服务器对单个 SQLite 文件提供强一致读写和单调章节修订号；不承诺多设备本地草稿同步。WAL 文件、主数据库和回执属于同一备份单元。
- API 成功只在 `COMMIT` 已确认或提交后核对为已应用时返回。客户端错误、取消或超时不能被解释为确认未应用。

## 错误与不确定性

- 稳定错误码必须按矩阵区分校验、认证、资源、版本冲突、忙碌、确认失败、确认未应用、未知提交、辅助依赖和辅助超时；界面文案可以本地化，但不得把这些类别合并为“保存失败”。
- 日志只记录操作 ID、资源 ID、修订号、结果码、耗时和 SQLite/供应商分类，不记录标题、正文、草稿、选区、指令或生成内容。错误追踪中的请求体捕获必须关闭。
- 仓库尚无认证、HTTP 框架、前端构建或辅助供应商实现。它们可以在计划中选择适配方式，但不得改变本规格的路由、数据形状、状态码、所有权、事务和验收契约；若现有运行时无法承载这些契约，必须先回到规格阶段处理。
- 仓库尚未版本化 SQLite 运行时。实现必须增加可重复的版本/PRAGMA 检查；未产生该证据前，事务保证不能视为完成。
- 供应商和模型不是本规格固定实现，但发布候选配置、数据处理条款和实际输出必须作为人工验收环境证据留存。配置缺失只降级辅助，不得阻断章节编辑或保存。

## 保证与测试追踪

| 保证 ID | 保证或失败契约 | 对应结果 ID 或状态 | 精确测试文件与名称 | 精确命令 | 可观察断言 |
| --- | --- | --- | --- | --- | --- |
| `G-01` | 创建作品与空白第一章原子完成，并返回不经过设定/大纲的编辑器地址。 | `O-01`；`absent -> created` | `tests/test_work_api.py::WorkApiTests.test_create_is_atomic_and_returns_blank_first_chapter`；`tests/e2e/direct-chapter-writing.spec.mjs::create work opens blank first chapter and survives reload` | `python3 -m unittest discover -s tests -p 'test_work_api.py' -v`；`npx playwright test tests/e2e/direct-chapter-writing.spec.mjs --project=chromium --grep 'create work opens blank first chapter and survives reload'` | API 只观察到成对的作品/第 1 章且正文为空、修订号为 0；浏览器直接到编辑器，保存后刷新内容仍在。 |
| `G-02` | 创建和保存的操作 ID至多生效一次；同 ID异参被拒绝。 | `O-01`, `O-02`, `O-05`, `O-08` | `tests/test_work_api.py::WorkApiTests.test_create_replay_and_key_reuse`；`tests/test_chapter_save_api.py::ChapterSaveApiTests.test_save_replay_is_exactly_once` | `python3 -m unittest discover -s tests -p 'test_work_api.py' -v`；`python3 -m unittest discover -s tests -p 'test_chapter_save_api.py' -v` | 重放返回同资源/修订号，数据库计数和修订号不增加；异参返回 409。 |
| `G-03` | 过期修订号永不写入，冲突响应提供服务器版本且保留本地版本。 | `O-06`, `O-11`；`saving -> conflict` | `tests/test_chapter_save_api.py::ChapterSaveApiTests.test_stale_revision_returns_current_without_write`；`tests/e2e/direct-chapter-writing.spec.mjs::stale save preserves both versions and resumes after explicit merge` | `python3 -m unittest discover -s tests -p 'test_chapter_save_api.py' -v`；`npx playwright test tests/e2e/direct-chapter-writing.spec.mjs --project=chromium --grep 'stale save preserves both versions and resumes after explicit merge'` | stale 请求为 409，数据库仍是先提交内容；界面同时显示两版，明确合并后可保存并刷新。 |
| `G-04` | 已确认保存恰好增加一次修订号；提交后核对为已应用等同原成功。 | `O-06`, `O-08`, `O-14` | `tests/test_chapter_save_api.py::ChapterSaveApiTests.test_save_success_and_reconciled_success_increment_once` | `python3 -m unittest discover -s tests -p 'test_chapter_save_api.py' -v` | 成功、重放和已应用核对后最终正文一致，修订号只增加 1，回执唯一。 |
| `G-05` | 相同正文保存不增加修订号，但产生可重放的无变化结果。 | `O-07` | `tests/test_chapter_save_api.py::ChapterSaveApiTests.test_identical_content_is_unchanged` | `python3 -m unittest discover -s tests -p 'test_chapter_save_api.py' -v` | 返回 `unchanged`，正文、修订号和更新时间不变，回执可重放。 |
| `G-06` | busy、提交前失败和确认未应用均无部分作品、章节或修订变化。 | `O-12`, `O-13`, `O-15` | `tests/test_sqlite_chapter_repository.py::SQLiteChapterRepositoryTests.test_busy_precommit_failure_and_not_applied_are_atomic` | `python3 -m unittest discover -s tests -p 'test_sqlite_chapter_repository.py' -v` | 两连接故障注入后三种结果分别可见，表计数、正文和修订号保持原值。 |
| `G-07` | 提交后核对严格区分已应用、确认未应用和仍未知，未知时不自动重发。 | `O-14`, `O-15`, `O-16`；`creating/saving -> reconciling` | `tests/test_sqlite_chapter_repository.py::SQLiteChapterRepositoryTests.test_commit_reconciliation_has_three_distinct_outcomes`；`tests/component/direct-writing-editor.test.mjs::unknown save polls before retry` | `python3 -m unittest discover -s tests -p 'test_sqlite_chapter_repository.py' -v`；`node --test tests/component/direct-writing-editor.test.mjs` | 故障注入分别返回三种稳定码；未知 UI 保留草稿、只轮询且不发第二个变更。 |
| `G-08` | 本地草稿在匹配的服务器成功前保留；草稿故障和冲突可见且可恢复。 | `O-11`, `O-17`, `O-18`, `O-19`, `O-20`, `O-21`, `O-22`, `O-23`, `O-24`, `O-25`；`dirty/conflict` 状态 | `tests/component/direct-writing-editor.test.mjs::draft remains until matching server save is confirmed`；`tests/component/direct-writing-editor.test.mjs::conflict requires explicit resolution`；`tests/component/direct-writing-editor.test.mjs::draft store distinguishes applied not-applied and unknown reconciliation`；`tests/e2e/direct-chapter-writing.spec.mjs::stale save preserves both versions and resumes after explicit merge` | `node --test tests/component/direct-writing-editor.test.mjs`；`npx playwright test tests/e2e/direct-chapter-writing.spec.mjs --project=chromium --grep 'stale save preserves both versions and resumes after explicit merge'` | 旧响应不清新草稿；失败不显示已保存；中断后分别识别新记录、旧/无记录和不可读；冲突关闭/刷新不丢本地文本。 |
| `G-09` | 未认证或非所有者不能读取、改变或推断他人作品、章节、回执和辅助请求。 | `O-04`, `O-10`, `O-29` | `tests/test_writing_permissions_api.py::WritingPermissionsApiTests.test_auth_and_owner_boundaries_are_uniform` | `python3 -m unittest discover -s tests -p 'test_writing_permissions_api.py' -v` | 未认证为 401；所有跨所有者 ID均为相同 404；数据库和供应商调用计数不变。 |
| `G-10` | 辅助完成、依赖失败、超时、取消和不完整流都不直接改变正文；仅完整结果可明确插入。 | `O-26`, `O-30`, `O-31`, `O-32`, `O-33`；辅助状态转换 | `tests/test_assistance_api.py::AssistanceApiTests.test_terminal_outcomes_do_not_write_chapter`；`tests/component/assistant-panel.test.mjs::only complete result can be explicitly inserted` | `python3 -m unittest discover -s tests -p 'test_assistance_api.py' -v`；`node --test tests/component/assistant-panel.test.mjs` | 所有终态后服务器正文/修订号不变；部分结果不可插入，完整结果仅点击后进入 dirty 草稿。 |
| `G-11` | 所有校验、状态和外部依赖失败可区分、无目标持久副作用且给出单一恢复动作。 | `O-03`, `O-05`, `O-09`, `O-19`, `O-22`, `O-25`, `O-27`, `O-28`, `O-30`, `O-31`, `O-33` | `tests/test_writing_failures_api.py::WritingFailuresApiTests.test_failures_have_stable_codes_and_no_side_effects`；`tests/component/direct-writing-editor.test.mjs::failure messages preserve recoverable input` | `python3 -m unittest discover -s tests -p 'test_writing_failures_api.py' -v`；`node --test tests/component/direct-writing-editor.test.mjs` | 每种失败码、重试责任和状态独立；资源计数、正文/修订号不变，输入或草稿仍可取回。 |
| `G-12` | SQLite 版本、WAL/FULL、锁先于读取、500 ms busy 边界和回滚规则得到真实引擎验证。 | `O-01`, `O-06`, `O-12`, `O-13`, `O-14`, `O-15`, `O-16`；所有写事务 | `tests/test_sqlite_chapter_repository.py::SQLiteChapterRepositoryTests.test_runtime_pragmas_and_minimum_version`；`tests/test_sqlite_chapter_repository.py::SQLiteChapterRepositoryTests.test_begin_immediate_serializes_competing_saves` | `python3 -m unittest discover -s tests -p 'test_sqlite_chapter_repository.py' -v` | 真实文件数据库报告版本 `>=3.35.0`、WAL/FULL/foreign_keys/busy_timeout；两连接只允许一个匹配修订号写入，锁在提交/回滚后释放。 |

## 验收类型与证据

| 验收项 | 验收类型 | 执行者 | 环境与步骤 | 可观察通过条件 | 留存证据 |
| --- | --- | --- | --- | --- | --- |
| 创建作品、直接进入空白第一章、保存并刷新 | 关键 E2E | CI 中的 Playwright 执行；实现工程师触发，发布负责人核对 | 使用发布候选构建、真实临时 SQLite 文件和 Chromium；执行 `npx playwright test tests/e2e/direct-chapter-writing.spec.mjs --project=chromium --grep 'create work opens blank first chapter and survives reload'` | 创建后 URL 直接为第一章编辑器且无设定/大纲步骤；初始正文空、修订号 0；输入保存后刷新仍为已保存内容 | Playwright HTML/JUnit 报告、网络 trace、创建后与刷新后截图、脱敏服务器结果日志 |
| 两会话竞争保存、冲突双版本恢复并继续 | 关键 E2E | CI 中的 Playwright 执行；实现工程师触发，发布负责人核对 | 同一发布候选环境开启两个独立浏览器上下文编辑同章；执行 `npx playwright test tests/e2e/direct-chapter-writing.spec.mjs --project=chromium --grep 'stale save preserves both versions and resumes after explicit merge'` | 先保存版本不被 stale 请求覆盖；后者同时看到服务器版和本地版；显式合并后保存成功，刷新为合并内容 | Playwright 报告、双上下文 trace、冲突与合并后截图、修订号审计日志 |
| 自然找到直接写作入口 | 目标用户人工验收 | 5 名未参与实现的长篇小说写作者执行；产品负责人主持并作通过判断 | 发布候选环境；只给任务“创建一部新小说并开始写第一章”，不提示导航路径 | 至少 4/5 在 60 秒内无需主持人提示进入空白第一章，且无人被迫完成设定集或大纲 | 去标识化任务路径、用时、主持记录和入口/编辑器截图 |
| 理解冲突并恢复继续编辑 | 目标用户人工验收 | 同一类 5 名目标写作者执行；产品负责人主持并作通过判断 | 发布候选环境注入可重复的双标签页冲突；要求解释提示、保留两段指定文字并完成保存 | 至少 4/5 无提示说清较新服务器内容未被覆盖，找到两版内容，完成显式合并并在刷新后看到两段指定文字；任何不可恢复丢失均判失败 | 去标识化口述摘要、前后文本哈希/修订号、任务记录和冲突/完成截图 |
| 写作辅助内容可用且连贯 | 目标用户人工验收 | 5 名长篇小说写作者执行；产品负责人管理发布候选配置并作通过判断 | 使用发布候选实际供应商配置；每人对自己的测试章节完成一次续写和一次改写，查看结果并选择是否插入 | 至少 4/5 对“与上下文连贯”和“可用于继续写作”两项均给出 5 分制不低于 4 分；参与者能分辨预览与已插入正文；任何部分流自动入文均判失败 | 去标识化评分、任务笔记、受控访问的提示/输出样本、配置标识和插入前后截图 |
| 编辑器视觉层级与专注感 | 目标用户人工验收 | 同一类 5 名目标写作者执行；产品负责人作通过判断 | 发布候选桌面基准视口 1440×900；打开第一章并连续写作 10 分钟，然后定位保存状态和冲突入口 | 至少 4/5 在 5 秒内指出正文主编辑区和保存状态，并对“视觉层级清楚”“有助于专注”两项均给出 5 分制不低于 4 分 | 去标识化观察记录、评分汇总、基准视口截图；仅在参与者同意时保存录屏 |

关键 E2E 只覆盖创建到持久化和冲突恢复两个跨层闭环。结果矩阵的其他分支由单元、API、组件和真实 SQLite 集成测试覆盖；人工验收不能替代这些自动化回归，E2E 也不能替代目标写作者的体验判断。

## 测试与文档

### 自动化范围

- 运行完整 Python 回归：`python3 -m unittest discover -s tests -v`，必须包含并保持现有 `OrderTests.test_new_order_is_created` 通过。
- API 与服务测试覆盖创建、保存、幂等、稳定错误码、所有权和提交核对；命令及精确测试名见保证追踪表。
- SQLite 集成测试使用真实临时文件和两个独立连接，覆盖版本/PRAGMA、`BEGIN IMMEDIATE`、busy、回滚和提交后三分支；mock 只可补充，不能替代。
- 浏览器状态组件测试运行 `node --test tests/component/direct-writing-editor.test.mjs tests/component/assistant-panel.test.mjs`，覆盖草稿竞态、冲突、恢复和辅助隔离。
- 仅运行验收表列出的两个 Chromium E2E 场景作为发布关键浏览器集合；其他输入/错误分支保留在低层测试。
- 产品负责人按验收表组织目标写作者人工验收。参与者判断、阈值与证据缺一项即对应体验标准未完成。

### 文档影响

- 更新 `README.md`：记录直接写作入口、开发/测试命令、SQLite 最低版本和发布候选验收入口。
- 新增 `docs/operations/direct-chapter-writing.md`：记录迁移、PRAGMA 启动证据、备份单元、busy/提交未知核对和辅助降级操作。
- 新增 `docs/user-guide/direct-chapter-writing.md`：说明本地草稿与服务器保存的区别、冲突双版本恢复、明确放弃流程和辅助结果插入边界。
- 发布检查记录必须引用自动化报告和去标识化人工验收证据位置，不把正文或辅助内容复制到普通日志或公开工件。

## 验收标准

| 完成标准 | 验证范围 | 执行者 | 必须留存的完成证据 |
| --- | --- | --- | --- |
| `AC-01`：作品和空白第一章原子创建，浏览器直接进入编辑器，保存后刷新内容仍在。 | `G-01`, `G-02`, `G-12` 的单元/API/真实 SQLite 测试，以及“创建并刷新”关键 E2E。 | 实现工程师运行低层测试；CI 运行 E2E；发布负责人核对。 | 完整测试日志、SQLite 版本/PRAGMA 输出、Playwright 报告/trace 和创建/刷新截图。 |
| `AC-02`：版本保存、幂等、无变化、busy、回滚和提交核对满足矩阵，任何 stale 保存都不覆盖较新正文。 | `G-02`–`G-07`, `G-12` 的 API/集成测试，以及“冲突恢复”关键 E2E。 | 实现工程师和 CI 执行；发布负责人核对结果码、修订号和数据库断言。 | 测试报告、故障注入日志、回执/修订号脱敏审计、冲突 E2E trace 与截图。 |
| `AC-03`：本地草稿只有在匹配服务器成功后清除；刷新、冲突、配额失败和未知保存均保留明确恢复路径。 | `G-08`, `G-11` 的组件测试、冲突 E2E 和目标用户冲突任务。 | CI 执行自动化；5 名目标写作者执行人工任务；产品负责人判定阈值。 | Node 测试报告、Playwright 工件、去标识化任务记录、前后哈希/修订号和恢复截图。 |
| `AC-04`：辅助所有终态与正文隔离，只有完整结果经明确插入进入草稿，实际内容达到可用与连贯阈值。 | `G-09`–`G-11` 的 API/组件测试，以及目标用户辅助内容任务。 | 实现工程师/CI 验证技术隔离；5 名目标写作者评分；产品负责人判定。 | API/组件报告、供应商发布候选配置标识、去标识化评分和受控样本、插入前后截图。 |
| `AC-05`：写作入口可发现，编辑器视觉主次和专注体验达到阈值。 | 验收表中的入口任务和 10 分钟视觉体验任务；自动化只证明路由与控件可操作，不替代体验判断。 | 5 名未参与实现的目标写作者执行；产品负责人主持、汇总并批准或拒绝。 | 参与者级去标识化路径/用时/评分、主持记录及基准视口截图。 |
| `AC-06`：主要回归层、两个最小关键 E2E、操作与用户文档全部完成且无遗漏保证。 | 完整 `unittest`、Node 组件测试、两条 Playwright 场景、`G-01`–`G-12` 双向追踪和三份文档检查。 | 实现工程师执行并汇总；独立实现审查者在后续获授权阶段检查；发布负责人核验证据齐全。 | 全量测试报告、保证追踪清单、文档 diff、发布检查记录；任一保证无自动化证据或任一人工阈值无证据均不完成。 |
```

需求文档：/workspace/fixture/docs/requirements/2026-07-19-direct-chapter-writing.md
需求主题：direct-chapter-writing
需求范围：功能
需求理解置信度：98
需求理解确认：已确认
需求文档用户批准：已批准
需求文档独立评审：已通过
技术规格门禁：已开放
技术规格：/workspace/fixture/docs/specs/2026-07-19-direct-chapter-writing-design.md
技术规格用户批准：待批准
技术规格独立评审：待评审
实施计划：/workspace/fixture/docs/plans/2026-07-19-direct-chapter-writing.md
计划评审状态：未通过
实施门禁：未开放