---
document_type: design
topic: workflow-handoff-optimization
requirements_path: docs/requirements/2026-07-17-workflow-handoff-optimization.md
requirements_topic: workflow-handoff-optimization
requirements_scope: phase
requirements_understanding_confidence: 98
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: approved
approved_at: 2026-07-17
independent_review: approved
independent_reviewer: independent-spec-reviewer
independent_reviewed_at: 2026-07-17
---

# 开发工作流交接体验优化技术规格

## 目标

- 让 PRD、技术规格和实施计划的标题、章节与解释性正文默认使用中文，同时保持技术标识符和机器可读字段稳定。
- 在 PRD 全部门禁打开后，由主 Agent 在同一会话无条件进入技术规格流程，不再要求用户重复调用 skill。
- 在技术规格与计划全部门禁打开且十四字段交接完成后，由主 Agent 自动进入会话适用性判断。
- 将 `generating-development-prompts` 扩展为“先判断会话去向、仅在需要时生成提示词”的交接入口，同时保留用户显式生成带阻断门提示词的既有能力。
- 让所有生成的新会话提示词位于单一、完整且可一键复制的 Markdown 代码框内。
- 对本项目三个项目级 Agent 形成逐角色覆盖结论和保留依据，本阶段不删除任何配置。

## 非目标

- 不新增 workflow orchestrator 服务、持久化会话状态、数据库、网络接口或新的 skill。
- 不让任一 skill 导入兄弟 skill 源码、读取兄弟 skill 安装目录或依赖固定的本机安装路径。
- 不自动创建、打开、发送或操作用户可见的 Codex 会话。
- 不在会话路由后自动开始实施；建议当前会话时仍等待用户明确批准。
- 不迁移、修改或安装 `agent-rules` 中的全局 Agent。
- 不在本阶段删除 `.codex/agents/` 中的任何项目级角色。
- 不改变 PRD、spec、plan 已有的理解确认、独立评审、用户批准和计划评审真实性规则。

## 当前证据

- `skills/creating-product-requirements/SKILL.md` 当前把已批准 PRD 定义为终端交付，并明确禁止调用兄弟 skill；`references/review-and-handoff.md` 要求每个回复以 requirements 八字段结束。
- `skills/creating-development-specs-and-plans/SKILL.md` 当前把十四字段文档交接定义为终端交付，并禁止调用兄弟 skill；其 plan 只有在真实独立评审通过后才使 `implementation_gate` 打开。
- `skills/generating-development-prompts/SKILL.md` 当前在发现成功后总是渲染提示词，并要求 renderer stdout 成为完整回复，即使用户要求 Markdown 代码框也不得包装。
- `skills/generating-development-prompts/scripts/discover_context.py` 已能只读收集仓库、规则、spec、plan、三态计划评审、歧义、错误和警告，输出 `schema_version: 1` JSON。
- `skills/generating-development-prompts/scripts/render_prompt.py` 已通过结构化 JSON 输入验证并安全替换模板变量，但当前 stdout 是普通 Markdown 正文，没有复制容器。
- 三个 authoring/prompt skill 的 `assets/` 模板中，PRD、spec、plan 模板章节为英文；开发提示词正文已经主要使用中文。
- `skills/*/tests/test_skill_contract.py` 固化了现有终端边界、固定字段和 prompt 无代码框合同；`tests/test_repository_contract.py` 已覆盖 PRD inspector 与 prompt discovery 的公共 CLI 集成。
- `docs/workflow.md` 规定八字段、十四字段以及显式 spec/plan 路径是跨 skill 的稳定交接接口；公共契约变化必须同步上下游集成测试。
- `.codex/agents/skill-reviewer.toml`、`final-reviewer.toml` 和 `workflow-final-reviewer.toml` 是本仓库版本化、对维护者稳定可用的项目专属评审角色。个人全局 Agent 并非本 plugin 的安装保证，不能单独证明这些角色可删除。
- 已批准 PRD 通过 `inspect_product_requirements.py` 校验：`status: approved`、`specification_gate: open`，topic 与 scope 分别为 `workflow-handoff-optimization`、`phase`。

## 行为与边界

