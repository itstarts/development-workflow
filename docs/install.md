# 安装指南

## 前置条件

- 已安装 Git 和 Python 3。
- Codex 已包含系统级 `skill-installer`。
- 目标目录 `${CODEX_HOME:-$HOME/.codex}/skills` 可写。

安装完成后启动一个新的 Codex 会话，使 skill 列表重新加载。

## 通过 plugin marketplace 安装

仓库根目录的 `.agents/plugins/marketplace.json` 把五个 skill 作为一个 `development-workflow` plugin bundle 发布。先添加 repo marketplace，再安装 plugin：

```bash
codex plugin marketplace add itstarts/development-workflow --ref main
codex plugin add development-workflow@development-workflow
```

当前 catalog 和其中 plugin entry 的 `source.ref` 都指向 `main`，适合获取当前公开开发版本。`codex plugin marketplace add ... --ref <tag>` 只固定 marketplace catalog 的快照，不能覆盖 entry 自己的 plugin Git ref。发布不可变 tag 时，维护者必须先把 `.agents/plugins/marketplace.json` 中的 `source.ref` 更新为同一个已验证 tag，完成验证后再创建该 tag；使用者随后同时以 `--ref <tag>` 添加 catalog。当前 `0.1.0` 仍为 Unreleased，不能把现有 `main` entry 表述为生产 pin。

安装完成后启动新的 Codex 会话，使 plugin 和 skill 列表重新加载。以上命令会修改当前用户的 Codex marketplace 和 plugin 安装状态；只在明确希望安装完整 bundle 时执行。

## 通过 skill-installer 安装全部 skill

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
- `skills/managing-agents-rules`

五个 skill 可独立安装和运行。marketplace 方式安装完整 plugin bundle；`skill-installer` 方式可以只选需要的 skill。PRD→spec→会话路由的完整自动链要求 `creating-product-requirements`、`creating-development-specs-and-plans` 和 `generating-development-prompts` 在同一运行时同时可用；单独安装其中一个时，它仍完成自身职责，并在需要进入未加载的下游 skill 时如实报告能力缺口，不读取兄弟 skill 的源码或安装目录。受控实施 skill 直接读取当前批准范围和仓库证据，`managing-agents-rules` 独立执行 AGENTS 规则治理。

## 安全更新

更新前不要直接覆盖正在使用的安装副本。两种安装方式使用不同的 staging 和比较边界。

### skill-installer 安装

installer 在目标 skill 目录已存在时会停止：

1. 使用临时 `CODEX_HOME` 安装候选版本。
2. 运行官方 skill validator，并使用仓库只读比较器核对候选内容：

   ```bash
   .venv/bin/python scripts/verify_install.py \
     --codex-home /path/to/staging-codex-home \
     --skill creating-product-requirements
   ```

   省略 `--skill` 时比较 registry 中全部已实现 skill。命令只报告 publishable payload 的 missing、extra、different 或非普通文件，不创建、复制、删除或修改目标，也不构成正式安装授权。内容 missing、extra 或 different 返回 `1`；参数、registry、路径、读取、symlink 或其它非普通文件错误返回 `2`。
3. 备份或移走旧目录后，再把已验证候选安装到正式位置。
4. 启动新 Codex 会话并确认五个 skill 均可见。

`verify_install.py` 只验证 `skill-installer` 写入的 skill 目录，不能验证 marketplace plugin cache。

### marketplace plugin 安装

1. 把待发布 plugin 放入临时 marketplace root。验证未提交候选时，entry 必须指向该候选的本地快照或临时 Git commit；不能用远端 `main` 的安装结果替代当前候选证据。
2. 使用临时 `CODEX_HOME` 执行 `codex plugin marketplace add <temporary-marketplace-root>` 和 `codex plugin add <plugin-name>@<marketplace-name>`。
3. 在 `<temporary-CODEX_HOME>/plugins/cache/<marketplace-name>/<plugin-name>/<version-or-local>` 找到 CLI 实际安装的副本，对该目录运行官方 plugin validator。
4. 将已安装副本的 `.codex-plugin/` 和 `skills/` 与待发布候选逐文件比较；validator 通过且没有 missing、extra 或 different，才证明当前候选经过真实安装。
5. 正式安装后启动新的 Codex 会话，并确认 plugin 及五个 skill 均可见。

仓库开发不得直接修改 `~/.codex/skills` 中的安装副本；源代码变更只在本仓库完成。
