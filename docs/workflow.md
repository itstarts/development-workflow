# 工作流与文档契约

## 完整交接链

### 1. 产品需求

`creating-product-requirements` 把产品意图收敛为一个稳定主题。范围类型只能是 `product`、`phase` 或 `feature`。只有需求理解置信度至少为 95%，且用户确认当前摘要后，才创建 PRD。

默认路径：

```text
docs/requirements/YYYY-MM-DD-<topic>.md
```

PRD 必须经过独立评审和用户明确批准，才能进入技术设计阶段。

### 2. 技术规格与计划

`creating-development-specs-and-plans` 先校验已批准 PRD，再生成 technical spec。spec 经独立评审和用户明确批准后，才生成 implementation plan；plan 必须经过独立评审。

默认路径：

```text
docs/specs/YYYY-MM-DD-<topic>-design.md
docs/plans/YYYY-MM-DD-<topic>.md
```

### 3. 开发提示词

`generating-development-prompts` 读取用户显式指定或从 `docs/specs/`、`docs/plans/` 自动发现的 spec、plan 路径和仓库证据；显式路径优先。它生成可复制到新 Codex 会话的自包含开发提示词，不修改目标功能，也不替代 spec 或 plan 的批准门。plan 未批准或状态未知时仍可生成提示词，但提示词必须在修改前阻断实施。

## 受控实施入口

`implementing-bounded-changes` 用于现有或开发中项目里已经明确改动点和方案、且用户已明确同意推进的小改动或 Bug 修复。它不生成提示词，也不要求为了小任务创建 PRD、spec、plan 或进度文档。

实施前在当前会话冻结目标、改动点、方案、非目标、验证范围和文档影响。行为变化使用比例化 RED→GREEN；默认只运行最小充分的定向验证，可以使用边界清晰的 Sub Agent。完成前同步受影响的现有文档，并由一位未参与实现的评审者检查最新完整 diff；有修改时由同一评审者复审直到 `APPROVED`，通过后立即停止，不增加重复评审或额外评审者。未取得批准时保持阻塞，不能声明完成。

用户批准只覆盖冻结范围。实现或评审发现必须改变公共契约、依赖、架构、数据、权限、迁移、并发、一致性或其他已确认边界时，停止修改并重新请求用户批准。受控实施入口不得绕过目标仓库明确要求的产品、设计、迁移、安全或发布门。

## 协作边界

- 用户显式路径优先于默认路径。
- skill 之间只通过文档路径、评审状态和显式输出字段协作。
- skill 不通过相对 import、本机安装路径或 plugin cache 调用彼此。
- PRD、spec 或 plan 发生实质修改后，原有批准状态失效，必须重新评审或确认。
- 缺失、未知或无法验证的批准状态不得推断为已批准。
- 受控实施 skill 不读取或调用其它 skill；它只依据用户批准、当前会话范围卡和目标仓库证据执行。

## 交接记录

PRD 阶段固定报告 requirements 八字段。spec/plan 阶段校验并保留这些字段，再报告 requirements、spec、plan 和双门状态共十四字段。prompt 阶段保留显式 spec/plan 路径与评审状态，使下一会话可以从文件证据恢复，而不是依赖聊天记忆。

具体字段和文档模板以各 skill 的 `SKILL.md`、`references/` 与 `assets/` 为准；公共契约变化必须同时更新上下游集成测试。

## 评估证据

`evaluations/` 只保存脱敏后的固定场景、判据和选中证据。可能包含用户上下文、原始 trace、stderr、task/thread 标识符或本机路径的材料只保存在被 `.gitignore` 排除的 `work/` 中。
