已创建唯一草案：[2026-07-19-direct-chapter-writing-design.md](/workspace/fixture/docs/specs/2026-07-19-direct-chapter-writing-design.md)。

PRD 已重新验证，作者自审确认 38 个结果与 16 个保证双向对应；`git diff --check` 和现有 1 项测试通过。未创建 plan、未实施代码、未派发 reviewer、未操作 task/thread。由于本次明确没有独立 reviewer，规格仍待独立评审，也尚未请求用户批准。

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

- 写作者从作品列表执行“创建作品并开始写作”后，系统原子地创建作品和空白第一章，并直接导航到该章编辑器；正文获得输入焦点，不插入设定集、大纲或正文模板。
- 编辑器采用“先保护本地草稿、再提交服务端”的保存流程。服务端使用章节修订号进行比较并交换；任何过期保存都返回冲突，不能覆盖较新的服务端正文。
- 冲突、网络中断或提交结果未知时，写作者的本地正文保持可恢复、可继续编辑；客户端能够核对服务端提交状态，再安全重试。
- 在不削弱正文视觉主次和专注感的前提下，提供可折叠、版本化的起步写作辅助内容。
- 在上线前用自动化证据和目标写作者的主持式验收证据共同确认直接进入、冲突恢复、入口可发现性、提示可理解性、辅助内容质量及编辑器视觉层级。

## 非目标

- 不要求写作者创建或补全设定集、大纲、人物卡或世界观资料。
- 不新增大纲、设定集、章节编排、协作编辑、实时共同编辑、历史版本浏览或自动合并能力。
- 不接入生成式模型或外部写作辅助服务；本次辅助内容来自仓库内的版本化内容清单。
- 不定义新的身份认证机制。接口消费既有请求身份上下文；缺少身份时拒绝请求。
- 不改变现有 `src/orders.py` 的订单模型及其测试，也不在本次功能中迁移既有写作数据；当前仓库没有可迁移的写作实体证据。
- 不声明完整的浏览器兼容政策；本功能的发布关键路径至少在 CI 固定版本的 Chromium 中验收。

## 当前证据

- 已批准需求为 `docs/requirements/2026-07-19-direct-chapter-writing.md`，其 `topic` 为 `direct-chapter-writing`、`scope_type` 为 `feature`，需求理解置信度为 98，需求理解确认、独立评审和用户批准均已通过。技能检查器返回 `status: approved` 和 `specification_gate: open`。
- 根目录 `AGENTS.md` 要求规格经独立评审且由用户明确批准后才能生成计划；本草案保持“技术规格独立评审: 待评审”和“技术规格用户批准: 待批准”。
- `README.md` 将产品定义为面向长篇小说写作者的浏览器应用，带小型 API 和本地持久化层；单元、组件和 API 测试是主要回归套件，浏览器 E2E 只覆盖少量跨层发布关键路径。产品负责人能够招募目标写作者，并保留任务记录、参与者判断和截图作为验收证据。
- 当前仓库只包含 `src/orders.py` 和 `tests/test_orders.py` 的最小订单示例，没有写作 UI、写作 API、写作数据模型、身份实现、依赖清单或既有写作测试可复用。`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` 当前通过 1 项测试。
- 当前执行环境是 Python 3.9.6，标准库 `sqlite3` 驱动版本为 2.6.0，运行时 SQLite 为 3.51.0。该探测结果是本规格选择 SQLite 事务语义的当前依据；实现后的启动检查和 CI 证据必须再次记录实际 `sqlite_version()`，不能只依赖本次探测。
- 工程风险等级为跨浏览器 UI、API、本地草稿和服务端并发持久化的高风险 `feature`；冲突、事务、未知提交状态和草稿恢复都必须有自动化覆盖。

## 行为与边界

### 创建并进入第一章

1. 作品列表的主操作使用可访问名称“创建作品并开始写作”。点击后客户端生成 UUID 格式的 `Idempotency-Key`，向 `POST /api/works` 提交可选标题；空标题由服务端规范化为“未命名作品”。
2. 服务端在一个事务中创建作品和序号为 1 的第一章。第一章标题为“第一章”，正文严格为空字符串，修订号为 1。
3. 成功响应必须同时返回作品、第一章和规范化的 `editor_url`。客户端使用历史替换导航到 `/works/{work_id}/chapters/{chapter_id}/edit`，避免“返回”再次提交创建命令。
4. 编辑器加载后，正文编辑区是主视觉区域并取得输入焦点。辅助内容只能出现在可折叠的次级区域；占位提示不是正文，不能随保存写入。
5. 创建响应丢失时，客户端不能生成第二个操作标识重新创建。它先用原操作标识核对；确认未应用后才以同一操作标识重试原命令。

### 编辑、保存与冲突恢复

1. 章节读取结果包含当前 `revision` 和与之对应的强 ETag。客户端编辑会进入 `dirty` 状态。
2. 每次远端保存前，`SaveCoordinator` 必须先在 IndexedDB 的 `drafts` 对象仓中完成一个 `readwrite` 事务，保存正文、基础修订号和本次操作标识。只有本地事务完成后才能发送远端 `PUT`。
3. 远端保存携带 `If-Match` 和新的 UUID `Idempotency-Key`。服务端只在基础修订号等于当前修订号时更新正文并把修订号加 1；比较、更新和操作回执在同一 SQLite 事务中完成。
4. 如果正文与当前服务端正文相同，服务端记录幂等回执但不增加修订号，并返回 `no_change: true`。
5. 如果基础修订号过期，服务端返回 `409 revision_conflict` 及当前服务端快照，不修改章节。客户端保留 IndexedDB 草稿，以本地正文作为可编辑主版本，显示服务器快照和明确提示：“检测到另一处保存；你的内容已保留，本次未覆盖服务器版本。”
6. 冲突界面提供“继续编辑我的内容”和“查看服务器版本”；写作者可将服务器变化人工合并进本地正文，再以最新修订号保存。系统不提供绕过修订检查的强制覆盖命令。
7. “舍弃本地草稿”是次级危险操作，必须二次确认；取消确认不改变草稿。未明确舍弃或未成功保存前，冲突草稿不得删除。
8. 远端成功后，客户端把本地记录标记为 `synced`。如果该本地标记操作失败，正文仍保留，客户端显示可恢复警告，并用原操作标识核对后再决定是否重试；不得把已成功的远端保存当作失败重新创建新操作。
9. HTTP 取消、连接中断、超时或 SQLite 提交结果无法判定时，状态为 `unknown`。客户端冻结该操作标识、保留草稿并调用核对接口；在得到 `applied` 或 `not_applied` 前，不宣称“已保存”或“未保存”。

