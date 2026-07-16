修复已完成：

- `src/account_utils.py`：空姓氏时直接返回名字，非空姓名行为和函数签名保持不变。
- `tests/test_account_utils.py`：新增空姓氏回归测试。
- `README.md`：同步正确示例。

验证结果：`python3 -m unittest tests.test_account_utils`，2 项测试全部通过；`git diff --check` 通过。未运行完整测试套件，未处理其他问题，也未创建提交。
