# development-workflow

`development-workflow`（简称 `dw`）是一组面向 Codex 的开发工作流 skill。它先按已确认事实选择最短安全路径，再提供自动连续的文档交接、已批准小改动的受控实施和独立 AGENTS rule governance：

```text
development request → fast | standard | full | blocked
standard → PRD → spec+plan technical package → development prompt
full → PRD → approved spec → reviewed plan → development prompt
approved bounded change → implementation
substantive development → AGENTS rule governance
```

仓库同时提供 plugin-compatible 打包、repo marketplace、可复现验证和脱敏后的评估证据。六个 skill 职责独立；路由器只分类和交接，完整文档链通过路径与批准状态协作，受控实施入口直接执行用户已批准的边界，规则治理入口只处理有证据且逐 diff 批准的长期规则，均不依赖本机安装路径或插件缓存。

## Skills

| Skill | 职责 |
|---|---|
| `routing-development-workflows` | 在没有显式 workflow 入口时，依据批准、范围、风险和验证事实选择 `fast | standard | full | blocked`，只输出稳定交接，不创建文档或实施 |
| `creating-product-requirements` | 澄清产品范围、用户场景和验收标准；已有批准基线时默认生成不复刻完整基线的单主题增量 PRD，否则生成完整 PRD；门禁打开后自动进入 spec workflow |
| `creating-development-specs-and-plans` | 校验已批准 PRD；`standard` 把 spec+plan 合并为一次技术包评审，`full` 保留逐级批准；十四字段验证通过后自动进入会话路由 |
| `generating-development-prompts` | 从已批准十四字段或显式请求判断当前会话、新会话或阻塞；仅在需要新会话时生成单一代码框中的可复制提示词 |
| `implementing-bounded-changes` | 在用户明确批准后，以冻结范围、比例化 TDD、定向验证和文档同步完成小改动或 Bug 修复；纯机械改动可按严格条件免独立评审 |
| `managing-agents-rules` | 在实质性开发前检查项目根规则，并在任务完成时对有证据的项目级或全局 AGENTS 规则候选执行逐 diff 批准治理 |

## 快速安装

通过 repo marketplace 安装完整 plugin bundle：

```bash
codex plugin marketplace add itstarts/development-workflow --ref v0.1.2
codex plugin add development-workflow@development-workflow
```

当前稳定版本为 `v0.1.2`。catalog 与 plugin entry 均固定到该不可变 tag，避免安装内容随 `main` 变化。

也可以通过 `skill-installer` 一次安装全部 skill：

```bash
python3 \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo itstarts/development-workflow \
  --ref v0.1.2 \
  --path \
    skills/routing-development-workflows \
    skills/creating-product-requirements \
    skills/creating-development-specs-and-plans \
    skills/generating-development-prompts \
    skills/implementing-bounded-changes \
    skills/managing-agents-rules
```

还可以只安装一个 skill。安装器在目标目录已存在时会停止，不会静默覆盖。完整步骤、两种安装方式和安全更新边界见 [安装指南](docs/install.md)。

## 工作流

1. `routing-development-workflows` 在没有显式入口时选择一条路径：只有范围稳定、用户已批准实施、无高风险边界且定向验证充分时进入 `fast`；普通需求进入 `standard`；公共契约、架构、数据、权限、迁移、并发、一致性或外部状态等边界进入 `full`；确定性能力或授权缺口进入 `blocked`。
2. `creating-product-requirements` 在理解置信度达到 95% 且用户确认摘要后创建 PRD。存在可靠批准基线时默认另建增量 PRD，只写确认摘要中的变化和必要影响，不覆盖或复刻完整基线；没有相关基线时创建完整 PRD。route 与风险事实仍保存到 `工作流分流`，不改变 canonical 八字段。PRD 经独立评审和用户批准后，在同一会话自动进入 spec workflow。
3. `creating-development-specs-and-plans` 复验 PRD。`standard` 在 spec 用户批准前先生成 spec+plan 草案，由一位 reviewer 统一评审；评审通过但 spec 未获用户批准时，计划评审真实保持已通过，实施门仍关闭。`full` 保留 spec 评审→用户批准→plan 评审的逐级顺序。
4. `generating-development-prompts` 基于已验证十四字段和当前会话证据输出 `current-session`、`new-session` 或 `blocked`；它分别保留计划评审状态与实施门，不会把“技术包已评审、spec 待用户批准”误判为可实施。

普通非阻塞澄清只显示固定三行“当前阶段 / 主题 / 下一步”；暂停、阻塞、摘要确认、批准、文档阶段完成与跨 skill 交接继续显示完整中文八字段或十四字段。内部英文 canonical 字段、门禁计算与旧英文输入兼容性保持不变。完整契约见[工作流与文档契约](docs/workflow.md)。

对于不需要 PRD、spec 和 plan 的已确认小改动，`implementing-bounded-changes` 在用户明确批准推进后冻结改动点、方案、非目标、验证和文档边界，再执行最小 TDD、定向验证和相关文档更新。同一相关状态下已通过的检查不会因评审或 Agent 交接而重复运行；变化只使受影响结果失效，仓库要求的最终门在最后一次相关变化后运行一次，并在覆盖同一 focused seam 时直接充当 GREEN。任务中形成的项目验证映射只作为可选规则候选展示，必须由用户逐 diff 选择是否加入项目 `AGENTS.md`。只有纯文档、格式或确定性机械改动，且不改变行为、配置语义、公共契约、产品含义或操作流程时，才可免独立评审；其它变更仍使用一位 reviewer。连续两轮修复与复审仍未通过时停止自动循环并保持阻塞，用户偏好不能替代正确性证据。

`managing-agents-rules` 独立应用于实质性开发的前置检查和完成扫描。它不会调用其它 skill，也不会自动写规则；每个项目级或全局候选都必须有当前任务证据、明确目标和当前最小 diff，并取得只对该 diff 有效的批准。

默认文档路径、批准门和交接字段见 [工作流与文档契约](docs/workflow.md)。

## 开发

修改前完整读取 [AGENTS.md](AGENTS.md) 和作用域更深的规则。Agent 角色、TDD 证据、独立评审和发布边界见 [Agent 开发指南](docs/agent-development.md)。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt

.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s skills/routing-development-workflows/tests -v
.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python -m unittest discover -s skills/implementing-bounded-changes/tests -v
.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v

# 当前 evaluation stage 对应的定向检查；全部 review-approved 后可使用 --full
.venv/bin/python scripts/check.py --skill creating-product-requirements
```

完整验证命令见 [Agent 开发指南](docs/agent-development.md#发布前验证)。支持 Python 3.9 及以上；日常和发布验证使用项目当前 `.venv`，不要求重复运行第二个 Python 版本。

## 文档

| 文档 | 内容 |
|---|---|
| [安装指南](docs/install.md) | 安装、单 skill 安装和安全更新 |
| [工作流与文档契约](docs/workflow.md) | 完整交接链、受控实施入口、默认路径和批准门 |
| [Agent 开发指南](docs/agent-development.md) | 仓库规则、TDD、评估、评审和发布流程 |
| [Release notes 规范](docs/release-notes.md) | GitHub Release 的结构、内容边界和版本链接规则 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献范围和提交前检查 |
| [SECURITY.md](SECURITY.md) | 安全问题报告和敏感信息边界 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变化 |

## License

[MIT](LICENSE) © itstarts
