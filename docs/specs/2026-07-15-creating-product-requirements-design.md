---
document_type: design
topic: creating-product-requirements
user_approval: approved
approved_at: 2026-07-15
independent_review: approved
independent_reviewer: independent-spec-reviewer
independent_reviewed_at: 2026-07-15
---

# Creating Product Requirements 设计规格

## 1. 背景

当前工作流从 `creating-development-specs-and-plans` 开始，把尚未定型的开发请求直接澄清为技术 design spec，再生成 implementation plan。仓库缺少一个职责独立的产品需求阶段，用于在技术设计前明确产品范围、目标用户、用户场景、业务规则和验收标准。

本次新增 `creating-product-requirements`，把工作流调整为：

```text
产品需求理解与 PRD
  -> 技术 design spec 与 implementation plan
  -> 新会话开发提示词
```

三个 skill 通过稳定文档路径、文档元数据和显式状态字段协作，不通过本机安装路径、插件缓存或源码 import 互相调用。

## 2. 目标

- 支持完整产品、版本或阶段、单个功能三种 PRD 范围，并要求每次明确一种范围。
- 一份 PRD 只对应一个稳定主题；多个可独立推进的主题必须先拆分并由用户确认。
- 在生成 PRD 前读取适用规则、现有产品文档、代码、测试和其他与产品事实直接相关的仓库证据。
- 对会改变产品目标、范围、用户、业务规则、优先级或验收标准的重要歧义持续提问。
- 只有 Agent 自评需求理解置信度达到至少 95%，且用户明确确认当前“需求理解摘要”后，才允许生成 PRD。
- PRD 经未参与编写的独立评审者批准后，再请求用户明确批准当前书面版本。
- 只有当前 PRD 的独立评审和用户批准都有效时，才打开技术 spec 阶段。
- 默认生成 `docs/requirements/YYYY-MM-DD-<topic>.md`；用户显式路径优先，其次遵循目标仓库已有文档约定。
- 同步收窄 `creating-development-specs-and-plans` 的职责，使其强制消费已批准的 PRD，并在 PRD 契约不可靠时阻止 spec 创建。
- 保持三个 skill 可单独安装、独立验证，并由 plugin bundle 统一暴露。

## 3. 非目标

- PRD 不定义架构方案、API、数据库模型、代码文件或实施步骤。
- PRD 不用技术方案替代产品决策；只记录会影响产品行为的技术约束和非功能需求。
- 新 skill 不创建 design spec、implementation plan 或新会话开发提示词。
- 新 skill 不实现目标项目代码，不调用兄弟 skill，不创建或管理用户可见 task/thread。
- 不把 Agent 自评置信度、独立评审或用户对理解摘要的确认互相替代。
- 不从用户语气、沉默、旧批准、文件名或缺失证据推断确认或批准。
- 不通过哈希、签名或本机状态绑定 PRD 版本；状态可靠性由文档元数据、当前文件检查和实质修改后的显式失效规则保证。
- 不安装到真实 `CODEX_HOME`，不 commit、push、merge、rebase、tag、release 或改变外部状态。

## 4. 范围模型

`scope_type` 只允许以下值：

- `product`：完整产品的目标、用户、能力边界和总体成功标准。
- `phase`：一个版本、里程碑或阶段的范围、优先级和阶段验收标准。
- `feature`：一个可独立定义和验收的产品功能。

每次工作流必须先确定 `scope_type` 和唯一 `topic`。当请求同时包含多个可独立排期、独立批准或独立验收的主题时，Agent 必须列出拆分建议并等待用户选择；不得把它们静默合并为一份 PRD。

## 5. PRD 前置理解门

### 5.1 证据与提问

Agent 先区分：

- 已由仓库或用户确认的事实；
- 可由仓库证据解决的问题；
- 只有用户能够决定的产品选择；
- 不影响产品语义、可以沿用现有模式的局部细节。

只要仍存在会改变目标用户、问题定义、范围、非目标、业务规则、优先级、成功标准或验收条件的重要未知项，理解置信度就不得达到 95%，也不得生成 PRD。每轮优先询问一个影响最大的关键问题，避免用大量低价值问题阻塞用户。

### 5.2 需求理解摘要

Agent 自评达到至少 95% 后，必须先向用户提交简短、可核对的需求理解摘要，至少包含：

- 范围类型和稳定主题；
- 产品问题、目标和目标用户；
- 核心用户场景；
- 范围与非目标；
- 关键业务规则和约束；
- 验收方向；
- 剩余假设或明确声明没有实质性未知项。

