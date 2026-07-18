# 工作流与文档契约

## 完整交接链

### 1. 产品需求

`creating-product-requirements` 把产品意图收敛为一个稳定主题。范围类型只能是 `product`、`phase` 或 `feature`。一轮可以询问一至三个真正互不依赖的问题；只要一个答案会改变其它问题的适用性、选项或优先级，就只问当前决定性问题。只有需求理解置信度至少为 95%，且用户确认当前摘要后，才创建 PRD。

进入任何 PRD 状态、路径选择或八字段输出前，先识别用户最终要求的交付物。最终只需要旁白、脚本、文案、提纲、文章或其他内容文档，且用户没有明确要求 PRD，也不在定义后续产品行为或开发范围时，本 skill 不适用；内容的结构、时长或覆盖范围变化本身不构成产品需求。主 Agent 直接返回原任务制作内容，不创建 PRD，不输出八字段，也不进入 spec 或 plan。

默认路径：

```text
docs/requirements/YYYY-MM-DD-<topic>.md
```

PRD 必须经过独立评审和用户明确批准，才能进入技术设计阶段。全部门禁打开后，skill 先写入并验证批准状态与 requirements 八字段；下游能力在当前运行时可用时，主 Agent 无需用户再次输入 skill 名称或路径，直接在同一会话进入技术规格阶段。下游能力不可用时，返回能力缺口并保留真实八字段。用户看到的是同一英文 canonical 快照的中文八字段视图。

### 2. 技术规格与计划

`creating-development-specs-and-plans` 先校验已批准 PRD，再以相同的依赖感知规则澄清技术选择并生成 technical spec。spec 经独立评审和用户明确批准后，才生成 implementation plan；plan 必须经过独立评审。双门全部打开后，主 Agent 重新验证 PRD、spec、plan 与十四字段快照，再自动进入会话路由。

技术 spec 对每个改变持久化状态的命令和异步完成路径维护结果/失败矩阵；矩阵按结果而不是按命令归一化，每个成功、无变化、失败和提交核对分支使用唯一 Outcome ID 单独成行，调用方动作或一致性效果不同时不得合并。数据库、事务或锁影响正确性时，必须基于实际引擎、模式、驱动和配置说明读写顺序、锁获取与持有、读转写、竞争超时、回滚和公开错误分类，不能只写框架级泛化语义。每项重要保证使用唯一 Guarantee ID，并映射到 Outcome ID、精确测试文件与名称、执行命令和可观察断言；implementation plan 保留这些 ID，不能留下未覆盖保证或无法回溯的必需测试。

implementation plan 把任务拆分用于实施和定向验证，不据此自动增加独立评审门。默认在所有任务完成、集成并通过相关验证后，由一名未参与实现的评审者检查最新完整 diff；只有计划明确识别真实高风险边界，或后续任务依赖尚未验证的关键基础时，才增加中间里程碑评审。任务数量本身不是评审触发条件。

默认路径：

```text
docs/specs/YYYY-MM-DD-<topic>-design.md
docs/plans/YYYY-MM-DD-<topic>.md
```

### 文档 frontmatter 本地化

本功能生效后从头创建的 PRD、technical spec 和 implementation plan 使用完整中文 frontmatter 键及中文生命周期值，例如“产品需求 / 技术规格 / 实施计划”“产品 / 阶段 / 功能”“待批准 / 已批准”和“待评审 / 已通过”。路径、stable topic、reviewer role、ISO 日期以及 skill 间传递的 requirements 八字段、workflow 十四字段继续使用原有技术值和英文 canonical 字段；renderer、CLI 与 JSON shape 不变。

既有英文 PRD、spec 和 plan 属于 `english-legacy`：正文维护、批准失效、批准和重新评审都继续写回英文 schema，不因本功能自动改写，也不批量迁移历史文档。读取端同时接受完整 `chinese-current` 和兼容的 `english-legacy`；mixed schema、语义重复、冲突、畸形 flat scalar、未知 Unicode key 或不受支持的中文值一律按不可靠状态失败关闭，不选择较有利的批准值。

plan discovery 保留非对称兼容边界：中文 frontmatter 必须具备完整 plan 固定字段和一致生命周期；历史英文 frontmatter 继续使用既有 review-only 合同。无 frontmatter 的 legacy header 只接受 ASCII 英文字段，不接受中文 header。

