# development-workflow

`development-workflow`（简称 `dw`）是一组面向 Codex 的开发工作流 skill，提供完整文档交接和已批准小改动的受控实施两条入口：

```text
PRD → technical spec/plan → development prompt
approved bounded change → implementation
```

仓库同时提供 plugin-compatible 打包、可复现验证和脱敏后的评估证据。四个 skill 职责独立；完整交接链通过文档路径和批准状态协作，受控实施入口直接执行用户已批准的边界，不依赖本机安装路径或插件缓存。

## Skills

| Skill | 职责 |
|---|---|
| `creating-product-requirements` | 澄清产品范围、用户场景和验收标准，生成经独立评审和用户批准的单主题 PRD |
| `creating-development-specs-and-plans` | 校验已批准 PRD，生成经批准的技术 spec 和经独立评审的实施计划 |
| `generating-development-prompts` | 从已有 spec、plan 和仓库证据生成可复制的新会话开发提示词 |
| `implementing-bounded-changes` | 在用户明确批准后，以冻结范围、比例化 TDD、定向验证、文档同步和独立评审完成小改动或 Bug 修复 |

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
    skills/implementing-bounded-changes
```

也可以只安装一个 skill。安装器在目标目录已存在时会停止，不会静默覆盖。完整步骤和安全更新方式见 [安装指南](docs/install.md)。

## 工作流

1. `creating-product-requirements` 在理解置信度达到 95% 且用户确认摘要后创建 PRD；PRD 经过独立评审和用户批准才成为稳定输入。
2. `creating-development-specs-and-plans` 校验 PRD，先生成并批准技术 spec，再生成经独立评审的 plan。
3. `generating-development-prompts` 读取已选择的 spec、plan 和仓库事实，生成自包含的开发提示词；plan 未批准或状态未知时，提示词会保留实施阻断门。

对于不需要 PRD、spec 和 plan 的已确认小改动，`implementing-bounded-changes` 在用户明确批准推进后冻结改动点、方案、非目标、验证和文档边界，再执行最小 TDD、定向验证、相关文档更新和独立评审；发现范围或设计必须扩大时停止并重新请求批准。

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
