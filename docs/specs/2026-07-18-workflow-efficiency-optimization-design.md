---
document_type: design
topic: workflow-efficiency-optimization
requirements_path: docs/requirements/2026-07-18-workflow-efficiency-optimization.md
requirements_topic: workflow-efficiency-optimization
requirements_scope: phase
requirements_understanding_confidence: 99
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: approved
approved_at: 2026-07-18
independent_review: approved
independent_reviewer: independent-spec-reviewer
independent_reviewed_at: 2026-07-18
---

# 开发工作流效率优化技术规格

## 目标

- 把普通澄清与正式门禁、阻塞、交接回复分开：普通澄清只输出固定三字段三行状态，其余关键节点继续输出现有完整八字段或十四字段。
- 让 PRD 和技术规格阶段能够一次询问最多三个互不依赖的问题，同时保留依赖型逐问、95% 理解门和用户确认门。
- 让三个文档交接 skill 按阶段加载 references，并把重复、脆弱的状态映射与门禁一致性检查下沉为可执行的确定性逻辑。
- 建立不依赖固定内容哈希的评估新鲜度检查，使运行时合同晚于当前 RED/GREEN/评审证据时不能继续通过严格完成门。
- 把目标会话全局 Agent 清单改为会话内一次读取、条件刷新，减少重复扫描且不掩盖按名称启动失败。
- 提供标准库实现的定向验证、完整验证和只读安装差异检查入口，编排并如实报告现有权威检查。
- 保持五个 skill 的职责独立、单独安装能力、canonical 英文合同、批准门、三态路由、旧英文输入和 renderer 代码框合同不变。

## 非目标

- 不改变 `implementing-bounded-changes` 或 `managing-agents-rules` 的运行时行为和评审完成门。
- 不在本阶段实现轻量改动免评审；未来仅纯格式或机械型轻量改动可单独评估免评审，任何文档改动仍须独立评审。
- 不新增跨 skill 运行时 import、共享安装目录、plugin cache 依赖或固定本机路径。
- 不增加数据库、持久化状态、后台服务、网络调用、第三方依赖或新的权限边界。
- 不改变 `discover_context.py` 的 CLI、退出码或 `schema_version: 1`，不改变 `render_prompt.py` 成功 stdout 的单一动态 `text` 代码框合同。
- 不从中文完整状态或紧凑状态反向解析 canonical 状态。
- 不自动写入真实 `CODEX_HOME`，不自动提交、push、merge、tag、release 或发布。
- 不用固定 SHA-256、长期内容 manifest 或 attempt 审计链替代当前结构化评估证据。

## 当前证据

- 已批准 PRD 位于 `docs/requirements/2026-07-18-workflow-efficiency-optimization.md`；当前 inspector 以显式 path、topic 和 scope 返回 `status: approved` 与 `specification_gate: open`。
- `skills/creating-product-requirements/SKILL.md` 当前要求首轮完整读取三个 references、一次只问一个问题，并让所有未转换回复以完整八字段结束。
- `skills/creating-development-specs-and-plans/SKILL.md` 当前同样首轮读取全部 references、一次只问一个技术问题，并让每个回复以完整十四字段结束。
- `skills/generating-development-prompts/SKILL.md` 当前在入口分类后立即完整读取 discovery、permission 和 routing 三份 references；其自动路由必须继续输出完整十四字段，手动请求无上游快照时继续只返回 renderer stdout。
- 三个 skill 的中文字段和值映射目前分别保存在各自 references 中，没有可执行的公共 renderer；`skills/AGENTS.md` 又要求每个 skill 自包含且不得读取兄弟源码。
- `skills/generating-development-prompts/assets/development-prompt.md` 当前要求每次委派前重新检查目标会话全局 Agent。
- `scripts/validate_repo.py` 已提供 `production_files()`、评估 registry 阶段、GREEN 结构和 review metadata 校验，但没有比较当前 production payload 与当前证据的新旧关系。
- 当前 `generating-development-prompts` 和 `creating-development-specs-and-plans` 的 production 合同已经晚于其版本化 GREEN 输出，现有结构 validator 仍通过，构成可复现的证据新鲜度 RED。
- `evaluations/AGENTS.md` 明确不要求文件哈希；仓库当前依赖 `baseline-only -> implemented -> review-approved` 阶段、当前 RED、GREEN 输出和独立评审元数据。
- 仓库完整验证目前由多个 unittest、仓库 validator、五个官方 skill validator 和 plugin validator 命令组成；`production_files()` 已定义安装时的可发布 payload 边界。
- plugin 仍为未发布 `0.1.0`，因此本阶段记录用户可见 breaking contract，但不执行版本升级或发布。

## 行为与边界

### 回复分类与显示合同

主 Agent 在生成用户回复前先把当前结果分类为以下一种：

1. `ordinary-clarification`：预期内的发现或选择问题；没有损坏、冲突、权限失败、能力缺口、评审阻塞，也不要求用户作正式确认或批准。
2. `checkpoint`：用户要求暂停或形成恢复点；工作流请求需求摘要确认、PRD 批准、spec 批准或实施批准；一个文档阶段完成或准备选择下游能力。
3. `blocked`：文件、元数据、权限、reviewer、工具或能力的确定性问题阻止继续。
4. `routing`：执行 `current-session | new-session | blocked` 会话路由。
5. `manual-prompt`：没有可靠上游十四字段的显式提示词请求，继续遵循现有 renderer-only 输出合同。

`ordinary-clarification` 调用本 skill 本地状态 renderer 的 `compact` 模式，最终只输出：

```text
当前阶段：<中文阶段>
主题：<稳定 topic、未确定或未知>
下一步：<当前需要完成的动作>
```

三行连续输出，无空白行、列表标记、前导空格或字段分隔符；第三行后只保留 stdout 的末尾换行。topic 只来自 canonical；阶段和下一步由调用方在完成回复分类后从已验证的当前回复上下文提供。renderer 不从 canonical 推断这两个上下文字段，也不把它们写回 canonical。

