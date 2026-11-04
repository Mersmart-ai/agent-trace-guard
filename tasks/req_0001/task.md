# Content-Type 里参数没有值时，解析结果不对

有些服务器返回的响应头长这样：

```
Content-Type: text/html; charset
```

`charset` 后面没有 `=值`，只有参数名。这时：

- 解析出来的参数字典里，会多出一个值为 `True` 的键
- `get_encoding_from_headers()` 拿不到编码，返回 `None`

按规范，没有值的参数应该被忽略；编码应该退回默认的 `ISO-8859-1`。

## 要求

- 只改 `src/requests/` 下的代码
- 不要改测试
- 改完必须全部测试通过
