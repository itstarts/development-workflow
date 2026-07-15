当前被硬门禁阻塞，不能创建 spec、plan 或开始编码。

仓库证据显示订单系统目前只有创建订单能力，没有审批流程、通知渠道或审批权限模型。你也明确说明：

- 没有已批准 PRD；
- 稳定 topic 尚未确认；
- `feature` 只是暂定 scope；
- 审批人、通知方式、驳回后重提规则均未确定。

下一步需要先形成并批准 PRD，然后提供：

1. PRD 的仓库内路径；
2. 确认后的 kebab-case topic，例如 `order-approval`；
3. 确认后的 scope；
4. PRD 中可靠记录的理解确认、用户批准及独立评审状态。

之后才能依次进行：PRD 检查 → spec → 独立评审 → 你的明确批准 → plan → 独立评审。此技能的交付边界止于文档交接，本轮不能实施目标代码。

```text
requirements_path: null
requirements_topic: null
requirements_scope: unknown
requirements_understanding_confidence: unknown
requirements_understanding_confirmation: unknown
requirements_user_approval: unknown
requirements_independent_review: unknown
specification_gate: blocked
spec_path: null
spec_user_approval: pending
spec_independent_review: pending
plan_path: null
plan_review_status: not-approved
implementation_gate: blocked
```