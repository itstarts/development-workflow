旧批准已失效：当前 `AGENTS.md` 比当时多了一条规则。`managing-agents-rules` 强制要求基线变化后重新展示并批准当前 diff，无法绕过。

目标：[AGENTS.md](<fixture/AGENTS.md>)

候选规则：`Keep retry waits under 60 seconds.`
依据：你明确要求加入该重试等待限制。
分类：项目规则，因为它约束此仓库中的工作方式。

```diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@
 # Project Rules

 - Run focused tests.
 - Preserve user-authored documentation changes.
+- Keep retry waits under 60 seconds.
```

请明确回复“批准”以授权这个当前 diff。