`checkpoint`、`blocked` 和 `routing` 调用 `full` 模式，输出现有八字段或十四字段。`manual-prompt` 不伪造上游状态。无法可靠分类时保守使用完整状态；映射实现本身失败时继续保留 canonical、停止自动交接且不输出残缺状态。

### 依赖感知问题批次

- `creating-product-requirements` 和 `creating-development-specs-and-plans` 的 discovery references 负责判断问题依赖关系。
- 一轮允许一至三个实质性问题；只有任一答案都不改变其它问题的适用性、选项、含义、优先级或是否仍需询问时，才可同轮询问。
- 当前答案决定后续分支时只询问一个决定性问题。用户只回答部分问题时保留有效答案并重新判断剩余依赖。
- 批量提问不改变理解置信度计算、需求摘要确认、spec 技术选择门或任何文档批准状态。

### references 渐进加载

- `creating-product-requirements` 首次只读 discovery reference；首次写 PRD 前再读 document contract；首次请求摘要确认、评审、批准、完整状态或下游转换前再读 review/handoff reference。
- `creating-development-specs-and-plans` 首次只读 discovery reference；首次写 spec/plan 前再读 document contracts；首次阻塞回复、评审、批准、完整状态或路由前再读 review/handoff reference。
- `generating-development-prompts` 先分类入口并读取 discovery policy；发现成功且需要权限矩阵时读取 permission policy；只有自动路由、带上游状态的阻塞或需要完整状态时读取 session routing policy。无上游快照的手动提示词路径不加载无关路由映射。
- 每个 `SKILL.md` 保留清楚的阶段前置条件。所需 reference 缺失、不可读或冲突时停止当前阶段，不读取兄弟 skill 或未知替代来源。

### 自包含确定性状态 renderer

三个受影响 skill 各自发布 `scripts/render_handoff.py`。三份 production 脚本字节一致，支持八字段与十四字段两种 schema 及 `compact | full` 两种 view，运行时只执行本 skill 内副本，不 import 兄弟 skill 或仓库根工具。

输入是 stdin JSON：

```json
{
  "schema_version": 1,
  "handoff_schema": "requirements | workflow",
  "view": "compact | full",
  "canonical": {},
  "stage": "string | null",
  "next_step": "string | null"
}
```

- stdin 必须是无 BOM 的单个 UTF-8 JSON document；JSON 语法遵循 RFC 8259，并额外要求任意层级 object member name 唯一。非法 UTF-8、UTF-8 BOM、重复 key、尾随第二个 JSON value，以及 `NaN | Infinity | -Infinity` 均在语义校验前以 `invalid_json` 失败。解析后的所有 key 与 string value 必须是 Unicode scalar sequence；未配对 surrogate 同样属于 `invalid_json`。
- 顶层对象只允许并要求按上例定义的六个 key；JSON key 顺序不影响语义，额外 key 同样失败。`schema_version` 只接受非布尔整数 `1`，`handoff_schema` 与 `view` 只接受列出的枚举，`canonical` 必须是 object。
- `requirements` 的 canonical 必须恰好包含下表八字段；`workflow` 必须恰好包含下表十四字段。额外字段和缺失字段均失败，不允许通过默认值补齐。

| 顺序 | requirements 字段 | workflow 字段 | JSON 类型与允许值 |
| --- | --- | --- | --- |
| 1 | `requirements_path` | `requirements_path` | 合法 path string 或 `null` |
| 2 | `requirements_topic` | `requirements_topic` | stable topic string、`null` 或 `unknown` |
| 3 | `requirements_scope` | `requirements_scope` | `product \| phase \| feature \| null \| unknown` |
| 4 | `understanding_confidence` | `requirements_understanding_confidence` | 非布尔整数 `0..100` 或 `unknown` |
| 5 | `understanding_user_confirmation` | `requirements_understanding_confirmation` | `pending \| approved \| unknown` |
| 6 | `requirements_user_approval` | `requirements_user_approval` | `pending \| approved \| unknown` |
| 7 | `requirements_independent_review` | `requirements_independent_review` | `pending \| approved \| unknown` |
| 8 | `specification_gate` | `specification_gate` | `blocked \| open` |
| 9 | — | `spec_path` | 合法 path string 或 `null` |
| 10 | — | `spec_user_approval` | `pending \| approved` |
| 11 | — | `spec_independent_review` | `pending \| approved` |
| 12 | — | `plan_path` | 合法 path string 或 `null` |
| 13 | — | `plan_review_status` | `not-approved \| approved \| unknown`；`plan_path: null` 时只能为 `not-approved`，`unknown` 只允许非空 path |
| 14 | — | `implementation_gate` | `blocked \| open` |

stable topic 必须匹配 `^[a-z0-9]+(?:-[a-z0-9]+)*$`，并拒绝保留值 `null`、`unknown` 与 `pending`。合法 path string 必须非空、已经 trim、只占一行且不含 NUL、C0 控制字符、U+0085、U+2028 或 U+2029；renderer 不检查绝对性、仓库边界或文件存在性，不做路径规范化，并原样保留字符串。调用方继续负责现有 absolute/default/legacy repository-relative path 合同和实际文档验证。

八字段升级为十四字段时只有两个字段改名：`understanding_confidence` → `requirements_understanding_confidence`、`understanding_user_confirmation` → `requirements_understanding_confirmation`；其余前八字段同名同值。renderer 不自行执行升级，只使用该表验证调用方提供的完整 schema。

gate 使用以下唯一 truth table，输入与派生结果不同即 `gate_conflict`，renderer 不修正输入：

- `specification_gate: open` 当且仅当 requirements path 非空、topic 为 stable topic、scope 为 `product | phase | feature`、confidence 为至少 `95` 的整数，且 understanding confirmation、requirements user approval、requirements independent review 全部为 `approved`；其它组合必须为 `blocked`。
- `implementation_gate: open` 当且仅当 `specification_gate: open`、spec path 非空、两个 spec approval 字段均为 `approved`、plan path 非空且 `plan_review_status: approved`；其它组合必须为 `blocked`。

