---
document_type: design
topic: localized-workflow-document-metadata
requirements_path: docs/requirements/2026-07-19-localized-workflow-document-metadata.md
requirements_topic: localized-workflow-document-metadata
requirements_scope: feature
requirements_understanding_confidence: 98
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: approved
approved_at: 2026-07-19
independent_review: approved
independent_reviewer: spec-plan-reviewer
independent_reviewed_at: 2026-07-19
---

# 工作流文档元数据中文化技术规格

## 目标

- 本功能生效后，从头创建的 PRD、技术规格和实施计划使用已批准 PRD 规定的单套中文 frontmatter 字段和中文生命周期值。
- 功能生效前已存在的英文文档继续按现有格式读取、维护和重新评审，不发生隐式迁移。
- 文档读取端先把受支持的中文或英文 frontmatter 归一化为既有英文语义，再执行当前批准、评审和门禁校验。
- requirements 八字段、workflow 十四字段、各 renderer 的严格 JSON 输入输出和门禁真值表保持字节及语义兼容。
- 缺失、格式错误、混合语言、语义重复、冲突或不受支持的元数据继续失败关闭，不因本地化获得批准或开放门禁。

## 非目标

- 不修改 Skill 的名称、frontmatter 名称或 Codex 界面显示名称。
- 不修改八字段、十四字段、CLI JSON、脚本参数、API、协议、代码标识符或 renderer 的英文 canonical 契约。
- 不迁移或批量改写现有 `docs/requirements/`、`docs/specs/`、`docs/plans/`、评估输出或 Git 历史。
- 不引入通用 YAML 框架、跨 Skill 共享运行时模块、新依赖或新的持久化格式。
- 不把仓库中其它 Markdown frontmatter、Skill frontmatter 或 YAML 文件纳入本地化。
- 不改变既有批准顺序、评审职责、批准失效、门禁计算、会话路由或内容任务适用性门禁。
- 不在本规格阶段修改生产 Skill、生成实施计划、安装、提交或发布。

## 当前证据

- 已批准产品需求为 `docs/requirements/2026-07-19-localized-workflow-document-metadata.md`。使用显式 topic `localized-workflow-document-metadata` 和 scope `feature` 运行 PRD inspector 后，返回 `status: approved`、`specification_gate: open` 且 `issues: []`。
- `skills/creating-product-requirements/assets/prd-template.md`、`skills/creating-development-specs-and-plans/assets/spec-template.md` 和 `assets/plan-template.md` 当前均写英文 frontmatter 键和值。
- `skills/creating-development-specs-and-plans/scripts/inspect_product_requirements.py` 当前只接受 ASCII 键以及 `product-requirements`、`product | phase | feature`、`pending | approved` 等英文值；中文键会被判为 malformed。
- `skills/generating-development-prompts/scripts/discover_context.py` 当前只从 plan frontmatter 读取 `review_status`、`reviewer`、`reviewed_at`，并只把英文 `approved` 识别为通过。
- `skills/creating-development-specs-and-plans/scripts/render_handoff.py`、`skills/creating-product-requirements/scripts/render_handoff.py` 和 `skills/generating-development-prompts/scripts/render_handoff.py` 处理的是英文 canonical 与中文回复视图，不读取 PRD/spec/plan frontmatter，因此不属于本次修改范围。
- 仓库规则要求跨 Skill 公共契约采用 RED→GREEN、分别定向验证、完整 plugin 回归和一次覆盖最新完整 diff 的独立评审。
- 当前分支已有另一已评审批次的未提交变更，并与两个 authoring Skill 有文件重叠。后续实施必须基于当前 worktree 增量修改，不回滚、覆盖或把既有变更误归为本功能。

## 行为与边界

### 文档语言分类

文档 authoring、PRD inspector 以及 spec/plan 工作流门禁只接受两种完整文档 schema：

1. `english-legacy`：frontmatter 使用当前既有英文键和值；
2. `chinese-current`：frontmatter 使用已批准 PRD 中对应文档类型的完整中文键和值。

识别顺序如下：

1. frontmatter 必须从文件首字节开始、正确闭合，且每行是单层 `key: scalar`；
2. 根据已知字段别名判断文档 schema；
3. 同一 frontmatter 同时出现任何已知英文键和已知中文键时，分类为 `mixed_schema`，不继续择优；
4. 在单一 schema 内先把键归一化为既有英文语义键，再检测语义重复；
5. 根据字段语境把受支持值归一化为既有英文 canonical 值；
6. 最后复用当前 topic、scope、confidence、批准、评审、路径和门禁校验。

两个 raw key 即使值相同，只要归一化到同一语义字段，也属于重复。未知、嵌套、多行、引用或不受支持的状态不通过语言映射兜底。

Development prompt discovery 保留一项明确的非对称兼容边界：`chinese-current` plan 必须满足本功能定义的完整 plan schema 和生命周期条件；`english-legacy` plan 继续沿用现有 review-only 提取合同，以免破坏历史手写 plan 和无 frontmatter 的英文 header 输入。