### 3. 开发提示词

`generating-development-prompts` 接收已验证的十四字段，结合当前会话、仓库、权限、工具和 Agent 能力给出 `current-session`、`new-session` 或 `blocked`。`current-session` 建议继续当前会话并等待用户显式实施批准，不生成提示词也不开始实施；`new-session` 才生成单一 Markdown 代码框中的自包含提示词；`blocked` 明确缺失证据或确定性阻塞。自动路由回复仍以同一中文十四字段视图结尾，不修改文档批准状态。

显式的手动提示词请求保持兼容：它读取用户指定或从 `docs/specs/`、`docs/plans/` 自动发现的 spec、plan 路径和仓库证据，显式路径优先；plan 未批准或状态未知时仍可生成提示词，但提示词必须在修改前阻断实施。没有上游十四字段时不伪造 requirements 或双门状态。

生成的实施合同要求每项任务执行 TDD 和影响范围匹配的验证，但默认只在集成后对最新完整 diff 做一次独立整体评审。计划显式声明的风险里程碑可以增加中间评审；同一评审门内的修复由同一评审者复审至 `APPROVED` 后停止。

目标会话第一次实际需要委派时读取可按名称启动的个人全局 Agent，建立只存在于当前对话上下文的 inventory，记录 `name`、`description` 与读取可靠性。后续委派复用该 inventory；只有配置变化、首次读取失败、按名称启动失败、inventory 与可观察能力冲突或用户显式要求时刷新一次。刷新后仍失败则保留能力缺口，不静默降级。

## 自动交接与字段映射

PRD workflow 的 requirements 八字段按下表成为 spec/plan 十四字段的前八项：

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

进入下游前复验失败时不选择下游、不构造十四字段，上游仍以真实八字段或 `unknown` 状态结束。进入下游后复验失败时仍输出完整十四字段：requirements 侧按已确认规则关闭 `specification_gate`，spec/plan 侧保留可靠路径与真实状态，并令 `implementation_gate: blocked`。

plan 评审通过后必须重新验证并冻结十四字段快照，再进入三态路由。自动路由回复仍以同一十四字段快照结尾；路由结论、理由和可复制提示词位于该快照之前。

### 用户可见状态视图

八字段和十四字段的英文 canonical 名称、允许值、门禁计算及 skill 间传递保持不变；旧英文八字段和十四字段输入继续兼容。三个交接 skill 各自发布字节一致、运行时自包含的 `scripts/render_handoff.py`，以严格 JSON 输入校验 canonical、gate 和显示映射，不 import 兄弟 skill。

只有普通、预期内、非阻塞且不要求正式确认或批准的澄清使用 compact 视图，固定为连续三行且没有空行、列表标记或末尾内容：

```text
当前阶段：<需求澄清 | 技术规格澄清 | 实施计划澄清>
主题：<stable-topic | 未确定 | 未知>
下一步：<当前动作>
```

暂停或恢复点、需求摘要确认、PRD/spec/实施批准、确定性阻塞、文档阶段完成和跨 skill 或会话路由使用完整中文八字段或十四字段。纯进度回复不属于 compact；无法可靠分类时保守使用完整状态。十四字段中的计划状态继续结合 plan 路径与评审状态区分“未开始”“未通过”“已通过”和“未知”。

每个 skill 都先验证并冻结英文 canonical 快照，再调用自身 renderer。renderer 或映射失败时 stdout 为空；调用方保留 canonical 和门禁事实，停止本次自动交接，只输出可定位的阻塞说明且不附加状态块，不输出残缺、混合或英文 fallback 状态块。

这项显示变化不改变 `render_prompt.py` stdout 的字节级合同。自动 `new-session` 回复把 prompt renderer 的唯一动态代码框放在 handoff renderer 生成的中文十四字段状态块之前，状态块位于动态代码框之外；手动请求没有可靠上游快照时仍只返回 `render_prompt.py` stdout。

## 受控实施入口

`implementing-bounded-changes` 用于现有或开发中项目里已经明确改动点和方案、且用户已明确同意推进的小改动或 Bug 修复。它不生成提示词，也不要求为了小任务创建 PRD、spec、plan 或进度文档。

