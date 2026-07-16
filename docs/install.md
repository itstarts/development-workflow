# 安装指南

## 前置条件

- 已安装 Git 和 Python 3。
- Codex 已包含系统级 `skill-installer`。
- 目标目录 `${CODEX_HOME:-$HOME/.codex}/skills` 可写。

安装完成后启动一个新的 Codex 会话，使 skill 列表重新加载。

## 安装全部 skill

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

`main` 适合获取当前公开版本。仓库发布 tag 后，生产或团队环境应把 `--ref` 固定为已验证 tag，以避免安装内容随分支变化。

## 单独安装

把 `--path` 设置为一个 skill 目录：

```bash
python3 \
  "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo itstarts/development-workflow \
  --ref main \
  --path skills/creating-product-requirements
```

可用路径：

- `skills/creating-product-requirements`
- `skills/creating-development-specs-and-plans`
- `skills/generating-development-prompts`
- `skills/implementing-bounded-changes`

四个 skill 可独立安装和运行；完整交接链通过目标项目文档协作，受控实施 skill 直接读取当前批准范围和仓库证据，均不读取兄弟 skill 的源码或安装目录。

## 安全更新

installer 在目标目录已存在时会停止。更新前不要直接覆盖正在使用的安装副本：

1. 使用临时 `CODEX_HOME` 安装候选版本。
2. 运行官方 skill validator，并比较候选内容与当前安装。
3. 备份或移走旧目录后，再把已验证候选安装到正式位置。
4. 启动新 Codex 会话并确认四个 skill 均可见。

仓库开发不得直接修改 `~/.codex/skills` 中的安装副本；源代码变更只在本仓库完成。
