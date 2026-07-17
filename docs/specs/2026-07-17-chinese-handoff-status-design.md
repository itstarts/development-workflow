---
document_type: design
topic: chinese-handoff-status
requirements_path: docs/requirements/2026-07-17-chinese-handoff-status.md
requirements_topic: chinese-handoff-status
requirements_scope: feature
requirements_understanding_confidence: 99
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

# 工作流交接状态中文化技术规格

## 目标

- 把三个工作流 skill 现有的英文八字段或十四字段用户可见状态块替换为唯一、顺序稳定的中文状态块。
- 在产生中文视图前先验证并冻结现有英文 canonical 快照；批准、评审、门禁和自动路由继续只依据 canonical 状态。
- 保持既有英文八字段、十四字段输入和文档元数据兼容，不改变字段集合、枚举集合或门禁计算。
- 用各 skill 的自包含运行时说明和仓库级一致性测试同时保证独立安装能力与跨 skill 译法一致。
- 映射无法完整、唯一地完成时保留原 canonical 快照，停止依赖该快照的本次自动交接，并输出确定性阻塞说明而不是残缺或英文降级状态块。

## 非目标

- 不增加中文机器字段、双语 JSON/YAML schema 或第二套持久化状态。
- 不从中文状态块反向解析或推断批准、评审和门禁状态。
- 不修改 PRD、技术规格、计划和会话路由的既有批准条件、状态转换或三态路由规则。
- 不翻译路径、主题、skill 名称、命令、代码标识符以及 `current-session`、`new-session`、`blocked` 等不属于八字段或十四字段快照的技术标识符。
- 不引入共享运行时包、跨 skill import、新依赖或真实 `CODEX_HOME` 安装。
- 不重写历史交接输出；已有英文输出只作为兼容输入和迁移前证据保留。
- 不创建或操作用户可见 Codex 任务，不启动第二个 Codex 客户端或本地服务，不提交、push、tag、release 或发布。

## 当前证据

- 已批准产品需求位于 `docs/requirements/2026-07-17-chinese-handoff-status.md`，明确要求用户可见状态中文化、内部 canonical 英文契约保持不变、旧英文输入兼容和映射失败关闭。
- `skills/creating-product-requirements/references/review-and-handoff.md` 当前定义八字段英文纯文本输出，以及批准后把完整英文 canonical 快照传给下游能力的契约。
- `skills/creating-development-specs-and-plans/references/review-and-handoff.md` 当前定义十四字段英文纯文本输出、字段顺序、plan 跨字段状态语义和路由前快照冻结规则。
- `skills/generating-development-prompts/references/session-routing-policy.md` 当前要求自动路由结果以同一十四字段快照结束，并把可复制提示词代码框放在快照之前。
- `evaluations/creating-product-requirements/green/09-output.md`、`evaluations/creating-development-specs-and-plans/green/12-output.md` 和 `evaluations/generating-development-prompts/green/01-output.md` 至 `03-output.md` 保存了当前英文用户可见状态块的前向证据。
- 三个 skill 以 Markdown 契约指导 Agent 输出，没有一个共同的状态块运行时 renderer。`skills/AGENTS.md` 同时要求 skill 自包含、禁止兄弟源码依赖，并要求交接契约变化具备上下游集成回归测试。
- `tests/test_repository_contract.py` 当前把英文十四字段后缀及唯一性锁定为仓库契约；三个 skill 的 `tests/test_skill_contract.py` 分别锁定本地输出边界。
- `docs/workflow.md` 当前公开英文 canonical 八字段到十四字段的传递关系，是说明“机器状态不变、用户视图变化”的现有文档入口。
- 当前开发分支为 `codex/workflow-handoff-optimization`，工作树中三个受影响 skill、测试、评估和公开文档已有同一交接优化的未提交改动。这些改动是本功能必须保留的集成基线；后续实施只能在当前树上叠加，不能 reset、覆盖、切换到遗漏这些改动的干净 `HEAD`，也不能把既有变化误归为本功能新增。