### 写作辅助与视觉层级

- `context=blank-first-chapter` 的写作辅助是仓库内版本化的有序内容清单，至少包含“场景目标”“立即发生的动作”“下一拍变化”三个短块；块 ID 和版本稳定，正文内容不发送给外部服务。
- 辅助区域默认收起或以次级宽度呈现，不得遮盖正文、抢占初始焦点或阻止保存。读取辅助内容失败时，编辑器和保存仍可用，区域显示可重试的非阻塞提示。
- 保存状态必须以文本加图形表达 `dirty`、`protecting_local`、`saving_remote`、`saved`、`conflict`、`unknown` 和 `local_error`，不能只靠颜色。
- 冲突提示使用可被辅助技术立即感知的状态区域；焦点保留在可恢复的本地正文，除非写作者主动进入服务器快照区域。

### 权限和内容边界

- 所有作品、章节、操作回执和核对都按请求上下文中的 `writer_id` 隔离。未认证返回 401；访问其他写作者资源按不存在处理并返回 404，避免枚举。
- 正文、服务器冲突快照和本地草稿不得进入 URL、结构化日志、分析事件或错误追踪正文。日志只允许记录资源 ID、操作 ID、修订号、内容字节数、结果码和耗时。
- IndexedDB 记录以 `writer_id + chapter_id` 命名空间隔离。退出登录时由既有会话生命周期调用本功能的 `clearWriterDrafts(writer_id)`；若清理失败，退出仍继续，但必须记录不含正文的本地警告。其他身份只能查询自己的命名空间；原写作者下次登录时可以恢复或再次确认清理残留草稿。

## 组件与控制流

| 组件 | 职责 | 消费 | 产出 |
| --- | --- | --- | --- |
| `WorkListView` | 呈现唯一主创建入口并防止按钮重复提交 | 请求身份、创建状态 | `CreateWork` 命令 |
| `CreateWorkController` | 生成并固定操作标识、调用 API、核对未知结果、成功后替换导航 | `WorkApi` | 编辑器 URL 或可操作错误 |
| `ChapterEditor` | 管理正文、焦点、视觉层级和保存状态 | 章节快照、辅助内容、`SaveCoordinator` 状态 | 编辑意图、保存意图 |
| `SaveCoordinator` | 串联本地保护、远端比较并交换、未知结果核对和同步标记 | `DraftStore`、`ChapterApi`、`OperationApi` | `saved`、`conflict`、`unknown` 或错误状态 |
| `ConflictPanel` | 同时呈现本地可编辑版本与只读服务器快照，支持人工合并和显式舍弃 | 冲突结果、`DraftStore` | 新的保存意图或确认后的舍弃命令 |
| `WritingAidPanel` | 读取并呈现版本化起步内容，失败时非阻塞降级 | `WritingAidApi` | 辅助块或重试提示 |
| `WritingApplicationService` | 校验身份与输入，编排作品创建、章节保存和操作核对 | 请求 DTO、仓储 | 领域结果 DTO |
| `SQLiteWritingRepository` | 实现原子创建、修订比较、幂等回执、核对和迁移 | SQLite 3.35+ | 提交结果或规范化持久化错误 |
| `DraftStore` | 用 IndexedDB 原子保存、标记和显式删除草稿 | 编辑器正文和状态 | 本地持久化结果 |
| `WritingAidRepository` | 从仓库内只读清单按 locale/context 返回有序辅助块 | 版本化内容文件 | 辅助内容 DTO |

创建控制流：`WorkListView → CreateWorkController → POST /api/works → BEGIN IMMEDIATE → works + chapters + operation_receipts → COMMIT → replace(editor_url) → ChapterEditor`。

保存控制流：`ChapterEditor → DraftStore.put(dirty) → PUT /api/chapters/{id} → BEGIN IMMEDIATE → operation receipt check → chapter revision compare → chapter update/no-op + receipt → COMMIT → DraftStore.markSynced`。任何远端冲突都在 SQLite 回滚后进入 `ConflictPanel`；任何提交未知都转入操作核对，不直接重放为新操作。

## API 与技术接口

### 通用约定

- 请求身份由 `RequestContext.writer_id` 提供；未提供时返回 401。
- 所有改变服务端状态的请求都要求 UUID `Idempotency-Key`。服务端计算规范化命令和负载的 SHA-256 `request_hash`；同一写作者、同一 key、同一 hash 返回原结果，同一 key 不同 hash 返回 `409 idempotency_key_reused`。
- JSON 错误统一包含 `error.code: string`、`error.message: string`、`error.retryable: boolean` 和 `operation_id: UUID|null`；例如 `{"error":{"code":"revision_conflict","message":"检测到较新版本","retryable":false},"operation_id":"550e8400-e29b-41d4-a716-446655440000"}`。错误 `message` 可本地化，客户端分支只依赖 `code` 和字段。
- 章节 ETag 形式固定为 `"chapter:{chapter_id}:revision:{revision}"`。保存请求必须携带 `If-Match`；响应同时返回数值 `revision` 和 ETag。
- 正文必须是 UTF-8 字符串，编码后不超过 2 MiB；标题去除首尾空白后不超过 120 个 Unicode 码点。未知 JSON 字段返回 422，避免客户端拼写错误被忽略。

### HTTP 接口

| 接口 | 输入 | 成功输出 | 失败边界 |
| --- | --- | --- | --- |
| `POST /api/works` | header `Idempotency-Key`; body `{"title": string|null}` | 201；`work`、空白 `first_chapter`、`editor_url`、`operation_id`、`replayed:false` | 401、409 key 复用、422、503 busy/unknown、500 已确认回滚 |
| `GET /api/chapters/{chapter_id}` | 路径 ID 和身份 | 200；`id`、`work_id`、`title`、`content`、`revision`、`updated_at`，附 ETag | 401、404、500 |
| `PUT /api/chapters/{chapter_id}` | headers `Idempotency-Key`, `If-Match`; body `{"content": string}` | 200；`chapter_id`、`revision`、`updated_at`、`no_change`、`operation_id`、`replayed`，附新 ETag | 401、404、409 revision/key 冲突、422、503 busy/unknown、500 已确认回滚 |
| `POST /api/operations/{operation_id}/reconcile` | 身份；不接受正文 | 200；`state: applied` 和最小结果，或 `state: not_applied` | 401、409 所属命令不匹配、503 无法取得排他写入时状态仍未知、500 |
| `GET /api/writing-assistance?context=blank-first-chapter&locale=zh-CN` | context、locale | 200；`version`、`context`、有序 `blocks[{id,title,body}]` | 404 未支持 context/locale、500；不影响编辑保存 |

