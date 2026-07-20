# AGENTS.md — development-workflow

## 适用范围

本文件适用于整个仓库。子目录存在更具体的 `AGENTS.md` 时，按更深层规则执行；用户当前明确指令始终优先。

## 仓库目标

本仓库维护 Codex 开发交接工作流，简称 `dw`：

- `routing-development-workflows`：在没有显式入口时，依据批准、范围、风险和验证事实选择 `fast | standard | full | blocked`，只负责分类和交接。
- `creating-product-requirements`：把产品意图澄清为单一稳定主题、经独立评审和用户批准的 PRD。
- `creating-development-specs-and-plans`：只从已批准 PRD 生成技术 spec 与 plan；`standard` 使用统一技术包评审，`full` 保留逐级批准。
- `generating-development-prompts`：读取已有 spec、plan 和仓库证据，生成可复制到新 Codex 会话的开发提示词。
- `implementing-bounded-changes`：在用户明确批准后，以冻结范围、比例化 TDD、定向验证、相关文档更新和风险匹配的评审直接完成小改动或 Bug 修复。
- `managing-agents-rules`：在实质性开发前检查项目根规则，并在任务完成时对有证据的项目级或全局长期规则候选执行逐 diff 批准治理。
- `.codex-plugin/plugin.json`：把可用 skill 作为一个 plugin bundle 发布。

六个 skill 必须保持职责独立。总路由 skill 只分类和交接，不创建下游制品或实施；三个文档交接 skill 通过文档路径、评审状态和显式输出字段协作；受控实施 skill 直接依据用户批准、当前范围和仓库证据执行；规则治理 skill 只管理有证据且逐 diff 批准的长期规则。任何 skill 都不通过本机安装路径或插件缓存路径互相调用。

## 当前状态

- `routing-development-workflows` 已实现并完成无目标 baseline、GREEN 前向验证和仓库验证；维护时继续保留单一路由、未知风险失败关闭、稳定 handoff 和只路由不执行的合同。
- `generating-development-prompts` 已有经过验证的实现，可以维护。
- `creating-product-requirements` 和 `creating-development-specs-and-plans` 均已实现并完成独立评审；维护时仍须保留 RED 证据、GREEN 前向结果、仓库验证和独立评审门。
- `implementing-bounded-changes` 已实现并完成无目标 baseline、GREEN 前向验证、仓库验证和独立评审；维护时继续保留范围控制、比例化 TDD、最终评审通过且不过度评审的合同。
- `managing-agents-rules` 已实现并完成无目标 baseline、GREEN 前向验证、仓库验证和独立评审；维护时继续保留会话内状态、零候选静默、逐 diff 批准、批准失效和写后验证合同。

## 开发流程

1. 修改前完整读取本文件、`skills/AGENTS.md`、相关 skill 及其测试。
2. 创建或修改 skill 时必须使用 `skill-creator`，并遵循仓库规定的写作、TDD、诊断和完成前验证流程。
3. 新 skill 严格执行 RED→GREEN→REFACTOR：先冻结场景并用无 skill 的全新代理运行基线，记录可观察失败，再写最小 skill。
4. 现有 skill 修改先补失败契约或前向场景，确认按预期失败后再改生产内容。
5. 跨 skill 公共契约变更可作为一个集成范围实施；每个受影响 skill 必须分别通过定向验证，不得批量编写多个未经验证的 skill。评审按下文的风险边界和最新完整 diff 执行。
6. 遇到异常或测试失败，先复现并定位根因，再做最小修复。
7. 完成声明前运行新鲜验证，不复用旧结果替代当前证据。

## 规则与安全

- skill 必须自包含；不得依赖 `~/.codex/plugins/cache/`、其他用户目录或固定版本的外部方法文件。
- 禁止把本机绝对路径、密钥、令牌、凭证、生产数据或用户 task/thread 标识符写入版本库。
- 不修改 `~/.codex/skills` 中的已安装副本来进行开发；只修改本仓库，验证通过后再执行显式安装流程。
- 未经用户明确要求，不得创建或操作用户可见 Codex task/thread，不得 push、merge、rebase、tag、release 或创建远程仓库。
- 不覆盖既有安装目录；更新前先安装到 staging 或临时 `CODEX_HOME`，验证并比较差异。
- 不手工复制外部 skill 正文。可复用通用原则，但本仓库的行为与测试必须独立可维护。

## Agent 配置与公开文档

