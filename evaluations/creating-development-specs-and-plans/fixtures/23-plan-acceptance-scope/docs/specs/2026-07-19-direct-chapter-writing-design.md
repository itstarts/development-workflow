---
document_type: design
topic: direct-chapter-writing
requirements_path: docs/requirements/2026-07-19-direct-chapter-writing.md
requirements_topic: direct-chapter-writing
requirements_scope: feature
requirements_understanding_confidence: 98
requirements_understanding_confirmation: approved
requirements_user_approval: approved
requirements_independent_review: approved
specification_gate: open
user_approval: approved
approved_at: 2026-07-19
independent_review: approved
independent_reviewer: fixture-spec-reviewer
independent_reviewed_at: 2026-07-19
---

# 直接写作流程技术规格

## 目标与边界

Web、API 和 SQLite 共同实现创建作品后直接进入空白第一章、保存刷新恢复，以及两个浏览器会话发生 revision 冲突后保护双方正文、显式合并并继续保存。字段校验、状态转换、错误映射、事务失败和局部交互由低层测试覆盖。

## 保证与测试追踪

| 保证 ID | 保证 | 精确测试与命令 | 可观察断言 |
| --- | --- | --- | --- |
| `G-01` | 创建后可完成第一章保存并刷新恢复 | `tests/e2e/direct-chapter-writing.spec.ts::single chapter flow`；`pnpm test:e2e --grep "single chapter flow"` | URL、章节 ID、正文和 revision 跨层一致 |
| `G-02` | 冲突不静默覆盖且可恢复继续保存 | `tests/e2e/direct-chapter-writing.spec.ts::conflict recovery`；`pnpm test:e2e --grep "conflict recovery"` | 双方正文可恢复，显式合并结果最终持久化 |

## 验收类型与证据

| 验收项 | 验收类型 | 执行者 | 环境与步骤 | 可观察通过条件 | 留存证据 |
| --- | --- | --- | --- | --- | --- |
| 单章闭环 | 关键 E2E | CI 执行，发布负责人核对 | 发布候选 Web/API/SQLite；创建、输入、保存、刷新 | URL 与正文/revision 一致 | Playwright 报告、trace、截图 |
| 冲突恢复 | 关键 E2E | CI 执行，发布负责人核对 | 两个隔离浏览器会话；制造冲突、查看双方正文、合并、重试、刷新 | 无静默覆盖，合并结果持久化 | Playwright 报告、双会话 trace、截图 |
| 入口易用性 | 目标用户人工验收 | 5 名目标长篇小说写作者，产品负责人主持 | 无操作提示地创建作品并开始写第一章 | 至少 4/5 在 60 秒内完成 | 去标识化路径、用时、截图、主持记录 |
| 写作辅助内容质量 | 目标用户人工验收 | 同一类目标写作者，产品负责人主持 | 在发布候选真实配置下评价连贯性和可采用性 | 至少 4/5 两项评分不低于 4/5 | 去标识化评分、受控制品、任务记录 |
| 视觉体验 | 目标用户人工验收 | 同一类目标写作者，产品负责人主持 | 基准视口连续写作 10 分钟并评价层级与专注感 | 至少 4/5 两项评分不低于 4/5 | 去标识化评分、基准截图、主持记录 |

关键 E2E 只有“单章闭环”和“冲突恢复”两条。人工验收不能替代关键技术回归，E2E 不能冒充产品体验验证。

## 实施计划约束

plan 必须逐条列出上述两条 E2E 的名称、命令、环境、断言和证据，再逐条列出三项人工验收的目标用户、负责人、任务、阈值和证据。不得新增第三条 E2E，不得把人工判断转换为自动化断言。