### 新文档写入

- `creating-product-requirements` 从头创建 PRD 时，按批准 PRD 的完整字段表写中文键和值。
- `creating-development-specs-and-plans` 从头创建技术规格和实施计划时，按批准 PRD 的完整字段表写中文键和值。
- 审批和评审写回继续更新当前文档的同一 schema。中文文档写中文状态及中文角色/日期键；英文历史文档继续写英文状态及英文角色/日期键。
- 新中文文档不附加英文别名。路径、stable topic、ISO 日期、置信度整数和 reviewer role 值原样写入。
- 本功能实施前已经存在的当前 PRD、当前技术规格及后续可能创建的英文实施计划均属于 `english-legacy`；后续维护不得仅因功能上线而转换它们。

### 读取和门禁

- PRD inspector 同时接受完整 `english-legacy` PRD 和完整 `chinese-current` PRD，并继续输出现有英文 JSON schema。
- 技术规格与计划工作流的文档合同同时说明两种输入 schema，并要求批准写回保持原 schema；其十四字段 handoff 仍是英文 canonical 的内部快照。
- development prompt discovery 同时接受符合现有 review-only 合同的 `english-legacy` plan 和满足本功能完整字段/生命周期的 `chinese-current` plan；其 `documents.plan.review` JSON 仍只输出 `approved | not-approved | unknown`。
- 兼容读取不改写输入文件。读取历史英文文档不产生仅为本地化的 diff。
- `mixed_schema`、语义重复、冲突或不受支持的中文值映射为现有 `unknown` 路径；可靠的中文“待批准”或“待评审”只映射到既有 pending/not-approved 语义，不升级门禁。

## 组件与控制流

### Authoring 合同与模板

`skills/creating-product-requirements/references/document-contract.md` 和 `assets/prd-template.md` 定义新 PRD 的中文 schema。合同增加“新建写中文、既有英文保持原 schema”的写回规则；模板使用中文字段和值，但 stable topic 插槽和置信度插槽保持技术格式。

`skills/creating-development-specs-and-plans/references/document-contracts.md`、`assets/spec-template.md` 和 `assets/plan-template.md` 以相同规则定义新 spec/plan。`SKILL.md` 与 `references/review-and-handoff.md` 中直接依赖 `review_status: pending` 等英文文档字面量的行为说明改为 schema-neutral 语义，同时保留 canonical handoff 的英文名称和值。

### PRD inspector

`skills/creating-development-specs-and-plans/scripts/inspect_product_requirements.py` 在原始 frontmatter 解析阶段完成本地、确定性的 PRD alias normalization，不能等现有 ASCII key regex 已经拒绝中文键后再处理：

- raw line parser 保留现有 flat scalar、闭合 marker、缩进、quoted/multiline 拒绝规则；raw key 只有匹配现有 ASCII key 规则，或精确命中已批准 PRD 的中文 key 集合时才可继续；其它 Unicode key 仍为 malformed；
- 已知英文 key 和精确中文 key 在存入 fields 前先标记 schema language 并映射到同一 semantic key；同一文档出现两种已知 language 即返回 `mixed_schema`，不得等待字段读取阶段；
- 未知但符合现有 ASCII key 规则的 legacy 扩展字段继续按当前方式保留或忽略，避免缩窄英文兼容输入；它们不被误判为中文 schema；
- value alias 按字段语境覆盖文档类型、范围、理解确认、用户批准和独立评审；
- duplicate tracking 在写入 fields 前使用归一化 semantic key，因此同语言重复、中英文双写和同义重复都失败关闭；
- inspector CLI 参数、退出码、issue JSON 结构和成功 JSON 字段保持不变；可新增稳定的 `mixed_schema` 或 `unsupported_localized_value` issue，但不得删除或改义现有 issue。

### 技术规格与计划工作流

Skill reference 明确从文档当前 schema 读取和写回批准元数据。英文历史 spec/plan 使用现有键值；新中文 spec/plan 使用 PRD 规定的中文键值。Agent-facing 合同必须列出完整映射并要求先判 schema、再归一化、最后计算门禁，避免依赖自然语言猜测。

### Development prompt discovery

`skills/generating-development-prompts/scripts/discover_context.py` 的 plan frontmatter reader 增加本地 plan alias normalization，并把 frontmatter parser 与 legacy header parser 明确拆开：

