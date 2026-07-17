---
document_type: implementation-plan
topic: agents-rule-governance
spec_path: docs/specs/2026-07-17-agents-rule-governance-design.md
spec_user_approval: approved
review_status: approved
reviewer: independent-plan-reviewer
reviewed_at: 2026-07-17
---

# AGENTS 规则治理 Implementation Plan

**Goal:** 新增可独立安装的 `managing-agents-rules` skill，在每个项目首次实质性开发前检查长期项目规则，并在任务完成时仅对有证据的项目级或全局规则候选进行逐次批准更新，同时保持五-skill plugin、评估证据和公开文档一致。

**Architecture:** 以第五个自包含 skill 承载触发、会话内项目/任务状态、候选归类和写入批准合同；详细策略拆入三个一层 references，不新增运行时依赖或持久化状态。新 skill 与现有开发 skill 可以同时适用但不调用兄弟 skill。项目级规则修改在适用的最终评审前进入最新仓库 diff；全局规则默认写入 Codex home 的长期 `AGENTS.md`，非空 override 只告警，显式选择时才作为独立目标。

**Tech Stack:** Markdown skill 与 references、YAML UI metadata、Python 3.9/3.14 `unittest`、仓库 Python validator、系统 `skill-creator`/`plugin-creator` validator、Codex 隔离评估 runner、JSON 评估证据。

## Global Constraints

- 实施前完整读取根、`skills/`、`tests/`、`evaluations/` 下适用的 `AGENTS.md`，以及已批准 PRD 和 spec；创建 skill 必须使用系统 `skill-creator`。
- 新 skill 必须先完成看不到目标 skill 的新鲜 Agent baseline，并保存可观察 RED；baseline 完成前不得创建 `skills/managing-agents-rules/SKILL.md`。
- 固定 registry 顺序：`baseline-only → implemented → review-approved`。`--evidence-only managing-agents-rules` 只在 `implemented` 阶段运行。
- 新 skill 自包含，不读取、导入或调用兄弟 skill，不依赖 plugin cache、固定本机路径、真实用户状态或 `agent-rules`。
- 不读取、修改、验证或同步 `agent-rules`；不安装到真实 `${CODEX_HOME:-$HOME/.codex}/skills`。
- 不持久化会话降噪状态，不记录真实 task/thread 标识符；所有评估使用虚构路径和脱敏内容。
- 项目级和全局规则分别逐次批准具体 diff；批准后基线变化会使批准失效。全局长期默认目标是 Codex home 的基础 `AGENTS.md`，override 默认只告警。
- 项目级候选修改必须进入最新完整仓库 diff、受影响验证和适用最终评审；无需独立评审的轻量任务不制造评审门。
- 不增加依赖，不升级 plugin 版本，不 commit、push、merge、安装或发布。
- 每个任务只处理其列出的文件；发现公共契约、依赖、权限或范围需要扩大时，停止并重新请求用户批准。

### Task 1: 冻结行为场景并建立无目标 skill RED baseline

**Exact files:**