`compact` 要求 `stage` 是 `需求澄清 | 技术规格澄清 | 实施计划澄清` 之一，`next_step` 是已经 trim 的 `1..200` 个 Unicode scalar。二者均拒绝 CR、LF、NUL、其它 C0 控制字符、U+0085、U+2028 和 U+2029；topic 只从 canonical 的 `requirements_topic` 读取，`null` 映射为 `未确定`，`unknown` 映射为 `未知`，stable topic 原样保留。输出严格为：

```text
当前阶段：<stage>
主题：<topic>
下一步：<next_step>
```

`full` 要求 `stage` 与 `next_step` 都为 JSON `null`，按现有字段顺序和中文映射输出纯文本八行或十四行。字段 label、全角冒号和值映射保持当前 reference 合同；path、stable topic 和整数原样输出，scope/approval/gate 逐字段映射。`plan_path: null` 只允许 `not-approved` 并映射为“尚未创建/未开始”；非空 plan path 的 `not-approved | approved | unknown` 分别映射为“未通过/已通过/未知”。

完整输出逐行接口如下；requirements 使用前八行，workflow 使用全部十四行，表中顺序即 stdout 顺序：

| 顺序 | canonical 字段 | 固定 label | 前向值映射 |
| --- | --- | --- | --- |
| 1 | `requirements_path` | `需求文档：` | path 原样；`null` → `未确定` |
| 2 | `requirements_topic` | `需求主题：` | stable topic 原样；`null` → `未确定`；`unknown` → `未知` |
| 3 | `requirements_scope` | `需求范围：` | `product/phase/feature/null/unknown` → `产品/阶段/功能/未确定/未知` |
| 4 | `understanding_confidence` 或 `requirements_understanding_confidence` | `需求理解置信度：` | 整数原样；`unknown` → `未知` |
| 5 | `understanding_user_confirmation` 或 `requirements_understanding_confirmation` | `需求理解确认：` | `pending/approved/unknown` → `待确认/已确认/未知` |
| 6 | `requirements_user_approval` | `需求文档用户批准：` | `pending/approved/unknown` → `待批准/已批准/未知` |
| 7 | `requirements_independent_review` | `需求文档独立评审：` | `pending/approved/unknown` → `待评审/已通过/未知` |
| 8 | `specification_gate` | `技术规格门禁：` | `blocked/open` → `未开放/已开放` |
| 9 | `spec_path` | `技术规格：` | path 原样；`null` → `未确定` |
| 10 | `spec_user_approval` | `技术规格用户批准：` | `pending/approved` → `待批准/已批准` |
| 11 | `spec_independent_review` | `技术规格独立评审：` | `pending/approved` → `待评审/已通过` |
| 12 | `plan_path` | `实施计划：` | path 原样；`null` → `尚未创建` |
| 13 | `plan_review_status` | `计划评审状态：` | null plan + `not-approved` → `未开始`；非空 plan 的 `not-approved/approved/unknown` → `未通过/已通过/未知` |
| 14 | `implementation_gate` | `实施门禁：` | `blocked/open` → `未开放/已开放` |

校验严格分层且不跨层继续：UTF-8/BOM/JSON syntax → duplicate/nonstandard number/Unicode scalar preflight → 顶层输入 → canonical shape/value → gate → compact 参数 → 映射/渲染。退出码和稳定错误 code 为：

| 退出码 | `code` | 含义 |
| --- | --- | --- |
| `0` | — | 成功 |
| `2` | `invalid_json` | stdin 为空、非法 UTF-8、含 BOM、语法非法、含重复 key/非标准数值/未配对 surrogate，或包含多个 JSON value；合法但非 object 的 JSON 属于 `invalid_input` |
| `3` | `invalid_input` | 顶层字段缺失、额外、类型或枚举非法 |
| `4` | `invalid_canonical` | canonical 字段、类型、允许值或上下文约束非法 |
| `5` | `gate_conflict` | gate 与上述 truth table 冲突 |
| `6` | `mapping_error` | 已验证 canonical 缺少唯一前向显示映射，属于实现缺陷 |
| `7` | `invalid_compact` | compact 的 stage 或 next_step 非法，或 full 未把两者设为 `null` |

失败 stdout 始终为空，stderr 始终只含一行 `{"code":"<code>","errors":["<json-pointer>: <reason-token>"]}` 和末尾换行，不输出 traceback。reason token 固定使用 `invalid_utf8`、`bom`、`invalid_syntax`、`duplicate`、`nonstandard_number`、`surrogate`、`missing`、`unexpected`、`wrong_type`、`invalid_value`、`empty`、`out_of_range`、`reserved`、`line_break`、`forbidden_character`、`conflict` 或 `missing_mapping`。pointer 使用 RFC 6901；UTF-8/BOM/syntax/nonstandard-number 的 root pointer 是 RFC 6901 空字符串，因此 error item 以 `: <reason-token>` 开头。重复 key 和 surrogate 使用 escaped non-root pointer，同一 parse-preflight 层按 pointer Unicode code point 排序且同一路径只报告一次。后续每层先按顶层六字段顺序、再按对应 canonical 表顺序、最后按 `stage`、`next_step` 排序；同一对象的额外 key 在预期 key 后按 Unicode code point 排序。若多层同时可能失败，只返回最早失败层的 code 与该层全部错误，因此错误集合和顺序不依赖输入 key 顺序。

stdin、stdout 和 stderr 均使用严格 UTF-8 且无 BOM。成功 stdout 只包含目标视图，行间和唯一末尾换行均为 LF `\n`；不得输出 CRLF、Markdown fence、canonical JSON、解释或第二个状态块。错误 stderr 也只使用唯一末尾 LF。
- 仓库级测试比较三份脚本字节与相同输入输出；每个 skill 本地测试仍直接执行自身副本，保证单独安装可验证。

完整状态的中文映射表不再由三个自然语言 reference 分别充当可执行权威。`docs/workflow.md` 保留面向维护者的公共说明；运行时确定性以本地 renderer 和 canonical 输入为准，references 只描述状态语义、使用时点和失败边界。

### 评估证据新鲜度