实施前在当前会话冻结目标、改动点、方案、非目标、验证范围和文档影响。行为变化使用比例化 RED→GREEN；默认只运行最小充分的定向验证，可以使用边界清晰的 Sub Agent。完成前同步受影响的现有文档，并由一位未参与实现的评审者检查最新完整 diff；有修改时由同一评审者复审直到 `APPROVED`，通过后立即停止，不增加重复评审或额外评审者。未取得批准时保持阻塞，不能声明完成。

用户批准只覆盖冻结范围。实现或评审发现必须改变公共契约、依赖、架构、数据、权限、迁移、并发、一致性或其他已确认边界时，停止修改并重新请求用户批准。受控实施入口不得绕过目标仓库明确要求的产品、设计、迁移、安全或发布门。

## AGENTS 规则治理入口

`managing-agents-rules` 独立处理长期项目规则和 Codex 全局规则，不替代 PRD、spec、plan、开发提示词或受控实施。它在实质性开发首次生产写入前检查项目根 `AGENTS.md`；任务完成时只从当前 diff、验证、纠正或稳定运维证据中筛选可复用候选。

缺失项目根规则时先展示有仓库证据的最小候选 diff；已有但不可读时阻断生产写入，不把不可读误判为缺失。每个项目级或全局目标分别展示目标、证据、范围理由和当前最小 diff，批准只对该目标和当前 diff 有效；写入前基线变化会使批准失效。没有合格候选时不发出规则治理提示，也不把会话状态持久化到项目或用户目录。

候选 diff 在回复中只完整显示一次，并使用比 diff 内最长连续反引号更长的动态 Markdown fence；批准问题位于关闭 fence 之后。Codex 客户端不保证渲染 HTML disclosure，因此不使用 `<details>` 或 `<summary>` 折叠候选，避免标签外露或内层代码围栏提前截断 diff。

项目规则变更在适用的最终评审前进入最新仓库 diff 并重新验证。全局规则默认以当前 Codex home 的基础 `AGENTS.md` 为长期目标；非空 override 会遮蔽基础文件，因此只告警，只有用户显式选择后才把现有 override 作为独立目标。Git 初始化与规则文件创建始终是两个独立决定。

## 协作边界

- 用户显式路径优先于默认路径。
- skill 之间只通过文档路径、评审状态和显式输出字段协作。
- skill 不通过相对 import、本机安装路径或 plugin cache 调用彼此。
- PRD、spec 或 plan 发生实质修改后，原有批准状态失效，必须重新评审或确认。
- 缺失、未知或无法验证的批准状态不得推断为已批准。
- 受控实施 skill 不读取或调用其它 skill；它只依据用户批准、当前会话范围卡和目标仓库证据执行。
- `managing-agents-rules` 不读取或调用其它 skill；它只治理长期规则，不接管实现、文档创作或评审职责。

## 交接记录

PRD 阶段在内部固定维护 requirements 英文 canonical 八字段，对用户显示同序中文八字段。spec/plan 阶段校验并按上表保留这些 canonical 字段，再维护 requirements、spec、plan 和双门状态共十四字段；自动进入下游后，最终只保留一个中文十四字段结尾。prompt 路由保留同一 canonical 快照及其预验证中文视图，使当前或下一会话可以从文件证据恢复，而不是依赖聊天记忆。

具体字段和文档模板以各 skill 的 `SKILL.md`、`references/` 与 `assets/` 为准；公共契约变化必须同时更新上下游集成测试。

## 评估证据

`evaluations/` 只保存脱敏后的固定场景、判据和选中证据。可能包含用户上下文、原始 trace、stderr、task/thread 标识符或本机路径的材料只保存在被 `.gitignore` 排除的 `work/` 中。版本化输出中的 `/workspace/fixture` 是唯一允许的固定合成仓库根，不代表真实机器路径；公开扫描允许该前缀，并拒绝常见 macOS、Linux、Windows 本机用户或临时路径以及其它 `/workspace/...` 根。

`green/result.json` 的 `fresh_cases` 记录 production 变化后实际重跑并纳入当前评审的场景。`scripts/validate_repo.py --require-freshness` 在干净 Git 树核对 RED → production → fresh GREEN → review 的祖先链，在有未提交变更时要求完整 worktree evidence bundle；非 Git 副本只能做结构检查，不能通过严格 freshness 门。
