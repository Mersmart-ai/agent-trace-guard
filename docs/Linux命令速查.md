# Linux / Git Bash 常用命令速查

> 用途：记不住的时候对着看。
> 全部在 Git Bash 里验证过（Windows 11）。
> 学会这些，以后上 Linux 服务器原样能用。

---

# 0. 先分清三层

```
终端（Terminal）    一个窗口，本身什么都不会
    ↓ 里面跑着
Shell（壳）         读懂你打的字，然后执行
    ↓ 你打的是
命令                具体干活的程序
```

**Windows 上有三种 Shell：**

| Shell | 例子 | 特点 |
|---|---|---|
| `cmd.exe` | `dir` `copy` `del` | 最老，命令最少 |
| `PowerShell` | `Get-ChildItem` `Copy-Item` | 微软新的，也能用 `ls`（别名） |
| **Bash**（Git Bash） | `ls` `cp` `rm` | **Unix 风格，和 Linux 服务器一样** |

**所以：Git Bash ≠ Linux，但命令语法一样。**

---

# 1. 文件与目录

| 命令 | 作用 | 例子 |
|---|---|---|
| `pwd` | 我在哪个目录 | `pwd` |
| `ls` | 列出文件 | `ls` |
| `ls -l` | 详细列表（权限、大小、时间） | `ls -l` |
| `ls -a` | 含隐藏文件（`.` 开头的） | `ls -a` |
| `ls -R` | **递归**列出子目录（大写 R） | `ls -R` |
| `cd 目录` | 进目录 | `cd fbs` |
| `cd ..` | 退回上一级 | `cd ..` |
| `cd ~` | 回到家目录 | `cd ~` |
| `cd -` | 回到上一次的目录 | `cd -` |
| `mkdir 名字` | 建目录 | `mkdir demo` |
| `mkdir -p a/b/c` | 建多层（父目录不存在就一起建） | `mkdir -p a/b/c` |
| `cp 源 目标` | 复制**文件** | `cp a.py b.py` |
| **`cp -r 源 目标`** | 复制**目录**（必须加 `-r`） | `cp -r src/ backup/` |
| `mv 源 目标` | 移动 / 改名 | `mv a.py b.py` |
| `rm 文件` | 删文件 | `rm a.py` |
| `rm -r 目录` | 删目录（**危险，没有回收站**） | `rm -r demo/` |
| `rm -rf 目录` | 强制删，不问确认（**极其危险**） | ❌ 别乱用 |
| `find . -name "*.py"` | 按名字找文件 | `find . -name "*.txt"` |
| `find . -name "*.py" -size +1M` | 找大于 1MB 的 | |

## 常见坑

**① `cp` 复制目录不加 `-r` 会失败**

```bash
$ cp src/ dst/
cp: -r not specified; omitting directory 'src'
```

**② `ls -r` 和 `ls -R` 完全不同**

```bash
ls -r     # 小写 r = reverse，倒序排列
ls -R     # 大写 R = recursive，递归进子目录
```

**③ `rm` 没有回收站**

```bash
rm a.py       # 直接没了，恢复不了
```

**要先确认再删，或者用 `rm -i`（删除前问一句）。**

---

# 2. 查看文件内容

| 命令 | 作用 | 例子 |
|---|---|---|
| `cat 文件` | 全部打印出来 | `cat config.py` |
| `head -20 文件` | 前 20 行（默认 10） | `head -20 agent.py` |
| `tail -20 文件` | 后 20 行 | `tail -20 agent.py` |
| `tail -f 文件` | 实时盯着（看日志用，Ctrl+C 退出） | `tail -f app.log` |
| `wc -l 文件` | 有多少行 | `wc -l agent.py` |
| `wc -c 文件` | 有多少字节 | |
| `less 文件` | 分页看（`q` 退出，`/` 搜索） | `less agent.py` |
| `sort 文件` | 排序 | `sort names.txt` |
| `uniq` | 去重（要先 sort） | `sort a.txt \| uniq` |

**`cat` 少用**——大文件会把终端刷爆。**先 `head` 看几行。**

---

# 3. 搜索（grep）