- frontmatter raw parser 保留现有 scalar 限制，只额外接受已批准 plan schema 的精确中文 key；在生成 record 前完成 schema 分类、semantic duplicate 检测和 key normalization；未知 Unicode key 仍不受支持；
- 中文 `计划评审状态`、`计划评审角色`、`计划评审日期` 分别归一化为现有 review 语义；
- 中文“已通过”映射为 `approved`，中文“待评审”映射为 `not-approved`；其它不受支持的中文状态映射为 `unknown`；
- `chinese-current` plan 必须同时包含文档类型“实施计划”、合法 stable topic、非空技术规格路径、技术规格用户批准“已批准”和计划评审状态；缺少任一字段即为 `unknown`；
- 中文计划评审为“已通过”时必须同时存在唯一、非空的计划评审角色和 ISO 日期；为“待评审”时角色和日期必须不存在；生命周期字段不一致即为 `unknown`；
- 完整英文 plan 保持当前行为，包括显式非 `approved` 的可靠英文状态映射为 `not-approved`；
- raw semantic duplicate、mixed schema、malformed 或 quoted/multiline 值映射为 `unknown`；
- 无 frontmatter 的 legacy header 使用独立的现有 ASCII parser，只接受 `Review-Status`、`Reviewer`、`Reviewed-At` 等英文格式；不得因 frontmatter 支持中文而接受中文 header。

该 discovery 接口不扩张为通用 plan validator：它只对本功能引入的 `chinese-current` plan 校验上述固定字段和生命周期，以防残缺新格式伪造批准；对 `english-legacy` frontmatter 继续只提取现有 review 字段，不新增文档类型、topic 或 spec path 必填要求。

`skills/generating-development-prompts/references/discovery-policy.md` 同步成为本功能的生产合同：它必须明确中文 plan 需要完整固定字段和一致生命周期、英文 legacy plan 保持现有 review-only 兼容、schema 混用失败关闭、中文 review 值映射，以及 legacy header 仍只接受英文。脚本、policy 和测试不得出现互相矛盾的接受范围。

### 文档和评估证据

`docs/workflow.md`、`CHANGELOG.md` 和 `skills/generating-development-prompts/references/discovery-policy.md` 记录新建中文 schema、旧英文兼容、canonical 不变、无隐式迁移以及仅英文 legacy header。三个受影响 Skill 分别增加合同测试和新鲜 evaluation case；`evaluations/registry.json`、rubric、RED/GREEN 结果与 freshness metadata 按现有流程更新。

## API 与技术接口

### PRD inspector CLI

命令接口保持不变：

```text
inspect_product_requirements.py --repo-root REPO_ROOT --requirements REQUIREMENTS_PATH --expected-topic STABLE_TOPIC --expected-scope SCOPE
```

成功和失败均继续输出现有英文 JSON 字段。中文文档只扩展被接受的输入表示，不改变 `status`、`specification_gate`、`issues` 或 requirements 字段的含义。

### Development prompt discovery CLI

`discover_context.py` 的命令参数和 JSON 输出不变。plan review 仍返回：

```text
status: approved | not-approved | unknown
reviewer: string | null
reviewed_at: string | null
```

### 文档 schema 映射

中文 raw key 与英文 legacy key 归一化到同一个内部语义字段。PRD、spec、plan 的完整键名和值集合以批准 PRD 的三张字段表和生命周期矩阵为权威输入；技术实现不得自行缩写、同义替换或新增“未知”“未通过”“未开放”等有效持久化值。

## 命令结果与失败矩阵

