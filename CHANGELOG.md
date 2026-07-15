# Changelog

本项目遵循语义化版本。三个 skill 共享 plugin 版本；每个版本分别记录 skill 与集成契约变化。

## 0.1.0 - Unreleased

### creating-product-requirements

- 新增产品、阶段和功能三种范围类型；一份 PRD 只承载一个稳定主题。
- 只有需求理解置信度至少 95 且用户明确确认当前摘要后才创建 PRD；Agent 自评不能替代用户确认。
- PRD 聚焦产品范围、用户场景和验收标准，不包含 API、数据模型、迁移或实现任务。
- 固定 PRD 独立评审、用户批准、实质修改失效和 requirements 八字段交接门禁。
- 通过无目标 skill baseline、8 个 GREEN 场景、官方 validator 和独立评审完成创建闭环。

### generating-development-prompts

- 导入经过任务级、集成和最终全量评审的初始实现。
- 统一 Python 3.9 与 Python 3.14 对深层 JSON 输入的 `invalid_json` 错误分类。
- 移除无法基于任务复杂度可靠判断的 effort 建议及其输入、渲染和校验契约。
- 仓库与分支状态段只保留实施门，不再展开工作目录、分支、HEAD 或 worktree 状态。
- 委派任务时优先使用职责匹配的个人全局 custom agent，并显式处理无法按名称启动的能力缺口。
- 默认自动发现目录改为 `docs/specs` 与 `docs/plans`；生成提示词不绑定外部开发方法或固定评审 skill，并以自包含合同要求任务级 TDD、独立评审循环和集成后的整体评审循环。

### creating-development-specs-and-plans

- 将已批准 PRD 设为创建或实质修改技术 spec 的强制上游门；缺失、不可靠、未批准或 topic/scope 不匹配时阻断。
- 新增只读 PRD inspector，校验仓库根、路径边界、稳定主题、范围、95% 置信度、摘要确认、独立评审和用户批准。
- 技术 spec 在相关时明确 API/技术接口、数据模型与实体关系、迁移、状态流转、事务、并发与一致性。
- 固定 requirements/spec/plan 十四字段绝对路径交接，同时保留 spec 和 plan 的双审批顺序门。
- 通过隔离的新鲜代理保留创建前 RED 审计、当前迁移 baseline 与 GREEN 前向证据。
- 评估证据收敛为场景、有效性和判据结果，移除文件哈希、候选 manifest 与逐次 attempt 审计。
- spec 的安全、权限和敏感数据设计改为仅在目标需求真实涉及对应边界时展开。
- 保持运行时自包含，不实现目标代码、不调用兄弟 skill，也不创建用户可见 task/thread 或改变外部状态。

### Repository

- 建立 plugin-compatible 目录、项目级 agent 角色、分层 `AGENTS.md` 和仓库验证入口。
- 增加 MIT License、贡献指南、安全策略、安装指南、工作流契约与 Agent 开发指南，形成公开仓库文档入口。
- 补齐本机凭证、编辑器状态、Python 缓存、原始评估、构建测试产物和临时日志的 `.gitignore` 边界。
- 将公开安装命令更新为 `itstarts/development-workflow`，并记录完整 Git 历史隐私审计要求。
- 固定 validator 开发依赖并声明 Python 3.9/3.14 维护矩阵。
- 仓库验证器忽略 Python 缓存和系统元数据，保持 skill 测试后的重复验证稳定。
- plugin 文案扩展为 PRD → technical spec/plan → development prompt 三段式工作流；本地 staging 验证三个 skill 可单独或组合复制且拒绝覆盖已有目标。
