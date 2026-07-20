# Agent 开发指南

本文件解释贡献者和开发 Agent 如何在本仓库内安全修改 skill、评估与项目级 reviewer。具有约束力的执行规则仍以根目录和子目录中的 `AGENTS.md` 为准。

## 规则层级

1. 当前用户明确指令。
2. 当前文件适用范围内最深层的 `AGENTS.md`，例如 `skills/AGENTS.md`、`tests/AGENTS.md` 或 `evaluations/AGENTS.md`。
3. 从当前目录逐级向上的其它 `AGENTS.md`；离当前文件越近，优先级越高。
4. 平台默认行为。所有仓库规则仍受系统和平台安全、权限约束限制。

修改前必须检查适用规则、相关实现与测试、`git status` 和当前 diff；不得覆盖或混入用户已有变更。

## 目录职责

| 路径 | 职责 |
|---|---|
| `skills/` | 可独立安装的六个 skill 及其运行时资源 |
| `tests/` | 仓库级契约和跨 skill 集成测试 |
| `evaluations/` | 可版本化、已脱敏的 RED/GREEN 场景与结果 |
| `.codex/agents/` | 仓库内只读评审角色 |
| `.codex-plugin/plugin.json` | 六个 skill 的 plugin bundle 元数据 |
| `.agents/plugins/marketplace.json` | 通过 Git source 暴露根级 plugin 的 repo marketplace catalog |
| `work/` | 本地原始评估、trace 和临时材料；禁止提交 |

## Skill 修改流程

创建或修改 skill 时必须使用系统 `skill-creator`，并遵循 RED→GREEN→REFACTOR：

1. 新 skill 先冻结场景，由看不到目标 skill 的全新 Agent 运行 baseline，记录可观察失败。
2. 修改现有 skill 时先新增失败合同或前向场景，确认 RED 原因来自目标行为。
3. 编写最小实现并运行定向单元测试、仓库 validator 和 GREEN 场景。
4. 使用与 baseline 不同、看不到 expected 或失败解释的全新 Agent 运行 GREEN。
5. 由未参与实现的只读 reviewer 检查最新 diff、证据、打包和交接契约。
6. 评审引发修改后重新验证并复审，直到没有阻塞 finding。

每个 skill 必须自包含，不能依赖 `~/.codex/plugins/cache/`、其他用户目录、固定外部版本或兄弟 skill 的源码。

GREEN 结果必须用 `fresh_cases` 列出 production 变化后真实重跑且纳入本次评审的 case，并包含 current RED 的 selected case。严格 freshness 不绑定固定内容哈希：干净 Git 树按 commit 祖先关系验证证据顺序；工作区可以复用已满足祖先关系的干净前序，但从第一个变化阶段起必须形成连续 dirty 后序，current RED 两份证据和全部 fresh outputs 各自保持完整。全新 creation-only skill 只有 registry、全部 production、baseline 和 GREEN 同属完整未提交 bundle 时才可得到 `worktree-creation-current`；既有 skill production 变化仍需 current RED。任何中间缺口、部分刷新或过期干净前序都失败；非 Git 副本标记为未验证。

## Reviewer 角色

`.codex/agents/` 中的三个角色仍稳定可用。它们在 diff、验证和完成门上有部分职责重叠，但项目专属证据范围、评审时点和批准条件不同；这些差异仍有必要，因此配置全部保留：

