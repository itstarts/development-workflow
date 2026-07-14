# AGENTS.md — development-workflow

## 适用范围

本文件适用于整个仓库。子目录存在更具体的 `AGENTS.md` 时，按更深层规则执行；用户当前明确指令始终优先。

## 仓库目标

本仓库维护 Codex 开发交接工作流，简称 `dw`：

- `creating-development-specs-and-plans`：把需求澄清为经批准的 spec，再生成可执行 plan。
- `generating-development-prompts`：读取已有 spec、plan 和仓库证据，生成可复制到新 Codex 会话的开发提示词。
- `.codex-plugin/plugin.json`：把可用 skill 作为一个 plugin bundle 发布。

两个 skill 必须保持职责独立，通过文档路径、评审状态和显式输出字段协作，不通过本机安装路径或插件缓存路径互相调用。

## 当前状态

- `generating-development-prompts` 已有经过验证的实现，可以维护。
- `creating-development-specs-and-plans` 尚未实现。出现经过记录的无 skill 失败基线之前，不得在 `skills/` 下创建其目录或 `SKILL.md`，也不得宣称该 skill 可用。

## 开发流程

1. 修改前完整读取本文件、`skills/AGENTS.md`、相关 skill 及其测试。
2. 创建或修改 skill 时必须使用 `skill-creator` 与 `superpowers:writing-skills`；实现行为变更还必须使用 `superpowers:test-driven-development`。
3. 新 skill 严格执行 RED→GREEN→REFACTOR：先冻结场景并用无 skill 的全新代理运行基线，记录可观察失败，再写最小 skill。
4. 现有 skill 修改先补失败契约或前向场景，确认按预期失败后再改生产内容。
5. 每个 skill 独立完成验证和评审后，才修改另一个 skill；不得批量编写多个未经验证的 skill。
6. 遇到异常或测试失败，使用 `superpowers:systematic-debugging` 定位根因。
7. 完成声明前使用 `superpowers:verification-before-completion` 运行新鲜验证。

## 规则与安全

- skill 必须自包含；不得依赖 `~/.codex/plugins/cache/`、其他用户目录或固定版本的 Superpowers 文件。
- 禁止把本机绝对路径、密钥、令牌、凭证、生产数据或用户 task/thread 标识符写入版本库。
- 不修改 `~/.codex/skills` 中的已安装副本来进行开发；只修改本仓库，验证通过后再执行显式安装流程。
- 未经用户明确要求，不得创建或操作用户可见 Codex task/thread，不得 push、merge、rebase、tag、release 或创建远程仓库。
- 不覆盖既有安装目录；更新前先安装到 staging 或临时 `CODEX_HOME`，验证并比较差异。
- 不手工复制 Superpowers 的 skill 正文。可复用其原则，但本仓库的行为与测试必须独立可维护。

## 文档交接契约

- 默认 spec 路径：`docs/specs/YYYY-MM-DD-<topic>-design.md`。
- 默认 plan 路径：`docs/plans/YYYY-MM-DD-<topic>.md`。
- 用户显式路径优先于默认路径。
- spec 必须经过用户明确批准后才能作为 plan 的稳定输入。
- plan 只有真实评审通过后才能记录 `review_status: approved`；不得预填或推断批准状态。
- 前置 skill 完成时必须报告 spec、plan 的绝对路径与评审状态；后置 skill 必须保留这些显式值。

## Git

- 默认分支为 `main`；开发应使用范围清晰的分支，不直接在 `main` 上维护已发布行为。
- 未经用户明确要求不 commit。用户要求 commit 时，使用 `<type>: 中文描述`。
- 不提交评估临时目录、虚拟环境、缓存、构建产物或本地安装副本。

## 验证

至少执行：

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/generating-development-prompts
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
```

开发环境先运行 `python3 -m venv .venv` 和 `.venv/bin/python -m pip install -r requirements-dev.txt`。维护矩阵至少覆盖 Python 3.9 和 Python 3.14。新增 skill 后，把它加入仓库 validator、官方 skill validator、安装测试和 plugin 验证。

## 评审

中等及以上变更必须由未参与实现的独立评审者检查 diff、skill 触发条件、TDD 证据、前向结果、plugin 打包、安装边界与文档契约。评审发现的改动必须重新验证并复审到收敛。