- Create: `evaluations/managing-agents-rules/rubric.json`
- Create: `evaluations/managing-agents-rules/cases/01-existing-root-silent.md`
- Create: `evaluations/managing-agents-rules/cases/02-missing-project-rules.md`
- Create: `evaluations/managing-agents-rules/cases/03-unreadable-project-rules.md`
- Create: `evaluations/managing-agents-rules/cases/04-non-git-workspace.md`
- Create: `evaluations/managing-agents-rules/cases/05-project-and-task-isolation.md`
- Create: `evaluations/managing-agents-rules/cases/06-project-candidate-review-order.md`
- Create: `evaluations/managing-agents-rules/cases/07-global-base-and-override.md`
- Create: `evaluations/managing-agents-rules/cases/08-no-candidate-silent.md`
- Create: `evaluations/managing-agents-rules/cases/09-approval-invalidation.md`
- Create: `evaluations/managing-agents-rules/cases/10-integration-boundaries.md`
- Create: `evaluations/managing-agents-rules/fixtures/common/README.md`
- Create: `evaluations/managing-agents-rules/fixtures/01-existing-root-silent/AGENTS.md`
- Create: `evaluations/managing-agents-rules/fixtures/03-unreadable-project-rules/AGENTS.md`
- Create: `evaluations/managing-agents-rules/fixtures/05-project-and-task-isolation/project-a/README.md`
- Create: `evaluations/managing-agents-rules/fixtures/05-project-and-task-isolation/project-b/README.md`
- Create: `evaluations/managing-agents-rules/fixtures/06-project-candidate-review-order/AGENTS.md`
- Create: `evaluations/managing-agents-rules/fixtures/08-no-candidate-silent/AGENTS.md`
- Create: `evaluations/managing-agents-rules/fixtures/09-approval-invalidation/AGENTS.md`
- Create: `evaluations/managing-agents-rules/fixtures/10-integration-boundaries/AGENTS.md`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/01-existing-root-silent.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/02-missing-project-rules.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/03-unreadable-project-rules.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/04-non-git-workspace.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/05-project-and-task-isolation.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/06-project-candidate-review-order.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/07-global-base-and-override.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/08-no-candidate-silent.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/09-approval-invalidation.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenarios/10-integration-boundaries.json`
- Create: `evaluations/managing-agents-rules/fixtures/scenario-files/07-global-base-and-override/AGENTS.md`
- Create: `evaluations/managing-agents-rules/fixtures/scenario-files/07-global-base-and-override/AGENTS.override.md`
- Create: `evaluations/managing-agents-rules/baseline/01-output.md` through `10-output.md`
- Create: `evaluations/managing-agents-rules/baseline/pre-creation-audit.json`
- Create: `evaluations/managing-agents-rules/baseline/result.json`
- Modify: `evaluations/registry.json`
- Modify: `scripts/run_skill_evaluations.py`
- Modify: `tests/test_skill_evaluation_runner.py`
- Local only, do not commit: `work/evaluations/managing-agents-rules/baseline/`

**Interfaces:**

- Consumes: approved PRD/spec behavior, `scripts/run_skill_evaluations.py` phases, managed evaluation schema used by existing `creation-only` skills.
- Produces: declarative fixture metadata for Git/non-Git roots, nested project roots, unreadable paths and isolated Codex-home AGENTS files; frozen case IDs `01`–`10`; valid no-target-skill outputs; `red_observed: true`; and registry entry `{evaluation_mode: managed, evidence_profile: creation-only, stage: baseline-only}`.

**Testing approach:** 先对 evaluation runner 新增失败测试，再实现最小声明式 fixture schema。每个新场景使用与 case 文件同 stem 的 `fixtures/scenarios/*.json`，对象必须包含 `schema_version: 1` 和 `repository_mode: "git" | "non-git"`，可选字段为字符串数组 `nested_git_roots`、字符串数组 `unreadable_paths`、以及对象 `codex_home_files`。`codex_home_files` 的 key 只允许 `AGENTS.md` 或 `AGENTS.override.md`，value 是位于相同 case stem 的 `fixtures/scenario-files/` 子目录内的源文件仓库相对路径；不得内嵌真实全局内容。所有相对路径必须保持在各自 allowlisted root 内、指向普通文件或目录且不经过 symlink。metadata 缺失时为兼容现有 evaluations 使用明确 legacy 默认值：Git 根、无 nested root、无 unreadable path、空 Codex-home 映射；metadata 存在但缺少必填字段、畸形、未知字段或越界时抛出 `EvaluationBlocked`。

Runner 准备顺序固定为：复制 common 与 case overlay → 按 `repository_mode` 初始化或跳过 fixture 根 Git → 初始化 `nested_git_roots` → staging 隔离 Codex home/auth → 从 allowlisted source 注入 Codex-home AGENTS 文件 → 最后对 `unreadable_paths` 设置不可读权限 → 启动 Agent。scenario metadata 和 Codex-home source files 不复制进 fixture repository。随后由看不到 `managing-agents-rules` 的 fresh Agents 运行 baseline；每个 case 记录行为失败而非工具失败。

- [ ] RED: Add runner tests for default Git behavior, explicit non-Git mode, nested Git roots, unreadable repository paths, isolated Codex-home base/override files, metadata allowlists and missing/malformed metadata; freeze rubric and case prompts before any target skill production file exists.
- [ ] Verify RED: Run `.venv/bin/python -m unittest discover -s tests -p 'test_skill_evaluation_runner.py' -v`; expect the new fixture-scenario tests to fail because the runner cannot yet prepare those states.
- [ ] GREEN: Extend `run_skill_evaluations.py` with the smallest validated fixture-scenario loader/preparer; preserve existing cases through an explicit default Git scenario when metadata is absent.
- [ ] Verify GREEN: Re-run `.venv/bin/python -m unittest discover -s tests -p 'test_skill_evaluation_runner.py' -v`; expect all runner tests, including existing isolation tests, to pass.
- [ ] Verify RED: Preflight case 03 alone with `.venv/bin/python scripts/run_skill_evaluations.py --skill-name managing-agents-rules --phase migration-baseline --case evaluations/managing-agents-rules/cases/03-unreadable-project-rules.md --output-root work/evaluations/managing-agents-rules/baseline/03-unreadable-project-rules`; require a valid observable behavior run. If Codex runtime rejects the unreadable file before the workflow can run, do not proceed or register baseline-only: redesign the fixture/case and affected rubric criteria, re-freeze them, and repeat preflight until the selected seam is valid.
- [ ] Verify RED: Only after case 03 preflight is valid, run `for case in evaluations/managing-agents-rules/cases/*.md; do case_name=${case##*/}; case_name=${case_name%.md}; .venv/bin/python scripts/run_skill_evaluations.py --skill-name managing-agents-rules --phase migration-baseline --case "$case" --output-root "work/evaluations/managing-agents-rules/baseline/$case_name" || exit 1; done`; expect every rubric case to preserve its own `trace.jsonl`, `stderr.txt`, `final.md` and `result.json`, with `valid: true` and at least one rubric failure caused by missing target behavior.
- [ ] Verify RED: Run `test ! -e skills/managing-agents-rules/SKILL.md`; expect exit `0` before finalizing `pre-creation-audit.json`.
- [ ] GREEN: Sanitize only selected per-case outputs into `evaluations/managing-agents-rules/baseline/`, create structured audit/result JSON, and register the skill at `baseline-only` without creating production skill files.
- [ ] Verify GREEN: Run `.venv/bin/python scripts/validate_repo.py`; expect `repository validation passed` with the registered baseline-only skill absent from `skills/`.
- [ ] REFACTOR: Remove duplicated criteria while retaining independent checks for trigger, authorization, session isolation, review ordering, override handling and forbidden boundaries.
- [ ] Documentation synchronization: None; this task records pre-creation evidence only.
- [ ] Task-level independent review: A read-only reviewer checks chronology, rubric/case agreement, baseline validity, privacy, and confirms no target skill existed when RED was captured; fix evidence issues and re-review.

### Task 2: 添加自动化合同 RED，固定第五个 skill 与仓库集成预期

**Exact files:**

- Create: `skills/managing-agents-rules/tests/test_skill_contract.py`
- Modify: `tests/test_repository_contract.py`

**Interfaces:**

- Consumes: spec 的 skill 名称、触发词、reference 边界、五-skill plugin 当前事实和 registry 真源。
- Produces: 在生产 skill、plugin 和文档尚未更新时可观察失败的合同测试；validator 对 active/review-approved skill 的公开文档覆盖采用动态检查，而不是新的硬编码“五个”列表。

**Testing approach:** 先写断言再写生产内容。skill 测试检查 frontmatter、三个 reference、前置/完成触发、项目/任务状态、Git 独立批准、项目评审顺序、长期基础全局文件、override 告警、逐次批准、批准失效、零提示和禁止边界。仓库测试把所有固定“四 skill”断言改为包含新 skill 的动态或明确五项合同，并要求 staging、manifest、安装文档和最终 reviewer 同步。

- [ ] RED: 新增 `test_skill_contract.py`，引用尚不存在的 `SKILL.md`、references 和 UI metadata。
- [ ] Verify RED: Run `.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v`; expect named failures caused by missing production skill files and contracts.
- [ ] RED: 更新仓库级测试，使当前 validator、四-skill manifest/docs/reviewer 状态无法满足新增合同；本任务不修改生产 validator。
- [ ] Verify RED: Run `.venv/bin/python -m unittest discover -s tests -v`; expect only the newly introduced fifth-skill/document coverage assertions to fail for the intended missing behavior.
- [ ] GREEN: This task does not add production behavior; preserve the observed RED outputs for the implementation handoff.
- [ ] Verify GREEN: Review failure names and traces; reject syntax/import/setup failures as invalid RED.
- [ ] REFACTOR: Consolidate shared expected skill names through the registry/active-skill seam where practical, without weakening explicit trigger-distinction assertions.
- [ ] Documentation synchronization: None; public docs intentionally remain RED until Task 4.
- [ ] Task-level independent review: Reviewer checks assertions are implementation-independent, offline, use temporary/fictitious state, and fail for the approved missing contracts rather than exact prose formatting.

### Task 3: 使用 skill-creator 实现最小自包含 skill 并取得 GREEN 前向证据

**Exact files:**

- Create: `skills/managing-agents-rules/SKILL.md`
- Create: `skills/managing-agents-rules/references/task-lifecycle-and-session-state.md`
- Create: `skills/managing-agents-rules/references/rule-candidates-and-scope.md`
- Create: `skills/managing-agents-rules/references/approval-and-write-safety.md`
- Create: `skills/managing-agents-rules/agents/openai.yaml`
- Create: `evaluations/managing-agents-rules/green/01-output.md` through `10-output.md`
- Create: `evaluations/managing-agents-rules/green/result.json`
- Modify: `evaluations/registry.json`
- Local only, do not commit: `work/skill-creator/managing-agents-rules/`
- Local only, do not commit: `work/evaluations/managing-agents-rules/green/`

**Interfaces:**

- Consumes: Task 1 frozen rubric/cases, Task 2 failing contracts, system `skill-creator`, applicable AGENTS rules.
- Produces: `$managing-agents-rules` trigger contract, three self-contained references, deterministic UI metadata, different fresh Agents 的 GREEN 输出，以及完成真实独立评审后的 registry `stage: review-approved`。

**Testing approach:** 完整读取系统 `skill-creator/SKILL.md` 后，只写使冻结场景和合同通过的最小 skill。`SKILL.md` 保持精炼；会话状态、候选分类、逐次批准分别进入指定 references。不新增脚本、assets 或依赖，除非当前证据证明纯指令合同无法满足 spec，并先取得范围批准。

- [ ] Implement: Ensure `work/skill-creator/managing-agents-rules/` is absent, deleting only a staging directory created by this task if a retry requires it. Run `.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/init_skill.py" managing-agents-rules --path work/skill-creator --resources references --interface 'display_name=Managing AGENTS Rules' --interface 'short_description=Govern project and global AGENTS rules' --interface 'default_prompt=Use $managing-agents-rules to check and update AGENTS rules with explicit approval.'`; expect successful initialization without touching the already existing `skills/managing-agents-rules/tests/` directory.
- [ ] Implement: Use the staged skill-creator output as the scaffold and create only the approved production `SKILL.md` and three references under `skills/managing-agents-rules/` with `apply_patch`; do not copy initializer examples or staging files blindly. After final SKILL wording, run `.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/generate_openai_yaml.py" skills/managing-agents-rules --interface 'display_name=Managing AGENTS Rules' --interface 'short_description=Govern project and global AGENTS rules' --interface 'default_prompt=Use $managing-agents-rules to check and update AGENTS rules with explicit approval.'` so `agents/openai.yaml` is created only by the deterministic generator.
- [ ] Verify: Run `.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v`; expect all new skill contract tests to pass.
- [ ] Verify: Run `.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/managing-agents-rules`; expect valid skill structure and metadata.
- [ ] GREEN: Change registry to `stage: implemented`; run `for case in evaluations/managing-agents-rules/cases/*.md; do case_name=${case##*/}; case_name=${case_name%.md}; .venv/bin/python scripts/run_skill_evaluations.py --skill-name managing-agents-rules --phase green --skill-dir skills/managing-agents-rules --case "$case" --output-root "work/evaluations/managing-agents-rules/green/$case_name" || exit 1; done` using Agents different from baseline and hidden from expected/failure analysis.
- [ ] Verify GREEN: Sanitize selected outputs and create `green/result.json` with all required criteria passed but review still pending; run `.venv/bin/python scripts/validate_repo.py --evidence-only managing-agents-rules`; expect evidence-only validation to pass.
- [ ] REFACTOR: Remove duplicated prose between `SKILL.md` and references without weakening gates; regenerate `agents/openai.yaml` deterministically if SKILL wording changes.
- [ ] Documentation synchronization: Production documentation remains limited to the skill files; public repository docs are Task 4.
- [ ] Task-level independent review: A read-only skill reviewer checks trigger scope, no sibling calls, task/project state, project review ordering, override behavior, write authorization, GREEN validity and self-containment. Resolve every in-scope finding, rerun affected tests/evaluations, and use the same reviewer until `APPROVED`. While registry remains `implemented`, rerun `.venv/bin/python scripts/validate_repo.py --evidence-only managing-agents-rules`; after approval, record generic reviewer/date metadata in `green/result.json`, set `review_status: approved`, change registry to `stage: review-approved`, run `.venv/bin/python scripts/validate_repo.py`, and ask the same reviewer only to confirm the metadata/stage accurately records its verdict. Do not repeat behavioral review when production/evidence content is unchanged.