### 中文文档合同

- `creating-product-requirements`、`creating-development-specs-and-plans` 生成的 PRD、spec 和 plan 使用中文文档标题、中文章节名、中文说明和中文占位提示。
- YAML frontmatter 键、允许值、skill 名称、命令、API、字段、协议、文件名、路径和代码标识符保持既有英文或技术形式。
- skill 内部开发说明可以继续使用现有语言；本项只约束面向用户生成的自然语言文档和交接说明。
- UI metadata 是否本地化不属于文档输出合同，不在本阶段强制修改。

### PRD 到技术规格的阶段转换

- PRD 的理解确认、独立评审和用户批准全部有效后，`creating-product-requirements` 先写入并验证当前批准元数据，构造完整 requirements 八字段记录。
- 主 Agent 随后以八字段记录中的显式 `requirements_path`、`requirements_topic`、`requirements_scope` 作为独立输入，在同一会话选择 `creating-development-specs-and-plans`。
- 自动转换不读取下游 skill 的源码或安装目录。下游 skill 是否可用由当前运行时暴露的 skill 能力决定；不可用时返回能力缺口，PRD 八字段仍保持真实状态。
- 自动转换路径中，最终用户回复由下游十四字段合同接管。十四字段的前八项必须逐值保留已验证的 requirements 八字段，因此不在同一回复中制造两个相互竞争的“固定结尾”。
- PRD 未批准、审批失效或 inspector 不能确认 `specification_gate: open` 时，不选择下游流程。

### 技术规格与计划到会话路由的阶段转换

- `creating-development-specs-and-plans` 继续按现有顺序创建、评审并取得用户对 spec 的批准，再创建和独立评审 plan。
- 只有 PRD gate 仍打开、spec 独立评审与用户批准有效、plan 真实评审通过时，才构造 `implementation_gate: open` 的完整十四字段记录。
- 主 Agent 验证十四字段后，在同一会话进入 `generating-development-prompts` 的会话路由流程，不要求用户再次输入 skill 名称、spec/plan 路径或开发目标。
- 自动路由回复必须保留已验证的十四字段并仍以该记录结尾。路由结论、推荐理由和可复制提示词位于十四字段之前。
- 十四字段缺失、冲突或未验证时不自动路由；既有十四字段阻塞回复保持不变。

### 手动提示词兼容

- 用户在任意会话显式请求新会话开发提示词时，`generating-development-prompts` 继续支持显式或自动发现 spec、plan 和仓库上下文。
- plan 为 `not-approved` 或 `unknown` 时仍允许生成提示词，但提示词中的实施阻断门必须保持，不能把生成行为升级为实施授权。
- 手动调用没有上游十四字段时，不伪造 requirements 或双门状态，也不要求输出十四字段；它只报告 discovery 能可靠确认的 spec、plan 与评审状态。

## 组件与控制流

### 1. `creating-product-requirements`

- 保留产品发现、95% 理解门、摘要确认、PRD 写入、独立评审和用户批准职责。
- 将“任何情况都不得调用兄弟 skill”的绝对边界收缩为：不得创建 spec/plan 内容，不得依赖兄弟源码或安装路径；PRD 批准后允许主 Agent使用已验证八字段切换到下游 skill。
- `references/review-and-handoff.md` 区分两种结束方式：未进入下游时回复仍以八字段结束；成功进入下游时八字段作为十四字段前缀被保留，最终回复遵循下游合同。
- `assets/prd-template.md` 仅本地化面向用户的标题、章节和占位说明，不改变 frontmatter schema。

### 2. `creating-development-specs-and-plans`

- 保留 PRD inspector、spec 双批准门、plan 独立评审门和三态 plan review 语义。
- 接受上游显式八字段作为正常入口，不从 PRD 文件名或正文反推 expected topic/scope。
- plan 审批完成后先重新校验 PRD、spec、plan 和十四字段，再由主 Agent切换到会话路由。
- 未进入路由或任何门禁阻塞时，回复继续以十四字段结束；进入路由后，路由回复也必须在末尾原样保留这十四字段。
- `assets/spec-template.md` 和 `assets/plan-template.md` 本地化标题、章节、标签和占位说明，保持 frontmatter schema 与技术路径格式不变。

