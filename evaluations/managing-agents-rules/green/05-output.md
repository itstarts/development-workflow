已完成：

- [project-a/README.md](fixture/project-a/README.md:3)：60 → 30 秒
- [project-b/README.md](fixture/project-b/README.md:3)：60 → 30 秒
- 两项目作为独立任务，各自完成一次检查和完成阶段扫描
- 两边 `git diff --check` 均通过

指定技能禁止将治理状态持久化，因此未创建 `.agents-governance-state.json`；检查、拒绝及扫描状态仅保留在当前会话中。