## 行为与边界

### 两阶段状态模型

每个受影响工作流按固定顺序处理状态：

1. 使用现有检查器、文档元数据和工作流规则构造英文 canonical 八字段或十四字段快照。
2. 按现有规则验证字段完整性、允许值、批准状态和门禁；无效或不可靠输入继续使用现有 `pending`、`unknown`、`not-approved`、`blocked` 语义关闭门禁。
3. 在自动下游选择或会话路由前冻结通过验证的 canonical 快照。
4. 从该快照单向预生成中文用户可见视图，并在任何下游能力选择、会话路由或 renderer 调用前校验字段数量、顺序、标签和值映射完整且唯一。中文视图不参与门禁判断，也不回写 canonical 快照。
5. 只有中文视图校验成功后，才允许下游能力接收冻结的英文 canonical 快照并执行自动阶段交接或会话路由。最终回复复用步骤 4 已验证的同一中文视图，不在路由后重新映射另一份状态。

英文 canonical 快照仍是唯一机器权威，但不作为第二个用户可见状态块输出。成功进入下游后只展示下游拥有的一个十四字段中文块，不再追加八字段块。

### 用户可见格式

- 状态块使用纯文本，不放入 Markdown 代码框；每行格式为 `中文字段名：值`，使用全角冒号且不增加列表符号、前导空格或语言标记。
- 字段顺序与现有 canonical 八字段、十四字段顺序一一对应。
- 每个固定字段在回复中只出现一次“字段名加全角冒号”的状态行；解释性正文不得复制同名状态行。
- 状态块位于回复末尾，十四字段块的最后一个非空行是“实施门禁”状态。状态块之后没有解释、提示或代码框。
- 自动路由生成新会话提示词时，动态反引号代码框及其正文完整位于中文十四字段块之前；状态中文化不改变 renderer stdout 和复制边界。
- 路径、主题和置信度数字按原值显示。Unicode、长路径和连续反引号正文不得进入状态映射或改变提示词 fence 选择。

### 八字段视图

| canonical 字段 | 中文字段名 |
| --- | --- |
| `requirements_path` | 需求文档 |
| `requirements_topic` | 需求主题 |
| `requirements_scope` | 需求范围 |
| `understanding_confidence` | 需求理解置信度 |
| `understanding_user_confirmation` | 需求理解确认 |
| `requirements_user_approval` | 需求文档用户批准 |
| `requirements_independent_review` | 需求文档独立评审 |
| `specification_gate` | 技术规格门禁 |

### 十四字段视图

| canonical 字段 | 中文字段名 |
| --- | --- |
| `requirements_path` | 需求文档 |
| `requirements_topic` | 需求主题 |
| `requirements_scope` | 需求范围 |
| `requirements_understanding_confidence` | 需求理解置信度 |
| `requirements_understanding_confirmation` | 需求理解确认 |
| `requirements_user_approval` | 需求文档用户批准 |
| `requirements_independent_review` | 需求文档独立评审 |
| `specification_gate` | 技术规格门禁 |
| `spec_path` | 技术规格 |
| `spec_user_approval` | 技术规格用户批准 |
| `spec_independent_review` | 技术规格独立评审 |
| `plan_path` | 实施计划 |
| `plan_review_status` | 计划评审状态 |
| `implementation_gate` | 实施门禁 |

### 值映射

值映射必须同时考虑字段语境，不能建立一个对所有字段生效的通用字符串替换表：