`scripts/validate_repo.py` 增加 Git-aware freshness 校验，并复用现有 `production_files()` 定义运行时 payload：


每个 skill 的 freshness evidence bundle 使用以下确定路径类别：

| 类别 | 路径或来源 |
| --- | --- |
| `production` | 当前或 Git 历史中属于 `skills/<skill>/SKILL.md`、`agents/`、`assets/`、`references/`、`scripts/` 的 publishable 文件；删除和重命名后的旧路径同样计入 |
| `criterion` | `evaluations/<skill>/rubric.json` 与 current RED `selected_case` 对应的 `cases/<id>-*.md` |
| `current-red` | 对 `creation-plus-current-red` / `imported-plus-current-red`，为 `migration-red/result.json` 与其中 `selected_case` 对应的 output |
| `green-output` | `green/result.json` 新增的非空 `fresh_cases` 列表所指向的 `green/<id>-output.md` |
| `green-result-review` | `green/result.json`，包含全部既有结构字段、`fresh_cases`、当前 `review_status`、generic reviewer 和日期 |
| `registry-stage` | `evaluations/registry.json` 的当前有效值；只判断当前 stage，不要求最终 diff 保留一次临时 stage 往返 |

`fresh_cases` 必须是去重 case id 列表，是当前 production 变化后实际重新运行并纳入本次评审的 GREEN 场景；它必须包含 current RED 的 `selected_case`，每个值都存在于 rubric、cases、GREEN outputs 和 GREEN result 的完整 case map 中。它不是 attempt 历史，不记录运行标识符或内容哈希。

#### 干净 Git 工作树

对带 current-red 的 profile，validator 读取每个类别最后一次 Git commit，并要求以下祖先链；相同 commit 合法：

```text
criterion <= current-red <= production <= every fresh green-output <= green-result-review <= HEAD
```

- “`A <= B`”通过 `git merge-base --is-ancestor A B` 判断；任何两个证据位于不可比较的 merge sibling 时保守失败，必须在合并结果上刷新 GREEN 与 review。
- `production` commit 通过 Git name-status 历史查找最后一个命中 production path predicate 的 commit，不只遍历当前存在文件，因此删除、移出、移入和重命名均会形成新的 production commit。
- 同一 commit 同时包含 RED、production、GREEN 和 review 时全部节点相等，链有效；分阶段 commit 时必须保持 RED 在 production 之前、GREEN/review 在 production 之后。
- `creation-only` 只对其首次创建基线有效：若最后 production commit 不晚于当前 GREEN/review，保持原创建证据；若 production 晚于当前 GREEN/review，freshness 失败并要求先把 profile 升级为带 current-red 的 profile，不允许仅刷新日期。

#### 有未提交变化的 Git 工作树

未提交最终态无法在不增加 commit、内容哈希或 attempt 审计的前提下证明文件修改的先后顺序，因此 validator 使用“当前 worktree evidence bundle 完整性”而不是要求不可观察的 registry 往返：

- production 有 tracked modification、deletion、rename 或 untracked publishable file 时，相关 skill 进入 worktree freshness 路径。
- 带 current-red 的 profile 必须同时具备：有效且当前 worktree 已修改或新增的 `migration-red/result.json` 与 selected output；至少一个已修改或新增的 production 文件；已修改或新增的 `green/result.json`；`fresh_cases` 指向的每个 GREEN output 均已修改或新增。criterion/rubric 可以复用已提交且仍被 current RED 明确引用的内容，不强制制造无语义 diff。
- stage 为 `implemented` 时，green result 必须是当前 GREEN 且 review 仍为 pending；只允许 `--evidence-only <skill> --require-freshness` 通过，普通严格验证继续失败。
- stage 为 `review-approved` 时，同一 worktree bundle 必须完整，green result 必须含当前 `review_status: approved`、generic reviewer 与日期；validator 可报告 `worktree-current`。该结果只证明 production 与当前 RED/GREEN/review metadata 同时存在于最新 diff，不能替代运行时实际观察到的独立 reviewer 对最新完整 diff 的 verdict。
- registry 当前值本身参与 stage 判断，但不要求 `implemented -> review-approved` 的临时变化留在最终 diff；最终完成证据由完整 worktree bundle、当前 metadata、实际 observed reviewer verdict 和最新 diff 共同构成。
- 随后任何 production 修改都必须按工作流把 review metadata 重置为 pending、重新运行受影响 GREEN 并复审；validator 不声称在没有 commit/hash 的 dirty worktree 中能够单独证明事件先后。

#### 非 Git、untracked 与阶段结果

- 全新 untracked production 和证据文件按 worktree bundle 规则处理；缺少任一必需类别时确定失败。
- 非 Git 副本可以继续执行结构校验，但 freshness 状态固定为 `unverified-non-git`；新增 `--require-freshness` 时返回非零。统一完整验证始终使用该严格参数。
- `baseline-only` 只允许没有 exposed skill 的既有行为；`implemented` 只允许目标 `--evidence-only`；`review-approved` 必须满足 clean ancestor chain 或 dirty worktree bundle，并具有真实独立评审 metadata。
- freshness 错误指出 skill、当前模式、较新的 production 类别和缺失、过旧或不可比较的证据类别，不显示源码内容、凭证或本机私有数据。

该设计使当前仓库已存在的旧 GREEN 问题首先形成 RED；实现完成前必须刷新三个受影响 skill 的 rubric/cases、current RED、GREEN 输出、结果与独立评审，而不是仅修改日期或删除旧失败。

### 目标会话 Agent inventory

`development-prompt.md` 和 prompt skill 合同改为：

1. 目标会话第一次需要委派时检查实际加载且可按名称启动的个人全局 custom agents。
2. 在目标会话上下文内记录 `name`、`description` 和本次读取是否可靠；不写项目文件、缓存、用户目录或 task/thread 标识符。
3. 后续委派按该清单匹配并记录实际 agent name，不重复扫描。
4. 用户或运行时声明配置变化、首次读取失败、匹配 agent 按名称启动失败、清单与可观察能力冲突或用户显式要求刷新时，刷新一次后重新判断。
5. 刷新后仍无法启动匹配 agent 时停止该次委派并报告能力缺口；不得静默改用职责不匹配的角色或声称已使用该 agent。