### 3. `generating-development-prompts`

- 扩展 description 和 workflow，使其同时覆盖显式提示词请求以及由已批准十四字段触发的会话路由。
- 新增一层 `references/session-routing-policy.md`，负责定义证据输入、三态结果、优先级、可解释理由和上游十四字段保留规则；不新增持久化脚本或评分数据库。
- `discover_context.py` 继续负责客观仓库证据，不读取聊天历史，也不决定会话去向；其 CLI 和 `schema_version: 1` 保持兼容。
- 主 Agent 将 discovery JSON、当前会话上下文、上游十四字段、可用权限、工具和 Agent 能力一起应用路由策略。新会话能力只能来自会话无关的仓库或平台事实、用户明确约束，或当前运行时能够验证的目标会话能力声明，不能从当前会话限制直接外推。
- 只有 `new-session` 结果或用户显式请求提示词时才调用 `render_prompt.py`；`current-session` 结果只给出理由并等待用户批准，`blocked` 结果只报告阻塞，除非用户随后显式请求带阻断门提示词。
- 自动路由路径允许在 renderer stdout 前添加简短中文结论与理由，并在其后附加原样十四字段；手动提示词路径可以只返回 renderer stdout。

### 4. `render_prompt.py` 与模板

- 保持 stdin JSON schema、JSON 嵌套深度上限、结构校验和模板变量替换逻辑不变；不新增输入字节数或字符数上限。
- renderer 先得到完整提示词正文，再选择长度大于正文中最长连续反引号序列的 Markdown fence，最少使用三个反引号，并以 `text` 信息字符串输出一个完整代码框。
- stdout 只包含一个可复制代码框及末尾换行，不把推荐理由、十四字段或其它执行内容混入代码框。
- 动态 fence 防止用户请求或文档内容中的反引号提前闭合复制区域；复制内容仍是完整提示词正文，不包含展示说明。

### 5. 项目 Agent 覆盖评估

- 在 `docs/agent-development.md` 增加逐角色评估表，比较稳定可用性、职责、输入证据、输出门禁、只读边界和外部状态限制。
- `skill-reviewer` 依赖本项目 skill 触发、RED/GREEN 证据、打包和跨 skill 契约，保留。
- `workflow-final-reviewer` 依赖完整五-skill plugin、评估证据和发布边界，保留。
- `final-reviewer` 虽与通用 final gate 角色部分重叠，但个人全局角色不是所有维护者的稳定依赖，且本角色明确覆盖本项目批准范围与集成证据，保留。
- 本阶段评估结论为无可执行删除候选；不修改 `.codex/agents/*.toml`。

## API 与技术接口

### requirements 八字段

- 字段名、顺序、允许值和 `specification_gate` 计算规则保持不变。
- 自动转换时八字段按下表映射为下游十四字段的前八项，不新增隐藏批准字段：

| requirements 八字段 | spec/plan 十四字段前缀 | 转换规则 |
|---|---|---|
| `requirements_path` | `requirements_path` | 字段名和值原样保留 |
| `requirements_topic` | `requirements_topic` | 字段名和值原样保留 |
| `requirements_scope` | `requirements_scope` | 字段名和值原样保留 |
| `understanding_confidence` | `requirements_understanding_confidence` | 只重命名字段，值原样保留 |
| `understanding_user_confirmation` | `requirements_understanding_confirmation` | 只重命名字段，值原样保留 |
| `requirements_user_approval` | `requirements_user_approval` | 字段名和值原样保留 |
| `requirements_independent_review` | `requirements_independent_review` | 字段名和值原样保留 |
| `specification_gate` | `specification_gate` | 字段名和值原样保留 |

