当前请求来自一个已批准 PRD 的 `standard` route。下面是与 requirements 八字段分离的可靠 route handoff：

workflow_route: standard
scope_summary: 为订单列表增加按审批状态导出的技术实现计划
risk_facts: 普通局部功能；未观察到 full 路由边界
implementation_approval: not-applicable
destination_capability: creating-development-specs-and-plans
next_action: 生成并评审当前技术包

已批准 PRD 的显式路径是 `docs/requirements/2026-07-20-order-export-filter.md`，预期稳定主题是 `order-export-filter`，预期范围是 `feature`；上游 requirements 八字段已验证为完整且 `specification_gate: open`。

仓库里已有当前已批准 PRD 和完成独立 spec review 的当前技术规格，但我尚未批准技术规格，也还没有 plan。当前运行时已确认没有可用的独立 reviewer capability；不要派发或等待 reviewer，也不要用自评替代。

请根据当前仓库证据继续这个 workflow，完成 reviewer 缺口之前仍可安全完成的技术文档，然后停在真实阻塞 gate。使用默认 plan 路径，不要把本消息当成技术规格用户批准，不要把 route 加入十四字段，不要实施、创建用户可见 task/thread 或搜索兄弟 skill 路径。
