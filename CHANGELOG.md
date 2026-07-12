# Changelog

本项目遵循语义化版本。两个 skill 共享 plugin 版本；每个版本分别记录 skill 与集成契约变化。

## 0.1.0 - Unreleased

### generating-development-prompts

- 导入经过任务级、集成和最终全量评审的初始实现。
- 统一 Python 3.9 与 Python 3.14 对深层 JSON 输入的 `invalid_json` 错误分类。
- 提示词只给出目标新会话的推荐 effort，不再生成模型能力或角色级 effort 配置。
- 仓库与分支状态段只保留实施门，不再展开工作目录、分支、HEAD 或 worktree 状态。
- 委派任务时优先使用职责匹配的个人全局 custom agent，并显式处理无法按名称启动的能力缺口。

### creating-development-specs-and-plans

- 记录 TDD 开发门；在无 skill baseline 完成前不创建可发布目录。

### Repository

- 建立 plugin-compatible 目录、项目级 agent 角色、分层 `AGENTS.md` 和仓库验证入口。
- 固定 validator 开发依赖并声明 Python 3.9/3.14 维护矩阵。
- 仓库验证器忽略 Python 缓存和系统元数据，保持 skill 测试后的重复验证稳定。