| 字段语境 | canonical 值 | 中文值 |
| --- | --- | --- |
| 需求范围 | `product` | 产品 |
| 需求范围 | `phase` | 阶段 |
| 需求范围 | `feature` | 功能 |
| 需求范围 | `null` | 未确定 |
| 需求范围 | `unknown` | 未知 |
| 需求理解确认 | `pending` | 待确认 |
| 需求理解确认 | `approved` | 已确认 |
| 需求理解确认 | `unknown` | 未知 |
| 需求文档用户批准 | `pending` | 待批准 |
| 需求文档用户批准 | `approved` | 已批准 |
| 需求文档用户批准 | `unknown` | 未知 |
| 技术规格用户批准 | `pending` | 待批准 |
| 技术规格用户批准 | `approved` | 已批准 |
| 需求文档独立评审 | `pending` | 待评审 |
| 需求文档独立评审 | `approved` | 已通过 |
| 需求文档独立评审 | `unknown` | 未知 |
| 技术规格独立评审 | `pending` | 待评审 |
| 技术规格独立评审 | `approved` | 已通过 |
| 技术规格门禁、实施门禁 | `blocked` | 未开放 |
| 技术规格门禁、实施门禁 | `open` | 已开放 |

合法 `unknown` 必须按字段允许集逐项处理：

| canonical 字段 | `unknown` 是否合法 | 中文结果或处理 |
| --- | --- | --- |
| `requirements_topic` | 是 | 未知 |
| `requirements_scope` | 是 | 未知 |
| `understanding_confidence` / `requirements_understanding_confidence` | 是 | 未知 |
| `understanding_user_confirmation` / `requirements_understanding_confirmation` | 是 | 未知 |
| `requirements_user_approval` | 是 | 未知 |
| `requirements_independent_review` | 是 | 未知 |
| `plan_review_status` | 仅当 `plan_path` 非空且既有计划评审元数据不可靠时合法 | 未知 |
| `spec_user_approval` | 否 | 按现有 canonical 校验失败规则关闭门禁，不进入中文映射 |
| `spec_independent_review` | 否 | 按现有 canonical 校验失败规则关闭门禁，不进入中文映射 |

路径字段不新增 `unknown` 枚举；不可可靠选择时继续使用现有 `null` 语义。双门字段仍只允许 `blocked | open`。

自由文本和空值按以下规则处理：

- `requirements_path`、`requirements_topic` 或 `spec_path` 为 `null` 且没有可靠默认值时显示“未确定”。
- `plan_path` 为 `null` 时显示“尚未创建”。
- 已由现有路径选择规则可靠选中的默认路径按实际路径显示，不用空值文案覆盖。
- 置信度整数原样显示；canonical `unknown` 显示“未知”。
- 非空路径和主题原样显示，不翻译、不规范化，也不改变 Unicode 内容。
- `plan_path` 为 `null` 时，`plan_review_status` 的 canonical `not-approved` 显示“未开始”。
- `plan_path` 非空时，`plan_review_status` 的 `not-approved`、`approved`、`unknown` 分别显示“未通过”“已通过”“未知”。
- 技术规格用户批准和独立评审不接受 `unknown`；若 canonical 校验发现缺失、冲突或非法元数据，沿用现有门禁关闭规则处理，不把 `unknown` 扩展成新的合法 spec 状态。

### 兼容性

- skill 之间通过运行时能力选择传递的仍是英文 canonical 字段和值；八字段到十四字段的字段重命名规则保持不变。
- 旧会话或显式输入中的英文八字段、十四字段继续按现有规则读取和校验。
- 新中文状态块只用于展示，不能作为 canonical 输入被反向解析。只有中文视图而没有可信 canonical 快照时，工作流必须从明确文档路径重新运行现有检查器和发现流程；无法恢复时保持门禁关闭。
- 这项改动对机器输入契约向后兼容，但会改变依赖回复末尾英文 handoff/status-block 的消费者，因此在当前未发布版本的变更记录中明确标记“用户可见状态块回复后缀契约”的 breaking contract change 和迁移方式。`render_prompt.py` 的 stdout 字节级合同不因本功能改变。

## 组件与控制流

### PRD 交接