用户必须明确确认当前摘要正确。Agent 自评达到 95% 不等于用户确认；用户仅回答其中一个问题、要求继续、保持沉默或确认旧摘要都不能打开 PRD 创建门。

### 5.3 失效规则

以下变化使理解摘要确认失效，并要求重新评估置信度和取得用户确认：

- `scope_type` 或稳定主题变化；
- 产品目标、目标用户、核心范围、非目标或关键业务规则发生实质变化；
- 验收方向或成功标准发生实质变化；
- 出现会使原摘要不完整的新证据。

不改变产品含义的文字、格式或引用修正不使理解确认失效。

## 6. PRD 文档契约

### 6.1 路径选择

路径优先级为：

1. 用户明确指定且有效的路径；
2. 目标仓库现有、适用于当前范围的需求文档约定；
3. `docs/requirements/YYYY-MM-DD-<topic>.md`。

相对显式路径以目标仓库根目录解析。不得覆盖未被用户指定为当前文档的既有文件。文档内部使用仓库相对路径，交接记录使用绝对路径。

### 6.2 Frontmatter

PRD 从文件首字节开始使用扁平 YAML frontmatter：

```yaml
document_type: product-requirements
topic: <stable-topic>
scope_type: <product-or-phase-or-feature>
understanding_confidence: <integer-from-95-through-100>
understanding_user_confirmation: approved
user_approval: pending
independent_review: pending
```

`understanding_user_confirmation: approved` 只表示用户确认了写文档前的需求理解摘要，不表示用户批准 PRD。`user_approval` 和 `independent_review` 是文档生成后的两个独立状态。

新建 PRD 时 `understanding_confidence` 必须是 95 至 100 的整数，因为低于门槛时禁止创建文件。既有 PRD 的理解确认失效后，Agent 必须重新评估并记录当前真实的 0 至 100 整数，同时把 `understanding_user_confirmation` 重置为 `pending`；置信度仍达到 95 以上也不能替代用户对最新摘要的确认。只有置信度至少 95 且确认重新为 approved 时，PRD 才能再次进入评审或下游 spec。

独立评审批准当前文件后，由主 Agent 将 `independent_review` 更新为 `approved`，并增加通用 reviewer 角色和评审日期。只有用户已被指向这个已独立评审通过的当前文件并明确批准时，才能把 `user_approval` 更新为 `approved`。

### 6.3 正文

PRD 至少包含：

- 背景与产品问题；
- 目标、非目标和成功标准；
- 目标用户或角色；
- 核心用户场景；
- 当前范围和明确排除项；
- 按可观察行为表达的产品需求；
- 必要的业务规则、状态和产品级错误体验；
- 可验证的验收标准；
- 仅在相关时记录的性能、兼容性、隐私、可用性等非功能需求；
- 依赖、风险、假设和仍不阻碍当前 PRD 的非实质性开放项；
- 对下游 design spec 的产品约束交接。

PRD 不包含架构、组件划分、API 字段、数据库表、迁移方案、精确代码路径或实施任务。若用户直接给出技术方案，PRD 只保留其已确认的产品结果或约束，技术实现交由 design spec 决定。

## 7. PRD 评审与批准

1. 主 Agent 写完 PRD 后先自检产品问题、用户、范围、业务规则和验收标准是否一致。
2. 派发一个未参与编写的全新只读评审者，向其提供用户请求、已确认的需求理解摘要、适用规则、当前 PRD 和必要仓库证据，不提供期望结论或作者辩护。
3. 评审者按严重级别输出 findings、open questions、verification gaps 和最终结论。
4. 主 Agent 修复全部 finding，并让独立评审者复审最新文件，直至批准或真实阻塞。
5. 独立评审通过后，主 Agent 更新文档的独立评审元数据，再向用户报告当前文件的绝对路径并请求明确批准。
6. 用户批准当前版本后，主 Agent 更新 `user_approval`。任何实质性 PRD 修改都会使独立评审和用户批准同时失效；若修改同时改变需求理解摘要，还会使摘要确认失效。

只有理解门、独立评审和用户批准均有效时，`specification_gate` 才为 `open`。

## 8. PRD Skill 输出契约

`creating-product-requirements` 的每次用户可见回复，包括提问和阻塞回复，都以以下固定字段结束：

```text
requirements_path: <absolute-path-or-null>
requirements_topic: <stable-topic-or-null-or-unknown>
requirements_scope: product | phase | feature | null | unknown
understanding_confidence: <integer-from-0-through-100> | unknown
understanding_user_confirmation: pending | approved | unknown
requirements_user_approval: pending | approved | unknown
requirements_independent_review: pending | approved | unknown
specification_gate: blocked | open
```