| 角色 | 稳定可用性 | 职责 | 输入 | 输出 | 边界 | 批准条件 | 结论 |
|---|---|---|---|---|---|---|---|
| `skill-reviewer` | 项目配置稳定可加载 | 单个 skill 的行为、TDD 证据、打包与跨 skill 契约；与最终角色共享 diff/验证检查，但范围止于一个 skill | 该 skill 的适用规则、需求、最新 diff、RED/GREEN、安装边界和验证结果 | findings、验证缺口、残留风险或 `APPROVED` | 只读；不提交、不安装、不改变任何外部状态 | 当前 skill 的项目专属证据范围完整且没有阻断问题 | 保留 |
| `final-reviewer` | 项目配置稳定可加载 | 一个已批准实施范围的整体完成门；与 workflow 最终角色共享完成门检查，但不负责完整六-skill 发布证据 | 规格、计划、批准范围、最新完整 diff、风险里程碑评审（若有）和验证证据 | findings、开放问题、验证缺口、残留风险或 `APPROVED` | 只读；不实施、不提交、不执行安装、不改变任何外部状态 | 已批准范围一致、验证完整且该实施的完成门全部满足 | 保留 |
| `workflow-final-reviewer` | 项目配置稳定可加载 | 完整六-skill plugin、总路由、文档交接、规则治理入口和发布证据；覆盖面大于通用最终评审 | 全部 skill 项目专属证据、风险里程碑评审（若有）、集成评审、manifest、隔离安装和发布边界 | findings、开放问题、验证缺口、残留风险或 `APPROVED` | 只读；不安装、不 push、不发布、不改变任何外部状态 | 六-skill 合同、集成、安装与发布边界证据完整且没有阻断问题 | 保留 |

角色必须保持只读、职责单一，不固定模型或 reasoning effort，不声称拥有运行时未暴露的权限。新增或修改角色时需同步说明其触发范围、输入证据、批准条件和外部状态边界。

## 本地与公开边界

以下内容不得提交：

- `.env`、密钥、token、凭证和真实生产数据；
- 真实 task/thread 标识符、未脱敏用户内容和原始 trace；
- 本机绝对路径、主机名、个人工具配置和插件缓存副本；
- 虚拟环境、测试缓存、构建产物、日志和编辑器状态。

可版本化评估必须使用虚构路径或仓库相对路径，并通过 `scripts/validate_repo.py` 的敏感信息检查。项目级 `.codex/agents/` 是有意发布的 reviewer 源码，不应被整体加入 `.gitignore`。

## 发布前验证

日常优先使用 stage-aware 统一入口：

```bash
.venv/bin/python scripts/check.py --skill <skill-name> [--skill <skill-name> ...]
.venv/bin/python scripts/check.py --full
```

任务开始时，如果全部 exposed skill 仍为 `review-approved`，先运行一次完整门以提前识别既有证据问题。最终评审前，把全部受影响 skill 放在同一条定向命令中；定向模式只运行目标 skill tests、每个目标的 stage-aware repository validator 和官方 skill validator，不重复运行与目标无关的根 `tests/`。共享脚本或仓库工具发生变化时，开发者另行运行其直接根测试；`--full` 在最终批准后统一运行完整根测试一次。由一位未参与实现的 reviewer 检查最新完整 diff；批准状态写回后直接运行一次统一完整门，没有新 diff 或失败时不重复定向门。

各 subprocess 独立超时且最终按固定顺序汇总，不跳过官方 validator。下面的展开命令仍是权威组成项和故障定位入口。

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s skills/routing-development-workflows/tests -v
.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python -m unittest discover -s skills/implementing-bounded-changes/tests -v
.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/routing-development-workflows
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/creating-product-requirements
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/creating-development-specs-and-plans
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/generating-development-prompts
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/implementing-bounded-changes
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/managing-agents-rules
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
git diff --check
```

仓库 validator 同时校验 repo marketplace 的名称、Git source、安装策略、分类以及 plugin 名称与 manifest 的一致性。

仓库支持 Python 3.9 及以上；验证使用项目当前 `.venv`，不重复运行第二个 Python 版本。发布前还要检查 Git 历史中的作者元数据、已删除内容和历史 blob，确保没有本机路径或敏感信息；仅扫描当前工作树不足以证明公开安全。

GitHub Release notes 必须遵循 [Release notes 规范](release-notes.md)。发布候选需同步 manifest 版本、Marketplace `source.ref`、README 与安装指南中的 tag、CHANGELOG 日期和 Release 标题；完成最新完整 diff 的独立评审、统一完整门和历史扫描后创建 tag，再从远端 tag 安装到临时 `CODEX_HOME` 并比较 payload，最后发布 GitHub Release。
