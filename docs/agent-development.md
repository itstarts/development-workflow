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
| `skills/` | 可独立安装的五个 skill 及其运行时资源 |
| `tests/` | 仓库级契约和跨 skill 集成测试 |
| `evaluations/` | 可版本化、已脱敏的 RED/GREEN 场景与结果 |
| `.codex/agents/` | 仓库内只读评审角色 |
| `.codex-plugin/plugin.json` | 五个 skill 的 plugin bundle 元数据 |
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

## Reviewer 角色

`.codex/agents/` 中的角色只服务本仓库开发：

- `skill-reviewer.toml`：检查单个 skill 的行为、TDD 证据、打包与跨 skill 契约。
- `final-reviewer.toml`：检查一个已批准实施范围的整体完成门。
- `workflow-final-reviewer.toml`：检查完整五-skill plugin、文档交接、受控实施、`managing-agents-rules` 规则治理入口和发布证据。

角色必须保持只读、职责单一，不固定模型或 reasoning effort，不声称拥有运行时未暴露的权限。新增或修改角色时需同步说明其触发范围、输入证据、批准条件和外部状态边界。

## 本地与公开边界

以下内容不得提交：

- `.env`、密钥、token、凭证和真实生产数据；
- 真实 task/thread 标识符、未脱敏用户内容和原始 trace；
- 本机绝对路径、主机名、个人工具配置和插件缓存副本；
- 虚拟环境、测试缓存、构建产物、日志和编辑器状态。

可版本化评估必须使用虚构路径或仓库相对路径，并通过 `scripts/validate_repo.py` 的敏感信息检查。项目级 `.codex/agents/` 是有意发布的 reviewer 源码，不应被整体加入 `.gitignore`。

## 发布前验证

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s skills/creating-product-requirements/tests -v
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python -m unittest discover -s skills/implementing-bounded-changes/tests -v
.venv/bin/python -m unittest discover -s skills/managing-agents-rules/tests -v
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

维护矩阵至少覆盖 Python 3.9 和 Python 3.14。发布前还要检查 Git 历史中的作者元数据、已删除内容和历史 blob，确保没有本机路径或敏感信息；仅扫描当前工作树不足以证明公开安全。