`reconcile` 虽不改变业务实体，但必须使用 `BEGIN IMMEDIATE` 取得写入保留锁后读取回执：取得锁后，不可能仍有同一数据库的未完成写事务。存在回执即确认已应用；不存在回执即确认该操作未提交。若取锁超时，只能返回 `operation_state_unknown`。

### 浏览器本地接口

| 接口 | 契约 |
| --- | --- |
| `DraftStore.put(draft)` | 在单个 IndexedDB `readwrite` 事务中按 `writer_id + chapter_id` 写入 `content`、`base_revision`、`operation_id`、`state`、`saved_at`；事务 `complete` 才算成功。 |
| `DraftStore.markSynced(chapter_id, operation_id, revision)` | 仅当记录中的操作 ID 匹配时改为 `synced` 并记录服务端修订号；不匹配返回状态失败，不覆盖较新的草稿。 |
| `DraftStore.discard(chapter_id, expected_operation_id)` | 仅在 UI 二次确认且操作 ID 匹配时删除；取消确认不调用接口。 |
| `DraftStore.clearWriterDrafts(writer_id)` | 会话退出钩子按写作者命名空间删除；失败不能把正文写入日志，其他身份不得枚举该命名空间，原写作者下次登录时获得恢复或再次清理选择。 |

## 命令结果与失败矩阵

