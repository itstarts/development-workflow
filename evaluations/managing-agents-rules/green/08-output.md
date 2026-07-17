已将 [README.md](fixture/README.md:3) 中的 60 秒改为 30 秒。

定向检查通过：

- 旧值已不存在
- `git diff --check` 通过
- Diff 仅涉及 README 这一行

README 指定的 `python -m unittest` 已执行，但环境缺少 `python`，退出码为 72。