### Task 4: 集成五-skill plugin、安装合同和公开文档

**Exact files:**

- Modify: `.codex-plugin/plugin.json`
- Modify: `README.md`
- Modify: `docs/install.md`
- Modify: `docs/workflow.md`
- Modify: `docs/agent-development.md`
- Modify: `CHANGELOG.md`
- Modify: `AGENTS.md`
- Modify: `.codex/agents/workflow-final-reviewer.toml`
- Modify: `tests/test_repository_contract.py`
- Modify: `scripts/validate_repo.py`

**Interfaces:**

- Consumes: review-approved `managing-agents-rules`, existing `skills: ./skills/` plugin bundle, dynamic evaluation registry and public documentation contracts.
- Produces: 五-skill plugin capability descriptions、完整/单 skill 安装路径、规则治理独立入口、五-skill validation/reviewer 范围，以及动态验证所有 review-approved active skill 在关键公开文档中可发现。

**Testing approach:** 让 Task 2 的仓库合同 RED 变 GREEN。保留 plugin version `0.1.0`；只更新 description/interface 文案和技能清单。安装 staging 测试必须包含新 skill 的独立 home 和五-skill combined home，并继续验证已有目标拒绝覆盖。

- [ ] Implement: Update manifest descriptions/default prompt to include AGENTS rule governance without changing `skills: ./skills/` or version.
- [ ] Implement: Update README, install/workflow/Agent-development docs, CHANGELOG, root rules and workflow final reviewer from four-skill to five-skill current facts; add `skills/managing-agents-rules` to full and single install guidance and validation commands.
- [ ] Implement: Make repository validator/document coverage derive expected review-approved skills from the registry/active skill set; keep explicit workflow-role assertions where semantic distinctions matter.
- [ ] Verify: Run `.venv/bin/python -m unittest discover -s tests -v`; expect Task 2 fifth-skill, staging, trigger-distinction, documentation and final-reviewer contracts to pass.
- [ ] Verify: Run `.venv/bin/python scripts/validate_repo.py`; expect `repository validation passed` with no local paths, placeholders, orphan evidence or unregistered skill.
- [ ] REFACTOR: Remove obsolete names such as `test_all_four_skills_are_complete_and_exposed` and repeated hardcoded skill lists when registry-driven checks preserve stronger coverage.
- [ ] Documentation synchronization: All listed public and contributor documents are part of this task; do not update unrelated docs or release state.
- [ ] Task-level independent review: A read-only reviewer checks five-skill discovery, install commands, plugin wording, trigger overlap, root rule changes, reviewer role scope and that no `agent-rules` or real installation was touched.

