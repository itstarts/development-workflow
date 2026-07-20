# Security Policy

## 报告安全问题

发现 skill、脚本、评估数据或仓库配置中的安全问题时，优先使用 GitHub Private Vulnerability Reporting / Security Advisory。若该入口尚未启用，请创建只包含最小信息的 issue，请维护者提供私下联系方式。

不要在公开 issue、PR、日志或评估输出中提交 token、密钥、凭证、私有路径、真实 task/thread 标识符、完整本机配置或生产数据。

## 支持范围

当前支持稳定版本 `v0.1.0` 和开发分支 `main`。安全修复优先合入 `main`；确认影响稳定版本时，同步更新受支持 tag 的发布说明。更早且未列出的快照不承诺维护。

## 仓库安全边界

- 六个 skill 不读取兄弟 skill 的源码、安装目录或 plugin cache。
- `work/` 只用于本地原始评估和 trace，并由 `.gitignore` 排除。
- 版本化评估必须脱敏，不包含真实用户上下文或真实本机绝对路径。`/workspace/fixture` 是评估输出唯一允许的合成仓库根，不是真实路径或隐私数据；公开检查允许该固定前缀，同时拒绝 macOS 用户与临时目录、Linux `/home/...` 与临时目录、Windows 用户目录及其它 `/workspace/...` 根。
- 安装器遇到已存在目标目录时停止，避免静默覆盖本地 skill。
- 项目级 reviewer 默认只读，不执行安装、push、release 或其它外部状态变更。

公开发布前应同时扫描当前树和完整 Git 历史；删除当前文件不能从已有 commit 中移除敏感信息。
