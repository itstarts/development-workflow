---
document_type: implementation-plan
topic: creating-development-specs-and-plans
spec_path: docs/specs/2026-07-12-creating-development-specs-and-plans-design.md
spec_user_approval: approved
review_status: approved
reviewer: independent-plan-reviewer
reviewed_at: 2026-07-15
---

# Creating Development Specs and Plans 实施计划

## 目标

完成并验证可单独安装的 `creating-development-specs-and-plans` skill，使其按“spec 独立评审 → 用户批准 → plan 独立评审”的顺序生成中性文档，并以固定六字段交接状态。仓库当前已有未提交候选实现和 RED/GREEN 证据，本计划先按批准 spec 核对现状，再只修复可观察缺口。

## 架构与边界

- Runtime skill 由精炼的 `SKILL.md`、三份一层 references、两份文档模板和 UI metadata 组成。
- 默认路径固定为 `docs/specs/` 与 `docs/plans/`；通过文档和显式状态与 `generating-development-prompts` 协作，不调用其源码或安装副本。
- 评估 runner 使用独立 fixture、临时 `CODEX_HOME`、结构化 trace 和基本文件边界；结果不记录哈希、候选 manifest 或 attempt 审计。
- 仓库 validator 检查结构、核心 RED/GREEN 状态、plugin 打包、安装覆盖边界和明显敏感值，不绑定固定文件字节。
- 不修改 downstream 生产文件，不执行真实安装、commit、push 或发布。

## Task 1：核对核心合同与最小 RED 证据

**Exact files**

- Modify if needed: `evaluations/creating-development-specs-and-plans/rubric.json`
- Modify if needed: `evaluations/creating-development-specs-and-plans/baseline/*.json`
- Modify if needed: `evaluations/creating-development-specs-and-plans/migration-red/*.json`
- Modify: `tests/test_repository_contract.py`
- Modify: `tests/test_skill_evaluation_runner.py`

**Interfaces**

- Consumes: 批准 spec、八个固定场景、已有本地原始运行证据。
- Produces: 可解析的最小 baseline/migration RED 结果和防回归测试。

**Testing approach**

- [ ] RED：针对仍存在的过度校验或错误状态映射先添加/调整定向测试。
- [ ] Verify RED：运行命名测试，确认失败来自目标缺口，而非 fixture 或环境。
- [ ] GREEN：只修改对应 runner、结果模型或证据结构。
- [ ] Verify GREEN：重新运行相同命名测试并要求通过。
- [ ] REFACTOR：删除重复哈希、manifest、attempt 或 sandbox 探针逻辑，保持结果字段精简。
- [ ] Documentation synchronization：同步 `evaluations/AGENTS.md`。

**Commands**

```bash
.venv/bin/python -m unittest \
  tests.test_skill_evaluation_runner.SkillEvaluationRunnerTests.test_result_schema_keeps_only_operational_evidence \
  tests.test_repository_contract.RepositoryContractTests.test_evaluation_evidence_uses_minimal_results -v
```

预期：两项测试通过；版本化证据仅记录场景、有效性、判据和必要 warning。

## Task 2：完成 skill 文档合同

**Exact files**

- Modify: `skills/creating-development-specs-and-plans/SKILL.md`
- Modify: `skills/creating-development-specs-and-plans/references/discovery-and-clarification.md`
- Modify: `skills/creating-development-specs-and-plans/references/document-contracts.md`
- Modify: `skills/creating-development-specs-and-plans/references/review-and-handoff.md`
- Modify: `skills/creating-development-specs-and-plans/assets/spec-template.md`
- Modify: `skills/creating-development-specs-and-plans/assets/plan-template.md`
- Modify: `skills/creating-development-specs-and-plans/tests/test_skill_contract.py`
- Regenerate if stale: `skills/creating-development-specs-and-plans/agents/openai.yaml`

**Interfaces**

- Consumes: 已批准 spec、仓库规则和默认路径契约。
- Produces: 六字段 handoff，及 `pending → not-approved`、不可靠 metadata → `unknown` 的稳定映射。

**Testing approach**

- [ ] RED：先为默认路径、spec review 门、null/unknown 映射、按需安全设计和副作用边界增加失败合同。
- [ ] Verify RED：运行对应命名测试并确认目标行为缺失。
- [ ] GREEN：修改最少的 skill/reference/template 内容使合同成立。
- [ ] Verify GREEN：运行完整 skill 测试。
- [ ] REFACTOR：删除 SKILL 与 references 的重复说明，保持一层资源链接。
- [ ] Documentation synchronization：确认 spec/plan 模板字段与 downstream 公开解析合同一致。