### Task 5: 运行完整双版本验证、临时安装和最终全量评审

**Exact files:**

- Modify only if an in-scope validation/reviewer finding requires it: files created or modified in Tasks 1–4
- Test: `tests/test_repository_contract.py`
- Test: `tests/test_skill_evaluation_runner.py`
- Test: `skills/creating-product-requirements/tests/`
- Test: `skills/creating-development-specs-and-plans/tests/`
- Test: `skills/generating-development-prompts/tests/`
- Test: `skills/implementing-bounded-changes/tests/`
- Test: `skills/managing-agents-rules/tests/`
- Local only, do not commit: temporary Codex homes under `/tmp` or the platform temp directory

**Interfaces:**

- Consumes: latest complete five-skill tree, review-approved evidence, all repository rules and the full diff.
- Produces: Python 3.9/3.14 automated results, five official skill validations, plugin validation, independent/combined staging evidence, final workflow reviewer verdict and honest residual-risk report.

**Testing approach:** 先用现有 `.venv`（Python 3.9）执行完整规定矩阵，再用已存在的 `python3.14` 执行不需要新增依赖的仓库和五个 skill 单元测试/validator。若 Python 3.14 的某项验证确需安装 `requirements-dev.txt`，先请求用户授权在临时 venv 安装；未经授权不得声称 3.14 该项通过。最终 reviewer 必须检查最新完整 diff；任何修复都重跑受影响命令并由同一 reviewer 复审。