| 结果 ID | 命令或异步完成阶段 | 前置条件 | 结果类型 | 客户端可见结果 | 事务、回滚与副作用 | 调用方动作 | 保证 ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `O-01` | `POST /api/works` | 身份、有效输入、新 key | 成功 | 201，空白第一章、revision 1、`editor_url` | 单事务提交作品、章节、回执 | 替换导航到编辑器 | `G-01`, `G-02` |
| `O-02` | `POST /api/works` | 相同 key 和相同 hash 已提交 | 无变化 | 200，原结果，`replayed:true` | 不新增作品或章节，不改修订 | 使用原 `editor_url` | `G-06` |
| `O-03` | `POST /api/works` | 标题或 JSON 无效 | 校验 | 422 `validation_error` | 事务开始前拒绝，无副作用 | 修正输入，使用原 key 重试 | `G-11` |
| `O-04` | `POST /api/works` | 无请求身份 | 状态 | 401 `authentication_required` | 事务开始前拒绝，无副作用 | 重新认证后发起新命令 | `G-03` |
| `O-05` | `POST /api/works` | key 已用于不同 hash | 冲突 | 409 `idempotency_key_reused` | 不执行创建，不改原回执 | 停止并生成新的明确用户命令 | `G-06` |
| `O-06` | `POST /api/works` | 250ms 内无法取得写入锁 | 持久化 | 503 `persistence_busy`, `retryable:true` | 未取得写锁或已回滚，无副作用 | 退避后以同一 key 重试 | `G-08` |
| `O-07` | `POST /api/works` | 插入或提交失败且确认回滚 | 持久化 | 500 `persistence_error`, `retryable:true` | 作品、章节、回执全部不存在 | 以同一 key 重试；连续失败则停止 | `G-08` |
| `O-08` | `POST /api/works` 完成阶段 | HTTP 已发出后客户端取消请求 | 取消 | 客户端无响应 | 服务器可能完整提交或完整回滚；不存在部分业务提交 | 保留 key，先调用核对，禁止新建 key | `G-07`, `G-08` |
| `O-35` | `POST /api/works` 完成阶段 | 连接丢失或客户端等待超时 | 超时 | 客户端无响应 | 服务器可能完整提交或完整回滚；不存在部分业务提交 | 保留 key，先调用核对，禁止新建 key | `G-07`, `G-08` |
| `O-36` | `POST /api/works` 完成阶段 | 服务端无法证明 COMMIT 或 ROLLBACK 结果 | 未知 | 503 `commit_state_unknown` | 持久化状态未知，但业务行和回执仍满足同事务原子性 | 保留 key，先调用核对，禁止新建 key | `G-07`, `G-08` |
| `O-09` | `DraftStore.put` | 有可用 IndexedDB 配额 | 成功 | 状态进入 `saving_remote` | 本地草稿事务提交，远端尚未调用 | 发送远端保存 | `G-05`, `G-15` |
| `O-10` | `DraftStore.put` | 内容、revision、operation_id 与现有记录一致 | 无变化 | 状态仍可进入 `saving_remote` | IndexedDB 不产生语义变化 | 发送同一远端保存 | `G-05` |
| `O-11` | `DraftStore.put` | 配额、权限、事务中止或浏览器存储错误 | 本地持久化 | `local_error`，明确“尚未发送到服务器” | 本地事务中止；远端命令未调用；内存正文保留 | 释放空间/复制正文后重试本地保护 | `G-05`, `G-15` |
| `O-12` | `PUT /api/chapters/{id}` | 身份、有效正文、当前 ETag、新 key | 成功 | 200，新 revision，`no_change:false` | 章节更新和回执同事务提交；本地草稿仍在 | 标记本地草稿 synced | `G-04`, `G-05` |
| `O-13` | `PUT /api/chapters/{id}` | ETag 当前且正文 hash 未变 | 无变化 | 200，revision 不变，`no_change:true` | 只提交幂等回执，不改章节正文或 revision | 标记本地草稿 synced | `G-04`, `G-05`, `G-06` |
| `O-14` | `PUT /api/chapters/{id}` | 相同 key/hash 已提交 | 无变化 | 200，原结果，`replayed:true` | 不再次更新章节 | 按原结果标记 synced | `G-05`, `G-06`, `G-09` |
| `O-15` | `PUT /api/chapters/{id}` | 缺少/非法 ETag、正文超限或 JSON 无效 | 校验 | 422 `validation_error` | 事务开始前拒绝，章节和回执不变 | 修正请求；正文草稿继续保留 | `G-11`, `G-05` |
| `O-16` | `PUT /api/chapters/{id}` | 章节不存在或不属于当前写作者 | 状态 | 404 `chapter_not_found` | 回滚或事务前拒绝，无副作用 | 停止保存并保留本地草稿 | `G-03`, `G-05` |
| `O-17` | `PUT /api/chapters/{id}` | ETag 修订号落后 | 冲突 | 409 `revision_conflict`，返回当前服务端快照 | 回滚，不修改章节或回执；IndexedDB 草稿不变 | 展示冲突面板，人工合并后用最新 revision 新建保存操作 | `G-04`, `G-05`, `G-13` |
| `O-18` | `PUT /api/chapters/{id}` | key 已用于不同 hash/命令 | 冲突 | 409 `idempotency_key_reused` | 不执行章节更新 | 停止该请求；保留草稿并创建新的明确保存操作 | `G-06`, `G-05` |
| `O-19` | `PUT /api/chapters/{id}` | 250ms 内无法取得写入锁 | 持久化 | 503 `persistence_busy`, `retryable:true` | 无章节或回执变化 | 退避后以同一 key 和正文重试 | `G-08`, `G-05` |
| `O-20` | `PUT /api/chapters/{id}` | 更新/回执写入失败且确认回滚 | 持久化 | 500 `persistence_error`, `retryable:true` | 章节与回执一并回滚 | 保留草稿，以同一 key 重试 | `G-08`, `G-05` |
| `O-21` | `PUT /api/chapters/{id}` 完成阶段 | HTTP 已发出后客户端取消请求 | 取消 | 客户端无响应 | 服务器可能完整提交或完整回滚；本地草稿保留 | 冻结 key 并核对，禁止先生成新保存操作 | `G-07`, `G-05`, `G-08` |
| `O-37` | `PUT /api/chapters/{id}` 完成阶段 | 连接丢失或客户端等待超时 | 超时 | 客户端无响应 | 服务器可能完整提交或完整回滚；本地草稿保留 | 冻结 key 并核对，禁止先生成新保存操作 | `G-07`, `G-05`, `G-08` |
| `O-38` | `PUT /api/chapters/{id}` 完成阶段 | 服务端无法证明 COMMIT 或 ROLLBACK 结果 | 未知 | 503 `commit_state_unknown` | 持久化状态未知；本地草稿保留，业务行与回执仍原子 | 冻结 key 并核对，禁止先生成新保存操作 | `G-07`, `G-05`, `G-08` |
| `O-22` | `POST /api/operations/{id}/reconcile` | 取得写锁并找到回执 | 核对成功 | 200 `state:applied`，返回最小原结果 | 不改业务实体；读事务结束 | 按结果导航或标记 synced | `G-07`, `G-09` |
| `O-23` | `POST /api/operations/{id}/reconcile` | 取得写锁且无回执 | 确认未应用 | 200 `state:not_applied` | 锁证明无在途写事务；不产生副作用 | 以相同 key 重试原命令 | `G-07` |
| `O-24` | `POST /api/operations/{id}/reconcile` | 无法取得锁、超时或数据库 I/O 不确定 | 未知 | 503 `operation_state_unknown` | 不声称存在或不存在提交 | 保留草稿和 key，退避后再次核对 | `G-07`, `G-08` |
| `O-25` | `DraftStore.markSynced` | 本地 operation_id 匹配远端结果 | 成功 | 状态 `saved` | IndexedDB 记录改为 synced 并记录 revision | 继续编辑 | `G-09` |
| `O-26` | `DraftStore.markSynced` | 本地事务失败或 operation_id 不匹配 | 本地持久化 | 显示“服务器已保存，本地状态待核对” | 不删除草稿；远端提交保持有效 | 用原 key 核对，再重试标记；不重发新保存 | `G-09`, `G-05` |
| `O-27` | `DraftStore.discard` | 写作者二次确认且 operation_id 匹配 | 成功 | 草稿移除，编辑器载入明确选择的服务器快照 | 只删除对应本地草稿，不改服务器 | 继续编辑服务器版本 | `G-05` |
| `O-28` | 舍弃确认 | 写作者取消确认 | 取消/无变化 | 冲突面板与本地正文保持 | 不调用 IndexedDB 删除 | 继续编辑或合并 | `G-05`, `G-13` |
| `O-29` | `DraftStore.discard` | 删除事务失败 | 本地持久化 | 显示舍弃失败，本地正文仍可见 | 删除回滚，服务器不变 | 保留正文并允许重试 | `G-05` |
| `O-33` | `DraftStore.clearWriterDrafts` | 退出登录且 IndexedDB 删除事务完成 | 成功 | 退出流程继续 | 只删除该 writer_id 命名空间的本地草稿，服务器不变 | 完成退出 | `G-16` |
| `O-34` | `DraftStore.clearWriterDrafts` | 删除事务中止、超时或存储不可用 | 本地持久化 | 退出流程继续并显示不含正文的本地警告 | 草稿可能保留，但其他 writer_id 无法读取；服务器不变 | 其他身份继续隔离；原写作者下次登录时恢复或再次确认清理 | `G-16` |
| `O-30` | 数据库 schema v1 迁移完成 | `user_version=0` 且取得独占锁 | 成功 | 应用启动就绪 | 单事务创建三表、索引并设置 `user_version=1` | 启动服务 | `G-10` |
| `O-31` | 数据库 schema v1 迁移完成 | DDL、锁或提交失败 | 持久化 | 应用启动失败，健康检查不就绪 | DDL 和 `user_version` 一并回滚 | 修复存储原因后重新启动 | `G-10`, `G-08` |
| `O-32` | 数据库 schema 检查 | `user_version` 不是 0 或 1 | 状态/无变化 | 应用启动失败 `unsupported_schema_version` | 不执行降级或未知迁移，不改数据库 | 停止并执行人工版本处置 | `G-10` |

本功能没有远端生成服务、消息队列或后台异步发布阶段，因此不存在外部依赖成功、取消或异步发布结果；辅助内容读取是只读接口，其失败按非阻塞降级处理。HTTP 生命周期中的取消、超时和服务端未知提交分别由 `O-08`/`O-21`、`O-35`/`O-37`、`O-36`/`O-38` 覆盖，并全部进入 `O-22`—`O-24` 的核对分支。

## 数据模型与实体关系

### SQLite schema v1

