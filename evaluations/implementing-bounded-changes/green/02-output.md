已完成，将 `retry_delay` 最大等待时间从 60 秒调整为 30 秒。

改动：

- `src/account_utils.py`：上限改为 30。
- `tests/test_retry_policy.py`：对应封顶测试改为 30 秒。
- `README.md`：同步上限说明。

验证结果：

- RED：修改测试后运行，得到预期失败 `30 != 60`。
- GREEN：`python3 -m unittest tests/test_retry_policy.py`，2 个测试全部通过。
- `git diff --check`：通过。
- 独立审查者 `independent_review`：`APPROVED`，未发现范围偏离或回归风险。

未运行全量测试，因为仓库规则注明其中存在已知无关遗留失败。未修改其他行为，也未创建提交。