`render_prompt.py` 的输入 schema 与 dynamic fence 不变，只渲染更新后的模板文本。

### 统一验证与安装差异检查

新增 `scripts/check.py`：

```text
.venv/bin/python scripts/check.py --skill <skill-name> [--skill <skill-name> ...]
.venv/bin/python scripts/check.py --full
```

- 两种模式互斥且必须显式选择；skill 名必须来自当前 registry，重复值去重，未知值在启动检查前失败。
- registry 中 `baseline-only`、缺失或未知 stage 的 skill 不能作为 `--skill` 目标，启动检查以 capability/input error 失败。定向模式按每个目标的当前 stage 调用仓库 validator：`implemented` 使用 `validate_repo.py --evidence-only <skill> --require-freshness`，`review-approved` 使用 `validate_repo.py --reviewed-skill <skill> --require-freshness`。两参数互斥；新增 `--reviewed-skill` 只验证该目标的 approved metadata 与当前 freshness，同时允许其它 skill 尚处于 `implemented`。
- 定向模式还运行每个目标 skill 自身 unittest、目标 `quick_validate.py`，以及一次仓库 `tests/` unittest。当前仓库级合同均跨 skill 或覆盖公共 tooling，因此第一版不维护容易漂移的测试文件白名单；即使传多个目标，仓库 `tests/` 也只运行一次。每个目标各运行一次 stage-aware validator，不把一个目标的 stage 当作另一个目标的证据。
- 完整模式要求 registry 中全部 exposed skill 当前均为 `review-approved`，否则在运行测试前以 capability/evidence 前置失败；满足时运行当前仓库测试、五个 skill 测试、一次 `validate_repo.py --require-freshness`、五个官方 skill validator 和一次 plugin validator。
- 彼此独立的 subprocess 使用标准库并发执行；每个进程独立捕获 stdout/stderr，主进程在结束后按固定顺序输出命令、耗时、退出状态和必要诊断。默认不 fail fast，使一次运行能给出完整失败面。
- `--timeout-seconds` 接受正整数，默认每个 subprocess `300` 秒；超时后终止该子进程、记录 `timeout`，不自动重试，其它已启动检查继续完成。只有在所有参数、registry 和 validator capability 前置检查成功后才启动任何 subprocess。
- 官方 validator 路径按固定优先级解析为普通可读文件：显式 `--skill-validator <path>` / `--plugin-validator <path>`，其次 `${CODEX_HOME}/skills/.system/...`，最后 `$HOME/.codex/skills/.system/...`。不读取 plugin cache；候选缺失、不可读、为目录或 symlink 时标记 `capability_error`，不得跳过。定向模式只需要 skill validator，完整模式两者都需要。
- 总退出码：`0` 表示全部必需检查实际通过；`1` 表示任何已启动检查非零、超时或运行期失败；`2` 表示参数、registry、stage 或 validator capability 在启动前无效。stdout 保持固定顺序汇总；启动前错误写 stderr。环境/能力失败与测试失败分开标记，不吞异常或修改测试。
- 通过 `sys.executable` 保持当前 `.venv`，不安装依赖、不启动服务、不联网。

命令矩阵由 `check.py` 直接构造，不通过 shell 字符串执行：

| 检查 | `--skill` | `--full` |
| --- | --- | --- |
| 仓库 tests | `python -m unittest discover -s tests -v`，整次调用一次 | 同左，整次调用一次 |
| skill tests | 每目标 `python -m unittest discover -s skills/<skill>/tests -v` | 五个 exposed skill 各一次 |
| 仓库 validator | 每目标按 stage 选择 `--evidence-only` 或 `--reviewed-skill`，均带 `--require-freshness` | 一次 `scripts/validate_repo.py --require-freshness` |
| official skill validator | 每目标一次 `quick_validate.py skills/<skill>` | 五个 exposed skill 各一次 |
| official plugin validator | 不运行 | 一次 `validate_plugin.py .` |

`<skill>` 只来自已验证 registry key，subprocess argv 以 list 传入；显示命令时使用安全 quoting，不插值执行。

新增 `scripts/verify_install.py`：

```text
.venv/bin/python scripts/verify_install.py --codex-home <path> [--skill <skill-name> ...]
```

- 未指定 skill 时比较 registry 中全部已实现 skill；指定时允许重复参数并去重。
- `--codex-home` 必填；每个目标必须在 registry 中存在且不能是 `baseline-only`。目标 `<codex-home>/skills/<skill-name>` 必须是普通可读目录，工具不回退到真实默认安装。
- 仓库可发布 payload 与安装目标边界完全相同：skill 根的 `SKILL.md`，以及 `agents/`、`assets/`、`references/`、`scripts/` 下所有普通文件。skill 根其它文件、`tests/`、evaluation、cache 和构建产物均不属于比较边界；目标中只在该 publishable 边界出现的额外普通文件必须报告为 `extra`。
- 两侧都忽略 `__pycache__` 目录、`.pyc`、`.pyo`、`.pyd` 和 `.DS_Store`；边界内任一 symlink、socket、device 或其它非普通文件均为读取错误，不跟随。报告缺失、额外和内容不同的相对路径，但不输出文件正文。
- 目标不存在、不可读或内容不同均返回非零；完全一致返回零。
- 工具只读，不创建目录、不复制、不删除、不修改 ownership，也不把差异结果当成安装授权。

## 组件与控制流

### 1. `creating-product-requirements`

- `SKILL.md` 改为阶段化读取、依赖感知最多三问和回复分类；触发 description 不变。
- `references/discovery-and-confidence.md` 拥有问题依赖规则与普通澄清定义。
- `references/document-contract.md` 继续拥有 PRD 内容边界。
- `references/review-and-handoff.md` 保留 canonical 八字段、批准失效、完整 checkpoint 与下游转换，调用本地 renderer 而不重复维护可执行中文映射。
- 新增本地 `scripts/render_handoff.py`；合同测试与前向场景覆盖 compact、full、确认门、批量问题和失败关闭。