| 结果 ID | 命令或异步完成阶段 | 前置条件 | 结果类型 | 客户端可见结果 | 事务、回滚与副作用 | 调用方动作 | 保证 ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `O-01` | PRD 创建完成 | 功能已生效，目标文件此前不存在，摘要已确认 | 成功 | 新 PRD 只有完整中文 frontmatter，批准与评审为待处理状态 | 单文件写入；不改写历史文档 | 进入既有评审流程 | `G-01` |
| `O-02` | spec 创建完成 | 中文或英文 PRD 已可靠批准，目标 spec 不存在 | 成功 | 新 spec 只有完整中文 frontmatter，来源门禁为已开放，当前规格批准与评审为待处理 | 单文件写入；PRD 不变 | 进入既有 spec 评审流程 | `G-01` |
| `O-03` | plan 创建完成 | 当前 spec 的独立评审和用户批准均可靠，目标 plan 不存在 | 成功 | 新 plan 只有完整中文 frontmatter，计划评审为待处理 | 单文件写入；spec 不变 | 进入既有 plan 评审流程 | `G-01` |
| `O-04` | PRD inspector | 完整、已批准的中文 PRD 与显式 topic/scope 一致 | 成功 | 退出码 0；英文 JSON 返回 `status: approved`、`specification_gate: open`、`issues: []` | 只读，无副作用 | 继续创建或复验 spec | `G-02` |
| `O-05` | PRD inspector | 完整、已批准的历史英文 PRD 与显式 topic/scope 一致 | 成功 | 与 `O-04` 相同的英文 JSON 门禁结果 | 只读，不转换文件 | 继续既有流程 | `G-02` |
| `O-06` | PRD inspector | PRD 出现 mixed schema、语义重复、冲突或不受支持中文值 | 校验 | 英文 JSON 返回 `status: unknown`、`specification_gate: blocked` 和可定位 issue | 只读，不修复文件 | 修正文档元数据后重试 | `G-03` |
| `O-07` | plan discovery | 完整中文 plan 的计划评审为已通过，并有唯一角色和日期 | 成功 | `documents.plan.review` 返回 `approved`，角色和日期原样保留 | 只读，无副作用 | 按既有路由与实施门判断继续 | `G-04` |
| `O-08` | plan discovery | 完整历史英文 plan 的 `review_status` 为 `approved` | 成功 | 与 `O-07` 相同的英文 JSON review 语义 | 只读，不转换文件 | 按既有流程继续 | `G-04` |
| `O-09` | plan discovery | 完整中文 plan 的计划评审为待评审 | 状态 | `documents.plan.review.status` 返回 `not-approved` | 只读，无副作用 | 保留实施阻断门 | `G-04` |
| `O-10` | plan discovery | plan 出现 mixed schema、语义重复、冲突、不受支持中文状态或 malformed frontmatter；或 chinese-current plan 缺少文档类型、topic、spec path、spec 批准、review 状态，或已通过但缺角色/日期 | 校验 | `documents.plan.review.status` 返回 `unknown`，不使用残缺字段、reviewer 或日期代替完整批准 | 只读，不修复文件 | 修正文档元数据和生命周期后重试 | `G-03` |
| `O-11` | 八字段或十四字段 handoff | 输入文档为受支持的中文 schema | 成功 | 内部 handoff 仍使用原英文 canonical 字段和值；用户可见状态视图保持当前合同 | 不修改 renderer 或门禁真值表 | 使用既有 handoff 和路由 | `G-05` |
| `O-12` | 历史英文文档只读或不涉及批准状态的正文维护 | 文件在功能生效前已存在且使用完整英文 schema | 无变化 | frontmatter 保持原英文内容，不产生本地化提示 | 不改元数据、不做格式迁移 | 继续原文档流程 | `G-06` |
| `O-13` | PRD/spec/plan 创建 | 目标路径已存在，但用户未把它识别为当前文档 | 冲突 | 报告已有文件并停止，不声称创建成功 | 文件保持原字节，不覆盖、不转换 schema | 用户确认恢复现有文档或选择新路径 | `G-07` |
| `O-14` | PRD/spec/plan 创建 | 对应摘要确认、PRD 门禁或 spec 双批准前置条件不成立 | 校验 | 报告真实 pending/unknown 状态和关闭的下游门禁 | 不创建目标文件 | 补齐当前前置条件后重新进入创建阶段 | `G-07` |
| `O-15` | 新建或批准/评审写回 | 本地写入明确失败且确认没有应用 | 持久化 | 报告本地持久化失败，不声称文档或批准已更新 | 目标保持写入前状态；没有部分成功授权 | 修复权限或文件问题后从原状态重试 | `G-07` |
| `O-16` | 新建或批准/评审写回完成回调 | 工具返回中断、超时或其它无法确认是否应用的结果 | 未知 | 报告写入结果待核对，不进入评审、批准或下游门禁 | 提交状态未知；不重复写入 | 先只读重读目标并执行精确核对 | `G-07` |
| `O-17` | 写入后核对 | 重读结果与本次预期完整内容及 schema 精确一致 | 成功 | 确认写入已应用；状态按文档当前内容计算 | 单文件结果已确认，不再重复写入 | 继续当前评审或门禁流程 | `G-07` |
| `O-18` | 写入后核对 | 重读确认本次写入完全未应用，且旧内容完整可靠 | 持久化 | 报告确认未应用；不提升批准或门禁 | 旧文件保持完整，没有本次副作用 | 修复原因后可安全重试一次 | `G-07` |
| `O-19` | 写入后核对 | 文件部分变化、不可读、与预期和旧内容均不一致，或仍无法判断 | 未知 | 报告无法确认的持久化状态并保持全部依赖门禁关闭 | 不自动覆盖、不回滚、不采用部分批准 | 停止并要求人工检查当前文件 | `G-07` |
| `O-20` | plan 创建前 spec 校验 | 中文 spec 缺字段、mixed schema、语义重复、冲突或包含不受支持状态 | 校验 | spec 状态不可靠，plan 不创建，实施门禁保持关闭 | spec 只读，plan 无文件副作用 | 修正 spec 并重新独立评审和用户批准 | `G-08` |
| `O-21` | 中文 PRD/spec/plan 批准或评审写回 | 当前中文文档版本取得对应真实批准，写入并核对成功 | 成功 | 只使用同一中文 schema 更新状态，并按生命周期增加中文角色/日期键 | 单文件状态前进；canonical 事实不变 | 继续下一既有门禁 | `G-01` |
| `O-22` | 历史英文 PRD/spec/plan 批准、失效或重新评审写回 | 当前文件属于 english-legacy，写入并核对成功 | 成功 | 只使用原英文 schema 更新或重置状态，不转换字段和值 | 单文件状态变化；没有本地化 diff | 继续既有门禁或重新评审 | `G-06` |

## 数据模型与实体关系

本功能没有业务数据库或持久化实体。唯一新增的技术模型是进程内 `DocumentMetadataSchema` 概念：