实际输出的每个字段只写一个值，不复制备选符号。理解置信度低于 95、用户未确认当前摘要、PRD 不存在、独立评审未批准或用户未批准时，`specification_gate` 必须为 `blocked`。

状态映射固定为：

- 用户提供了有效显式路径，或 Agent 已经根据唯一主题可靠选定路径时，即使文件尚未创建，也保留该绝对候选路径；只有路径本身无法唯一确定时才输出 `requirements_path: null`。
- 多主题未决且没有可靠显式路径时，topic、scope 和 path 均为 `null`；有效显式路径不因内容问题被丢弃。
- 尚未产生或尚未取得某个确认/批准时使用 `pending`。
- 现有文件不可读，frontmatter 缺失、非法、重复或冲突，字段值不受支持，评审结论模糊，或者无法判断当前批准是否对应当前版本时，对受影响的 topic、scope、confidence、确认或批准字段使用 `unknown`。
- 已知路径指向不存在的文件时保留路径，但文档批准字段为 `pending`，gate 为 `blocked`；已存在但不可读或格式不可靠时保留路径，受影响字段为 `unknown`，gate 为 `blocked`。
- 独立评审最终结论只接受 `APPROVED`、`CHANGES_REQUESTED` 或 `BLOCKED`。只有当前文件得到明确 `APPROVED` 后，主 Agent 才能把 `requirements_independent_review` 置为 `approved`；后两者及没有最终结论都不能升级状态。

状态转换规则固定为：

- PRD 正文发生实质修改时，立即把 `user_approval` 和 `independent_review` 重置为 `pending`，删除旧 reviewer 和批准日期元数据。
- 实质修改同时改变已确认的理解摘要时，另把 `understanding_user_confirmation` 重置为 `pending`，并将 `understanding_confidence` 更新为重新评估后的真实 0 至 100 整数；无法可靠评估时在回复中报告 `unknown`。即使真实置信度仍为 95 以上，确认 pending 也会独立关闭 gate。
- 仅修正文案、格式、引用或更新当前批准元数据且不改变产品含义时，不触发上述失效。
- 从 `pending` 恢复为 `approved` 必须重新执行对应的摘要确认、独立评审或用户批准门，不允许批量恢复旧状态。

## 9. 下游强制门禁

### 9.1 `creating-development-specs-and-plans` 输入

现有 skill 的触发描述和正文必须收窄为：基于已批准 PRD 创建技术 design spec 和 implementation plan，或维护已经存在且仍有可靠上游 PRD 的当前 planning 文档。一般产品需求澄清和 PRD 编写由新 skill 负责。

创建或实质修改 spec 前，现有 skill 必须检查：

- `requirements_path` 存在、可读，并解析为当前目标仓库内的明确文件；
- frontmatter 从文件首字节开始、为扁平字段且没有重复或冲突键；
- `document_type` 为 `product-requirements`；
- `topic` 非空，且与已确认的上游交接 topic 一致；
- `scope_type` 是 `product`、`phase` 或 `feature`，且与已确认的上游交接 scope 一致；
- `understanding_confidence` 是 95 至 100 的整数；
- `understanding_user_confirmation` 可靠地为 `approved`；
- `independent_review` 可靠地为 `approved`；
- `user_approval` 可靠地为 `approved`。

缺失、不可读、格式错误、重复、冲突、主题不一致、非法范围或任何未批准状态都关闭 specification gate。现有 skill 不得自行补写 PRD 元数据、把 `pending` 升级为 `approved`，或通过口头需求绕过 PRD。

### 9.2 确定性检查

为避免仅靠提示词主观解析，`creating-development-specs-and-plans` 增加一个使用 Python 3.9 标准库的本地只读检查脚本。脚本接收 PRD 路径、期望主题和期望范围类型，输出结构化 JSON 状态；不修改 PRD，不读取兄弟 skill 安装目录，不依赖第三方包。

期望主题和期望范围来自上游 `creating-product-requirements` 在用户确认理解摘要后形成的固定交接记录，而不是从待检查 PRD 内部反向读取。进入下游 skill 时必须显式保留这两个交接值；缺失、`null` 或 `unknown` 时先向用户确认或报告阻塞。脚本分别比较交接值与 PRD frontmatter；不一致时报告 `unknown` 并关闭 gate，禁止用文档自己的 topic 与自身比较来冒充验证。

脚本区分：