- [ ] Verify: Run `.venv/bin/python -m unittest discover -s tests -v`; expect all repository tests pass.
- [ ] Verify: Run `.venv/bin/python scripts/validate_repo.py`; expect `repository validation passed`.
- [ ] Verify: Run `.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v`, `.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v`, `.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v`, `.venv/bin/python -m unittest discover -s skills/implementing-bounded-changes/tests -v`, and `.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v`; expect all pass.
- [ ] Verify: Run `for skill in skills/creating-product-requirements skills/creating-development-specs-and-plans skills/generating-development-prompts skills/implementing-bounded-changes skills/managing-agents-rules; do .venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "$skill" || exit 1; done`; expect every skill valid.
- [ ] Verify: Run `.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .`; expect plugin validation pass.
- [ ] Verify: Run `python3.14 -m unittest discover -s tests -v`, then `for tests_dir in skills/creating-product-requirements/tests skills/creating-development-specs-and-plans/tests skills/generating-development-prompts/tests skills/implementing-bounded-changes/tests skills/managing-agents-rules/tests; do python3.14 -m unittest discover -s "$tests_dir" -v || exit 1; done`, then `python3.14 scripts/validate_repo.py`; expect all dependency-free checks pass or report the exact dependency gate.
- [ ] Verify: Use the repository staging contract in `tests/test_repository_contract.py` to stage every skill independently and all five together into temporary Codex homes; verify byte-for-byte payload equality and refusal to overwrite an existing destination.
- [ ] Verify: Run `git diff --check`, inspect `git status --short --branch`, and inspect the full latest diff including new untracked files; expect no whitespace error, unrelated modification, secret, task/thread identifier, real user data or machine absolute path.
- [ ] Documentation synchronization: Confirm README, install/workflow/Agent-development docs, CHANGELOG, root rules, manifest and workflow reviewer all describe the same five-skill current state and no release claim.
- [ ] Task-level independent review: `workflow-final-reviewer` inspects the approved PRD/spec/plan, complete diff, RED/GREEN evidence, all validation results, trigger coexistence, project-rule review order, global override boundary, staging and public docs. Fix every in-scope finding, rerun affected validation and re-review with the same reviewer until `APPROVED`; stop after approval.

## Final Verification

Implementation is complete only when all five tasks are closed in order and the following evidence agrees:

1. Baseline outputs prove valid RED before `skills/managing-agents-rules/SKILL.md` existed.
2. Automated contract tests show RED before production content and GREEN afterward.
3. The different fresh-Agent GREEN run passes the frozen rubric without seeing expected or baseline analysis.
4. `evaluations/registry.json` finishes at `review-approved`; ordinary repository validation passes and evidence-only is not misused in the final stage.
5. Python 3.9 full tests, five skill tests, five official validators, repository validator and plugin validator pass.
6. Python 3.14 dependency-free test/validator matrix passes, or any dependency installation gate is explicitly authorized and then verified; unavailable checks remain reported, not upgraded.
7. Temporary staging proves all five skills install independently and together without overwriting existing destinations; the real skill home remains unchanged.
8. Project-level rule changes produced by evaluation scenarios appear before applicable final review; global-rule scenarios remain separate and never touch real global files or `agent-rules`.
9. The latest complete diff has no unrelated changes, prohibited identifiers, sensitive values, placeholders or machine paths.
10. The independent skill review and final workflow review both approve their latest respective diffs with no unresolved finding or verification gap.