- 映射成功但 spec/plan 尚未创建时，优先保留根据已确认 topic 可靠选定的默认绝对路径；只有路径本身无法可靠选择时才使用 `null`。不存在 spec 时两个 spec approval 为 `pending`，不存在 plan 时 `plan_review_status: not-approved`，`implementation_gate` 为 `blocked`。
- 在选择下游 skill 之前发现任一八字段缺失、值非法或 PRD 复验失败时，不进入下游、不构造十四字段；上游回复保留真实八字段或 `unknown` 状态并报告输入缺口。
- 主 Agent 已进入 `creating-development-specs-and-plans` 后，若 inspector 再次复验失败，必须仍输出完整十四字段：requirements 侧按既有 `unknown`/`not-approved` 映射关闭 `specification_gate`，spec/plan 侧保留所有可靠选定或已有路径及其真实状态，并令 `implementation_gate: blocked`，不得退回八字段回复。
- 下游必须使用显式 path/topic/scope 调用 PRD inspector，不能仅信任聊天摘要。

### spec/plan 十四字段

- 字段名、顺序、允许值和双门计算规则保持不变。
- 自动路由前必须重新验证并冻结当前回复使用的十四字段快照。
- 自动路由最终回复以同一十四字段快照结尾；路由流程不得修改文档批准状态。

### prompt discovery JSON

- `discover_context.py` 的参数、退出码和 `schema_version: 1` 保持不变。
- 会话路由不向 discovery JSON 伪造聊天上下文字段；聊天上下文由主 Agent在策略层读取。
- renderer 输入继续使用当前扩展后的 discovery 对象，包括 development goal、target branch、session rules 和 permission matrix。

### renderer stdout

- 成功 stdout 从普通提示词正文变为单个 Markdown 代码框，这是有意的用户可见输出变更。
- 代码框内部文本与既有模板渲染结果语义一致；失败 stderr JSON、错误码和无部分输出规则保持不变。
- 该变化对把 stdout 当作裸提示词正文解析的调用方属于 breaking contract change。仓库内搜索确认除 skill 与测试外没有机器调用方，但公开使用者仍需改为提取唯一代码框内容。
- plugin 当前为 `0.1.0 - Unreleased`，尚无已发布版本兼容承诺，因此本阶段保持 manifest `0.1.0`，不执行版本升级或发布；CHANGELOG 必须在未发布 `0.1.0` 下明确记录 stdout 迁移说明。

## 数据模型与实体关系

本阶段不引入持久化数据模型、数据库实体或跨进程共享状态。

- requirements 八字段和 spec/plan 十四字段是会话内不可变交接快照，来源仍是版本化文档与当前验证结果。
- 路由结果是 `current-session | new-session | blocked` 三态临时决策，不写入项目文件、缓存或用户目录。
- 项目 Agent 覆盖评估只写入公开维护文档，不成为运行时注册表或安装清单。

## 状态转换、迁移边界与一致性

### PRD 阶段

1. `requirements_gate_blocked`：任一理解、评审或用户批准门未满足，停留在 PRD workflow，回复以八字段结束。
2. `requirements_gate_open`：写入并验证用户批准，构造八字段。
3. `spec_transition`：下游 skill 可用时把八字段作为显式输入进入 spec workflow；不可用时返回能力缺口，不改变已批准 PRD。进入下游前复验失败仍使用八字段，进入下游后的复验失败始终使用完整十四字段并关闭双门。

### spec/plan 阶段

1. `spec_pending`：spec 未获独立评审或用户批准，回复十四字段且 implementation gate 阻塞。
2. `plan_pending`：spec 双批准有效但 plan 未真实评审通过，回复十四字段且 implementation gate 阻塞。
3. `implementation_gate_open`：重新验证 PRD、spec 和 plan，构造十四字段快照。
4. `routing_transition`：将快照交给会话路由；路由失败不回写文档批准状态。

### 路由阶段

按以下优先级产生唯一结果：

1. 上游十四字段不完整或 `implementation_gate` 非 `open`：自动路由不启动；显式提示词请求仍可带阻断门处理。
2. 存在能够跨会话成立的确定性阻塞证据：`blocked`。允许的证据仅包括会话无关的缺失或不可读必要文档、未开放且不能由换会话改变的批准门、适用于任何会话的仓库硬约束或用户权限限制、平台明确声明的目标会话能力缺口，或当前运行时能够验证的新会话能力边界。
3. 证据不足、证据冲突或无法可靠比较两个会话：`new-session`，理由标记不确定性。
4. 只有当前会话缺少工具、权限或 Agent 能力，而没有证据证明新会话同样受限：`new-session`，不得判定 `blocked`。
5. 当前会话存在无关主题、未解决冲突、明显上下文负担，或实施范围、复杂度、风险、持续时间更适合隔离：`new-session`。
6. 当前会话上下文完整一致、范围可控、工作区与批准状态明确，且所需权限、工具和 Agent 能力可用：`current-session`。