- `approved`：字段可靠且所有前置门通过；
- `not-approved`：文件和字段语法可靠，且至少一个必需确认或批准字段明确为允许值 `pending`，不存在更高优先级的 unknown 错误；
- `unknown`：文件或元数据缺失、不可读、重复、冲突、非法或无法可靠解释。

合法审批字段值只包括 `pending` 和 `approved`。缺失、其他值、重复、冲突或无法解释一律为 `unknown`，不得把非法值归入 `not-approved`。只有 `approved` 能打开 specification gate。脚本失败、不可执行或输出不可解析时保持 `unknown`，不得静默回退到宽松的人工推断。

### 9.3 Spec 与状态交接

spec frontmatter 增加 PRD 来源字段：

```yaml
requirements_path: docs/requirements/YYYY-MM-DD-<topic>.md
requirements_topic: <stable-topic>
requirements_scope: <product-or-phase-or-feature>
requirements_user_approval: approved
requirements_independent_review: approved
```

`creating-development-specs-and-plans` 的每次用户可见回复都以以下完整、唯一顺序的十四字段记录结束：

```text
requirements_path: <absolute-path-or-null>
requirements_topic: <stable-topic-or-null-or-unknown>
requirements_scope: product | phase | feature | null | unknown
requirements_understanding_confidence: <integer-from-0-through-100> | unknown
requirements_understanding_confirmation: pending | approved | unknown
requirements_user_approval: pending | approved | unknown
requirements_independent_review: pending | approved | unknown
specification_gate: blocked | open
spec_path: <absolute-path-or-null>
spec_user_approval: pending | approved
spec_independent_review: pending | approved
plan_path: <absolute-path-or-null>
plan_review_status: not-approved | approved | unknown
implementation_gate: blocked | open
```

requirements 八字段沿用第 8 节的映射。spec 和 plan 六字段沿用现有 skill 的映射。`specification_gate` 只有在 requirements 路径存在且可读、topic 和 scope 与独立交接值一致、理解置信度至少 95、理解摘要确认、PRD 用户批准和独立评审均可靠为 approved 时才为 `open`。

`implementation_gate` 只有在 `specification_gate` 仍为 `open`，且当前 spec 独立评审、spec 用户批准和当前 plan 独立评审全部有效时才为 `open`。PRD 后续失效会同时关闭两个 gate，即使既有 spec 或 plan 元数据仍显示 approved；恢复前必须先处理上游失效，再按受影响范围重新评审下游文档。

`generating-development-prompts` 继续消费已批准 spec 和 plan；本次不改变其运行时输入契约。

## 10. 技术 Spec 的职责补强

`creating-development-specs-and-plans` 的 spec 契约明确包含与当前功能相关的：

- 架构和组件职责；
- API、事件或其他技术接口；
- 数据模型、实体关系、约束和迁移边界；
- 状态流转、一致性和技术错误边界；
- 测试设计和文档影响。

上述内容只在相关时展开。具体代码文件、逐步实施顺序、测试命令和任务级评审继续属于 implementation plan。

## 11. Skill 结构

新 skill 采用以下最小结构：

```text
skills/creating-product-requirements/
├── SKILL.md
├── agents/openai.yaml
├── assets/prd-template.md
├── references/
│   ├── discovery-and-confidence.md
│   ├── document-contract.md
│   └── review-and-handoff.md
└── tests/test_skill_contract.py
```

现有 skill 增加 PRD 检查脚本、对应单元测试，并修改其触发描述、references、spec 模板和交接契约。两个 skill 不共享源码或相对 import，只通过 PRD 文档契约协作。

## 12. TDD、评估与仓库集成

### 12.1 新 skill RED→GREEN

- 在创建新 skill 生产文件前，冻结脱敏场景和 rubric。
- 用未加载目标 skill 的全新代理运行 baseline，至少观察以下核心 RED：过早生成 PRD、未取得摘要确认、混入技术设计、缺少双审批门、合并多个稳定主题或输出状态不完整。
- 将本地原始输出保存到被忽略的 `work/evaluations/creating-product-requirements/baseline/`，只把脱敏后的固定场景、选中输出和结构化结果写入 `evaluations/creating-product-requirements/`。
- 使用与 baseline 不同的全新代理加载候选 skill，运行相同场景并取得 GREEN。
- 先完成新 skill 的单元测试、官方 validator、baseline/GREEN 和独立 skill 评审，确认其可单独安装和使用；在这个独立闭环通过前，不修改现有 `creating-development-specs-and-plans` 的生产内容。

### 12.2 现有 skill 修改