- `.codex/agents/` 只保存本仓库开发使用的只读评审角色。角色必须职责单一，不固定模型或 reasoning effort，不声称拥有运行时未暴露的权限，也不得包含本机路径、凭证或用户 task/thread 标识符。
- 新增或修改角色时，必须同步检查触发范围、输入证据、批准条件、只读边界和外部状态限制，并更新 `docs/agent-development.md` 中的角色说明。
- `README.md` 保持面向使用者的简明入口；安装细节、工作流契约和 Agent 开发流程分别维护在 `docs/install.md`、`docs/workflow.md` 和 `docs/agent-development.md`，避免把内部执行规则堆入 README。
- 公开安装命令、仓库地址、许可证、版本状态或发布边界变化时，同步更新 README、相关 `docs/`、`CHANGELOG.md` 和 plugin manifest 中受影响的当前事实。
- 发布前同时扫描当前树和完整 Git 历史中的本机路径、凭证、真实用户数据与 task/thread 标识符；只删除当前文件不能证明历史可公开。

## 文档交接契约

- 默认 PRD 路径：`docs/requirements/YYYY-MM-DD-<topic>.md`。
- 默认 spec 路径：`docs/specs/YYYY-MM-DD-<topic>-design.md`。
- 默认 plan 路径：`docs/plans/YYYY-MM-DD-<topic>.md`。
- 用户显式路径优先于默认路径。
- 一份 PRD 只对应一个稳定主题，范围类型只能是 `product | phase | feature`；理解置信度至少 95 且用户确认当前摘要后才能创建 PRD。
- 总路由提供的 `standard | full` 与风险事实保存在 PRD 正文并作为独立 route handoff 传递，不增加 requirements 八字段；route 缺失、冲突或不可靠时按 `full` 处理。
- PRD 必须经过独立评审和用户明确批准，才能作为技术 spec 的稳定输入。
- `standard` route 可在 spec 用户批准前创建 spec 与 plan 草案，并由同一位 package reviewer 给出覆盖两份当前文档的 verdict；package 已通过但 spec 尚未获用户批准时，实施门必须保持关闭。
- `full`、route 缺失或 route 不可靠时，spec 必须经过独立评审和用户明确批准后才能创建 plan，plan 再独立评审。
- plan 只有真实评审通过后才能记录 `review_status: approved`；不得预填或推断批准状态。
- PRD skill 固定报告 requirements 八字段；specs/plans skill 必须校验并保留这些字段，再以十四字段报告 requirements、spec、plan 与双门状态；prompt skill 保留显式 spec/plan 路径与评审状态。
- bounded implementation skill 不依赖上述文档链；必须保留用户推进批准、冻结范围、定向验证和相关文档更新。只有不改变行为、配置语义、公共契约、产品含义或操作流程，且确定性检查充分、仓库规则不强制评审的纯文档、格式或机械改动，才可记录具体理由并免独立评审。

## Git

- 默认分支为 `main`；开发应使用范围清晰的分支，不直接在 `main` 上维护已发布行为。
- 未经用户明确要求不 commit。用户要求 commit 时，使用 `<type>: 中文描述`。
- 不提交评估临时目录、虚拟环境、缓存、构建产物或本地安装副本。

## 验证

受影响 skill 在独立评审写回前，按当前 registry stage 运行一次统一定向门；同一任务涉及多个 skill 时，在同一命令中重复 `--skill`：

```bash
.venv/bin/python scripts/check.py --skill <skill-name> [--skill <skill-name> ...]
```

独立评审批准并写回全部受影响 skill，且全部已公开 skill 均为 `review-approved` 后，直接运行一次统一完整门：

```bash
.venv/bin/python scripts/check.py --full
```

定向 `check.py --skill` 执行目标 skill 测试、stage-aware freshness 和官方 skill validator，不重复运行无关根测试；共享脚本或仓库工具变化时按实际 diff 单独运行其直接根测试。`--full` 执行完整仓库测试、全部 skill 测试、严格 freshness、全部官方 skill validator 和 plugin validator。开发环境先运行 `python3 -m venv .venv` 和 `.venv/bin/python -m pip install -r requirements-dev.txt`。仓库支持 Python 3.9 及以上；验证使用项目当前 `.venv`，不要求重复运行第二个 Python 版本。没有新 diff 或验证失败时，不在完整门前重复定向门。新增 skill 后，把它加入仓库 validator、官方 skill validator、安装测试和 plugin 验证。

## 评审

任务拆分用于实施和定向验证，不自动形成独立评审门。独立评审默认以风险边界和最新完整 diff 为单位，不得仅因任务数量或受影响 skill 数量增加而逐任务、逐 skill 评审；仅当单项任务独立触及高风险边界，或后续工作依赖尚未验证的关键基础时，才设置中间里程碑评审。

中等及以上变更必须由未参与实现的独立评审者检查 diff、skill 触发条件、TDD 证据、前向结果、plugin 打包、安装边界与文档契约。最终评审必须覆盖受影响 skill、相关跨 skill 回归，以及完整六-skill plugin 的打包与安装边界证据；未受影响 skill 只需按风险和集成关系提供必要回归，不重复逐 skill 评审。评审发现的改动必须重新验证并由同一评审者复审；连续两轮修复与复审仍未通过时停止自动循环并保持阻塞，用户方向可以解决范围选择，但不能替代缺失的正确性或评审证据。