**`grep` 是这个项目里最有用的命令**——你的 agent 的 `grep` 工具就是照它写的。

| 命令 | 作用 |
|---|---|
| `grep "关键词" 文件` | 在**一个文件**里搜 |
| **`grep -r "关键词" 目录`** | 在**整个目录**里递归搜（最常用） |
| `grep -n "关键词" 文件` | 显示**行号** |
| `grep -rn "关键词" .` | 递归 + 行号（`.` = 当前目录） |
| `grep -i "关键词" 文件` | 忽略大小写 |
| `grep -c "关键词" 文件` | 只数有多少行匹配 |
| `grep -v "关键词" 文件` | **反选**：不包含的行 |
| `grep -l "关键词" *.py` | 只列出**文件名**，不列内容 |
| `grep -A3 "关键词" 文件` | 匹配行 + 后面 3 行 |
| `grep -B3 "关键词" 文件` | 匹配行 + 前面 3 行 |

## 实际例子

```bash
# 找 "test_state" 在所有 py 文件里出现的地方
grep -rn "test_state" fbs/

# 输出：
fbs/trace.py:31:        "test_state": test_state,
fbs/loop.py:57:                test_state = judge_state(run_tests(workspace, tests))
fbs/judge.py:9:    """把 run_tests 的结果翻成 test_state。只有两种取值：
```

**格式 = `文件:行号: 内容`**

**这个格式和你 agent 的 `grep` 工具输出一模一样。**

---

# 4. 管道与重定向

## 管道 `|`

**把前一个命令的输出，喂给后一个命令。**

```bash
ls *.py | wc -l          # 数有多少个 py 文件
cat app.log | grep ERROR # 只看日志里的错误行
ls | grep "test"         # 只列名字含 test 的
ps aux | grep python     # 看有没有 python 进程在跑
```

**`|` 左边是"生产者"，右边是"消费者"。**

## 重定向

| 写法 | 作用 |
|---|---|
| `命令 > 文件` | 输出写进文件（**覆盖**） |
| `命令 >> 文件` | 输出**追加**到文件末尾 |
| `命令 < 文件` | 从文件读输入 |
| `命令 2> 文件` | 把**错误**输出写进文件 |
| `命令 > 文件 2>&1` | 正确和错误**都**写进文件 |
| `命令 2>/dev/null` | 把错误**丢掉**（不显示） |

**例子：**

```bash
echo "hello" > note.txt      # 写进去（覆盖）
echo "world" >> note.txt     # 追加
cat note.txt                 # hello / world

ls 不存在的目录 2>/dev/null   # 什么都不显示（错误被丢掉了）
```

**`2>&1` 是什么意思**：

- `1` = 标准输出（正常结果）
- `2` = 标准错误（报错信息）
- `2>&1` = "把 2 指向 1 去的地方"，也就是**两样都进同一个文件**

---

# 5. 退出码（对 agent 最重要）

**每条命令跑完，都会留一个数字：0 = 成功，非 0 = 失败。**

```bash
ls fbs/
echo $?        # 0

ls 不存在的目录
echo $?        # 2
```

**`$?` 就是"上一条命令的退出码"。**

## 为什么这个最重要

**你的 `run_tests` 就是靠它判断的：**

```python
r = subprocess.run([...])
return {"exit_code": r.returncode, ...}
#                         ↑ 就是 $?
```

**agent 加了 bash 工具之后，也是靠退出码判断"这条命令成没成"。**

**常见退出码：**

| 码 | 意思 |
|---|---|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 用法错误（参数不对） |
| 127 | **命令不存在**（拼错了） |
| 130 | 被 Ctrl+C 中断 |

---

# 6. 权限与压缩

## 权限

```bash
ls -l script.sh
# -rwxr-xr-x  1 user  staff  1234 Nov 4 12:00 script.sh
#  ↑↑↑
#  ||└─ 其他人：r-x（读+执行）
#  |└── 同组：r-x
#  └─── 自己：rwx（读写执行）

chmod +x script.sh      # 加执行权限（最常用）
chmod 644 file.txt      # 自己读写，别人只读
chmod 755 script.sh     # 自己读写执行，别人读执行
```

