# Changelog

本项目遵循语义化版本。两个 skill 共享 plugin 版本；每个版本分别记录 skill 与集成契约变化。

## 0.1.0 - Unreleased

### generating-development-prompts

- 导入经过任务级、集成和最终全量评审的初始实现。
- 统一 Python 3.9 与 Python 3.14 对深层 JSON 输入的 `invalid_json` 错误分类。
- 移除无法基于任务复杂度可靠判断的 effort 建议及其输入、渲染和校验契约。
- 仓库与分支状态段只保留实施门，不再展开工作目录、分支、HEAD 或 worktree 状态。
- 委派任务时优先使用职责匹配的个人全局 custom agent，并显式处理无法按名称启动的能力缺口。
- 默认自动发现目录改为 `docs/specs` 与 `docs/plans`；生成提示词不绑定外部开发方法或固定评审 skill，并以自包含合同要求任务级 TDD、独立评审循环和集成后的整体评审循环。

### creating-development-specs-and-plans

- 新增需求澄清、spec 独立评审、用户书面批准和 plan 独立评审的顺序门禁。
- 固定 spec/plan 默认路径、显式路径优先级、三态 plan review 映射和六字段绝对路径交接。
- 通过隔离的新鲜代理保留创建前 RED 审计、当前迁移 baseline 与 GREEN 前向证据。
- 评估证据收敛为场景、有效性和判据结果，移除文件哈希、候选 manifest 与逐次 attempt 审计。
- spec 的安全、权限和敏感数据设计改为仅在目标需求真实涉及对应边界时展开。
- 保持运行时自包含，不实现目标代码、不调用兄弟 skill，也不创建用户可见 task/thread 或改变外部状态。

### Repository

- 建立 plugin-compatible 目录、项目级 agent 角色、分层 `AGENTS.md` 和仓库验证入口。
- 固定 validator 开发依赖并声明 Python 3.9/3.14 维护矩阵。
- 仓库验证器忽略 Python 缓存和系统元数据，保持 skill 测试后的重复验证稳定。
- plugin 文案扩展为同时覆盖 spec/plan authoring 与开发提示词 handoff；本地 staging 验证两个 skill 可单独或组合复制且拒绝覆盖已有目标。