`skills/creating-product-requirements/references/review-and-handoff.md` 继续拥有八字段 canonical 构造、批准门和下游选择边界，并增加八字段中文视图及失败关闭规则。`SKILL.md` 明确回复展示中文视图、向下游传递英文 canonical 快照。其本地契约测试验证字段顺序、标签、语境化值、单一块和 approved transition 不变。

### 技术规格与计划交接

`skills/creating-development-specs-and-plans/references/review-and-handoff.md` 继续拥有十四字段 canonical 构造、plan 跨字段状态、实施门禁和路由前冻结，并增加完整十四字段中文视图。`SKILL.md` 明确门禁和路由使用 canonical，回复尾部使用中文视图。其测试覆盖 plan 未创建与未通过的区分、spec 状态允许集和下游复验失败。

### 会话路由交接

`skills/generating-development-prompts/references/session-routing-policy.md` 接收并保留上游英文 canonical 十四字段快照，先预生成并验证其中文视图，再允许执行路由或调用 renderer；路由结果和提示词生成完成后复用该中文视图结束回复。`SKILL.md` 的输出合同明确 renderer stdout 不包含状态块，状态视图由路由回复追加。当前会话、新会话和阻塞三条自动路由路径使用同一映射；手动提示词请求在没有上游快照时仍只返回 renderer stdout，不伪造中文状态块。

### 跨 skill 一致性

每个 skill 在自身 `references/` 中保留运行所需的完整映射子集，以满足独立安装和自包含要求。`tests/test_repository_contract.py` 作为开发期一致性门，比较三个 skill 中同一 canonical 字段的中文标签和值，并验证版本化 GREEN 输出的中文后缀顺序和唯一性。任何映射修改必须同时更新受影响的本地契约测试、上下游集成测试和评估证据；运行时不读取仓库根文档或兄弟 skill 文件。

控制流如下：

```text
文档与会话证据
  -> 现有 canonical 校验与门禁计算
  -> 冻结英文 canonical 快照
  -> 预生成并完整校验中文视图
  -> 校验成功后自动下游选择或会话路由使用 canonical 快照
  -> 将预生成的同一中文状态块放在回复末尾
```

## API 与技术接口

### 内部 canonical 接口

现有八字段和十四字段的英文名称、顺序与允许值不变。八字段到十四字段前缀的转换仍只把：

- `understanding_confidence` 重命名为 `requirements_understanding_confidence`；
- `understanding_user_confirmation` 重命名为 `requirements_understanding_confirmation`；
- 其余前八字段名和值原样保留。

此接口继续用于检查器结果、skill 间显式交接、评估输入和门禁计算。

### 用户可见接口

用户可见接口是回复末尾的八行或十四行纯文本中文状态块。它是 canonical 快照的只读投影，不是可反向解析 API。字段数量、顺序、全角冒号、映射值和“最后一个非空行”均属于可测试输出契约。

不新增命令行参数、JSON schema、网络 API 或 renderer stdin/stdout 字段。`scripts/render_prompt.py` 继续只负责单一动态反引号代码框，其 stdout 必须与本功能修改前保持同一字节级合同；状态块不进入 stdout，以免破坏客户端完整复制测试。

## 数据模型与实体关系

不新增持久化数据模型。逻辑上存在两个瞬时对象：

- canonical 快照：现有英文键和值组成的唯一权威状态，来源于文档元数据、检查器和工作流规则；
- 中文视图：从一个已冻结 canonical 快照单向生成的无持久化展示结果。

两者是一对一投影关系。中文视图没有独立生命周期、版本号或批准权，不得写回 PRD、spec、plan frontmatter，也不得成为门禁输入。

## 状态转换、迁移边界与一致性