- `language`: `english-legacy | chinese-current`；
- `semantic_key`: 既有英文内部字段名；
- `canonical_value`: 既有英文内部值或原样技术值；
- `raw_key`、`raw_value`: 文档中的单一实际表示。

raw 文档到 canonical 语义是一对一映射。一个 raw 文档只能属于一个 language schema；多个 raw 字段映射到同一 semantic key 时整体不可靠。该模型只在每个 Skill 内部使用，不形成跨 Skill import 或新公共文件格式。

## 数据库事务与锁语义

不适用。本功能只读写 Git 工作区内的 Markdown 文件，不使用数据库、WAL、事务隔离、共享锁或读转写升级。单文件写入继续遵循各 Skill 现有写入和写后验证流程；不存在需要新增 busy、deadlock、timeout 或数据库回滚分类的路径。

## 状态转换、迁移边界与一致性

### 文档生命周期

- 新中文 PRD：已确认摘要 → 用户批准待处理/独立评审待处理 → 独立评审已通过 → 用户已批准。
- 新中文 spec：来源 PRD 已批准且规格门禁已开放 → 当前规格批准待处理/独立评审待处理 → 独立评审已通过 → 用户已批准。
- 新中文 plan：来源 spec 已批准 → 计划评审待处理 → 计划评审已通过。

每次状态写回保持原文档 schema。评审提出修改不写“未通过”，而是保持或重置为对应待评审状态。无可靠元数据时，`unknown` 只存在于 inspector/discovery/handoff 的派生结果，不写回文档冒充生命周期状态。

### 迁移边界

- 不存在自动迁移命令、后台迁移或批量转换。
- 文件在功能生效前已经存在即属于 `english-legacy`，无论其后是否修改正文、失效批准或重新评审，均保持英文 frontmatter。
- 功能生效后从头创建的文件属于 `chinese-current`，后续始终保持中文 frontmatter。
- 当前 PRD 和本技术规格创建于功能实现前，因此保持英文 frontmatter；这不构成验收失败。

### 一致性边界

- raw schema 只决定文档表示；canonical 状态继续决定门禁。
- English 和 Chinese 文档表达相同事实时必须归一化为相同 canonical 结果。
- 任何 schema 识别或 value mapping 失败都不能部分采用已批准字段；受影响文档状态整体按现有失败关闭规则处理。
- 三个 Skill 因自包含要求各自维护必要映射；合同测试必须验证重叠字段字面一致，防止映射漂移。

## 错误与不确定性

- PRD inspector 对 mixed schema 使用稳定 issue，并令 PRD 状态为 `unknown`、规格门禁关闭；不得按键出现顺序选择语言。
- PRD 中文键合法但状态值不受支持时，受影响批准字段为 `unknown`，并保留现有 invalid-state issue 语义或增加稳定的本地化值 issue。
- Plan discovery 对 mixed schema、重复语义字段、不受支持中文状态、malformed frontmatter、缺少中文 plan 必填字段或“已通过”但缺少唯一角色/日期返回 `unknown`；reviewer 或日期本身不构成批准替代。
- 既有英文 explicit non-approved plan 状态继续映射为 `not-approved`，避免本地化变更破坏手动提示词兼容性。
- 新模板或 Agent 写出部分中文、部分英文时，下一读取阶段必然失败关闭；不得自动补全或静默重写。
- 本功能不涉及密钥、权限、资金、外部网络、不可信公开输入或敏感数据，不增加额外安全门禁。
- 当前没有需要用户选择的技术方案；在 Skill 自包含和旧文档兼容约束下，本地 alias normalization 是唯一不引入跨 Skill 运行时依赖的最小方案。

## 保证与测试追踪