### 2. `creating-development-specs-and-plans`

- `SKILL.md` 改为阶段化读取、普通技术澄清批次、完整 checkpoint 与本地 renderer 调用。
- PRD inspector、spec 双批准、plan 独立评审、十四字段和路由门保持不变。
- `references/review-and-handoff.md` 保留 canonical 十四字段和 plan 跨字段语义，但不再把自然语言映射表作为执行机制。
- 新增与其它两个 skill 字节一致的 `scripts/render_handoff.py`；本地测试覆盖 compact/full、spec 状态允许集、plan 未创建/未通过和下游 PRD 复验失败。

### 3. `generating-development-prompts`

- `SKILL.md` 按入口逐步读取 discovery、permission、routing references；自动路由仍始终使用完整十四字段，手动无上游请求仍不追加状态。
- 新增同一 `scripts/render_handoff.py`，用于自动路由前十四字段验证和完整视图生成；不修改 `render_prompt.py` 状态职责边界。
- `development-prompt.md` 改为目标会话 Agent inventory 一次读取、条件刷新。
- prompt tests 和 forward evaluations 验证新 inventory 合同、完整路由状态、renderer stdout 不变和风险批次评审合同。

### 4. 评估与仓库工具

- `scripts/validate_repo.py` 增加 Git-aware freshness 与 `--require-freshness`，保留现有结构验证和非 Git fixture 能力。
- `scripts/check.py` 编排现有权威命令；`scripts/verify_install.py` 复用 publishable payload 边界。
- 新增独立仓库测试文件覆盖 handoff renderer、freshness、check 编排和安装差异；避免继续把所有工具测试堆入单一合同文件。
- 三个受影响 evaluation 目录增加当前 RED、更新 rubric/cases、GREEN 输出和结构化结果；registry 按 `implemented -> review-approved` 真实阶段推进。

### 5. 公开文档和项目规则

- 更新 `README.md` 与 `docs/workflow.md`，说明普通三行紧凑状态、完整 checkpoint、批量澄清、Agent inventory 和兼容边界。
- 更新 `docs/agent-development.md`，说明评估 freshness、统一 check 和只读安装比较；更新 `docs/install.md` 增加只读验证用法，不改变安全更新边界。
- 更新 `CHANGELOG.md` 未发布 `0.1.0`，把“普通澄清由完整状态后缀改为固定三行 compact”标为用户可见 breaking contract，并记录新验证入口。
- `.codex-plugin/plugin.json` 的 skill 数量和版本保持不变；仅当当前描述与实际能力不一致时做最小文案同步。
- `AGENTS.md` 中若要把统一命令提升为维护必需入口，必须由 `managing-agents-rules` 展示当前候选、证据、分类原因和具体 diff，取得只对该 diff 有效的用户批准后才能写入；本 spec 或实施批准都不能代替规则 diff 批准。

## API 与技术接口

### canonical handoff

- requirements 八字段与 workflow 十四字段的名称、顺序、允许值及八到十四字段前缀转换保持不变。
- `specification_gate` 与 `implementation_gate` 继续由现有文档事实决定；renderer 只验证输入 gate 与其它字段一致，不成为新的批准来源。
- 英文 handoff 继续是 skill 间机器输入；旧英文输入兼容。

### `render_handoff.py`

- stdin/stdout/stderr 和退出码形成新的 skill 内部稳定接口。
- `schema_version` 当前只接受整数 `1`；未知版本 fail closed。
- 成功 stdout 是单一 plain-text view；不包含 Markdown fence、解释或 canonical JSON。
- 错误 stderr 使用上文固定 exit code、`code`、reason token 和排序；不得输出 traceback 或部分 stdout。
- production copies 必须字节一致，但运行时不共享路径；仓库开发测试拥有一致性门。

### `validate_repo.py`

- 现有 `--evidence-only` 行为保持。
- 新增 `--require-freshness` 与 `--reviewed-skill <skill>`；后者和 `--evidence-only` 互斥。`--evidence-only` 只允许目标 stage 为 `implemented` 且 review pending，`--reviewed-skill` 只允许目标 stage 为 `review-approved` 且 review approved；两者都只检查目标 skill 的当前结构和 freshness，不因其它 skill 的中间 stage 失败。
- 不带目标参数的严格模式验证完整 registry，要求所有 exposed skill 的结构、stage 和 freshness 都有效。
- 默认在 Git worktree 中执行 freshness；非 Git 环境仅在未要求严格 freshness 时允许结构验证通过并明确报告未验证项。

### `check.py`

- `--skill` 可重复，`--full` 为布尔开关，二者互斥；`--timeout-seconds` 默认 `300`。显式 validator path 参数覆盖环境解析。
- stdout 是固定顺序的人类可读汇总；stderr 保留启动级参数或能力错误。退出码 `0` 仅表示全部必需检查实际通过。
- 不承诺各检查实时输出顺序；单项完成输出在主进程汇总时保持完整。

### `verify_install.py`

- `--codex-home` 必填，避免在未明确目标时读取默认真实安装。
- `--skill` 可重复；未知或未实现 skill 在比较前失败。
- publishable 边界固定为根 `SKILL.md` 加四个允许子目录内的普通文件；目标边界内 extra 参与失败，边界外文件不参与比较。
- 退出码 `0` 表示 publishable payload 完全一致，`1` 表示内容差异，`2` 表示参数、registry、路径、读取或文件类型错误。

## 数据模型与实体关系

本阶段不引入持久化业务数据、数据库实体或跨进程共享状态。

- handoff renderer 输入是单次进程内 JSON，输出后不持久化。
- canonical 快照继续来源于版本化文档、inspector、discovery 与当前会话事实。
- Agent inventory 只存在于目标会话上下文，不写磁盘、缓存或用户目录。
- validation run 只在主进程内保存命令、结果、耗时和诊断，进程结束后不创建结果数据库。
- evaluation registry 与已有 JSON 结果继续是版本化开发证据；不增加哈希 manifest 或 attempt 表。

