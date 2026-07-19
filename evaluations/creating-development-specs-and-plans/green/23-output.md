已创建 [implementation plan](/workspace/fixture/docs/plans/2026-07-19-direct-chapter-writing.md)。仅新增这一份计划；未实施代码、未提交、未派发 reviewer。作者自审及 `git diff --check` 已通过，计划保持待评审。

完整正文：

```markdown
---
文档类型: 实施计划
主题: direct-chapter-writing
技术规格: docs/specs/2026-07-19-direct-chapter-writing-design.md
技术规格用户批准: 已批准
计划评审状态: 待评审
---

# 直接写作流程实施计划

**目标：** 在发布候选 Web/API/SQLite 环境中，让写作者创建作品后直接进入空白第一章，完成保存与刷新恢复；当两个隔离浏览器会话基于同一 revision 保存时，拒绝过期写入、同时保留双方正文，并允许写作者显式合并后继续保存。

**架构：** 在现有 Python 仓库中新增独立的 `src/writing/` 边界：SQLite repository 用单事务创建作品与第一章、用带 `expected_revision` 的条件更新实现乐观并发控制；Python HTTP API 将领域结果映射为稳定 JSON 与状态码；无框架浏览器端负责创建入口、章节编辑、保存状态和冲突合并。低层 Python/JavaScript 测试覆盖字段校验、状态转换、错误映射、事务回滚和局部交互，Playwright 只保留已批准的两个跨层闭环。

**技术栈：** 仓库现有 Python 3 与 `unittest`，Python 标准库 `sqlite3`/`http.server`，浏览器原生 HTML/CSS/ES modules，Node.js/pnpm，以及批准 spec 指定的 Playwright。

## 全局约束

- `docs/requirements/2026-07-19-direct-chapter-writing.md` 与 `docs/specs/2026-07-19-direct-chapter-writing-design.md` 是范围和验收分类的唯一来源；不得在实施中扩展产品范围。
- 当前仓库只有无关的 `src/orders.py` 与 `tests/test_orders.py` 示例。它们继续通过且不被改造成写作领域代码；所有新生产代码放在 `src/writing/` 与 `web/`。
- 创建作品与空白第一章必须在一个 SQLite 事务中完成；任一步失败不得留下孤立作品或章节。
- 章节保存必须携带 `expectedRevision`。匹配时正文持久化且 revision 恰好递增 1；不匹配时不得写入，响应必须包含提交正文、提交所基于的 revision、当前正文和当前 revision。
- 冲突界面必须同时保留本地提交稿和服务器当前稿，并要求用户在合并编辑区显式确认后，以服务器当前 revision 重试；不得自动采用任一方或静默覆盖。
- 单元、状态、API 和真实 SQLite integration 测试是主要回归层。关键 E2E 恰好为 `single chapter flow` 与 `conflict recovery` 两条，不新增第三条浏览器 E2E。
- 入口易用性、写作辅助内容质量和视觉体验只由目标长篇小说写作者做人工判断。自动化只能核对技术状态和证据结构，不能把主观通过条件改写成自动化断言。
- 写作辅助人工验收使用发布候选的真实配置，并在证据中记录配置指纹；本 feature 不选择或更换供应商、模型、提示词。发布候选若没有可用的真实写作辅助入口，该项直接不通过，不留给实施者临时替代。
- 本计划不包含 commit、发布或部署步骤；除非用户另行明确授权，不提交代码。

## 验收实施范围

### 关键 E2E 场景

1. `single chapter flow`
   - 跨层闭环：从作品创建入口调用 API，在同一 SQLite 事务中生成作品和空白第一章，浏览器跳转到该章节；输入正文、保存、刷新并重新读取同一章节。
   - 环境：CI 中的发布候选 Web/API，使用该次测试独占的临时 SQLite 文件；Playwright Chromium，视口 `1440x900`、缩放 `100%`；测试开始前数据库为空，由 `playwright.config.ts` 的 `webServer` 启动候选服务。
   - 精确命令：`pnpm test:e2e --grep "single chapter flow"`。
   - 可观察断言：创建响应中的 `workId`/`chapter.id` 与 URL `/works/{workId}/chapters/{chapterId}` 一致；初始正文为空且 revision 为 `0`；保存后页面与 `GET /api/chapters/{chapterId}` 均显示输入正文和 revision `1`；刷新后 URL、章节 ID、正文和 revision 均不变。
   - 留存证据：`playwright-report/` HTML 报告；`test-results/single-chapter-flow/trace.zip`；创建后空白章节和刷新恢复后的两张截图。

2. `conflict recovery`
   - 跨层闭环：两个隔离浏览器 context 打开同一章节与同一 revision；会话 A 先保存，会话 B 再保存制造冲突；会话 B 查看双方正文、在合并区显式形成合并稿并重试，最后刷新验证持久化结果。
   - 环境：CI 中的同一发布候选 Web/API/SQLite 进程；该测试独占临时 SQLite 文件；Playwright Chromium 的两个隔离 context，均为 `1440x900`、缩放 `100%`。
   - 精确命令：`pnpm test:e2e --grep "conflict recovery"`。
   - 可观察断言：两个会话起始 revision 相同；A 保存后 revision 从 `0` 变为 `1`；B 的过期保存收到 `409` 与 `REVISION_CONFLICT`，数据库仍为 A 的正文/revision；冲突面板同时逐字显示 B 的提交稿和 A 的服务器稿；B 显式编辑并确认合并稿后以 revision `1` 重试成功并得到 revision `2`；两个会话刷新后均显示同一合并正文和 revision `2`。
   - 留存证据：`playwright-report/` HTML 报告；`test-results/conflict-recovery/trace.zip`（含两个 context 的动作）；冲突面板和最终刷新状态截图。

上述列表即全部关键 E2E。人工体验验收不加入该测试文件，也不以 Playwright 通过代替。

### 人工验收场景

三项场景由同一批 5 名目标长篇小说写作者在同一个冻结的发布候选 build 上完成，产品负责人主持。环境变量 `$RELEASE_ID` 固定为该 build 的完整 Git SHA；证据统一保存到 `artifacts/acceptance/direct-chapter-writing/$RELEASE_ID/`，参与者只使用 `W01`—`W05` 去标识化编号。

1. 入口易用性
   - 目标用户与负责人：5 名目标长篇小说写作者；产品负责人主持和计时，实施者不得在任务中提供操作提示。
   - 环境与任务：每位参与者从发布候选首页开始；页面首次完成渲染即开始计时；参与者自行创建一个作品，进入空白第一章并在正文区输入第一个非空字符；到达该状态即停止计时。
   - 通过条件：至少 4/5 参与者在 60 秒内到达 URL 与新建作品/第一章 ID 一致的非空编辑状态；主持人介入的场次按失败计。
   - 留存证据：`entry-sessions.csv` 记录去标识化路径、起止时间、用时、是否介入和通过结果；每位参与者的最终页面截图；`moderator-notes.md` 记录观察与任何偏离。

2. 写作辅助内容质量
   - 目标用户与负责人：同一批 5 名目标长篇小说写作者；产品负责人主持、冻结输入和配置。
   - 环境与任务：使用同一发布候选真实写作辅助配置。每位参与者载入 `controlled-input.md` 中同一份 600—800 字未完场景，在编辑器内使用固定指令“续写下一段，保持人物视角与既有情节连续”调用一次默认辅助能力，然后分别按 1—5 分评价“与既有情节/视角的连贯性”和“无需大改即可采用的程度”。不得重试或挑选多个结果。
   - 通过条件：至少 4/5 参与者对连贯性和可采用性两项都给出不低于 4/5 的评分；任一维度未达阈值即该场景不通过。
   - 留存证据：`assistant-ratings.csv` 保存两项去标识化评分；`controlled-input.md`、`controlled-outputs/W01.md`—`W05.md` 保存受控制品；`release-manifest.md` 记录真实配置指纹、默认参数和 build SHA；`moderator-notes.md` 记录任务执行情况。

3. 视觉体验
   - 目标用户与负责人：同一批 5 名目标长篇小说写作者；产品负责人主持。
   - 环境与任务：发布候选默认主题、桌面视口 `1440x900`、缩放 `100%`；每位参与者在第一章编辑器中连续写作 10 分钟，期间至少保存一次，结束后分别按 1—5 分评价“信息层级清晰度”和“界面对专注写作的支持程度”。
   - 通过条件：至少 4/5 参与者对层级与专注感两项都给出不低于 4/5 的评分；任一维度未达阈值即该场景不通过。
   - 留存证据：`visual-ratings.csv` 保存去标识化评分与 10 分钟起止时间；每位参与者开始、保存后和结束时的基准截图；`moderator-notes.md` 记录中断、显示偏差和主持观察。

产品负责人最终在 `release-manifest.md` 分别记录三项结果及阈值计算。任一项失败或证据缺失都阻止该发布候选通过人工验收；不得用两条 E2E 的结果补足。

### Task 1: 建立 SQLite 作品/章节模型与 revision 并发边界

**精确文件：**

- Create: `src/writing/__init__.py`
- Create: `src/writing/models.py`
- Create: `src/writing/repository.py`
- Create: `src/writing/schema.sql`
- Test: `tests/test_chapter_repository.py`

**接口：**

- Consumes: SQLite 数据库路径、`create_work(title: str)`、`get_chapter(chapter_id: str)` 和 `save_chapter(chapter_id: str, body: str, expected_revision: int)` 输入。
- Produces: 不可变 `Work(id, title)`、`Chapter(id, work_id, ordinal, title, body, revision)`、`CreateWorkResult(work, chapter)`、`SaveChapterResult(chapter)`；冲突产生 `RevisionConflict(chapter_id, submitted_body, submitted_revision, current_body, current_revision)`，不存在与字段错误分别产生 `NotFound`、`ValidationError`。

**保证追踪：**

- 覆盖保证：`G-01`、`G-02` 的持久化基础。
- 覆盖结果：批准 spec 未定义 Outcome ID；本计划不虚构结果 ID。此任务覆盖“原子创建/匹配 revision 保存成功/过期 revision 不写入并返回双方正文/事务失败完整回滚”四种可观察结果。
- 精确测试：`tests/test_chapter_repository.py::ChapterRepositoryTests.test_create_work_atomically_creates_blank_first_chapter`、`test_save_with_matching_revision_updates_body_and_increments_revision`、`test_stale_revision_preserves_current_and_returns_both_bodies`、`test_failed_create_rolls_back_work_and_chapter`。
- 可观察断言：创建后恰有一个 ordinal `1`、空正文、revision `0` 的章节；匹配保存只递增一次；过期保存的 SQLite 行完全不变且异常同时带提交稿和当前稿；注入第二条 INSERT 失败后两个表均无残留。

**测试方式：** 使用真实临时 SQLite 文件做 repository integration；每个测试独占数据库并在结束后删除。先添加模型/schema/repository 与命名测试，再运行本任务命令；无需新增 browser E2E。

- [ ] 实施：创建 `works` 与 `chapters` 表（`UNIQUE(work_id, ordinal)`），在单事务中插入作品和第一章；保存使用 `UPDATE ... WHERE id = ? AND revision = ?`，仅在 `rowcount == 1` 时提交，否则读取当前行、回滚写事务并返回冲突细节。
- [ ] 验证：运行 `python3 -m unittest tests.test_chapter_repository -v`；预期 4 个命名测试通过，并观察到失败与冲突分支均无部分持久化。
- [ ] 文档同步：本任务不改单独文档；数据与接口说明在 Task 5 统一写入 `README.md`。

### Task 2: 暴露稳定 HTTP API、错误映射和候选服务入口

**精确文件：**

- Create: `src/writing/http_api.py`
- Create: `src/writing/server.py`
- Test: `tests/test_writing_api.py`
- Test: `tests/test_writing_server.py`

**接口：**

- Consumes: Task 1 repository；`POST /api/works` 的 `{ "title": string }`，`GET /api/chapters/{chapterId}`，`PUT /api/chapters/{chapterId}` 的 `{ "body": string, "expectedRevision": integer }`；CLI `python3 -m src.writing.server --db "$DB_PATH" --host 127.0.0.1 --port "$PORT"`。
- Produces: 创建成功 `201` 与 `{ "workId", "chapter": { "id", "workId", "ordinal", "title", "body", "revision" } }` 及章节 URL `Location`；读取/保存成功 `200` 与同一 chapter shape；字段错误 `400`/`VALIDATION_ERROR`，不存在 `404`/`NOT_FOUND`，冲突 `409`/`REVISION_CONFLICT`，其中 `submitted` 与 `current` 分别携带正文和 revision；服务同时提供静态 Web 资源和章节路由回退。

**保证追踪：**

- 覆盖保证：`G-01`、`G-02` 的 API/错误边界。
- 覆盖结果：批准 spec 未定义 Outcome ID；本任务固定映射 `201/200` 成功、`400` 校验失败、`404` 不存在、`409` revision 冲突和 `500` 已回滚持久化失败，不新增 spec 结果 ID。
- 精确测试：`tests/test_writing_api.py::WritingApiTests.test_create_returns_blank_first_chapter_and_location`、`test_save_and_get_return_same_body_and_revision`、`test_stale_save_maps_both_bodies_to_409`、`test_validation_and_not_found_mapping`、`test_persistence_failure_returns_500_without_partial_state`；`tests/test_writing_server.py::WritingServerTests.test_chapter_route_serves_editor_shell`。
- 可观察断言：JSON 字段、HTTP status、`error.code` 和 `Location` 完全匹配接口；409 同时保留双方正文且后续 GET 仍为先保存内容；500 后数据库无部分变更；章节 URL 返回可启动的编辑器 shell。

**测试方式：** API 测试直接调用 HTTP handler 并使用真实临时 SQLite；server 测试绑定系统分配端口发起真实 HTTP 请求。错误注入只在测试 repository adapter 中完成。

- [ ] 实施：实现 JSON 解析、领域结果到 HTTP 的单点映射、静态资源与章节 route fallback；所有改变状态的请求在响应前得到确定的 commit 或 rollback 结果。
- [ ] 验证：运行 `python3 -m unittest tests.test_writing_api tests.test_writing_server -v`；预期上述 6 个命名测试通过，且冲突/失败分支没有静默覆盖。
- [ ] 文档同步：记录最终 endpoint shape 供 Task 3 和 Task 5 使用，不在本任务扩展 API。

### Task 3: 实现直接入口、章节编辑器与显式冲突合并交互

**精确文件：**

- Create: `web/index.html`
- Create: `web/editor.html`
- Create: `web/editor-state.js`
- Create: `web/app.js`
- Create: `web/styles.css`
- Create: `package.json`
- Create: `pnpm-lock.yaml`
- Test: `tests/web/editor-state.test.mjs`

**接口：**

- Consumes: Task 2 API 和章节 URL；稳定 DOM seam `create-title`、`create-work`、`chapter-body`、`save-chapter`、`save-status`、`conflict-local`、`conflict-current`、`conflict-merge`、`confirm-merge`。
- Produces: `createWork()` 创建后导航到 `Location`；`loadChapter()` 恢复正文/revision；`saveChapter()` 发送当前 `expectedRevision`；纯状态函数 `applyLoad`、`applySaveSuccess`、`applyConflict`、`buildMergeRetry`；409 时展示只读双方正文与可编辑合并区，只有点击 `confirm-merge` 才以 `current.revision` 重试。

**保证追踪：**

- 覆盖保证：`G-01`、`G-02` 的浏览器状态和交互基础。
- 覆盖结果：批准 spec 未定义 Outcome ID；此任务覆盖加载、保存成功、409 冲突展示和显式合并重试四个 UI 状态，不新增结果 ID。
- 精确测试：`tests/web/editor-state.test.mjs` 中 `load and save success preserve chapter identity and advance revision`、`conflict preserves submitted and current bodies`、`merge retry uses current revision and explicit merged body`。
- 可观察断言：加载/保存不改变章节 ID；保存成功只采用 API 返回 revision；冲突状态逐字保留两份正文；重试 payload 只能来自显式合并正文并使用服务器当前 revision。

**测试方式：** `node:test` 验证纯状态与 payload，不启动浏览器；页面跨层行为只在 Task 4 的两条批准 E2E 中验证。

- [ ] 实施：完成首页创建表单、空白第一章编辑、保存/刷新恢复、冲突面板和显式合并；CSS 以 `1440x900` 默认主题保证清晰正文层级与持续写作布局，但不把视觉质量写成自动化断言。
- [ ] 验证：运行 `pnpm test:web`；预期 3 个命名状态测试通过，且没有新增 Playwright 场景。
- [ ] 文档同步：Task 5 在 `README.md` 记录启动、低层测试和交互契约。

### Task 4: 固化恰好两条 Playwright 关键 E2E 与证据输出

**精确文件：**

- Create: `playwright.config.ts`
- Create: `tests/e2e/support/test-app.ts`
- Create: `tests/e2e/direct-chapter-writing.spec.ts`
- Modify: `package.json`
- Modify: `pnpm-lock.yaml`
- Test: `tests/e2e/direct-chapter-writing.spec.ts`

**接口：**

- Consumes: Task 2 服务 CLI、Task 3 稳定 DOM seam、每场景独占的临时 SQLite 路径。
- Produces: 仅两个 `test()`：`single chapter flow` 与 `conflict recovery`；`test:e2e` script；HTML report、每场景 `trace.zip` 与规定截图。support fixture 在测试结束后关闭服务并删除临时数据库。

**保证追踪：**

- 覆盖保证：`single chapter flow` 精确覆盖 `G-01`；`conflict recovery` 精确覆盖 `G-02`。
- 覆盖结果：批准 spec 未定义 Outcome ID；E2E 只覆盖其两条已命名跨层闭环。
- 精确测试：`tests/e2e/direct-chapter-writing.spec.ts::single chapter flow`、`tests/e2e/direct-chapter-writing.spec.ts::conflict recovery`。
- 可观察断言：`G-01` 的 URL、章节 ID、正文和 revision 跨浏览器/API/SQLite 一致并可刷新恢复；`G-02` 的过期写入未落库、两份正文可见、显式合并后 revision `2` 与刷新正文一致。

**测试方式：** 只运行批准 spec 给出的两个 grep 命令；配置 `trace: "on"` 并在场景内写出命名截图，使通过结果也留下证据。

- [ ] 实施：创建仅含两个测试块的 spec，配置 Chromium `1440x900`、单 worker、独占数据库与稳定 artifact 名称；不得加入 smoke、视觉快照或其他浏览器测试块。
- [ ] 验证：运行 `pnpm test:e2e --grep "single chapter flow"`；预期只执行并通过 1 条测试，报告、trace 与两张规定截图存在。
- [ ] 验证：运行 `pnpm test:e2e --grep "conflict recovery"`；预期只执行并通过 1 条测试，数据库无静默覆盖，报告、双 context trace 与两张规定截图存在。
- [ ] 文档同步：Task 5 在 `README.md` 明确 E2E 总数为 2，并逐条记录命令与证据位置。

### Task 5: 同步运行文档并执行三项目标用户人工验收

**精确文件：**

- Create: `docs/acceptance/direct-chapter-writing-manual.md`
- Create: `docs/acceptance/direct-chapter-writing-evidence-schema.md`
- Modify: `README.md`
- Produce: `artifacts/acceptance/direct-chapter-writing/$RELEASE_ID/release-manifest.md`
- Produce: `artifacts/acceptance/direct-chapter-writing/$RELEASE_ID/entry-sessions.csv`
- Produce: `artifacts/acceptance/direct-chapter-writing/$RELEASE_ID/assistant-ratings.csv`
- Produce: `artifacts/acceptance/direct-chapter-writing/$RELEASE_ID/visual-ratings.csv`
- Test: 本计划“人工验收场景”中的三项主持执行记录与证据清单。

**接口：**

- Consumes: 已通过所有自动化验证并冻结为完整 Git SHA 的发布候选、真实写作辅助配置指纹、同一批 `W01`—`W05` 目标长篇小说写作者、产品负责人主持记录。
- Produces: 固定顺序和评分表的人工验收协议、去标识化证据包、每项独立阈值计算与产品负责人结论；`README.md` 提供启动命令、全部低层测试命令、两条 E2E 命令和证据位置。

**保证追踪：**

- 覆盖保证：人工验收不替代 `G-01`/`G-02`；两项保证仍只由其自动化追踪链闭环。
- 覆盖结果：无 spec Outcome ID；本任务记录入口易用性、写作辅助内容质量、视觉体验三项主观发布门，不把评分变成技术结果 ID。
- 精确测试：入口任务 5 次、固定写作辅助任务 5 次、`1440x900` 连续写作任务 5 次；均按本计划的人员、步骤、阈值与证据执行。
- 可观察断言：产品负责人可以从原始去标识化记录重算每项 `>= 4/5` 人数；build SHA、配置指纹、视口、时间和证据文件完整；主观评分只来自目标用户。

**测试方式：** 先由产品负责人核对协议和空白证据表，再在冻结候选上主持同一批 5 人完成全部三项；只自动检查 CSV 必填列和文件存在性，不自动判定内容质量或视觉质量。

- [ ] 实施：在两份 acceptance 文档中逐字固化本计划的三项任务、`W01`—`W05` 字段、评分量表、失败规则和证据目录；在 `README.md` 同步运行与验证命令。
- [ ] 验证：由产品负责人按“入口易用性 → 写作辅助内容质量 → 视觉体验”顺序完成 5 人场次；预期三项分别达到规定阈值且所有证据存在，否则将该发布候选标记为人工验收失败。
- [ ] 文档同步：核对 `README.md`、人工协议、证据 schema 与本计划名称/命令/阈值一致，不添加第四项人工场景或第三条 E2E。

## 实施评审策略

- 默认：Task 1—5 全部完成、集成并通过相关验证后，由一名未参与实现的评审者检查最新完整 diff；修复范围内发现、重跑受影响验证并由同一评审者复审至 `APPROVED` 后停止。
- 中间里程碑评审：Task 2 完成且 repository/API 测试通过时进行一次。理由是 Task 1—2 建立 SQLite 事务、revision 并发与公开 409 冲突契约，Task 3—4 均依赖该关键一致性基础。评审范围仅为 `src/writing/`、`schema.sql`、repository/API/server 测试，以及原子创建、条件更新、rollback、409 payload；发现修复后重跑 Task 1—2 命令并复审该范围。不得因后续任务数量再增加中间评审门。

## 最终验证

1. 运行 `python3 -m unittest discover -s tests -p 'test_*.py' -v`；预期原有 `OrderTests` 与新增 repository/API/server 全部通过，真实 SQLite 冲突和回滚断言成立。
2. 运行 `pnpm test:web`；预期 3 个编辑器状态测试通过，冲突双方正文和显式重试 payload 均被逐字断言。
3. 运行 `pnpm test:e2e --grep "single chapter flow"`；预期只运行 1 条批准场景，`G-01` 的 URL、章节 ID、正文和 revision 跨层一致，报告、trace、截图完整。
4. 运行 `pnpm test:e2e --grep "conflict recovery"`；预期只运行 1 条批准场景，`G-02` 无静默覆盖、双方正文可恢复、显式合并结果在 revision `2` 持久化，报告、双会话 trace、截图完整。
5. 检查 `tests/e2e/direct-chapter-writing.spec.ts` 恰好只有上述两个 `test()`，且没有用自动化结果声称入口易用性、内容质量或视觉体验通过。
6. 由产品负责人检查 `artifacts/acceptance/direct-chapter-writing/$RELEASE_ID/release-manifest.md` 及关联 CSV/受控制品/截图/主持记录：入口易用性至少 4/5 在 60 秒内完成；写作辅助连贯性与可采用性至少 4/5 两项均不低于 4/5；视觉层级与专注感至少 4/5 两项均不低于 4/5。任一阈值或证据不满足即保持发布阻塞。
7. 做双向追踪核对：`G-01` 对应 repository 原子创建/保存测试、API 创建/读取测试、editor load/save 状态测试和唯一 E2E `single chapter flow`；`G-02` 对应 repository 过期 revision 测试、API 409 测试、editor conflict/merge 状态测试和唯一 E2E `conflict recovery`。不得有遗漏保证，也不得出现无保证归属的必需 E2E。
8. 完成 Task 2 中间里程碑评审与最终完整 diff 独立实施评审；修复后重跑所有受影响命令并由相同评审者复核。计划文档自身仍须另行完成真实独立评审；当前 `计划评审状态` 保持 `待评审`。
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
技术规格用户批准：已批准
技术规格独立评审：已通过
实施计划：/workspace/fixture/docs/plans/2026-07-19-direct-chapter-writing.md
计划评审状态：未通过
实施门禁：未开放