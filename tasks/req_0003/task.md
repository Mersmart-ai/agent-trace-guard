# netrc 里空的条目被当成了有效凭据

`~/.netrc` 里有这样一条：

```
machine example.com
```

只有 `machine`，没有 `login` 和 `password`。

这时 `get_netrc_auth("https://example.com")` 会返回 `(None, None)`，
而不是 `None`。调用方拿到一个"看着像凭据、实际全是 None"的元组，
后面的认证就失败了。

这种条目应该和"没有这条记录"一样处理——返回 `None`。

## 要求

- 只改 `src/requests/` 下的代码
- 不要改测试
- 改完必须全部测试通过