| 实体 | 关键字段 | 关系与不变量 |
| --- | --- | --- |
| `works` | `id TEXT PK`, `owner_id TEXT NOT NULL`, `title TEXT NOT NULL`, `created_at TEXT NOT NULL` | 一个写作者拥有多个作品；所有读取带 `owner_id` 条件。 |
| `chapters` | `id TEXT PK`, `work_id TEXT FK`, `ordinal INTEGER`, `title TEXT`, `content TEXT`, `content_hash TEXT`, `revision INTEGER`, `updated_at TEXT` | 一个作品拥有多个章节；本次只创建 ordinal 1。`UNIQUE(work_id, ordinal)`；`revision >= 1`；`content_hash` 是规范 UTF-8 正文 SHA-256。 |
| `operation_receipts` | `owner_id TEXT`, `operation_id TEXT`, `command_type TEXT`, `request_hash TEXT`, `resource_id TEXT`, `result_code TEXT`, `result_revision INTEGER NULL`, `result_metadata TEXT`, `created_at TEXT` | 复合主键 `(owner_id, operation_id)`；`result_metadata` 只允许保存重放所需的作品/章节 ID、时间、revision 和 editor URL，不复制标题或正文；回执和业务更新同事务提交。 |

- `works.id`、`chapters.id` 和操作 ID 均使用服务端校验过的 UUID 文本。时间以 UTC ISO 8601 保存。
- 删除作品/章节不在本次接口范围内，因此不定义级联删除命令；外键仍设为 `ON DELETE CASCADE`，供未来显式删除事务使用。
- 操作回执本次不自动清理，避免增加未设计的异步持久化路径；回执不含正文。后续保留策略需另行规格化。

### IndexedDB schema v1

- 数据库名 `direct-chapter-writing`，版本 1，对象仓 `drafts`，主键 `[writer_id, chapter_id]`，索引 `by_writer`。
- 值包含 `content`、`base_revision`、`operation_id`、`state`（`dirty|conflicted|synced`）、`server_revision|null`、`saved_at`。正文只存在同源浏览器存储中。
- 不进行“读取旧值后另开事务写入”的升级；每个 `put`、`markSynced` 或 `discard` 在一个 `readwrite` 事务内读取、核对 operation_id 并写入/删除，事务完成事件是唯一成功边界。

### 写作辅助清单

- 只读清单以 `version`、`locale`、`context` 和有序 `blocks` 表示；块 ID 在同一版本内唯一。
- 清单属于发布资产，不存入 SQLite 或 IndexedDB，不读取正文，也不触发持久化或外部调用。

## 数据库事务与锁语义

- 服务端使用 Python 标准库 `sqlite3` 事务层和 SQLite，最低运行版本 3.35.0；当前可验证运行时为 SQLite 3.51.0。服务启动必须执行 `SELECT sqlite_version()` 并在低于最低版本时拒绝就绪，CI 报告实际值。
- 每个连接设置 `PRAGMA journal_mode=WAL`、`PRAGMA synchronous=FULL`、`PRAGMA foreign_keys=ON`、`PRAGMA busy_timeout=250`。应用显式管理事务，连接 `isolation_level=None`。
- 所有写命令先执行 `BEGIN IMMEDIATE`，在任何业务读取前取得数据库 RESERVED 写锁；随后依次读取操作回执、读取目标作品/章节、写业务行、写回执并 `COMMIT`。因此不存在 deferred transaction 的读锁升级写锁窗口。
- 唯一锁顺序是“SQLite 数据库写保留锁 → 表/页访问”；不叠加进程内互斥锁或第二数据库事务。写锁从 `BEGIN IMMEDIATE` 成功保持到 `COMMIT` 或 `ROLLBACK` 返回。WAL 中读请求使用各自语句/事务快照，不阻塞既有写者。
- 章节保存取得写锁后先检查回执，再读取当前 revision。若 revision 不匹配，立即 `ROLLBACK` 并返回冲突；若匹配，用 `UPDATE ... WHERE id=? AND work_id IN (...owner...) AND revision=?` 再检查影响行数，随后写回执。影响行数不是 1 时回滚并分类为冲突或不存在，不能继续提交。
- SQLite 在单数据库、单写锁顺序下不产生应用层锁环；`SQLITE_BUSY` 或 250ms 超时统一为 `persistence_busy`。服务端不做隐式事务重试；客户端拥有退避重试责任，并必须复用操作 ID。
- 任一 SQL 错误在提交前触发 `ROLLBACK`。只有确认回滚成功时才返回 `persistence_error`；连接中断、I/O 错误或提交返回值不能证明提交/回滚时返回 `commit_state_unknown`，调用方必须核对。
- 核对命令也执行 `BEGIN IMMEDIATE` 后读取回执，再 `ROLLBACK` 结束只读核对事务。取得写锁是“无回执即可确认未应用”的前提；普通快照读取不能作此结论。
- schema v1 迁移在应用接受流量前以 `BEGIN EXCLUSIVE` 执行，先读 `PRAGMA user_version`，只允许 0→1；三张表、索引和 `user_version=1` 同事务提交。失败回滚且健康检查保持未就绪，不进行部分启动。
- IndexedDB 不与 SQLite 构成分布式事务。本地草稿先提交、远端后提交是有意的一致性顺序：允许远端成功后本地仍显示待核对，但不允许远端冲突时没有已提交的本地恢复副本。

## 状态转换、迁移边界与一致性

| 当前状态 | 事件 | 下一状态 | 一致性要求 |
| --- | --- | --- | --- |
| `editing/saved` | 正文变化 | `dirty` | 只改变内存；服务器不变。 |
| `dirty/conflict` | 用户保存 | `protecting_local` | 固定本次 operation_id 和 base revision。 |
| `protecting_local` | IndexedDB 提交 | `saving_remote` | 本地可恢复副本已存在，才可发 HTTP。 |
| `protecting_local` | IndexedDB 失败 | `local_error` | 远端不得调用，内存正文保持。 |
| `saving_remote` | CAS 提交成功/无变化 | `marking_synced` | 服务器和回执原子完成。 |
| `saving_remote` | revision 冲突 | `conflict` | 服务器正文不变，本地草稿保持可编辑。 |
| `saving_remote` | HTTP/提交未知 | `unknown` | 不推断服务器状态，冻结 operation_id。 |
| `unknown` | 核对 applied | `marking_synced` | 使用回执的资源和 revision。 |
| `unknown` | 核对 not_applied | `dirty` | 允许以同一 operation_id 重试原负载。 |
| `marking_synced` | 本地标记成功 | `saved` | 客户端 revision 与服务器一致。 |
| `marking_synced` | 本地标记失败 | `unknown-local` | 不重发远端写入；先核对再修复本地状态。 |
| `conflict` | 人工合并并保存 | `protecting_local` | 使用冲突响应中的最新 revision 和新 operation_id。 |
| `conflict` | 确认舍弃且本地删除成功 | `editing` | 载入服务器快照；这是唯一允许丢弃冲突草稿的路径。 |

