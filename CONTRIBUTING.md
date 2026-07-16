# Contributing

欢迎贡献开发工作流、测试、评估和文档改进。提交前请先阅读 [AGENTS.md](AGENTS.md) 和 [Agent 开发指南](docs/agent-development.md)。

## 接受的改动

- 改善 PRD、technical spec/plan、development prompt 或受控小改动实施的稳定流程。
- 修复 skill 触发、批准门、路径优先级或错误处理问题。
- 增强可复现测试、脱敏评估、plugin 打包或安装验证。
- 改善公开文档和贡献体验。

不接受把个人机器路径、私有工作流、插件缓存内容、真实用户数据或未经脱敏的 Agent trace 提交到仓库。

## 开发流程

1. 从 `main` 创建范围清晰的分支。
2. 修改前读取适用的 `AGENTS.md`，检查现有代码、测试和工作区状态。
3. skill 行为变化必须先形成 RED，再做最小 GREEN 和整理。
4. 只版本化脱敏证据；原始材料保留在被忽略的 `work/`。
5. 运行与影响范围相称的测试及完整仓库 validator。
6. 中等及以上改动由未参与实现的只读 reviewer 检查最新 diff 和验证证据。

## Pull Request

PR 描述应包含：

- 目标、范围和非目标；
- RED 证据与实现摘要；
- 实际运行的验证命令和结果；
- 独立评审结论；
- 兼容性、安装或文档影响；
- 未解决问题和残留风险。

提交信息使用 `<type>: 中文描述`，例如 `docs: 整理开源项目文档`。不要在 PR 中粘贴 token、私有路径、task/thread 标识符或未经脱敏的完整本机配置。
