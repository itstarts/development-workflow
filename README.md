# development-workflow

`development-workflow`（简称 `dw`）在一个 GitHub 仓库中维护两个职责独立的 Codex skill，并提供 plugin-compatible 打包。

版本化、脱敏的 baseline 与 GREEN 证据放在 `evaluations/`；可能包含用户上下文的本地原始材料放在被忽略的 `work/`。

## Skills

| Skill | 状态 | 职责 |
|---|---|---|
| `creating-development-specs-and-plans` | planned，尚不可用 | 澄清需求、取得设计批准并生成实施计划 |
| `generating-development-prompts` | available | 从已有 spec、plan、仓库与会话证据生成可复制的开发提示词 |

planned skill 当前故意不出现在 `skills/` 下，因为 plugin 会把每个 skill 子目录当作可发布组件。必须先完成无 skill baseline，才能按照仓库 `AGENTS.md` 创建目录和实现。

## 安装

发布到 GitHub 后，可以一次安装两个已实现的 skill：

```bash
python3 \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo <owner>/development-workflow \
  --ref <tag> \
  --path \
    skills/creating-development-specs-and-plans \
    skills/generating-development-prompts
```

在 companion skill 尚未实现的当前版本，只安装可用 skill：

```bash
python3 \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo <owner>/development-workflow \
  --ref <tag> \
  --path skills/generating-development-prompts
```

installer 在目标目录已存在时会停止，不会静默覆盖。安装或更新后启动新 Codex 会话，让 skill 列表重新加载。

## 开发

完整读取 `AGENTS.md` 和作用域更深的规则后再修改。常用验证：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt

.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/generating-development-prompts
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
```

支持范围为 Python 3.9 及以上；当前维护矩阵至少验证 Python 3.9 和 Python 3.14。`requirements-dev.txt` 固定官方 skill/plugin validator 所需的开发依赖。

plugin manifest 位于 `.codex-plugin/plugin.json`。仓库尚未配置 GitHub remote、marketplace、license 或发布自动化；这些信息应在所有者明确选择后添加，不使用占位身份或虚构 URL。

## 来源

`skills/generating-development-prompts` 初始内容复制自 2026-07-12 已完成任务级、集成和最终全量评审的安装产物。导入后的兼容性修复与后续维护以本仓库测试、评审和版本记录为准。