路由不使用总分阈值。每个结论必须列出实际命中的主要证据；没有证据时不得声称当前会话适合继续。

### 兼容与迁移

- 已有 PRD、spec 和 plan frontmatter 无需迁移。
- 已有显式 prompt 请求继续可用；唯一输出变化是成功提示词进入代码框。
- 将 renderer stdout 当作裸文本的调用方必须迁移为读取唯一 Markdown 代码框内容；不提供并行 raw 模式，避免同一生成入口产生两种用户可见成功合同。
- 既有 `discover_context.py` 调用者无需修改参数或 JSON 解析。
- skill 单独安装时仍可完成自身核心职责；下游 skill 不可用只阻断自动阶段转换，不使当前文档无效。

## 错误与不确定性

- PRD inspector 非零退出、输出不可解析或 identity 不匹配时，技术规格门保持阻塞，不创建或修改 spec。
- 自动转换找不到下游 skill 能力时，报告能力缺口和当前真实 handoff；不得读取猜测的安装目录补救。
- 八字段或十四字段在转换前发生变化时，丢弃旧快照并基于最新文档重新验证。
- 路由所需证据不足或相互冲突时，推荐新会话并说明不确定性。只有会话无关事实或可验证的目标会话能力证据才能支持 `blocked`；仅有当前会话限制时不得外推。
- renderer 输入错误继续返回机器可读 stderr 且 stdout 为空；不得输出半个代码框或残缺提示词。
- 提示词过长或包含 fence 字符时，动态 fence 只改变展示边界，不截断、转义或重写正文。
- 一键复制是否由目标 Codex 客户端实际提供必须在实现验证中确认；若客户端不为代码框提供复制能力，不能声称验收通过。
- 全局 Agent 清单不可审计或仅存在于个人安装时，不形成项目级角色删除候选。

## 测试与文档

### RED 与定向测试

- 修改每个 skill 前先增加会失败的合同测试或前向场景，并确认失败原因对应目标行为。
- `creating-product-requirements`：覆盖中文 PRD 模板、批准后自动转换、八字段到十四字段前缀传递、下游不可用能力缺口，以及不读取兄弟源码/安装目录。
- `creating-development-specs-and-plans`：覆盖中文 spec/plan 模板、可靠默认路径在文件创建前仍被保留、进入下游后的 PRD 复验失败仍输出十四字段、十四字段先验证后路由、未开门禁不路由，以及路由回复保留十四字段结尾。
- `generating-development-prompts`：覆盖三态路由、判断不明确默认新会话、确定性阻塞、当前会话等待批准、未批准 plan 的手动提示词兼容、单一代码框和动态 fence。
- `render_prompt.py`：覆盖普通提示词、正文含三个或更多连续反引号、Unicode、现有嵌套深度边界、错误输入 stdout 为空和确定性输出；不得为本需求新增输入大小限制。
- 仓库集成测试：覆盖八字段前缀进入十四字段、十四字段进入路由、PRD/spec/plan 模板中文标题、discovery CLI schema 不变和 plugin 五-skill 边界。

### 前向评估

- 为受影响的三个 skill 各增加或更新一个固定、脱敏的 RED 场景；同一场景由不同的全新 Agent执行 GREEN。
- PRD 场景验证用户只回复“批准”后不会停在八字段终点，而会进入 spec workflow。
- spec/plan 场景验证 plan 评审通过后先完成十四字段，再自动给出会话路由。
- prompt 场景分别覆盖当前会话、新会话和阻塞三态，并验证新会话提示词位于一个代码框。
- 原始本地输出保留在 `work/`，版本库只保存脱敏场景、判据、选中输出和结构化结果。

### 文档同步

