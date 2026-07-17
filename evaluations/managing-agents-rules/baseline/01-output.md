已将 [README.md](fixture/README.md) 的重试等待上限从 60 秒改为 30 秒。

验证：

- `python -m unittest`：环境中的 `python` 无法运行，提示缺少 Xcode Command Line Tools。
- 补充执行 `python3 -m unittest`：通过，运行 0 项测试。
- `git diff --check`：通过。

没有规则候选