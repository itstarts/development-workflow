本轮未写入任何规则文件。

### 当前目标

经批准后，将 [VALIDATION.md](/workspace/fixture/VALIDATION.md) 的完整内容追加到项目根 [AGENTS.md](/workspace/fixture/AGENTS.md)，中间增加一个 Markdown 分隔空行。

### 证据与分类理由

- Git 确认当前目录就是项目根；根级 `AGENTS.md` 可读。
- `VALIDATION.md` 明确规定最低验证命令为 `python -m unittest`。
- 当前 `AGENTS.md` 只有通用的“保持验证命令可复现”规则，不与该具体命令重复。
- 任务上下文确认工程修改和验证已经完成，且该规则后续会重复使用。
- 分类为项目级规则：它描述本项目专属的验证入口，可减少后续重复确认和验证成本，不属于跨项目通用原则。
- 当前工作树干净；候选补丁通过 `git apply --check -`，仅增加 8 行。

<details>
<summary>查看完整候选 diff</summary>

````diff
diff --git a/AGENTS.md b/AGENTS.md
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

</details>

是否批准这一份具体 diff 写入上述项目级 `AGENTS.md`？请回复“批准此 diff”或“不批准”。批准仅适用于当前展示的 diff；若基线发生变化，需要重新展示并再次批准。
