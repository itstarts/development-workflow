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

- 记录 TDD 开发门；在无 skill baseline 完成前不创建可发布目录。

### Repository

- 建立 plugin-compatible 目录、项目级 agent 角色、分层 `AGENTS.md` 和仓库验证入口。
- 固定 validator 开发依赖并声明 Python 3.9/3.14 维护矩阵。
- 仓库验证器忽略 Python 缓存和系统元数据，保持 skill 测试后的重复验证稳定。