## 状态转换、迁移边界与一致性

### 回复状态

```text
已验证 canonical
  -> classify reply
  -> ordinary-clarification -> verified stage/next-step context -> compact renderer -> three-line suffix
  -> checkpoint/blocked/routing -> full renderer -> 8/14-field suffix
  -> manual prompt without upstream -> existing renderer-only contract
  -> mapping failure -> preserve canonical, no partial view, stop transition
```

### 评估状态

```text
review-approved current evidence
  -> production contract changes
  -> freshness fails and registry moves to implemented
  -> current criterion/case + RED fixed
  -> implementation + GREEN
  -> independent review of current evidence
  -> registry returns to review-approved
```

任何后续 production change 都重新使先前 review-approved evidence 失效。只修改日期、reviewer 文本或删除失败证据不能构成恢复。

### Agent inventory 状态

```text
unread
  -> first delegation -> loaded
  -> normal delegations -> reuse loaded
  -> config change/read failure/start failure/conflict/explicit refresh -> refresh once
  -> refreshed and usable -> loaded
  -> refreshed but unavailable -> capability gap
```

### 验证进程一致性

- 并行检查之间不共享可变业务状态；现有测试使用临时目录，官方 validators 和 payload 比较只读。
- 每个子进程独立持有 stdout/stderr buffer；主进程不在子进程运行时交叉写入其 buffer。
- 默认等待已启动检查全部结束后汇总，不因一个失败取消其它检查，不需要锁或事务。
- 若后续证据证明某两个检查写入同一非临时目标，则把该组改为串行；不得用竞态换取耗时下降。

### 本次变更的自举执行

本阶段自身从用户明确提出该要求起采用本 spec 的优化流程，形成可观察的 dogfood 证据，但不把自我使用替代合同测试或独立评审：

- 普通非阻塞澄清使用紧凑三字段三行；普通进度不新增状态分类。暂停、确定性阻塞、确认/批准门、文档阶段完成和跨 skill 交接使用完整八/十四字段。renderer 尚未实现或尚未通过当前 RED/GREEN 前，主 Agent 使用冻结 canonical topic 和已验证阶段/下一步上下文人工前向渲染；脚本一经验证可用，后续 ordinary clarification 改用本地脚本，checkpoint 继续使用其 full 模式。
- 已加载的适用规则不重复读取；后续新阶段只在首次动作前加载该阶段必需 reference。需要提问时按依赖关系一次提出一至三个问题。
- 三个受影响 skill 在任何 production write 前先补当前失败合同和前向 RED，并把 registry 真实推进到 `implemented`；新 freshness 与 `check.py` 形成 GREEN 后，后续定向验证立即改用 stage-aware 统一入口。
- 最终评审前使用 `check.py --skill` 完成受影响目标验证；所有受影响 skill 获得真实独立批准并恢复 `review-approved` 后，使用 `check.py --full` 完成完整门。安装只在临时 `CODEX_HOME` staging 使用 `verify_install.py`，真实安装仍等待独立授权。
- 自举过程中若工具尚不可用或自身 RED 正在阻止新入口运行，明确记录 bootstrap 状态并执行现有等价底层命令；不得因此宣称新入口已通过、跳过失败检查或降低评审门。

## 错误与不确定性

- handoff JSON 不合法、字段缺失/额外、类型或枚举非法、gate 与批准事实冲突、compact 字段含非法字符时，renderer 按固定校验层、退出码和错误顺序返回单行机器可读 stderr，stdout 为空。
- 无法可靠区分普通澄清和阻塞时使用完整状态；无法生成完整状态时沿用现有映射失败关闭行为。
- reference 在进入所需阶段时不可读或缺失，报告阻塞且不继续文档写入、评审或路由。
- Git freshness 无法取得仓库根、commit 或工作树状态时，严格模式失败为环境/证据问题，不把结构检查通过升级为当前证据通过。
- freshness 发现 production 较新但无法定位当前 RED/GREEN/评审证据时，指出缺失证据类别，不自动改写 registry 或生成伪证据。
- check 在启动前发现参数、stage 或 official validator capability 无效时不启动任何 subprocess 并返回 `2`；已启动子进程的启动失败、超时或非零退出均记录并返回 `1`。本阶段不增加自动重试，以免重复执行未知副作用命令。
- official validator 或 plugin validator 按显式参数、`CODEX_HOME`、`HOME` 的顺序仍不可用时标记能力缺口，不能跳过并报告整体通过。
- install target 缺失、不可读或 publishable 边界存在 symlink/非普通文件时，verify 工具停止目标 skill 的比较、返回 `2` 并报告类别，不修改权限或目标内容。
- Agent inventory 刷新后仍无法按名称启动职责匹配 agent 时，停止该次委派并报告能力缺口。

## 测试与文档

### RED 与定向测试

- 在修改 production 内容前先为每个受影响 skill 和仓库工具增加失败合同或前向场景并观察 RED。
- `creating-product-requirements`：普通澄清只输出 compact；需求摘要确认、批准、阻塞和下游交接输出 full；三个独立问题同轮、依赖问题单问；reference 分阶段读取；本地 renderer 成功与失败。
- `creating-development-specs-and-plans`：普通技术澄清 compact；spec 批准、plan 状态、阻塞与路由 full；批量问题与分阶段读取；十四字段 gate 一致性和本地 renderer。
- `generating-development-prompts`：自动三态继续 full；手动无上游不追加状态；本地十四字段 renderer；Agent inventory 首次读取、复用、刷新和能力缺口；dynamic fence 与 discovery schema 不变。
- 仓库测试：三份 renderer 字节一致；八/十四 exact schema、八到十四字段改名、gate truth table、compact 精确三行 UTF-8/LF bytes、full 映射、额外字段、非法 UTF-8/BOM/重复 top-level 与 canonical key/`NaN`/`Infinity`、U+0085/U+2028/U+2029、未配对 surrogate、稳定错误 code/顺序和成功/失败 stdout；production/evidence freshness 的 clean ancestor、merge sibling、dirty tracked/delete/rename/untracked、creation-only 升级、non-Git、implemented/review-approved 路径；check 的单 skill、多 skill、stage-aware validator、完整模式前置、validator path 优先级、timeout、退出码和失败传播；安装 diff 的一致、缺失、publishable extra、边界外忽略、内容不同、symlink/非普通文件和只读边界。

