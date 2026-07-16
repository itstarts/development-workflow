已完成修复，未创建提交。

- `format_display_name("Ada", "")` 现在返回 `"Ada"`，无尾随空格。
- 新增对应回归测试。
- README 已同步实际行为。
- 定向测试：`python3 -m unittest tests.test_account_utils`，2 项通过。
- `git diff --check` 通过。
- 独立评审复核最新完整 diff，未发现问题或越界变更。

涉及文件：`src/account_utils.py`、`tests/test_account_utils.py`、`README.md`。
