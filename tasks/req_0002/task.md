# no_proxy 的匹配范围太宽

设了 `no_proxy=localhost` 之后，访问 `http://prelocalhost/` 也被当成了"不走代理"。

但 `prelocalhost` 和 `localhost` 是两个无关的域名，不该被匹配。

正确的边界是：

- `localhost` 本身 → 匹配
- `foo.localhost`（子域）→ 匹配
- `prelocalhost`（只是结尾碰巧一样）→ **不匹配**

## 要求

- 只改 `src/requests/` 下的代码
- 不要改测试
- 改完必须全部测试通过