- 本改动不改变 `pending`、`approved`、`unknown`、`not-approved`、`blocked`、`open` 等 canonical 状态转换。
- 文档批准或评审变化后，先按现有规则重建并验证 canonical 快照，再生成新的中文视图；不能复用旧中文文本判断当前状态。
- 自动阶段交接和会话路由使用冻结 canonical 快照；中文视图必须先从同一快照预生成并验证，避免理由、提示词和结尾状态来自不同版本。
- 中文视图校验完成前不得选择下游能力、决定会话路由或调用 renderer。映射失败不撤销已经验证的文档批准，也不把 canonical 门禁改写为 `blocked`；它只阻止本次自动转移。
- 修复映射缺陷后，从失败时保留的 canonical 快照重新验证并生成视图；如果源文档已变化，则按现有规则重新构造快照，而不是沿用聊天中的中文文本。
- 不涉及数据库迁移、事务、锁、并发写或跨进程共享状态。

## 错误与不确定性

先区分 canonical 校验失败与中文映射失败：

- canonical 字段缺失、元数据冲突、非法 spec 状态、文档不可读或门禁证据不足，继续由现有规则映射为 `unknown`、`not-approved` 或关闭门禁；这不是中文映射缺陷。
- 已定义的 canonical `unknown`、路径空值和 plan 未创建状态均有确定中文值，属于正常映射。
- 一个通过现有校验的 canonical 值没有中文映射、同一字段和值存在冲突译法、中文标签缺失，或生成结果字段数量、顺序不完整时，才是中文映射失败。

映射失败时：

- 保留原 canonical 快照、批准事实和门禁事实，不修改任何文档元数据；
- 不输出部分中文状态块、中文与英文混合块或英文 fallback 状态块；
- 允许输出简短中文阻塞说明，但该回复不附加状态块；这是“每次回复以状态块结束”规则的唯一显式异常；
- 不进入下游 workflow，不执行自动会话路由，也不生成依赖该路由的新会话提示词；
- 错误说明应指出发生映射失败的字段或完整性条件，但不得打印第二份 canonical 状态块来规避限制。

本功能不触及密钥、权限、敏感数据或外部信任边界，不新增安全机制。

## 测试与文档

### TDD 与契约测试

- 先在三个 skill 的本地契约测试和仓库集成测试中写入中文字段、值、顺序、唯一性、兼容性和失败关闭断言，并运行确认当前英文实现按预期 RED。
- PRD skill 测试至少覆盖八字段正常批准、待确认/待批准/待评审、单一中文块和英文 canonical 下游传递，并逐项覆盖 topic、scope、confidence、confirmation、requirements approval、requirements review 的合法 `unknown`。
- spec/plan skill 测试至少覆盖十四字段完整状态、spec pending/approved、plan 未创建/未通过/已通过/未知、下游 PRD 复验失败和实施门禁关闭；明确拒绝 spec approval/review 的 `unknown`。
- prompt skill 测试覆盖 `current-session`、`new-session`、`blocked` 三条自动路由的同一中文后缀；确认动态 fence、长 Unicode 正文与连续反引号复制结果不变，中文状态块始终位于 fence 之外。测试必须按动态 fence 提取 renderer 内部正文，并逐字断言与输入正文一致。
- 仓库集成测试验证三个 skill 的重叠字段译法一致、canonical 英文字段仍存在于内部交接契约、旧英文快照仍可作为输入，以及版本化输出不再出现用户可见英文字段后缀。
- 增加未覆盖合法枚举或冲突映射的失败场景，断言在任何下游能力选择和 renderer 调用前失败、没有部分中文、没有英文 fallback、没有自动转移，并保留可重试的 canonical 来源。

### 评估证据

按仓库现有维护流程，为三个受影响 skill 分别保存当前英文输出的 RED 证据和中文输出的 GREEN 前向证据。更新评估 case、rubric、结果元数据和版本化输出时，保留批准、路由和提示词复制等原有判据，不用中文化弱化既有门禁。

### 文档同步

