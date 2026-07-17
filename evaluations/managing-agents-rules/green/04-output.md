预检确认：项目根目录缺少 `AGENTS.md`，且当前不是 Git 工作区。README 尚未修改。

请分别批准或拒绝：

1. 创建根目录 `AGENTS.md`

```diff
--- /dev/null
+++ AGENTS.md
@@ -0,0 +1,3 @@
+# Project Instructions
+
+- Run `python -m unittest` after changes.
```

依据：README 指定该项目使用 `python -m unittest` 验证。

2. 执行 `git init`

建议初始化 Git，以便准确审计后续修改；这与创建 `AGENTS.md` 是完全独立的动作。

请回复类似：`1 拒绝，2 批准`。在收到两个分别明确的决定前，我不会创建 `AGENTS.md`、执行 `git init` 或修改 README。