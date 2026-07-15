# development-workflow

`development-workflow`（简称 `dw`）在一个 GitHub 仓库中维护两个职责独立的 Codex skill，并提供 plugin-compatible 打包。

版本化、脱敏的 baseline 与 GREEN 证据放在 `evaluations/`；可能包含用户上下文的本地原始材料放在被忽略的 `work/`。

## Skills

| Skill | 状态 | 职责 |
|---|---|---|
| `creating-development-specs-and-plans` | available | 澄清需求、取得设计批准并生成经独立评审的实施计划 |
| `generating-development-prompts` | available | 从已有 spec、plan、仓库与会话证据生成可复制的开发提示词 |

两个 skill 职责独立：前者以显式文档路径和状态字段交付 spec/plan，后者读取这些文档和状态生成开发提示词；二者不通过本机安装路径互相调用。

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

也可按职责单独安装其中一个 skill：

```bash
python3 \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo <owner>/development-workflow \
  --ref <tag> \
  --path skills/creating-development-specs-and-plans
```

或：

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
.venv/bin/python -m unittest discover -s skills/creating-development-specs-and-plans/tests -v
.venv/bin/python -m unittest discover -s skills/generating-development-prompts/tests -v
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/creating-development-specs-and-plans
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  skills/generating-development-prompts
.venv/bin/python "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
```

支持范围为 Python 3.9 及以上；当前维护矩阵至少验证 Python 3.9 和 Python 3.14。`requirements-dev.txt` 固定官方 skill/plugin validator 所需的开发依赖。

plugin manifest 位于 `.codex-plugin/plugin.json`。仓库尚未配置 GitHub remote、marketplace、license 或发布自动化；这些信息应在所有者明确选择后添加，不使用占位身份或虚构 URL。

`evaluations/creating-development-specs-and-plans/` 保存脱敏后的固定场景、创建前 RED 结论、迁移 baseline 与 GREEN 评分；原始 JSONL trace 和 stderr 只保存在被忽略的 `work/`。版本化结果只记录场景、有效性、判据和必要 warning，不维护文件哈希或逐次 attempt 审计。本地 staging 已覆盖两个 skill 的单独/组合载荷及拒绝覆盖行为。由于仓库尚无 GitHub remote/tag 且本次未授权发布，Git tag 多路径安装仍是发布前未执行门。

## 来源

`skills/generating-development-prompts` 初始内容复制自 2026-07-12 已完成任务级、集成和最终全量评审的安装产物。导入后的兼容性修复与后续维护以本仓库测试、评审和版本记录为准。
