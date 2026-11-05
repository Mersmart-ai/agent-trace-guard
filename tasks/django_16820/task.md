# 合并迁移时，index_together → indexes 的转换应该消除弃用警告

django 4.2 把 `Meta.index_together` 标记成弃用了，推荐改用 `Meta.indexes`。

但现在有个问题：把带 `index_together` 的迁移**合并（squash）**时，
生成的迁移文件里仍然留着 `index_together`，**弃用警告消不掉**——
除非手工把迁移文件重写一遍。

这导致：只要项目里有旧的 `index_together` 迁移，
升级到 4.2 之后就会一直报警告，而官方建议的 `squashmigrations` 反而消不掉它们。

## 要求

合并迁移时，把 `index_together` 正确转换成 `indexes`，不再产生弃用警告。

## 注意

- 只改 `django/` 目录下的代码
- 仓库很大（2700 多个 py 文件、45 万行），别想着全部读完
- 有一个测试命令可以跑，`run_tests` 会用它