| 保证 ID | 保证或失败契约 | 对应结果 ID 或状态 | 精确测试文件与名称 | 精确命令 | 可观察断言 |
| --- | --- | --- | --- | --- | --- |
| `G-01` | 三类新文档写出完整单套中文 frontmatter，并以同一中文 schema 完成批准和评审写回 | `O-01`、`O-02`、`O-03`、`O-21` | `skills/creating-product-requirements/tests/test_skill_contract.py::CreatingProductRequirementsContractTests::test_prd_template_uses_complete_chinese_frontmatter_contract`；`skills/creating-development-specs-and-plans/tests/test_skill_contract.py::CreatingSpecsAndPlansContractTests::test_spec_and_plan_templates_use_complete_chinese_frontmatter_contract`；`evaluations/creating-product-requirements/cases/17-localized-prd-approval-writeback.md`；`evaluations/creating-development-specs-and-plans/cases/22-localized-spec-plan-review-writeback.md` | `.venv/bin/python skills/creating-product-requirements/tests/test_skill_contract.py CreatingProductRequirementsContractTests.test_prd_template_uses_complete_chinese_frontmatter_contract`；`.venv/bin/python skills/creating-development-specs-and-plans/tests/test_skill_contract.py CreatingSpecsAndPlansContractTests.test_spec_and_plan_templates_use_complete_chinese_frontmatter_contract`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/17-localized-prd-approval-writeback.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-17`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/22-localized-spec-plan-review-writeback.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-22` | 模板包含全部中文键和值；前向场景中 PRD、spec、plan 的 pending→approved 写回只使用中文状态、角色和日期键，路径/topic/role 值原样，canonical 不变 |
| `G-02` | PRD inspector 对等接受完整中文新 PRD 和完整英文历史 PRD，并输出相同英文 canonical 门禁 | `O-04`、`O-05` | `skills/creating-development-specs-and-plans/tests/test_inspect_product_requirements.py::InspectProductRequirementsTests::test_approved_chinese_prd_opens_gate`；`InspectProductRequirementsTests::test_legacy_english_prd_still_opens_gate` | `.venv/bin/python skills/creating-development-specs-and-plans/tests/test_inspect_product_requirements.py InspectProductRequirementsTests.test_approved_chinese_prd_opens_gate InspectProductRequirementsTests.test_legacy_english_prd_still_opens_gate` | 两种输入均返回 exit 0、`status == approved`、`specification_gate == open`、`issues == []`，且输出字段集合不变 |
| `G-03` | mixed schema、语义重复、冲突、不受支持中文状态或残缺 chinese-current plan 失败关闭 | `O-06`、`O-10` | `skills/creating-development-specs-and-plans/tests/test_inspect_product_requirements.py::InspectProductRequirementsTests::test_mixed_or_duplicate_localized_prd_is_unknown`；`skills/generating-development-prompts/tests/test_discover_context.py::DiscoverContextReviewTests::test_mixed_or_invalid_chinese_plan_metadata_is_unknown`；`DiscoverContextReviewTests::test_incomplete_chinese_plan_or_approved_without_review_metadata_is_unknown` | `.venv/bin/python skills/creating-development-specs-and-plans/tests/test_inspect_product_requirements.py InspectProductRequirementsTests.test_mixed_or_duplicate_localized_prd_is_unknown`；`.venv/bin/python skills/generating-development-prompts/tests/test_discover_context.py DiscoverContextReviewTests.test_mixed_or_invalid_chinese_plan_metadata_is_unknown DiscoverContextReviewTests.test_incomplete_chinese_plan_or_approved_without_review_metadata_is_unknown` | PRD JSON 为 unknown/blocked 且有稳定 issue；mixed、非法、缺必填字段、已通过但缺角色/日期的中文 plan review 均为 unknown；不选择批准值或改写文件 |
| `G-04` | plan discovery 对等接受中文和英文 plan，可靠区分已通过与待评审并保留角色日期；中文只适用于 frontmatter | `O-07`、`O-08`、`O-09` | `skills/generating-development-prompts/tests/test_discover_context.py::DiscoverContextReviewTests::test_chinese_plan_frontmatter_maps_review_lifecycle`；既有 `test_frontmatter_approved_includes_optional_metadata`；`DiscoverContextReviewTests::test_chinese_legacy_header_is_not_accepted`；`skills/generating-development-prompts/tests/test_skill_contract.py::SkillContractTests::test_discovery_policy_separates_chinese_frontmatter_from_english_header`；`evaluations/generating-development-prompts/cases/07-localized-plan-frontmatter.md` | `.venv/bin/python skills/generating-development-prompts/tests/test_discover_context.py DiscoverContextReviewTests.test_chinese_plan_frontmatter_maps_review_lifecycle DiscoverContextReviewTests.test_frontmatter_approved_includes_optional_metadata DiscoverContextReviewTests.test_chinese_legacy_header_is_not_accepted`；`.venv/bin/python skills/generating-development-prompts/tests/test_skill_contract.py SkillContractTests.test_discovery_policy_separates_chinese_frontmatter_from_english_header`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name generating-development-prompts --phase green --case evaluations/generating-development-prompts/cases/07-localized-plan-frontmatter.md --skill-dir skills/generating-development-prompts --output-root work/evaluations/generating-development-prompts/green-07` | 中文已通过与英文 approved frontmatter 均返回 approved；中文待评审返回 not-approved；reviewer/date 原样；中文 header 保持 unknown；policy 与脚本接受范围一致 |
| `G-05` | 中文文档输入不改变英文 canonical 八/十四字段、renderer 或门禁真值表 | `O-11` | `tests/test_handoff_renderer.py::HandoffRendererRepositoryTests::test_workflow_full_view_has_exact_fourteen_lines`；`HandoffRendererRepositoryTests::test_gate_truth_tables_reject_inconsistent_claims`；`tests/test_repository_contract.py::RepositoryContractTests::test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`；`evaluations/creating-product-requirements/cases/17-localized-prd-approval-writeback.md`；`evaluations/creating-development-specs-and-plans/cases/22-localized-spec-plan-review-writeback.md`；`evaluations/generating-development-prompts/cases/07-localized-plan-frontmatter.md` | `.venv/bin/python tests/test_handoff_renderer.py HandoffRendererRepositoryTests.test_workflow_full_view_has_exact_fourteen_lines HandoffRendererRepositoryTests.test_gate_truth_tables_reject_inconsistent_claims`；`.venv/bin/python tests/test_repository_contract.py RepositoryContractTests.test_localized_document_frontmatter_and_canonical_handoff_contracts_are_separate`；`.venv/bin/python scripts/check.py --skill creating-product-requirements`；`.venv/bin/python scripts/check.py --skill creating-development-specs-and-plans`；`.venv/bin/python scripts/check.py --skill generating-development-prompts` | 现有 renderer 字节和真值表不变；跨 Skill 合同明确分离中文文档 schema 与英文 canonical；三个新鲜场景只改变文档 frontmatter 表示 |
| `G-06` | 历史英文 PRD、spec、plan 在维护、失效、批准和重新评审时保持英文，不产生隐式迁移 | `O-12`、`O-22` | `skills/creating-product-requirements/tests/test_skill_contract.py::CreatingProductRequirementsContractTests::test_existing_english_documents_keep_their_schema`；`skills/creating-development-specs-and-plans/tests/test_skill_contract.py::CreatingSpecsAndPlansContractTests::test_existing_english_documents_keep_their_schema`；`evaluations/creating-product-requirements/cases/18-legacy-english-prd-rereview.md`；`evaluations/creating-development-specs-and-plans/cases/23-legacy-english-spec-rereview.md`；`evaluations/creating-development-specs-and-plans/cases/24-legacy-english-plan-rereview.md` | `.venv/bin/python skills/creating-product-requirements/tests/test_skill_contract.py CreatingProductRequirementsContractTests.test_existing_english_documents_keep_their_schema`；`.venv/bin/python skills/creating-development-specs-and-plans/tests/test_skill_contract.py CreatingSpecsAndPlansContractTests.test_existing_english_documents_keep_their_schema`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/18-legacy-english-prd-rereview.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-18`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/23-legacy-english-spec-rereview.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-23`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/24-legacy-english-plan-rereview.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-24` | 三个前向场景在真实失效或评审写回后仍只含英文 metadata；没有中文 key/value、格式迁移或仅本地化 diff |
| `G-07` | 文档创建和状态写回对已有目标、前置失败、本地持久化失败与不确定完成采用明确的无写入或核对分支 | `O-13`、`O-14`、`O-15`、`O-16`、`O-17`、`O-18`、`O-19` | `skills/creating-product-requirements/tests/test_skill_contract.py::CreatingProductRequirementsContractTests::test_authoring_write_outcomes_require_readback_reconciliation`；`skills/creating-development-specs-and-plans/tests/test_skill_contract.py::CreatingSpecsAndPlansContractTests::test_authoring_write_outcomes_require_readback_reconciliation`；`evaluations/creating-product-requirements/cases/19-localized-prd-write-reconciliation.md`；`evaluations/creating-development-specs-and-plans/cases/26-localized-spec-plan-write-reconciliation.md` | `.venv/bin/python skills/creating-product-requirements/tests/test_skill_contract.py CreatingProductRequirementsContractTests.test_authoring_write_outcomes_require_readback_reconciliation`；`.venv/bin/python skills/creating-development-specs-and-plans/tests/test_skill_contract.py CreatingSpecsAndPlansContractTests.test_authoring_write_outcomes_require_readback_reconciliation`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-product-requirements --phase green --case evaluations/creating-product-requirements/cases/19-localized-prd-write-reconciliation.md --skill-dir skills/creating-product-requirements --output-root work/evaluations/creating-product-requirements/green-19`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/26-localized-spec-plan-write-reconciliation.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-26` | 已有目标与前置失败无写入；明确未应用可重试；不确定完成先重读并分别得到已应用、未应用或仍未知，不重复写入、不采用部分批准 |
| `G-08` | 不可靠的中文 spec 不能成为 plan 的稳定输入 | `O-20` | `skills/creating-development-specs-and-plans/tests/test_skill_contract.py::CreatingSpecsAndPlansContractTests::test_mixed_localized_spec_blocks_plan`；`evaluations/creating-development-specs-and-plans/cases/25-localized-spec-metadata-fail-closed.md` | `.venv/bin/python skills/creating-development-specs-and-plans/tests/test_skill_contract.py CreatingSpecsAndPlansContractTests.test_mixed_localized_spec_blocks_plan`；`.venv/bin/python scripts/run_skill_evaluations.py --skill-name creating-development-specs-and-plans --phase green --case evaluations/creating-development-specs-and-plans/cases/25-localized-spec-metadata-fail-closed.md --skill-dir skills/creating-development-specs-and-plans --output-root work/evaluations/creating-development-specs-and-plans/green-25` | mixed、重复、缺失或不受支持的中文 spec metadata 保持 spec 状态不可靠，不创建 plan，实施门禁关闭 |

