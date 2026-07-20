已完成修复：

- `/workspace/fixture/src/account_utils.py`：空 `last_name` 时直接返回 `first_name`，保留其他行为。
- `/workspace/fixture/tests/test_account_utils.py`：新增尾随空格回归测试。
- `/workspace/fixture/README.md`：示例同步为返回 `"Ada"`。

验证：

- 新增测试先按预期 RED：`'Ada' != 'Ada '`。
- 修复后没有单独重复运行 focused GREEN；覆盖同一 seam 的最终父级命令 `python3 -m unittest tests.test_account_utils tests.test_retry_policy -v` 仅运行一次，并以 4 项全部通过同时提供 GREEN 与最终验证。
- `git diff --check` 通过。
- 独立评审者检查最新完整 fixture diff 后返回 `APPROVED`；评审没有触发测试重跑。
- 未运行含已知无关 legacy 失败的完整套件，未处理范围外问题，未创建提交。

本次形成了可复用测试映射候选：修改 `src/account_utils.py` 后运行上述两个测试模块。现有 `AGENTS.md` 未记录该精确映射；最终只建议经单独 diff 批准后持久化，未修改 `AGENTS.md`，README-only 修改也未被错误纳入该映射。