- 创建作品和第一章是强一致单事务，不会出现只有作品没有第一章的可见状态。
- 单章服务端保存提供线性化的写入顺序：`BEGIN IMMEDIATE` 的写锁取得点串行化所有写者，revision CAS 防止静默覆盖。
- 本地与服务端是可核对的顺序一致，而非原子一致。客户端始终优先保留可能尚未在服务端确认的正文。
- schema v1 是新增边界，无写作数据回填。`user_version=1` 之外的数据库拒绝启动，避免猜测迁移。

## 错误与不确定性

- 客户端只能根据稳定错误码决定修正、合并、退避、核对或停止；不得通过本地化文案解析分支。
- 409 `revision_conflict` 是预期并发结果，不记录错误级日志；响应必须包含当前服务端 revision、正文和 ETag，且只发送给资源所有者。
- `persistence_busy` 表示已确认无本次副作用，可以同 key 退避重试；`commit_state_unknown` 和 `operation_state_unknown` 表示不能推断副作用，只能核对。
- IndexedDB 不可用时，远端保存被阻止，编辑器内存正文继续可选中和复制。UI 必须明确区分“本地保护失败，未发送”与“服务器结果未知”。
- 辅助内容缺失或格式错误不阻断创建、编辑和保存，但发布验收仍要求目标写作者认为实际发布版本的内容可用且连贯。
- 当前仓库没有身份实现、HTTP 框架、前端框架或依赖锁文件。本规格只固定请求身份接口、HTTP/数据契约和 SQLite/IndexedDB 保证；具体框架不得改变这些契约。实现计划必须选择与 Python 3.9.6 兼容的最小依赖并保留这里的测试接缝。
- Chromium 是本功能发布关键 E2E 的明确最低验证范围，不代表其他浏览器被产品支持或不支持；扩大兼容范围需要独立证据。

## 保证与测试追踪

