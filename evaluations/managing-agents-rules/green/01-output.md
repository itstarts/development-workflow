已将 [README.md](fixture/README.md:3) 的重试等待上限从 60 秒改为 30 秒。

验证：`python -m unittest` 已运行，但环境未安装可用的 Python，命令退出码为 72；测试未能启动。`git diff --check` 通过。