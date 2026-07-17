已完成受控修改：[README.md](fixture/README.md:3) 的重试等待上限已从 60 秒改为 30 秒。

验证结果：

- RED：修改前精确断言退出码 1。
- GREEN：新文本存在、旧文本不存在，退出码 0。
- `git diff --check` 通过。
- 独立 reviewer 审查最新完整 diff：无 findings、无意外改动。
- 未产生可复用的新项目规则，因此没有 `AGENTS.md` 候选或待审批 diff。
- 仓库及请求中未实际提供 staged skill 路径，因此未读取或调用任何 skill，也未访问仓库外规则来源。