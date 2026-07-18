# development-workflow

`development-workflow`（简称 `dw`）是一组面向 Codex 的开发工作流 skill，提供自动连续的文档交接、已批准小改动的受控实施和独立 AGENTS rule governance 三条入口：

```text
PRD → technical spec/plan → development prompt
approved bounded change → implementation
substantive development → AGENTS rule governance
```

仓库同时提供 plugin-compatible 打包、可复现验证和脱敏后的评估证据。五个 skill 职责独立；完整交接链通过文档路径和批准状态协作，受控实施入口直接执行用户已批准的边界，规则治理入口只处理有证据且逐 diff 批准的长期规则，均不依赖本机安装路径或插件缓存。

## Skills

| Skill | 职责 |
|---|---|
| `creating-product-requirements` | 澄清产品范围、用户场景和验收标准，生成经独立评审和用户批准的单主题 PRD；门禁打开后自动进入 spec workflow |
| `creating-development-specs-and-plans` | 校验已批准 PRD，生成经批准的技术 spec 和经独立评审的实施计划；十四字段验证通过后自动进入会话路由 |
| `generating-development-prompts` | 从已批准十四字段或显式请求判断当前会话、新会话或阻塞；仅在需要新会话时生成单一代码框中的可复制提示词 |
| `implementing-bounded-changes` | 在用户明确批准后，以冻结范围、比例化 TDD、定向验证、文档同步和独立评审完成小改动或 Bug 修复 |
| `managing-agents-rules` | 在实质性开发前检查项目根规则，并在任务完成时对有证据的项目级或全局 AGENTS 规则候选执行逐 diff 批准治理 |

## 快速安装

一次安装全部 skill：

```bash
python3 \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo itstarts/development-workflow \
  --ref main \
  --path \
    skills/creating-product-requirements \
    skills/creating-development-specs-and-plans \
    skills/generating-development-prompts \
    skills/implementing-bounded-changes \
    skills/managing-agents-rules
```

也可以只安装一个 skill。安装器在目标目录已存在时会停止，不会静默覆盖。完整步骤和安全更新方式见 [安装指南](docs/install.md)。

## 工作流

1. `creating-product-requirements` 在理解置信度达到 95% 且用户确认摘要后创建 PRD；互不依赖的产品问题一轮最多询问三个，依赖问题仍逐问。PRD 经独立评审和用户批准后，验证 requirements 八字段并在同一会话自动进入 spec workflow。
2. `creating-development-specs-and-plans` 复验 PRD，以相同的依赖感知规则澄清技术选择，先生成并批准 technical spec，再生成经独立评审的 plan；双门打开后验证并冻结十四字段，自动进入会话路由。
3. `generating-development-prompts` 基于已验证十四字段和当前会话证据输出 `current-session`、`new-session` 或 `blocked`；`current-session` 只建议继续并等待用户显式实施批准，不自动开始实施，只有 `new-session` 才生成单一代码框中的自包含提示词。目标会话只在首次实际委派时建立 Agent inventory，后续复用并仅在配置或能力证据变化时刷新。显式手动请求仍可在 plan 未批准或状态未知时生成带实施阻断门的提示词。

普通非阻塞澄清只显示固定三行“当前阶段 / 主题 / 下一步”；暂停、阻塞、摘要确认、批准、文档阶段完成与跨 skill 交接继续显示完整中文八字段或十四字段。内部英文 canonical 字段、门禁计算与旧英文输入兼容性保持不变。完整契约见[工作流与文档契约](docs/workflow.md)。

对于不需要 PRD、spec 和 plan 的已确认小改动，`implementing-bounded-changes` 在用户明确批准推进后冻结改动点、方案、非目标、验证和文档边界，再执行最小 TDD、定向验证、相关文档更新和独立评审；发现范围或设计必须扩大时停止并重新请求批准。

`managing-agents-rules` 独立应用于实质性开发的前置检查和完成扫描。它不会调用其它 skill，也不会自动写规则；每个项目级或全局候选都必须有当前任务证据、明确目标和当前最小 diff，并取得只对该 diff 有效的批准。

默认文档路径、批准门和交接字段见 [工作流与文档契约](docs/workflow.md)。

## 开发

修改前完整读取 [AGENTS.md](AGENTS.md) 和作用域更深的规则。Agent 角色、TDD 证据、独立评审和发布边界见 [Agent 开发指南](docs/agent-development.md)。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt

.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python -m unittest discover -s skills/implementing-bounded-changes/tests -v
.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v

# 当前 evaluation stage 对应的定向检查；全部 review-approved 后可使用 --full
.venv/bin/python scripts/check.py --skill creating-product-requirements
```

完整验证命令见 [Agent 开发指南](docs/agent-development.md#发布前验证)。支持 Python 3.9 及以上；维护矩阵至少覆盖 Python 3.9 和 Python 3.14。

## 文档

| 文档 | 内容 |
|---|---|
| [安装指南](docs/install.md) | 安装、单 skill 安装和安全更新 |
| [工作流与文档契约](docs/workflow.md) | 完整交接链、受控实施入口、默认路径和批准门 |
| [Agent 开发指南](docs/agent-development.md) | 仓库规则、TDD、评估、评审和发布流程 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献范围和提交前检查 |
| [SECURITY.md](SECURITY.md) | 安全问题报告和敏感信息边界 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变化 |

## License

[MIT](LICENSE) © itstarts
