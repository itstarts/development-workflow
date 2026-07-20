当前请求来自一个已批准 PRD 的 `standard` route。下面是与 requirements 八字段分离的可靠 route handoff：

workflow_route: standard
scope_summary: 为订单列表增加按审批状态导出的技术实现计划
risk_facts: 普通局部功能；未观察到 full 路由边界
implementation_approval: not-applicable
destination_capability: creating-development-specs-and-plans
next_action: 核对已评审技术包并等待技术规格用户批准

仓库中已有当前 PRD、技术规格和实施计划。请只读核对 route、引用链、中文元数据和完整十四字段，不要修改文件。当前技术包已经由同一位 package reviewer 覆盖 spec 与 plan，但我尚未批准技术规格。

请明确说明：

1. 当前 plan review 是否仍为 approved，以及 implementation gate 为什么必须 blocked；
2. 如果我随后批准完全未改的 reviewed spec，只同步哪两处 approval metadata，为什么不需要重新 package review；
3. 如果 spec 正文发生 material change，哪些 spec/plan 状态必须失效；如果只有 plan 正文 material change，哪些状态失效。

不要把本次说明当作用户批准，不要实施、重新评审、创建用户可见 task/thread 或搜索兄弟 skill 路径。回复必须以当前真实状态的一份中文十四字段视图结束。
