# 工作流与文档契约

## 三阶段职责

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

## 协作边界

- 用户显式路径优先于默认路径。
- skill 之间只通过文档路径、评审状态和显式输出字段协作。
- skill 不通过相对 import、本机安装路径或 plugin cache 调用彼此。
- PRD、spec 或 plan 发生实质修改后，原有批准状态失效，必须重新评审或确认。
- 缺失、未知或无法验证的批准状态不得推断为已批准。

## 交接记录

PRD 阶段固定报告 requirements 八字段。spec/plan 阶段校验并保留这些字段，再报告 requirements、spec、plan 和双门状态共十四字段。prompt 阶段保留显式 spec/plan 路径与评审状态，使下一会话可以从文件证据恢复，而不是依赖聊天记忆。

具体字段和文档模板以各 skill 的 `SKILL.md`、`references/` 与 `assets/` 为准；公共契约变化必须同时更新上下游集成测试。

## 评估证据

`evaluations/` 只保存脱敏后的固定场景、判据和选中证据。可能包含用户上下文、原始 trace、stderr、task/thread 标识符或本机路径的材料只保存在被 `.gitignore` 排除的 `work/` 中。
