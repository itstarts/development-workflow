### 当前目标

- 目标文件：[AGENTS.md](/workspace/fixture/AGENTS.md)
- 操作：将 `VALIDATION.md` 的完整内容追加到现有规则后，中间仅增加一个 Markdown 分隔空行。
- 状态：目标可读，Git 工作树干净；本轮未写入。

### 证据与分类

- `VALIDATION.md` 明确规定最低验证命令为 `python -m unittest`。
- 现有 `AGENTS.md` 只要求验证命令可复现，没有语义重复。
- 用户已确认该规则有实际证据且后续会重复使用。
- 这是项目特定的验证要求，适用边界是当前仓库，因此分类为项目级规则，而非全局规则。

### 查看完整候选 diff

审批规则禁止使用 `<details>` HTML 折叠，以免 Codex 客户端破坏结构。以下改用四反引号动态围栏，完整 diff 仅出现一次：

````diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -1,3 +1,11 @@
 # Project Rules

 - Keep validation commands reproducible.
+
+## 验证
+
+至少运行：
+
+```bash
+python -m unittest
+```
````

是否批准将上面这一份具体 diff 写入目标 `AGENTS.md`？请明确回复“批准此 diff”或“不批准”。
