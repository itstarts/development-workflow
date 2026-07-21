```text
开发目标：依据已批准的需求文档 /workspace/fixture/docs/requirements/2026-07-17-example.md、已批准技术规格与已评审计划，实施可验证的示例功能：通过现有公共接口实现并保持兼容。先完整读取需求文档，并将其已批准范围作为实施和独立评审的上限。对于评审中超出需求的建议，明确标记为范围外，单独报告且不实施，除非用户另行批准扩围。修复范围内发现后，由同一独立评审者针对修复后的最新完整 diff 及受影响范围复审，验证原发现与相关回归风险；复审不得借机扩大已批准需求范围，并按提示词规定直至 APPROVED 或达到停止条件。

开发目标与来源文档
规格：/workspace/fixture/docs/specs/2026-07-17-example-design.md（来源：explicit）
计划：/workspace/fixture/docs/plans/2026-07-17-example.md（来源：explicit；评审：approved）

规则与文档优先级
- /workspace/fixture/AGENTS.md（来源：filesystem；优先级：0）
先完整读取规格、计划和所有适用的 AGENTS.md，再做任何修改。实施前核对文档路径、适用规则与计划评审状态。

主代理执行合同
按照计划和适用的仓库规则实施，不擅自扩大范围或修改未授权的公共契约。每项任务使用 TDD，完成与影响范围匹配的验证。

完成条件与报告
全部计划任务完成并集成后，先运行完整的相关验证，再由一名未参与实现的独立评审者对最新完整 diff 执行整体评审。发现范围内问题时，修复范围内发现、重跑受影响验证，再由同一评审者复审变更后的完整 diff。获得 APPROVED 后停止。
```

The valid current-skill run repeated the user-supplied scope ceiling in the generated goal, but the reusable execution contract still had no `BLOCKING_IN_SCOPE`, `SCOPE_CHANGE_REQUIRED`, or `NON_BLOCKING_NOTE` classification, no mandatory basis and minimum in-scope correction per finding, and no delta-only re-review rule. It still directed the implementer to fix all vaguely defined in-scope findings and re-review the complete diff.