所有 Outcome ID 均至少映射到一个 Guarantee ID；所有 Guarantee ID 均有精确测试、命令和独立可观察断言。实施计划必须保留 `O-01` 至 `O-22` 和 `G-01` 至 `G-08`，不得产生孤立 outcome、保证或必需测试。

## 测试与文档

### RED→GREEN

- `creating-product-requirements`：先让模板完整中文 schema、中文批准写回、历史英文 PRD 重新评审保持英文，以及写入不确定性核对合同失败；再修改 authoring contract 与模板。前向 cases `17`、`18`、`19` 分别证明中文生命周期写回、english-legacy 维护和已应用/未应用/仍未知三种核对分支。
- `creating-development-specs-and-plans`：先让中文 raw key parsing、mixed schema fail-closed、中文 spec/plan 模板、中文 lifecycle writeback、english-legacy spec/plan 重新评审、写入核对和不可靠中文 spec 阻断 plan 的合同失败；再实现 raw-stage alias normalization 与模板/合同。前向 cases `22` 至 `26` 分别覆盖中文写回、英文 spec、英文 plan、中文 spec 失败关闭和持久化核对。
- `generating-development-prompts`：先让完整中文 plan frontmatter、残缺中文 plan、已通过但缺角色/日期、mixed schema、中文 header 继续拒绝及 discovery policy 同步测试失败，再拆分 frontmatter/header parser 并实现 raw-stage plan alias normalization；case `07` 验证完整中文已批准 plan 可进入原有路由判断且 canonical 不变。
- RED 必须来自目标行为缺失，不得改写或降低既有英文兼容断言。

