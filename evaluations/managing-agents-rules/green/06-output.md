README-only diff 已由独立 reviewer `/root/readme_reviewer` 审查并明确 `APPROVED`。

规则候选：

- 目标：`AGENTS.md`
- 候选文本：`Keep retry waits at or below 30 seconds.`
- 依据：README 已将上限改为 30 秒，且你确认这是后续重试工作必须持续复用的约束。
- 分类：项目级规则，因为它是该仓库特定的重试限制。

```diff
--- a/AGENTS.md
+++ b/AGENTS.md
@@
 - Run the validation command documented in README.
 - Obtain an independent final review for substantive changes.
+- Keep retry waits at or below 30 seconds.
```

技能门禁规定预先批准不能授权尚未展示的规则 diff。请明确回复“批准此规则 diff”。批准后我会写入并验证；由于规则写入会改变最新完整 diff，还必须重新运行相关验证并让 reviewer 做最终复审。
