# 空列表会把程序搞崩

`mean([])` 直接抛异常，应该返回 `0`。

复现：

```
>>> mean([])
ZeroDivisionError: division by zero      # 期望 0
```

正常输入是好的：

```
>>> mean([2, 4, 6])
4.0
```

## 要求

- 只改 `src/calc.py`
- 不要改测试
- 改完必须全部测试通过
