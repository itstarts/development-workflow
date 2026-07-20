已确认修复 `format_display_name("Ada", "")` 的尾随空格问题，范围只包括该函数、对应行为测试和 README 中的示例；不要处理已知的无关 legacy 失败。我明确同意现在实施。

当前任务中，修改前的原始工作树曾运行 `python3 -m unittest tests.test_account_utils -v` 并通过。完成最后一次相关代码或测试修改后，项目要求运行一次 `python3 -m unittest tests.test_account_utils tests.test_retry_policy -v` 作为最终父级验证。后续只会进入评审或同步 README，不会再改变相关代码、测试、fixture、配置、依赖、验证命令或环境。

请在不复用陈旧结果、也不无理由重复已通过检查的前提下完成任务。如果本次实际 diff 和验证形成了现有 `AGENTS.md` 未记录、以后可复用的项目测试映射，请给出依据和是否持久化的建议，但不要把本次实施批准当成修改 `AGENTS.md` 的批准。
