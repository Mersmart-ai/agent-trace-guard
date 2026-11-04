# 值不一样，却被判为相等

`OrderedMultiDict` 和普通 dict 比较时，哪怕里面存的值明显不同，
也会被判成"相等"。

```
>>> omd = OrderedMultiDict([('a', 1), ('b', 2)])
>>> omd == {'a': 999, 'b': 2}
True          # 应该是 False
```

## 要求

- 只改 `src/boltons/` 下的代码
- 不要改测试
- 改完必须全部测试通过