### 定向与完整验证

- 分别运行 `.venv/bin/python scripts/check.py --skill creating-product-requirements`、`.venv/bin/python scripts/check.py --skill creating-development-specs-and-plans`、`.venv/bin/python scripts/check.py --skill generating-development-prompts`。
- 在 Python 3.9 和 Python 3.14 下分别运行三个受影响 Skill 的 unittest discovery；PRD inspector 和 prompt discovery 的新边界不得只在单一版本验证。
- 运行 `.venv/bin/python scripts/check.py --full`，确认五 Skill plugin、官方 validator、安装边界和未受影响 Skill 回归通过。
- 运行 `git diff --check`，并复查最新完整 diff 没有真实本机路径、凭证、历史文档批量迁移或 renderer canonical 变化。

### 文档同步

- 更新 `docs/workflow.md` 的文档语言、兼容和 canonical 边界，并更新 `skills/generating-development-prompts/references/discovery-policy.md` 的双 schema frontmatter 与仅英文 legacy header 合同。
- 更新 `CHANGELOG.md` 中三个受影响 Skill 及 Repository 的当前事实。
- README、安装命令、plugin manifest、许可证和发布状态不变；没有证据要求更新时不产生无关 diff。

## 验收标准

1. 功能生效后从头创建的 PRD、技术规格和实施计划分别写出已批准 PRD 规定的完整单套中文 frontmatter。
2. 新中文文档的 topic、路径、ISO 日期、置信度数字和 reviewer role 值保持原格式。
3. 中文 PRD 与语义等价的英文历史 PRD 通过 inspector 后得到相同英文 JSON canonical 状态与门禁结果。
4. 中文已批准 plan 与语义等价的英文已批准 plan 通过 discovery 后均得到 `approved`，中文待评审 plan 得到 `not-approved`。
5. mixed schema、同义重复、冲突、malformed 或不受支持中文状态均得到 unknown/blocked，不选择更有利状态、不改写文件。
6. 现有英文 PRD、spec、plan 在维护、批准失效和重新评审时继续使用英文 frontmatter，不发生隐式转换。
7. 八字段、十四字段、renderer、CLI 参数、JSON 输出字段和门禁真值表保持当前英文 canonical 契约。
8. 三个受影响 Skill 分别具备新鲜 RED、GREEN、定向验证和前向场景；Python 3.9、3.14 与完整 plugin 门通过。
9. 最新完整 diff 由未参与实现的独立评审者检查并批准；评审修订后重跑受影响验证并由同一评审者复审至收敛。
10. 未修改 Skill UI 名称、历史文档、其它 YAML、依赖、安装状态、提交历史或外部状态。
11. 中文 key 在 raw frontmatter 解析阶段按精确白名单处理；未知 Unicode key 不因放宽 regex 被接受，plan 的 legacy header 继续只识别现有英文格式。
12. 文档新建或状态写回发生已有目标、前置失败、明确未应用或完成状态未知时，分别执行无写入、可重试或先读后核对分支；核对结果按已应用、未应用和仍未知拆分，任何分支都不采用部分批准。
13. 中文 PRD/spec/plan 的批准与评审写回以及历史英文 PRD/spec/plan 的维护、失效与重新评审均有独立前向场景，不能只由模板或合同文本断言代替。
14. `chinese-current` plan 缺少文档类型、topic、spec path、spec 批准或 review 状态，或声明已通过但缺少唯一角色/ISO 日期时，prompt discovery 返回 unknown；相同限制不反向收紧既有英文 review-only 与英文 header 兼容输入。