- 更新 `docs/workflow.md`，同时说明英文 canonical 交接、中文用户视图、单一块、兼容性和映射失败例外。
- 更新 `CHANGELOG.md`，明确这是用户可见 handoff/status-block 回复后缀的 breaking contract change，但 renderer stdout 字节级合同、机器 canonical 与旧英文输入仍兼容。
- 仅当现有 README 的用户入口需要说明状态显示行为时做最小同步；不重复完整映射表。
- 不修改真实安装说明来暗示功能已经安装；临时 `CODEX_HOME` 验证由后续实施计划按既有边界安排。

### 验证范围

后续实施至少运行三个受影响 skill 的定向测试、仓库契约测试、完整仓库单元测试、仓库 validator、三个 skill 的官方 quick validator，以及完整 plugin validator。不得安装依赖或下载工具；使用现有 `.venv` 和临时隔离 `CODEX_HOME` staging 完成验证，不能安装到真实 `CODEX_HOME`。

还必须执行真实 Codex 客户端的一键复制回归：复用当前已运行的单实例客户端，不启动第二个客户端或本地开发服务；用已确认的 Unicode、长路径和连续反引号压力样本触发 `new-session` 展示，通过客户端复制按钮取得剪贴板正文，并与仓库测试从 renderer 动态 fence 内提取的预期正文逐字比较。剪贴板内容只在本机验证，不发送到外部服务。若当前运行时无法操作复制按钮、读取剪贴板或完成逐字比较，必须把客户端复制标记为阻断或未验证，不能宣称整体验证完成。

## 验收标准

1. PRD 工作流的用户可见回复以八行中文状态块结束，字段顺序、字段名和语境化值符合本规格，且不存在第二个英文或中文状态块。
2. 技术规格与计划工作流的用户可见回复以十四行中文状态块结束，前八项与 PRD 语义一致，spec、plan 和双门状态完整。
3. 三条自动会话路由均保留同一冻结 canonical 快照的中文十四字段视图；路由正文和新会话提示词位于状态块之前。
4. `new-session` 的动态反引号代码框只包含完整开发提示词正文；仓库测试按动态 fence 提取的正文与输入逐字一致，中文状态块位于 fence 之外。
5. 复用当前单实例 Codex 客户端执行一键复制后，剪贴板正文与 renderer fence 内预期正文逐字一致，不增加外层 fence、语言标记、前导空格、状态行或末尾解释；无法执行该比较时不宣称整体完成。
6. 英文 canonical 八字段和十四字段的字段集合、允许值、八到十四字段转换、门禁计算和 skill 间传递保持不变。
7. 旧英文状态快照仍可作为下游输入被校验；新中文状态块不会被反向解析为批准或门禁证据。
8. 需求范围、理解确认、用户批准、独立评审和双门状态分别按字段语境显示，不使用全局字符串替换造成错误译法。
9. 没有可靠路径时，requirements/spec 相关空值显示“未确定”，plan 路径显示“尚未创建”；可靠默认路径显示实际路径。
10. 计划未创建、已创建但未通过、已通过和未知分别显示“未开始”“未通过”“已通过”“未知”。
11. topic、scope、confidence、confirmation、requirements approval、requirements review 和 existing-plan review 各自合法的 canonical `unknown` 均显示“未知”，不触发映射失败。
12. 技术规格用户批准和独立评审只接受 canonical `pending | approved`，中文化不把 `unknown` 引入其机器合同。
13. 对通过 canonical 校验但缺少唯一中文映射的状态，工作流在任何下游选择、路由或 renderer 调用前保留 canonical 快照、不修改门禁、不输出部分或英文降级状态块，并停止本次自动交接。
14. 映射修复后可以从原 canonical 来源重新验证和生成完整中文视图，不依赖聊天中的中文文本补造状态。
15. 实施在当前 `codex/workflow-handoff-optimization` 未提交工作树上叠加并保留全部既有交接优化；不 reset、覆盖、提交、发布、创建用户可见任务或安装到真实 `CODEX_HOME`。
16. 三个 skill 的 RED、GREEN、定向测试、仓库验证和独立评审证据完整，完整五-skill plugin 回归通过。
