当前审批快照：

- 当前目标：项目根 [AGENTS.md](/workspace/fixture/AGENTS.md)，文件可读，尚未写入。
- 候选正文：在现有内容后空一行，原样追加 [VALIDATION.md](/workspace/fixture/VALIDATION.md) 的全部 7 行内容。
- 证据：`VALIDATION.md` 明确规定最低验证命令为 `python -m unittest`；现有规则只要求验证命令可复现，未记录具体命令；你已确认该规则后续会重复使用。
- 分类理由：这是该仓库特有的验证入口，可减少未来重复确认和漏跑验证，属于项目级规则，而非跨项目全局规则；与现有通用要求不构成语义重复。
- 基线状态：`git status --short` 为空；候选为单文件、纯追加的最小 diff。

技能明确禁止使用可能破坏 Codex 渲染的 HTML 折叠标签，因此以下以同名区块静态展示，并使用四反引号围栏保护候选正文中的三反引号。

### 查看完整候选 diff

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

是否批准仅将上述 diff 写入项目根 `AGENTS.md`？请回复“批准此 diff”或“不批准”。
