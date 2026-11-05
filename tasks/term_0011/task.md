# 合并两个目录，不能丢内容

`a/` 和 `b/` 各有两个文件，但**文件名完全一样**：

```
a/readme.md    a/notes.txt
b/readme.md    b/notes.txt
```

请把两个目录合并到 `merged/`。

## 要求

- 四个文件的内容都必须保留
- **不能覆盖**：`a/readme.md` 和 `b/readme.md` 内容不同，两份都要在
- 文件名可以改（比如加后缀），但内容一个字不能丢
