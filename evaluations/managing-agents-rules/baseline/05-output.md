已完成两个独立项目的修改：

- [project-a/README.md](fixture/project-a/README.md)：60 秒改为 30 秒
- [project-b/README.md](fixture/project-b/README.md)：60 秒改为 30 秒
- 未创建任何 `AGENTS.md`
- 两个项目各执行一次完成阶段候选扫描，均发现 0 个候选
- 检查、拒绝和扫描状态已写入 [.agents-governance-state.json](fixture/.agents-governance-state.json)

验证：JSON 与 Git diff 检查通过；`python3 -m unittest` 通过（0 项测试）。环境没有 `python` 命令。