- 先增加会因当前实现接受无 PRD 请求、未验证 PRD 状态或缺少数据模型职责而失败的契约或前向场景，确认 RED 后再修改生产内容。
- 增加 PRD 检查脚本的单元测试，覆盖 approved、pending、缺失文件、格式错误、重复键、非法范围、低于 95 的置信度、摘要未确认、主题不一致、合法但与 expected scope 不一致和评审状态冲突。
- 增加跨 skill 集成测试，验证新 skill 生成的 approved PRD 能被现有 skill 接受，未批准或不可靠 PRD 被拒绝，文档路径和范围类型原样保留，并覆盖合法 scope 与独立上游 expected scope 不一致时阻断。
- 现有 skill 完成自己的 RED、GREEN、单元测试、官方 validator 和独立 skill 评审后，再执行跨 skill 集成验证与 plugin 最终全量评审。

### 12.3 仓库和插件

- 扩展仓库 validator，使每个新增 skill 都需要自己的 baseline、GREEN、评审状态和敏感信息检查，而不是继续只绑定一个固定 skill 名称。
- 将 `docs/requirements` 加入本仓库允许的文档 namespace，并更新 `tests/test_repository_contract.py`：正向测试只允许 `requirements`、`specs`、`plans`，反向测试继续拒绝其他未知 namespace。这样在本仓库按新 skill 默认路径生成 PRD 时不会破坏仓库验证。
- 泛化 `scripts/run_skill_evaluations.py`，使调用方必须显式提供 skill 名称；evaluation 目录、候选 skill 路径和注入给代理的 `$<skill-name>` 调用都由同一个已校验名称派生。baseline 虽不加载候选 skill，仍使用该名称选择 cases 和保存证据。未知名称、目录不匹配或候选 frontmatter 名称不一致时立即失败，不得回退到旧 skill。
- 扩展 `tests/test_skill_evaluation_runner.py`，分别验证两个 authoring skill 的 prompt、evaluation 路径、baseline、GREEN、错误 skill 名称和候选目录不匹配；确保新 skill 的运行不会继续调用 `$creating-development-specs-and-plans`。
- 更新安装 staging 测试，覆盖三个 skill 单独安装、组合安装和拒绝覆盖已有目标。
- 更新 README、CHANGELOG、plugin manifest 文案和验证命令，展示三段式工作流与新 skill。
- 当前 plugin 版本仍为未发布的 `0.1.0`；本次功能纳入该未发布版本，不执行发布操作。
- 分别运行新旧 skill 的官方 `quick_validate.py`、仓库测试、仓库 validator 和 plugin validator。

## 13. 错误与不确定性

- 仓库证据与用户表述冲突时，明确展示冲突并向用户确认，不选择有利于继续生成文档的一方。
- 无法达到 95% 理解置信度时继续澄清或报告阻塞，不输出半成品 PRD。
- 用户未确认当前需求理解摘要时，不创建 PRD 文件。
- 独立评审者不可用或结论不完整时，PRD 保持 pending。
- PRD 状态不可可靠解析时，下游报告 unknown 并阻止 spec，不静默降级。
- 用户显式要求只评审或更新既有 PRD 时，仍需确认当前文件的范围、主题和审批状态；实质修改按失效规则处理。

## 14. 验收标准

- `creating-product-requirements` 能区分 `product`、`phase`、`feature`，并拒绝在范围或稳定主题不明确时生成 PRD。
- 理解置信度低于 95 或用户未确认当前理解摘要时，不创建 PRD。
- PRD 只包含产品范围、用户场景、业务规则、验收标准及相关非功能约束，不包含架构、API、数据库模型或实施任务。
- PRD 未经真实独立评审和用户明确批准时，specification gate 保持关闭。
- PRD 实质修改按规则使理解确认和文档批准失效。
- 默认路径、显式路径优先级、frontmatter 和固定八字段交接符合本规格。
- `creating-development-specs-and-plans` 对缺失、未批准、不可靠或主题不一致的 PRD 一律拒绝创建 spec。
- 技术 spec 在相关时明确覆盖接口、数据模型、状态流转和技术错误边界，plan 继续负责精确文件和实施步骤。
- 两个 skill 均保持自包含，不通过安装路径、插件缓存或源码 import 协作。
- 新 skill 创建前 RED、候选 GREEN、现有 skill 修改 RED、单元测试、跨 skill 测试、仓库验证、官方 skill/plugin validators 和独立评审全部通过。
- README、CHANGELOG、plugin manifest、安装矩阵和仓库 validator 与三个 skill 的当前行为一致。
