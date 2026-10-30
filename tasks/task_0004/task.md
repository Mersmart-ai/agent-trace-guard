# 报告里的平均值不对

`run()` 返回的 `total` 是对的，`average` 偏小。

复现：

```
>>> from app import run
>>> run()
{'total': 15, 'average': 3.75}      # 期望 average 是 5.0
```

数据是 `[3, 5, 7]`，平均值应该是 5.0。

## 要求

- 只改 `src/` 下的代码
- 不要改测试
- 改完必须全部测试通过
