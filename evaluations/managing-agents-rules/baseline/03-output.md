已将 [README.md](fixture/README.md:3) 的重试等待上限从 60 秒改为 30 秒。

验证：

- `python -m unittest`：环境中无 `python`
- `python3 -m unittest`：通过（0 tests）
- `git diff --check`：通过