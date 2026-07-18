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

## 命令结果与失败矩阵

| 结果 ID | 命令或异步完成阶段 | 前置条件 | 结果类型 | 客户端可见结果 | 事务、回滚与副作用 | 调用方动作 | 保证 ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `O-01` | `PUT /orders/{id}` | revision 匹配 | 成功 | `200` 与新 revision | `BEGIN IMMEDIATE` 后原子提交 | 接受新 revision | `G-01` |
| `O-02` | `PUT /orders/{id}` | revision 不匹配 | 冲突 | `409 ORDER_REVISION_CONFLICT` 与当前 revision | 回滚且订单不变 | 合并后重试 | `G-02` |
| `O-03` | worker 完成归档 | 当前 revision 已变化 | 状态失败 | job 终态 `stale` | 只提交 stale，不替换归档 | 停止轮询并重新发起 | `G-03` |
| `O-04` | worker 完成归档 | 本地提交失败 | 持久化失败 | job 终态 `failed` 与 `ARCHIVE_PERSISTENCE_FAILED` | 回滚且最后归档不变 | 等待健康后重新发起 | `G-04` |

## 数据库事务与锁语义

所有写路径在首次业务读取前执行 `BEGIN IMMEDIATE`，避免 DEFERRED 读转写升级。锁持有到 `COMMIT` 或 `ROLLBACK` 返回；慢速序列化在事务外完成。busy timeout 后回滚并按结果矩阵分类。

## 保证与测试追踪

| 保证 ID | 保证或失败契约 | 对应结果 ID 或状态 | 精确测试文件与名称 | 精确命令 | 可观察断言 |
| --- | --- | --- | --- | --- | --- |
| `G-01` | 保存原子递增 revision | `O-01` | `tests/test_order_transactions.py::OrderSaveTests.test_save_commits_next_revision` | `python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_save_commits_next_revision -v` | 响应和数据库 revision 同为 expected + 1 |
| `G-02` | 冲突不修改订单 | `O-02` | `tests/test_order_transactions.py::OrderSaveTests.test_conflict_rolls_back_and_reports_current_revision` | `python3 -m unittest tests.test_order_transactions.OrderSaveTests.test_conflict_rolls_back_and_reports_current_revision -v` | 返回 409/currentRevision，数据库字节不变 |
| `G-03` | 陈旧快照不发布归档 | `O-03` | `tests/test_archive_worker.py::ArchiveCompletionTests.test_stale_snapshot_never_replaces_archive` | `python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_stale_snapshot_never_replaces_archive -v` | job 为 stale，最后归档字节不变 |
| `G-04` | 本地持久化失败独立分类并回滚 | `O-04` | `tests/test_archive_worker.py::ArchiveCompletionTests.test_persistence_failure_rolls_back_and_is_not_stale` | `python3 -m unittest tests.test_archive_worker.ArchiveCompletionTests.test_persistence_failure_rolls_back_and_is_not_stale -v` | job error 为 persistence failed，非 stale，最后归档不变 |

## 验收标准

`G-01` 至 `G-04` 均由对应精确测试验证，且每个测试能回溯唯一结果 ID。