| 保证 ID | 保证或失败契约 | 对应结果 ID 或状态 | 精确测试文件与名称 | 精确命令 | 可观察断言 |
| --- | --- | --- | --- | --- | --- |
| `G-01` | 创建作品和空白第一章原子提交，第一章 revision=1 且正文为空 | `O-01` | `tests/test_writing_service.py::CreateWorkTests.test_work_and_blank_first_chapter_commit_atomically` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_service.CreateWorkTests.test_work_and_blank_first_chapter_commit_atomically` | 成功时两实体和回执同时存在；注入章节插入失败时三者均不存在。 |
| `G-02` | 创建成功只产生一个作品并直接进入返回的第一章编辑 URL | `O-01`、创建导航 | `tests/e2e/test_direct_chapter_writing.py::DirectWritingE2E.test_create_opens_blank_first_chapter` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.e2e.test_direct_chapter_writing.DirectWritingE2E.test_create_opens_blank_first_chapter` | 单次主操作后 URL 匹配返回 ID，正文为空且获得焦点，后退不会再提交创建。 |
| `G-03` | 缺少身份或跨所有者访问不泄露、也不改变资源 | `O-04`, `O-16` | `tests/test_writing_api.py::WritingAuthorizationTests.test_missing_and_foreign_identity_cannot_mutate` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_api.WritingAuthorizationTests.test_missing_and_foreign_identity_cannot_mutate` | 无身份为 401；其他写作者为 404；正文、revision、回执计数不变。 |
| `G-04` | 修订 CAS 串行化保存，过期保存不能覆盖新正文；相同正文不增 revision | `O-12`, `O-13`, `O-17` | `tests/test_writing_persistence.py::ChapterConcurrencyTests.test_stale_revision_conflicts_without_overwrite` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_persistence.ChapterConcurrencyTests.test_stale_revision_conflicts_without_overwrite` | 两连接同 revision 保存仅一个成功；另一方 409；数据库正文等于胜者；no-op revision 不变。 |
| `G-05` | 每次远端保存前存在本地副本，冲突/失败/舍弃取消均保留正文，只有确认舍弃可删除 | `O-09`, `O-10`, `O-11`, `O-12`, `O-13`, `O-14`, `O-15`, `O-16`, `O-17`, `O-18`, `O-19`, `O-20`, `O-21`, `O-26`, `O-27`, `O-28`, `O-29`, `O-37`, `O-38` | `tests/e2e/test_direct_chapter_writing.py::DirectWritingE2E.test_conflict_keeps_draft_and_allows_continued_editing` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.e2e.test_direct_chapter_writing.DirectWritingE2E.test_conflict_keeps_draft_and_allows_continued_editing` | 两浏览器上下文制造冲突后，失败方 IndexedDB 和编辑器仍含其全文；取消舍弃不变；人工合并后可成功保存。 |
| `G-06` | 操作 key 同负载最多应用一次，不同负载不能复用 | `O-02`, `O-05`, `O-13`, `O-14`, `O-18` | `tests/test_writing_api.py::IdempotencyTests.test_replay_is_noop_and_changed_payload_is_rejected` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_api.IdempotencyTests.test_replay_is_noop_and_changed_payload_is_rejected` | 相同 key 重放返回同资源/revision 且行数不增；换负载返回 409 且正文不变。 |
| `G-07` | 取消、超时或未知提交状态只能经写锁核对分为 applied 或 not_applied，锁超时保持 unknown | `O-08`, `O-21`, `O-22`, `O-23`, `O-24`, `O-35`, `O-36`, `O-37`, `O-38` | `tests/test_writing_persistence.py::OperationReconciliationTests.test_reconcile_distinguishes_applied_not_applied_and_unknown` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_persistence.OperationReconciliationTests.test_reconcile_distinguishes_applied_not_applied_and_unknown` | 取消、超时或提交不明后，已提交核对为 applied、已回滚为 not_applied；持有写锁超过 250ms 返回 unknown，客户端不改 saved 标志。 |
| `G-08` | busy、SQL 失败、确认回滚及未知提交都不允许部分业务实体或孤立回执 | `O-06`, `O-07`, `O-08`, `O-19`, `O-20`, `O-21`, `O-24`, `O-31`, `O-35`, `O-36`, `O-37`, `O-38` | `tests/test_writing_persistence.py::TransactionFailureTests.test_busy_and_injected_failures_leave_no_partial_commit` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_persistence.TransactionFailureTests.test_busy_and_injected_failures_leave_no_partial_commit` | busy 为 503；每个注入点后业务行与回执一起存在或一起不存在；无半迁移 schema。 |
| `G-09` | 远端成功后的本地标记失败不会导致重复远端写入，可由原回执恢复 | `O-14`, `O-22`, `O-25`, `O-26` | `tests/e2e/test_direct_chapter_writing.py::DirectWritingE2E.test_local_sync_mark_failure_reconciles_without_duplicate_save` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.e2e.test_direct_chapter_writing.DirectWritingE2E.test_local_sync_mark_failure_reconciles_without_duplicate_save` | 注入 markSynced 失败后 revision 只增加一次；核对 applied；同 key 恢复 saved。 |
| `G-10` | schema 只允许原子 0→1，失败回滚，未知版本拒绝启动 | `O-30`, `O-31`, `O-32` | `tests/test_writing_persistence.py::SchemaMigrationTests.test_schema_v1_is_atomic_and_rejects_unknown_version` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_persistence.SchemaMigrationTests.test_schema_v1_is_atomic_and_rejects_unknown_version` | v0 得到完整三表和 user_version=1；注入失败仍为 v0；v2 字节不变且健康检查失败。 |
| `G-11` | 无效创建/保存输入在事务前被拒绝且无副作用 | `O-03`, `O-15` | `tests/test_writing_api.py::WritingValidationTests.test_invalid_payloads_have_no_durable_side_effects` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_api.WritingValidationTests.test_invalid_payloads_have_no_durable_side_effects` | 超长标题、超限正文、缺 ETag 和未知字段均为 422；实体、revision 和回执不变。 |
| `G-12` | 起步辅助内容顺序和版本稳定；加载失败不阻断编辑保存 | 辅助内容读取/降级 | `tests/components/test_editor_ui.py::WritingAidTests.test_versioned_aid_is_secondary_and_failure_is_non_blocking` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.components.test_editor_ui.WritingAidTests.test_versioned_aid_is_secondary_and_failure_is_non_blocking` | 三个固定块按序出现且正文仍聚焦；注入 500 后仍可输入并完成保存。 |
| `G-13` | 冲突提示明确说明未覆盖和本地已保留，并保持本地正文为可编辑主版本 | `O-17`, `O-28`、`conflict` 状态 | `tests/components/test_editor_ui.py::ConflictPanelTests.test_conflict_message_and_actions_preserve_local_text` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.components.test_editor_ui.ConflictPanelTests.test_conflict_message_and_actions_preserve_local_text` | 状态区含两项事实；编辑器是本地全文；服务器快照只读；取消舍弃后 IndexedDB 未删。 |
| `G-14` | 日志、URL、分析和回执不包含正文或冲突快照 | 所有 HTTP 和错误状态 | `tests/test_writing_api.py::ContentPrivacyTests.test_manuscript_content_is_not_logged_or_stored_in_receipts` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_writing_api.ContentPrivacyTests.test_manuscript_content_is_not_logged_or_stored_in_receipts` | 用唯一敏感标记执行成功、冲突和失败后，捕获日志、URL、事件和回执均不含标记。 |
| `G-15` | IndexedDB 保护成功是远端调用前置条件；保护失败时远端请求次数为零，内存正文仍可访问 | `O-09`, `O-11` | `tests/components/test_editor_ui.py::LocalPersistenceTests.test_remote_save_is_blocked_when_local_draft_fails` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.components.test_editor_ui.LocalPersistenceTests.test_remote_save_is_blocked_when_local_draft_fails` | 成功保护后才允许一次 API 调用；注入 quota/abort 后 API spy 调用为 0，状态为 local_error，编辑器仍含完整正文。 |
| `G-16` | 退出清理只影响当前写作者；清理失败不向下一个身份暴露草稿，原写作者仍可恢复或再次清理 | `O-33`, `O-34` | `tests/components/test_editor_ui.py::DraftIsolationTests.test_logout_cleanup_is_namespaced_and_failure_preserves_owner_recovery` | `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.components.test_editor_ui.DraftIsolationTests.test_logout_cleanup_is_namespaced_and_failure_preserves_owner_recovery` | 成功只删当前 writer；注入失败后另一 writer 查询为空且退出完成，原 writer 再登录可看见恢复/清理选择。 |

`O-01` 至 `O-38` 均至少映射到一个自动化保证；事务、并发、本地持久化、客户端可见失败和未知提交状态不依赖人工验证。人工验收用于验证“自然找到、理解、认为可用且连贯、认可视觉层级”等只有目标写作者能够提供的产品判断。

## 测试与文档

### 自动化测试范围

- 单元/领域层：作品与第一章原子创建、输入规范化、状态机、幂等 hash、错误分类和辅助清单校验。
- API 层：成功响应、稳定错误结构、身份隔离、ETag/CAS、幂等重放、正文日志脱敏和核对接口。
- SQLite 集成层：真实临时 SQLite 文件、WAL/FULL/foreign_keys/busy_timeout 设置、两个独立连接竞争、每个 SQL/COMMIT 注入失败点、迁移回滚和未知版本。
- 组件层：IndexedDB 成功/配额/中止、远端调用门禁、冲突提示语义、舍弃确认、保存状态文本、初始焦点、辅助内容次级布局和非阻塞降级。
- 浏览器 E2E 只保留三条跨层关键路径：创建后直接进入空白第一章；两个浏览器上下文产生冲突并恢复继续保存；远端成功但本地同步标记失败后核对且不重复保存。运行范围为 CI 固定 Chromium、全新 schema v1 数据库和相互隔离的写作者账户。
- 完整回归命令固定为 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`；发布证据必须同时包含该命令、保证表中的精确测试以及浏览器截图。当前 1 项订单测试必须继续通过。

### 人工验收协议

