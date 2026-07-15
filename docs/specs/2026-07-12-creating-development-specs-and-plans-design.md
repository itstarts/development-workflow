---
document_type: design
topic: creating-development-specs-and-plans
user_approval: approved
approved_at: 2026-07-15
independent_review: approved
independent_reviewer: independent-spec-reviewer
independent_reviewed_at: 2026-07-15
---

# Creating Development Specs and Plans 设计规格

## 1. 背景

`creating-development-specs-and-plans` 负责把尚未定型的开发需求转成两份稳定文档：用户明确批准的 design spec，以及由独立评审者批准的 implementation plan。它通过文档路径和显式状态与 `generating-development-prompts` 协作，不调用后者，也不执行目标项目代码。

## 2. 目标

- 读取适用规则、相关代码、测试和文档，用仓库事实约束设计。
- 澄清会改变范围、行为或公共契约的重要问题。
- 默认生成 `docs/specs/YYYY-MM-DD-<topic>-design.md`；用户显式路径优先。
- spec 经独立评审后，请用户明确批准当前书面版本。
- 仅在 spec 的独立评审和用户批准都有效时，生成 `docs/plans/YYYY-MM-DD-<topic>.md`。
- plan 包含精确文件、实施步骤、验证命令和预期结果，并经独立评审批准。
- 每次暂停或交付都输出固定六字段状态记录。
- 保持 skill 自包含、可单独安装，并纳入 plugin 和仓库验证。

## 3. 非目标

- 不实现目标代码，不生成新会话开发提示词。
- 不调用兄弟 skill，不创建或管理用户可见 task/thread。
- 不自动 commit、push、merge、rebase、tag、release、真实安装或改变外部状态。
- 不从语气、旧文档、文件名或缺失证据推断批准。
- 不为普通需求强制增加安全分析、哈希、审计链或与实际风险无关的校验。

## 4. 工作流

1. 读取适用规则和与需求直接相关的仓库证据，检查工作区是否存在重叠修改。
2. 只对影响范围、公共行为、数据、权限或不可逆决策的重要歧义提问；路径或 topic 无法唯一确定时先澄清，不猜测或覆盖已有文件。
3. 对存在真实取舍的设计比较可行方案；没有实质取舍时直接给出方案。
4. 写 spec，自检后交给未参与编写的只读子代理评审。主代理修复 findings，并对最新版本复审。
5. spec 独立评审通过后，向用户报告绝对路径并请求明确批准。实质修改会使原评审和用户批准失效。
6. 两项批准均有效后写 plan，自检并交给未参与编写的只读子代理评审，修复至 `APPROVED`。
7. 输出显式路径和状态；任一门禁缺失时停止，不伪造后续产物。

## 5. 文档契约

### 5.1 Spec

spec 至少包含：目标、非目标、现状证据、行为与边界、组件职责或控制流、错误与不确定性、测试、文档影响和可观察验收标准。权限、安全或敏感数据仅在目标需求确实涉及这些边界时展开，不作为每份文档的机械章节。

frontmatter 初始状态：

```yaml
document_type: design
topic: <stable-topic>
user_approval: pending
independent_review: pending
```

独立评审通过后由主代理补充通用 reviewer 角色和日期。只有用户已被指向当前文件并明确批准同一版本时，才能写 `user_approval: approved`。

### 5.2 Plan

plan 只能基于已批准的当前 spec 生成，内部用仓库相对路径引用 spec，frontmatter 从以下状态开始：

```yaml
document_type: implementation-plan
topic: <stable-topic>
spec_path: docs/specs/YYYY-MM-DD-<topic>-design.md
spec_user_approval: approved
review_status: pending
```

每个任务包含精确文件、输入输出接口、最小实现步骤、相关测试或验证命令、预期结果和必要文档同步。目标仓库要求 TDD 时写明 RED、GREEN、REFACTOR；只有真实 plan 评审通过后才把 `review_status` 改为 `approved`。

### 5.3 状态映射

- `review_status: pending` → `not-approved`
- 可靠的 `review_status: approved` → `approved`
- 已存在 plan 的字段缺失、重复、冲突、格式不可靠或不可读 → `unknown`
- plan 尚未生成 → `plan_path: null` 且 `plan_review_status: not-approved`

## 6. 输出契约

每次回复结尾输出以下六个字段；实际输出只写一个允许值，不复制备选符号：

```text
spec_path: <absolute-path> | null
spec_user_approval: pending | approved
spec_independent_review: pending | approved
plan_path: <absolute-path> | null
plan_review_status: not-approved | approved | unknown
implementation_gate: blocked | open
```

只有 spec 独立评审、用户批准和 plan 独立评审都为 `approved` 时，`implementation_gate` 才为 `open`。

## 7. Skill 结构

```text
skills/creating-development-specs-and-plans/
├── SKILL.md
├── agents/openai.yaml
├── assets/
│   ├── plan-template.md
│   └── spec-template.md
├── references/
│   ├── discovery-and-clarification.md
│   ├── document-contracts.md
│   └── review-and-handoff.md
└── tests/test_skill_contract.py
```

不新增运行时第三方依赖。`SKILL.md` 保持精炼，详细规则放在一层 references，文档模板放在 assets。

## 8. 最小验证模型

新 skill 保留能证明核心行为的最小证据：

- 固定脱敏场景和独立 rubric；场景不向代理暴露 expected 或失败分析。
- 创建 skill 前使用无目标 skill 的新鲜代理观察至少一个核心 RED。
- 使用不同的新鲜代理和相同场景运行 GREEN，确认批准门、路径、状态映射和无目标代码副作用。
- 原始 trace 和 stderr 仅保存在被忽略的 `work/`；版本库只保存选中输出和简洁结构化结果。
- 结果记录场景 ID、运行是否有效、通过或失败的判据及必要 warning；不记录输入、runner、trace、输出或候选文件哈希，也不维护 attempt 审计链。
- 基本污染检查只确认没有读取原仓库/其他评估材料、没有越界文件修改、没有缺失最终回复。普通诊断命令失败但已恢复时只记 warning。

仓库 validator 只检查必需证据存在且可解析、RED/GREEN 布尔状态真实、GREEN 场景完整、独立评审已批准，以及版本化评估材料没有明显本机路径或凭证文本。

## 9. 验收标准

- 默认路径为 `docs/specs/` 和 `docs/plans/`，显式路径优先。
- spec 未经独立评审或用户批准时不生成 plan。
- plan 未经真实独立评审时不标记 approved。
- 六字段输出在成功、澄清和阻塞场景中都完整、真实。
- `pending`、`unknown` 和 `null` 映射符合本规格。
- skill 不实现目标代码、不调用兄弟 skill、不创建用户可见 task/thread。
- 创建前 RED、最终 GREEN、skill 测试、仓库测试、官方 validators 和独立最终评审通过。
- 版本化证据与验证器不依赖哈希、候选 manifest 或逐次 attempt 审计。
