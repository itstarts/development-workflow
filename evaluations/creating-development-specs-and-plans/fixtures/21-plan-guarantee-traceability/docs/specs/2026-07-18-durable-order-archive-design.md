---
document_type: design
topic: durable-order-archive
requirements_path: docs/requirements/2026-07-18-durable-order-archive.md
requirements_topic: durable-order-archive
requirements_scope: feature
requirements_understanding_confidence: 98
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: approved
approved_at: 2026-07-18
independent_review: approved
independent_reviewer: fixture-spec-reviewer
independent_reviewed_at: 2026-07-18
---

# 持久化订单归档技术规格

## 目标

在 Python 3.14 标准库 `sqlite3` 与 SQLite 3.46 WAL 模式中保存订单，并从固定快照异步发布归档。

## 关键结果与失败边界

| 需求或已确认风险依据 | 触发条件 | 可观察结果 | 数据或一致性影响 | 调用方动作 |
| --- | --- | --- | --- | --- |
| revision 校验保存 | revision 匹配 | `200` 与新 revision | 订单与 revision 原子提交 | 接受新 revision |
| 冲突保留用户草稿 | revision 不匹配 | `409 ORDER_REVISION_CONFLICT` 与当前 revision | 订单不变 | 合并后重试 |
| 固定快照归档 | worker 完成时 revision 未变化 | job 终态 `completed` | 原子替换最后完成归档 | 停止轮询 |
| 陈旧与持久化失败可区分 | revision 已变化或本地提交失败 | job 分别为 `stale` 或 `failed`；失败含 `ARCHIVE_PERSISTENCE_FAILED` | 两者都不替换最后完成归档 | 重新发起或等待存储恢复 |

## 事务边界

慢速序列化在事务外完成。保存订单和发布归档各使用一个短写事务；归档提交在同一事务内重新校验 snapshot revision，仅在仍匹配时写入归档。事务失败回滚，不得把本地提交失败报告为 `stale`。锁的具体获取方式只需遵循仓库确认的 SQLite WAL 配置，不增加跨进程协调协议。

## 需求与验证追踪

| 需求或风险依据 | 最小技术保证 | 最小充分验证 |
| --- | --- | --- |
| revision 校验保存 | 成功保存原子递增 revision；冲突不修改订单并返回当前 revision | 保存成功与冲突两项事务测试 |
| 固定快照归档 | 慢序列化后重新校验；陈旧快照不发布 | worker 完成时 revision 变化的定向测试 |
| 失败状态可查询 | 本地持久化失败回滚并报告 `failed`，不与 `stale` 混淆 | 注入本地提交失败的 worker 定向测试 |

## 验收标准

上述三类批准需求均有定向自动化证据；不新增通用恢复框架、额外持久身份、额外状态机或与当前风险无关的并发测试矩阵。