- 更新 `docs/workflow.md`，说明两段自动衔接、八字段/十四字段在自动转换中的保留方式、三态路由和手动提示词兼容。
- 更新 `docs/agent-development.md`，记录三个项目级 Agent 的逐角色覆盖评估与保留结论。
- 更新 `README.md` 的工作流和 `generating-development-prompts` 职责说明，使自动衔接、会话路由和新会话时才生成提示词成为当前事实；安装命令不变。
- 更新 `.codex-plugin/plugin.json` 的 description、longDescription 和 defaultPrompt 以覆盖连续交接与会话路由；skill 数量和版本 `0.1.0` 保持不变。
- 更新 `CHANGELOG.md` 未发布 `0.1.0` 中三个受影响 skill 与 Repository 条目，明确 renderer stdout 的 breaking contract、代码框迁移方式、两段自动衔接和三态路由。
- `docs/install.md` 的安装与更新命令不变；只在其关于单 skill 独立运行或重新加载行为的现有表述与自动衔接边界冲突时做最小澄清，不新增安装步骤。

### 验证命令范围

- 运行三个受影响 skill 的定向 unittest。
- 运行仓库级 unittest、`scripts/validate_repo.py`、三个 skill 的官方 `quick_validate.py` 和 plugin validator。
- 运行三个受影响 skill 的 RED/GREEN 前向场景，并保存规定证据。
- 对最新 diff、每个 skill 的独立验证和完整五-skill plugin 进行独立评审；评审引发修改后重新验证并复审。
- 在 Codex 客户端人工验证长提示词代码框的一键复制结果与 renderer 正文完全一致。

## 验收标准

1. 新生成的 PRD、spec 和 plan 使用中文标题、章节和解释性正文，frontmatter 键和值保持现有契约。
2. 当前 PRD 全部门禁打开后，主 Agent完成并验证八字段，无需额外用户输入即进入 spec workflow。
3. 自动进入 spec workflow 后，成功复验时最终十四字段的前八项按映射表保留上游值；尚未创建的 spec/plan 仍保留可靠选定的默认路径。进入下游后的复验失败输出 requirements unknown/not-approved、真实后六字段和双门 blocked，不退回八字段；下游不可用时如实报告能力缺口。
4. spec 双批准和 plan 真实评审全部有效后，主 Agent先验证完整十四字段，再自动进入会话路由。
5. 自动路由回复保留原十四字段并以其结尾，不改变任何文档批准状态。
6. 当前会话满足完整上下文、范围可控和能力可用条件时，输出 `current-session` 建议、主要依据并等待用户批准，不生成提示词。
7. 当前会话更适合隔离或判断不明确时，输出 `new-session`、主要依据，并生成一个可复制提示词代码框。
8. 只有会话无关事实或可验证的目标会话能力边界证明两个会话都无法执行时才输出 `blocked`；仅有当前会话限制或证据不足时输出带理由的 `new-session`。`blocked` 不自动生成提示词，用户显式请求时生成带阻断门提示词。
9. plan 未批准或状态未知时不自动路由，但用户显式请求提示词仍可获得保留真实阻断门的结果。
10. renderer 对任意合法提示词正文只输出一个完整 Markdown 代码框，正文中的连续反引号不能提前闭合代码框。
11. 用户从目标 Codex 客户端一键复制得到的内容与完整提示词正文一致，不需要拼接代码框外内容。
12. `discover_context.py` 的 CLI、退出码和 `schema_version: 1` 保持兼容，现有 discovery 测试继续通过。
13. 三个项目级 Agent 均有可审计的逐角色评估；本阶段无配置删除，`agent-rules` 和实际全局安装状态未被修改。
14. 三个 skill 各自保持可独立安装和验证，自动转换不读取兄弟源码、兄弟安装目录或固定本机路径。
15. README、workflow、CHANGELOG 和 plugin manifest 准确记录 breaking stdout 变化与迁移方式；plugin 保持未发布 `0.1.0`，没有发布、tag 或安装外部状态变更。
16. 定向测试、仓库测试、官方 skill validator、plugin validator、RED/GREEN 前向场景和独立评审全部通过；任何未完成的客户端复制验证被如实报告为未验证，不能宣称整体完成。