**`+x` 是最常用的**——脚本没有执行权限就 `./script.sh` 跑不了。

## 压缩

```bash
tar -czf out.tar.gz 目录/     # 打包 + gzip 压缩
tar -xzf out.tar.gz           # 解包
tar -tzf out.tar.gz           # 只看里面有什么，不解压

zip -r out.zip 目录/          # zip 格式
unzip out.zip
```

**`tar` 那几个字母的意思：**

| 字母 | 意思 |
|---|---|
| `c` | **c**reate，创建 |
| `x` | e**x**tract，解压 |
| `z` | g**z**ip，压缩 |
| `f` | **f**ile，后面跟文件名 |
| `t` | lis**t**，列出内容 |

**记不住就记两个：`-czf` 打包，`-xzf` 解包。**

---

# 7. Windows vs Unix 命令对照

**这个表在你搞混的时候用：**

| 干什么 | Windows（cmd） | Unix（Git Bash） |
|---|---|---|
| 列文件 | `dir` | `ls` |
| 复制 | `copy` | `cp` |
| 复制目录 | `xcopy /E` | `cp -r` |
| 移动/改名 | `move` / `ren` | `mv` |
| 删除 | `del` / `rmdir` | `rm` / `rm -r` |
| 看内容 | `type` | `cat` |
| 清屏 | `cls` | `clear` |
| 当前目录 | `cd`（不带参数） | `pwd` |
| 找文件 | `where` | `which` / `find` |
| 搜文本 | `findstr` | `grep` |

---

# 8. Git Bash 的路径写法

**这是最容易卡住的地方。**

| Windows 写法 | Git Bash 写法 |
|---|---|
| `C:\Users\ASUS` | `/c/Users/ASUS` |
| `D:\data` | `/d/data` |

**规律：`C:\` → `/c/`，反斜杠 → 正斜杠。**

**从 Git Bash 打开 Windows 程序：**

```bash
notepad.exe note.txt        # 用记事本打开
explorer.exe .              # 用资源管理器打开当前目录
code .                      # 用 VS Code 打开（如果装了）
```

---

# 9. 常见坑

| 坑 | 现象 | 怎么办 |
|---|---|---|
| `cp` 目录不加 `-r` | `omitting directory` | 加 `-r` |
| `ls -r` 当成递归 | 只倒序了 | 递归是大写 `-R` |
| 路径用 `C:\` | `No such file` | 改成 `/c/` |
| `rm` 没有回收站 | 直接没了 | 先 `ls` 确认，或用 `rm -i` |
| 空格没引号 | 参数被拆开 | `cp "my file.txt" dst/` |
| 文件名有中文 | 可能与编码有关 | 尽量用英文名 |
| 命令不存在 | `command not found`（127） | `which 命令` 看装没装 |
| `cat` 大文件 | 终端刷爆 | 用 `head` / `less` |

---

# 10. 练习清单（30 分钟）

**在项目根目录打开 Git Bash，按顺序敲：**

```bash
# ① 确认位置
pwd
ls

# ② 进目录、看内容
cd fbs
ls -l
head -20 agent.py

# ③ 搜索
grep -n "def main" agent.py
grep -rn "test_state" . | head -5

# ④ 管道
ls *.py | wc -l
ls | grep "judge"

# ⑤ 退出码
ls
echo $?
ls 不存在
echo $?

# ⑥ 退回
cd ..
pwd
```

**做完这 6 组，基本操作就有了。**

---

# 11. 为什么这些和你的项目有关

**你的 agent 现在有 6 个工具，其中 `grep` 就是照本文件第 3 节写的：**

```python
def grep(workspace, pattern, path="."):
    # 相当于 grep -rn pattern path
```

**如果你给 agent 加 `bash` 工具，它就能用这个文件里的所有命令。**

**而"终端任务"的判据，正是靠第 5 节的退出码 + 最终状态检查。**

**所以这个文档不是"额外的知识"，是你项目下一步的基础设施。**

---

# 12. 查这个文件自己

**忘了某条命令，直接搜这个文档：**

```bash
grep -n "tar" docs/Linux命令速查.md
```

**或者用你的 agent 的 grep 工具搜。**
