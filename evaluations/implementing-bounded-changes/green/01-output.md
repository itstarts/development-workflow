修复已完成，未创建提交。

- `src/account_utils.py`：空姓氏时直接返回名字；非空双名字行为及签名不变。
- `tests/test_account_utils.py`：新增空姓氏回归测试。
- `README.md`：示例已同步为返回 `"Ada"`。

验证结果：

- RED：实现前回归测试按预期得到 `'Ada' != 'Ada '`。
- GREEN：`python3 -m unittest tests.test_account_utils`，2 项全部通过。
- `git diff --check` 通过。
- 独立审查者 `diff_reviewer`：`APPROVED`。

按仓库规则未运行含已知无关遗留失败的全量测试，也未处理其他问题。
