# Fixture engineering rules

- 当独立 route handoff 与已批准 PRD 正文都可靠且一致为 `standard` 时，完整 spec 可以在用户批准前生成 plan，当前 spec 与 plan 必须由同一位 package reviewer 统一评审；spec 用户批准前实施门保持关闭。
- 未改变正文的 spec 用户批准只同步 spec 与 plan 的批准元数据，不使 package review 失效。
- material spec change 使 spec review、spec 用户批准和 plan review 失效；material plan-only change 只使 plan review 失效。
- 未经明确要求不提交代码，不创建或操作用户可见 task/thread。