**Commands**

```bash
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/creating-development-specs-and-plans
```

预期：全部 skill 合同通过，官方 validator 输出 `Skill is valid!`。

## Task 3：完成最小 runner 与仓库验证

**Exact files**

- Modify: `scripts/run_skill_evaluations.py`
- Modify: `scripts/validate_repo.py`
- Modify: `tests/test_skill_evaluation_runner.py`
- Modify: `tests/test_repository_contract.py`
- Modify: `evaluations/AGENTS.md`

**Interfaces**

- Consumes: JSONL trace、选中输出、rubric 与三类结构化结果。
- Produces: `valid`、`contaminations`、`warnings`，以及仓库 validator 的受控错误。

**Testing approach**

- [ ] RED：分别覆盖 generic diagnostic failure 不应污染、敏感术语不应误伤、核心 RED/GREEN 布尔门必须拒绝无效值。
- [ ] Verify RED：运行三项命名测试，确认现有错误行为可观察。
- [ ] GREEN：缩窄 denial/敏感值匹配并保持必要结构检查。
- [ ] Verify GREEN：运行 runner 与 repository 测试全集。
- [ ] REFACTOR：集中结果读取与 staging helpers，不增加重复完整性校验。
- [ ] Documentation synchronization：同步 README 与 CHANGELOG 的最小证据说明。

**Commands**

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
```

预期：root 测试全部通过，validator 输出 `repository validation passed`。

## Task 4：验证跨 skill 与 plugin 集成

**Exact files**

- Modify if needed: `.codex-plugin/plugin.json`
- Modify tests only: `skills/generating-development-prompts/tests/test_skill_contract.py`
- Modify tests only: `skills/generating-development-prompts/tests/test_render_prompt.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces**

- Consumes: `docs/specs/`、`docs/plans/`、plan review metadata。
- Produces: downstream CLI 可读取的绝对文档路径和三态 review 状态；plugin 同时暴露两个 skill。

**Testing approach**

- [ ] RED：使用临时仓库通过 `discover_context.py` 公开 CLI 覆盖新默认路径和 review 状态；若现有合同不满足，先观察失败。
- [ ] GREEN：只修改允许的测试、plugin 或仓库文档；downstream 生产文件保持与 `HEAD` 相同。
- [ ] Verify GREEN：运行 downstream 79 项测试、跨 skill root 测试和 plugin validator。
- [ ] REFACTOR：确认两个 skill 无内部 import 或安装路径耦合。
- [ ] Documentation synchronization：安装命令、plugin 描述与 changelog 同步。

**Commands**

```bash
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
```

预期：downstream 测试全部通过，plugin validator 输出成功。

## Task 5：最终矩阵、staging 与独立评审

**Exact files**

- Modify only on evidence-backed failure: 上述已列文件。

**Interfaces**

- Supports: Python 3.9、Python 3.14、两个 skill 单独/组合 staging。
- Gate: 已存在 staging 目标必须拒绝覆盖；真实 GitHub tag 安装保持未执行发布门。

**Testing approach**

- [ ] 运行 Python 3.9 的 root、两个 skill 测试和 repository validator。
- [ ] 运行 Python 3.14 的同一矩阵。
- [ ] 运行两个官方 skill validator 和 plugin validator。
- [ ] 通过 root staging 测试验证单独/组合复制和拒绝覆盖。
- [ ] 扫描版本化内容，确认无外部方法命名空间、本机路径、明显凭证值、哈希 sidecar 或 attempt 审计。
- [ ] 让未参与实现的 reviewer 检查最新 diff、行为门、证据、plugin 和安装边界；修复 finding 后重跑受影响验证并复审。

**Commands**

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python scripts/validate_repo.py

python3.14 -m unittest discover -s tests -v
python3.14 -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
python3.14 -m unittest discover -s skills/generating-development-prompts/tests -v
python3.14 scripts/validate_repo.py

.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/creating-development-specs-and-plans
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/generating-development-prompts
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
```

预期：所有命令退出 0，独立 reviewer 输出 `APPROVED`；不执行真实安装、commit、push 或发布。
