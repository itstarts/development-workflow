仓库证据表明，现有系统仅支持创建订单和订单所有者查看，尚无审批权限模型。当前理解不足 95%，且审批角色会直接决定业务规则与验收标准，因此暂不创建 PRD，也不进入实现方案；API、表结构、队列和开发任务不属于 PRD 内容。

第一个关键问题：订单审批权限模型是什么——哪些角色可以审批，是否需要单人审批、多人会签或按顺序审批？

requirements_path: /workspace/fixture/docs/requirements/2026-07-15-order-approval.md
requirements_topic: order-approval
requirements_scope: feature
understanding_confidence: 35
understanding_user_confirmation: pending
requirements_user_approval: pending
requirements_independent_review: pending
specification_gate: blocked