- 产品负责人招募至少 5 名未参与本功能设计、符合 README 定义的长篇小说写作者，并确认可记录去标识化任务结果。研究主持人使用固定脚本逐人执行，实施工程师不得代替目标写作者给出产品判断。
- 每位参与者使用全新账户和空作品列表，在 CI 候选构建的 Chromium 上完成：找到入口并创建；在空白第一章写作；使用起步辅助；经历预设双会话冲突；恢复并继续保存；评价编辑器层级和专注感。主持人在任务进行中不得提供入口方向或解释冲突文案。
- “自然找到”定义为从作品列表开始 60 秒内、无方向性提示地触发创建并在空白第一章输入首个字符；“理解冲突”定义为参与者能用自己的话同时说出“服务器已有较新版本”和“我的内容仍被保留、尚未覆盖”，并完成一次合并后的成功保存。
- “辅助内容可用且连贯”使用两个独立二元问题：内容是否帮助决定开篇下一步、三个辅助块是否形成无自相矛盾的顺序；“视觉层级和专注感”使用两个独立二元问题：正文是否明显是首要操作区、辅助/状态元素是否不妨碍连续写作。
- 通过阈值为 5/5 参与者完成入口和冲突任务，且 5/5 对辅助内容的两个问题及视觉层级的两个问题均回答“是”。任一未通过即本完成标准未满足；修订候选构建后重新执行失败标准，不能用工程团队意见替代。
- 证据由研究主持人记录，产品负责人复核签字。版本化摘要只保存参与者代号、构建 ID、日期、每项通过/失败和产品负责人结论；截图/录屏放入访问受控的验收制品库。仓库和 CI 公共日志不得包含参与者身份或真实小说正文。

### 文档影响

- 实现时更新 `README.md`：说明创建即进入第一章、保存/冲突恢复语义、测试命令、SQLite 最低版本和本地草稿隐私边界。
- 新增 API 契约文档，逐项记录本规格的请求/响应、ETag、幂等和错误码；文案本地化不得改变稳定 code。
- 发布候选新增 `docs/acceptance/{build_id}-direct-chapter-writing.md` 的去标识化验收摘要；受控截图和录屏只在摘要中记录制品 ID，不提交原始内容。

## 验收标准

| 完成标准 | 验证范围与方法 | 执行者 | 通过条件 | 必需证据 |
| --- | --- | --- | --- | --- |
| `AC-01` 原子创建并直接进入 | 全新数据库上运行 `G-01`、`G-02` 的服务测试和 Chromium E2E；覆盖成功、插入失败、重复响应和浏览器后退 | CI 执行自动化；发布负责人核对 | 所有断言通过；只有一个作品和空白第一章；编辑器正文聚焦 | CI run ID、JUnit XML `artifacts/test-results/direct-chapter-writing.xml`、编辑器 URL/空白焦点截图 |
| `AC-02` 保存不静默覆盖 | 两个独立 SQLite 连接和两个浏览器上下文从同一 revision 保存不同正文，运行 `G-04`、`G-06`、`G-08` | CI 执行自动化；发布负责人核对 | 恰好一个更新成功，另一个 409；数据库正文等于胜者；失败方草稿等于其完整输入；无孤立回执 | 并发测试日志（不含正文）、JUnit XML、冲突前后 revision 记录、去正文截图 |
| `AC-03` 冲突后可恢复继续编辑 | 运行 `G-05`、`G-09`、`G-13`、`G-15` E2E，注入冲突、IndexedDB 标记失败、舍弃取消和 quota 失败 | CI 执行自动化 | 每个失败分支均保留应保留正文；合并后可成功保存；远端成功只增一次 revision；本地保护失败时远端调用为 0 | E2E trace、IndexedDB 状态导出（测试文本）、API 调用计数、冲突/恢复截图 |
| `AC-04` 未知提交可核对 | 用真实 SQLite 锁及传输故障运行 `G-07`，分别制造客户端取消、连接超时、服务端提交不明、已提交、已回滚和核对锁超时 | CI 执行自动化 | 传输故障不直接改变保存判断；核对返回 applied、not_applied、unknown 三种独立结果；unknown 时 UI 不显示 saved 且不生成新 key | JUnit XML、操作 ID/结果码/修订号日志、状态机断言 |
| `AC-05` 数据、权限和隐私边界成立 | 运行 `G-03`、`G-10`、`G-11`、`G-14`、`G-16`，覆盖身份、草稿命名空间/退出清理、迁移、无效输入及唯一敏感标记扫描 | CI 执行自动化；安全/发布负责人复核脱敏报告 | 全部测试通过；跨所有者 404；下一身份不能读取残留草稿；无部分迁移；日志、URL、事件、回执均无正文标记 | CI run ID、JUnit XML、schema/PRAGMA 报告、IndexedDB 隔离报告、脱敏扫描报告 |
| `AC-06` 写作入口可自然找到 | 5 名目标写作者按固定协议从空作品列表开始；60 秒内无提示观察 | 研究主持人执行；产品负责人复核 | 5/5 创建作品并在空白第一章输入首字符，无人先进入设定集或大纲 | 去标识化逐人任务时间/结果、入口与编辑器截图制品 ID、产品负责人签字摘要 |
| `AC-07` 冲突提示可理解且能继续 | 同 5 名参与者经历预设双会话冲突；要求口述两项事实并完成合并保存 | 研究主持人执行；产品负责人复核 | 5/5 正确说出“服务器较新”和“本地已保留未覆盖”，且各自完成后续成功保存 | 逐人口述判断勾选、最终 revision/成功状态、冲突与恢复截图制品 ID、签字摘要 |
| `AC-08` 辅助内容可用且连贯 | 同 5 名参与者使用发布候选的三个版本化辅助块后回答两个独立二元问题 | 研究主持人执行；产品负责人复核 | 5/5 认为内容帮助决定下一步，且 5/5 认为三个块顺序连贯、无自相矛盾 | 构建与辅助内容 version、逐人两项回答、任务记录、签字摘要 |
| `AC-09` 编辑器视觉层级和专注感获认可 | 同 5 名参与者连续写作至少 3 分钟后回答正文主次与干扰两个二元问题；主持人记录焦点中断 | 研究主持人执行；产品负责人复核 | 5/5 认为正文是首要操作区且辅助/状态不妨碍连续写作；无系统导致的意外焦点抢占 | 逐人两项回答、焦点中断计数、候选构建全屏截图制品 ID、签字摘要 |
| `AC-10` 回归和文档同步完成 | 运行完整 unittest discovery；逐项核对 README、API 契约和去标识化验收摘要 | CI 运行测试；技术负责人核对文档；产品负责人签署验收摘要 | 现有订单测试及所有新增测试通过；文档与发布 API/SQLite 设置一致；`AC-01`—`AC-09` 证据可定位 | 完整 CI run ID、测试清单、文档 diff、`docs/acceptance/{build_id}-direct-chapter-writing.md` |

只有 `AC-01` 至 `AC-10` 全部具备对应执行者产出的必需证据并满足通过条件，功能才算完成。实施计划只能把这些既定验证拆成执行任务，不能改变验证范围、执行角色、阈值或证据要求；任何变更都必须先修改并重新评审本规格。
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