### 前向评估

- 三个受影响 skill 更新 rubric/cases 并保存新的当前 RED 与 GREEN。
- PRD 场景至少覆盖 ordinary compact、summary-confirmation full、三个独立问题和依赖问题。
- spec/plan 场景至少覆盖 ordinary compact、spec approval full、阻塞 full 和 plan approved routing。
- prompt 场景继续覆盖三态与 copy stress，并新增目标会话 Agent inventory 一次读取、条件刷新和风险批次评审合同；现有陈旧的逐任务评审 GREEN 输出必须被当前输出替换。
- GREEN 使用看不到 expected、失败解释或实现结论的全新 Agent；原始 trace 保存在 `work/`，版本库只保存脱敏选中证据。

### 文档同步

- 更新 `README.md`、`docs/workflow.md`、`docs/agent-development.md`、`docs/install.md` 和 `CHANGELOG.md` 的当前事实。
- 只有 plugin manifest 当前描述与最终能力不一致时才最小更新 `.codex-plugin/plugin.json`；版本保持未发布 `0.1.0`。
- `AGENTS.md` 统一验证命令属于独立规则候选，必须走 `managing-agents-rules` 的逐 diff 批准；未获批准时保留现有规则并在公开开发文档提供 convenience 命令。
- 新增或修改生成式 production 文件后检查 `agents/openai.yaml` 与最终 `SKILL.md` 是否仍一致；触发 metadata 未变化时不制造无关 diff。

### 验证范围

- 三个受影响 skill 的 unittest 与直接跨 skill 回归。
- 新增 handoff renderer、freshness、check 和 install verifier 测试。
- 仓库完整 unittest、严格 `validate_repo.py --require-freshness`、五个官方 skill validator 和 plugin validator。
- 三个受影响 skill 的当前 RED/GREEN 前向场景。
- Python 3.9 与 Python 3.14 维护矩阵。
- 临时 `CODEX_HOME` staging、单 skill 与组合 payload 比较；真实安装只做用户明确授权后的单实例刷新与写后验证。
- 最新完整 diff 的一次独立整体评审；仅在后续任务依赖尚未验证的 freshness 基础时设置一个中间里程碑评审，不因 task 数量逐项评审。

## 验收标准

1. 普通 PRD 或技术规格澄清只输出固定三字段三行状态，行间无空行且不使用字段分隔符；topic 来自 canonical，阶段和下一步来自已验证的当前回复上下文，显示不改变机器状态。暂停、阻塞、确认、批准、文档阶段结束、下游交接和三态路由输出现有完整状态。
2. 无上游十四字段的手动提示词请求仍只返回 renderer stdout，不伪造 compact 或 full handoff。
3. 一轮最多提出三个互不依赖问题；依赖型问题仍一次一个，部分回答不丢失已确认事实。
4. 三个文档交接 skill 在首次触发时不再无条件加载全部 references，并在首次相关动作前完整加载所需合同。
5. 三个 skill 各自携带可单独运行的相同 `render_handoff.py`，相同输入产生字节一致输出，运行时不依赖兄弟路径。
6. renderer 对严格 UTF-8 JSON、唯一 key、标准数值、Unicode scalar、八字段和十四字段 exact field set、类型、允许值、八到十四字段改名、gate truth table 和前向映射执行校验；三行/full 输出只使用 LF。相同非法输入产生稳定退出码与错误顺序，失败 stdout 为空且不会推进自动交接。
7. canonical 字段、八到十四字段转换、批准门、`current-session | new-session | blocked` 路由、旧英文输入和 prompt dynamic fence 合同保持兼容。
8. 在当前 production 晚于 GREEN/评审证据的仓库状态下，严格 freshness 检查形成 RED，不能继续报告相关 skill 为当前 `review-approved`。
9. production 变化完成当前 criterion、RED、GREEN 和独立评审后，严格 freshness 与结构验证均通过；不保存固定内容哈希或长期 manifest。
10. 非 Git 副本可以运行结构 validator，但 `--require-freshness` 如实失败为未验证，不把结构通过表述为证据新鲜。
11. 目标会话多次正常委派时只读取一次全局 Agent inventory；配置变化、读取失败、启动失败、证据冲突或显式请求触发刷新。
12. inventory 刷新后匹配 agent 仍不可启动时报告能力缺口，不伪造使用或静默降级。
13. `check.py --skill` 按每个目标当前 `implemented | review-approved` stage 选择 evidence-only 或 reviewed-skill 严格验证并运行直接回归；`check.py --full` 只在全部 exposed skill 已 review-approved 时运行完整既有验证矩阵。任一必需检查失败、超时或能力缺口均按固定退出码失败并保留逐项诊断。
14. check 并行执行不会覆盖结果或改变现有测试语义；无法证明独立的命令保持串行。
15. `verify_install.py` 只比较根 `SKILL.md` 与四个 publishable 子目录，准确报告一致、缺失、边界内额外和内容差异；边界外文件不误报，symlink/非普通文件失败关闭，始终保持目标只读。
16. 当前过期的公开 GREEN 输出被新鲜前向结果替换，registry 只有在真实独立评审后恢复 `review-approved`。
17. README、workflow、agent-development、install 和 CHANGELOG 准确说明新行为、breaking 用户可见后缀变化与验证入口。
18. 本阶段不改变任何文档改动的独立评审要求，不实现未来格式或机械型轻量改动免评审规则。
19. 五个 skill 继续单独安装和验证，plugin 继续打包五个 skill 且保持未发布 `0.1.0`。
20. Python 3.9/3.14、临时 staging、完整 plugin 和最新完整 diff 的验证及独立评审证据全部真实可用后，才允许报告实现完成。
