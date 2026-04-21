# Linux 基础入门教案
### 视觉组内部培训 · 主讲人教学用文档

---

## 📋 课程信息

| 项目 | 内容 |
|------|------|
| 课程名称 | Linux 基础入门 |
| 适用对象 | 视觉组新成员（零基础或初学者） |
| 建议时长 | 3 ~ 4 小时（含练习） |
| 授课形式 | 讲解 + 现场演示 + 跟做练习 |
| 所需环境 | 已安装 Linux 系统或 WSL2 / SSH 连接到服务器 |

---

## 🗂️ 课程目录

1. [Linux 文件系统](#一linux-文件系统)
2. [文件权限](#二文件权限)
3. [常用指令](#三常用指令)
4. [Vim 编辑器](#四vim-编辑器)
5. [代码编译](#五代码编译)

---

## 一、Linux 文件系统

### 📌 教学目标

- 理解 Linux 一切皆文件的设计思想
- 掌握目录树结构及各顶层目录的含义
- 能够使用路径（绝对/相对）定位文件

---

### 1.1 讲课内容


#### 🌳 目录树结构

Linux 文件系统是一个**倒置的树状结构**，根目录为 `/`。

```
/
├── bin        → 基础命令（ls, cp, mv 等）
├── boot       → 启动文件（内核）
├── dev        → 设备文件（硬盘、USB 等）
├── etc        → 系统配置文件
├── home       → 用户家目录（/home/alice, /home/bob）
├── lib        → 系统库文件
├── media      → 可移动设备挂载点
├── mnt        → 临时挂载点
├── opt        → 第三方软件
├── proc       → 进程/内核虚拟文件系统（不是真实文件）
├── root       → root 用户的家目录
├── sbin       → 系统管理命令（需 root）
├── tmp        → 临时文件（重启后清空）
├── usr        → 用户程序（/usr/bin, /usr/lib）
└── var        → 可变数据（日志、缓存）
```

---

#### 📍 绝对路径 vs 相对路径

| 类型 | 说明 | 示例 |
|------|------|------|
| 绝对路径 | 从根目录 `/` 开始 | `/home/alice/project/main.c` |
| 相对路径 | 从当前位置开始 | `../project/main.c` |

**常用特殊路径符号：**

```python
~       # 当前用户的家目录，等价于 /home/用户名
.       # 当前目录
..      # 上一级目录
-       # 上一次所在目录（配合 cd 使用）
```

---

#### 🔍 演示操作（跟做）

```bash
# 查看当前所在位置
pwd

# 切换到根目录并查看
cd /
ls

# 切换到家目录
cd ~
pwd

# 使用绝对路径切换
cd /etc

# 使用相对路径切换（回到上一层）
cd ..

# 切换回上一次的目录
cd -
```

---

### 1.2 小练习

> 1. 打开终端，用 `pwd` 确认自己在哪里
> 2. 用绝对路径进入 `/tmp` 目录
> 3. 用相对路径回到家目录
> 4. 查看 `/etc` 下有哪些文件

---

## 二、文件权限

### 📌 教学目标

- 看懂 `ls -l` 输出的权限字段
- 理解用户/组/其他的三级权限模型
- 能使用 `chmod`、`chown` 修改权限

---

### 2.1 讲课内容


#### 🔐 权限字段解读

执行 `ls -l`，会看到类似：

```
-rwxr-xr-- 1 alice devteam 4096 Apr 10 10:30 script.sh
drwxr-xr-x 2 alice devteam 4096 Apr 10 10:00 project/
```

**字段分解：**

```
- r w x  r - x  r - -
│ │───│  │───│  │───│
│ 用户权限  组权限   其他权限
│
└── 文件类型：- 普通文件，d 目录，l 软链接
```

| 字符 | 含义 |
|------|------|
| `r` | 读（read） |
| `w` | 写（write） |
| `x` | 执行（execute） |
| `-` | 无此权限 |

---

#### 🔢 数字权限（八进制）

| 权限 | 二进制 | 数字 |
|------|--------|------|
| `rwx` | 111 | 7 |
| `rw-` | 110 | 6 |
| `r-x` | 101 | 5 |
| `r--` | 100 | 4 |
| `---` | 000 | 0 |

**示例：`chmod 755 file`**

```
7 = rwx  → 用户（自己）：可读可写可执行
5 = r-x  → 组：可读可执行
5 = r-x  → 其他人：可读可执行
```

**常用权限速查：**

```bash
chmod 644 file.txt    # 标准文件：自己读写，他人只读
chmod 755 script.sh   # 可执行脚本：自己全权，他人可读可执行
chmod 700 secret/     # 私有目录：只有自己能访问
chmod 777 shared/     # 全开放（不推荐，仅调试用）
```

---

#### 🔧 修改权限与归属

```bash
# 修改文件权限（数字方式）
chmod 755 script.sh

# 修改文件权限（符号方式）
chmod u+x script.sh      # 给用户加执行权限
chmod g-w file.txt       # 去掉组的写权限
chmod o=r file.txt       # 设置其他人只有读权限
chmod a+r file.txt       # 所有人都加读权限（a = all）

# 修改文件所有者
chown alice file.txt

# 修改文件所属组
chown alice:devteam file.txt

# 递归修改整个目录
chmod -R 755 project/
chown -R alice:devteam project/
```

---

#### 📝 演示操作（跟做）

```bash
# 创建一个脚本文件
echo '#!/bin/bash' > hello.sh
echo 'echo "Hello, Linux!"' >> hello.sh

# 查看当前权限
ls -l hello.sh

# 尝试运行（会失败）
./hello.sh

# 添加执行权限
chmod +x hello.sh

# 再次运行（成功）
./hello.sh

# 查看修改后的权限
ls -l hello.sh
```


---

## 三、常用指令

### 📌 教学目标

- 掌握文件操作类指令（增删改查）
- 掌握文本查看与处理类指令
- 掌握进程与系统信息类指令
- 能组合使用管道和重定向

---

### 3.1 文件与目录操作

#### 📁 目录操作

```bash
# 列出文件（常用参数）
ls              # 列出当前目录
ls -l           # 详细信息（权限、大小、时间）
ls -a           # 显示隐藏文件（以 . 开头的文件）
ls -lh          # 人类可读的文件大小（KB、MB）
ls -lt          # 按时间排序
ls /path/to/dir # 列出指定目录

# 切换目录
cd /path        # 进入指定路径
cd ~            # 回到家目录
cd ..           # 返回上一级
cd -            # 切换到上次所在目录

# 创建目录
mkdir mydir           # 创建单个目录
mkdir -p a/b/c        # 递归创建多级目录

# 删除目录
rmdir emptydir        # 只能删除空目录
rm -r mydir           # 递归删除目录及其内容
rm -rf mydir          # 强制递归删除（⚠️ 慎用，不可恢复）
```

---

#### 📄 文件操作

```bash
# 创建文件
touch newfile.txt       # 创建空文件（或更新时间戳）
echo "hello" > a.txt    # 写入内容（覆盖）
echo "world" >> a.txt   # 追加内容

# 复制文件/目录
cp source.txt dest.txt      # 复制文件
cp -r src_dir/ dest_dir/    # 递归复制目录

# 移动/重命名
mv old.txt new.txt          # 重命名文件
mv file.txt /tmp/           # 移动文件到另一目录

# 删除文件
rm file.txt                 # 删除文件
rm -i file.txt              # 删除前询问确认（推荐加 -i 养成习惯）

# 查看文件信息
file image.png              # 查看文件类型
stat file.txt               # 查看详细元信息
du -sh mydir/               # 查看目录占用空间
```

---

### 3.2 文本查看与处理

```bash
# 查看文件内容
cat file.txt            # 直接输出全部内容
less file.txt           # 分页查看（q 退出，/ 搜索）
head -n 20 file.txt     # 查看前 20 行
tail -n 20 file.txt     # 查看后 20 行
tail -f log.txt         # 实时跟踪文件末尾（看日志很有用）

# 搜索文本
grep "keyword" file.txt         # 在文件中搜索关键词
grep -r "keyword" ./project/    # 递归搜索目录
grep -n "keyword" file.txt      # 显示行号
grep -i "keyword" file.txt      # 忽略大小写
grep -v "keyword" file.txt      # 显示不匹配的行

# 查找文件
find . -name "*.c"              # 在当前目录查找 .c 文件
find /home -name "test*"        # 在 /home 下查找 test 开头的文件
find . -type d -name "build"    # 查找名为 build 的目录
find . -size +1M                # 查找大于 1MB 的文件

# 统计
wc -l file.txt          # 统计行数
wc -w file.txt          # 统计单词数
```

---

### 3.3 管道与重定向(看情况讲)

```bash
# 重定向
command > file.txt    # 将输出写入文件（覆盖）
command >> file.txt   # 将输出追加到文件
command 2> err.txt    # 将错误输出写入文件
command &> all.txt    # 将标准输出和错误都写入文件

# 管道（|）：将前一个命令的输出作为后一个命令的输入
ls -l | grep ".c"           # 列出当前目录中的 .c 文件
cat file.txt | wc -l        # 统计文件行数
ps aux | grep python        # 查找 python 进程
cat /etc/passwd | sort      # 排序输出
```

**实用组合示例：**

```bash
# 查找当前目录下所有 .c 文件并统计数量
find . -name "*.c" | wc -l

# 查看占用空间最大的 5 个文件
du -sh * | sort -rh | head -5

# 查看系统中包含 "error" 的日志行
grep -r "error" /var/log/ 2>/dev/null | less
```

---

### 3.4 进程与系统信息（看情况）

```bash
# 查看进程
ps aux              # 查看所有进程
ps aux | grep vim   # 查找指定进程
top                 # 动态查看进程（q 退出）
htop                # 更友好的 top（需安装）

# 终止进程
kill PID            # 发送 SIGTERM 信号（正常终止）
kill -9 PID         # 发送 SIGKILL 强制终止
killall python      # 终止所有名为 python 的进程

# 系统信息
uname -a            # 系统和内核信息
df -h               # 磁盘使用情况
free -h             # 内存使用情况
uptime              # 系统运行时间和负载

# 网络
ping google.com     # 测试网络连通性
ifconfig / ip addr  # 查看网络接口信息
```

---

### 3.5 其他实用命令

```bash
# 软件包管理（Ubuntu/Debian）
sudo apt update             # 更新软件列表
sudo apt install vim        # 安装软件
sudo apt remove vim         # 卸载软件

# 帮助
man ls          # 查看 ls 的完整手册
ls --help       # 查看简要帮助
type ls         # 查看命令类型

# 历史与快捷键
history         # 查看历史命令
!!              # 重复上一条命令
!grep           # 重复上一条以 grep 开头的命令

# 好用的快捷键
Ctrl + C        # 中断当前命令
Ctrl + Z        # 暂停当前命令（后台挂起）
Ctrl + L        # 清屏（等同于 clear）
Ctrl + A        # 光标移到行首
Ctrl + E        # 光标移到行尾
Tab             # 自动补全
↑ / ↓           # 翻历史命令
```

---

### 3.6 综合练习

> 按顺序完成以下操作：
>
> 1. 在家目录创建 `linux_practice/` 目录，在里面创建 `src/` 和 `log/` 两个子目录
> 2. 在 `src/` 里用 `echo` 创建 `hello.c`，写入一行内容
> 3. 用 `cp` 把 `hello.c` 复制到 `log/` 下
> 4. 用 `grep` 在 `src/` 中搜索你写入的内容
> 5. 用 `find` 找出 `linux_practice/` 下所有 `.c` 文件
> 6. 用管道统计一共有几个 `.c` 文件

---

## 四、Vim 编辑器

### 📌 教学目标

- 理解 Vim 的模式系统
- 掌握基本的移动、编辑、保存操作
- 能独立在 Vim 中完成一次完整的编辑任务

---

### 4.1 讲课内容

#### 🧠 引入（5 分钟）

> **讲课要点：**
> "为什么要学 Vim？当你 SSH 登录到服务器，没有图形界面，只能用终端编辑文件，这时候 Vim 就是你最重要的工具。很多人第一次打开 Vim 连怎么退出都不知道——我们今天把这个痛苦一次性解决掉。"

---

#### 🧩 Vim 的三种模式

Vim 是**模态编辑器**，不同模式下按键含义完全不同：

```
┌─────────────────────────────────────────────┐
│                                             │
│   普通模式 (Normal)                          │
│   启动默认进入 / Esc 返回                     │
│   ↕ i / a / o / I / A / O                   │
│                                             │
│   插入模式 (Insert)                          │
│   像普通编辑器一样输入文字                     │
│   ↕ : (冒号)                                │
│                                             │
│   命令行模式 (Command)                        │
│   输入 :w :q :wq 等命令                      │
│                                             │
└─────────────────────────────────────────────┘
```

> **讲课要点：**
> 反复强调：**Esc 是回到普通模式的万能键**。遇到任何问题，先按 Esc，再想下一步。

---

#### 🚀 快速上手流程

```bash
# 打开文件
vim filename.txt

# 如果文件不存在，会新建一个
vim newfile.c
```

---

#### ✏️ 进入插入模式的几种方式

| 按键 | 进入位置 |
|------|---------|
| `i` | 光标前插入 |
| `a` | 光标后插入 |
| `o` | 在当前行下方新开一行 |
| `O` | 在当前行上方新开一行 |
| `I` | 在行首插入 |
| `A` | 在行尾插入 |

---

#### 🔄 普通模式下的移动

```
基本移动（可用方向键，也可用 hjkl）：
  h  ←    j  ↓    k  ↑    l  →

单词跳转：
  w   跳到下一个单词开头
  b   跳到上一个单词开头
  e   跳到当前单词结尾

行内跳转：
  0   跳到行首
  ^   跳到行首第一个非空字符
  $   跳到行尾

文件跳转：
  gg  跳到文件第一行
  G   跳到文件最后一行
  :n  跳到第 n 行（如 :42 跳到第 42 行）
```

---

#### ✂️ 普通模式下的编辑

```
删除：
  x     删除光标所在字符
  dd    删除（剪切）当前行
  dw    删除当前单词
  d$    删除从光标到行尾
  3dd   删除 3 行

复制粘贴：
  yy    复制当前行
  3yy   复制 3 行
  yw    复制当前单词
  p     粘贴到光标后
  P     粘贴到光标前

撤销与重做：
  u       撤销（Undo）
  Ctrl+r  重做（Redo）

修改：
  r   替换光标处单个字符
  cw  删除当前单词并进入插入模式
  cc  删除整行并进入插入模式

```

---

#### 🔍 搜索与替换

```vim
# 搜索
/keyword    向下搜索 keyword（Enter 确认）
?keyword    向上搜索
n           跳到下一个匹配
N           跳到上一个匹配

# 替换（在命令行模式）
:s/old/new/         替换当前行第一个匹配
:s/old/new/g        替换当前行所有匹配
:%s/old/new/g       替换全文所有匹配
:%s/old/new/gc      替换全文，每次询问确认
```

---

#### 💾 保存与退出

```vim
:w          保存文件
:q          退出（文件未修改时）
:wq         保存并退出（常用！）
:q!         强制退出，不保存
:wq!        强制保存并退出（只读文件需要）

# 快捷方式
ZZ          等价于 :wq
ZQ          等价于 :q!
```

---

#### ⚙️ 实用设置（临时）

```vim
:set number         # 显示行号
:set nonumber       # 关闭行号
:set tabstop=4      # Tab 显示为 4 格
:set autoindent     # 自动缩进
:set hlsearch       # 高亮搜索结果
:set nohlsearch     # 关闭高亮
```

> **讲课要点：**
> 可以介绍 `~/.vimrc` 配置文件，让设置永久生效。现场演示在 `~/.vimrc` 中加入 `set number` 后重新打开 Vim 的效果。

---

#### 📝 演示操作（完整流程，跟做）

```bash
# 1. 打开一个新文件
vim practice.txt

# 2. 进入插入模式，输入几行内容
# 按 i，然后输入：
# Hello, this is Vim!
# I am learning Linux.
# This is line 3.

# 3. 按 Esc 回到普通模式

# 4. 跳到第一行：gg

# 5. 搜索 "Linux"：/Linux，按 Enter

# 6. 将 "Linux" 替换为 "Vim"：
# :%s/Linux/Vim/g

# 7. 复制第 2 行并粘贴到第 3 行后：
# 2G → yy → G → p

# 8. 保存并退出
# :wq
```

---

### 4.2 Vim 速查卡（可打印）

```
┌─────────────────────────────────────────────────────┐
│                   VIM 速查卡                         │
├──────────────┬──────────────────────────────────────┤
│  模式切换    │ i/a/o 进插入  Esc 返回普通  : 命令行  │
├──────────────┼──────────────────────────────────────┤
│  移动        │ hjkl gg G 0 $ w b                     │
├──────────────┼──────────────────────────────────────┤
│  删除        │ x dd dw d$ (数字前缀倍增)              │
├──────────────┼──────────────────────────────────────┤
│  复制粘贴    │ yy yw  p P                            │
├──────────────┼──────────────────────────────────────┤
│  撤销重做    │ u  Ctrl+r                             │
├──────────────┼──────────────────────────────────────┤
│  搜索替换    │ /xxx  :%s/old/new/g                   │
├──────────────┼──────────────────────────────────────┤
│  保存退出    │ :w  :q  :wq  :q!  ZZ                  │
└──────────────┴──────────────────────────────────────┘
```

---

### 4.3 小练习

> 1. 用 Vim 新建一个文件 `note.txt`，写入至少 5 行内容
> 2. 使用搜索功能找到某个单词
> 3. 用替换命令把该单词全部替换为另一个词
> 4. 删除第 2 行，然后撤销这次删除
> 5. 保存并退出

---

## 五、代码编译

### 📌 教学目标

- 理解编译的基本概念和流程
- 能用 `gcc` 编译 C/C++ 程序并运行
- 了解 Makefile 的基本用法
- 能处理基本的编译错误

---

### 5.1 讲课内容

#### 🧠 引入（3 分钟）

> **讲课要点：**
> "我们写的 C/C++ 源代码，计算机看不懂，需要**编译器**把它翻译成机器码。Linux 上最主流的编译工具是 GCC。我们来学一下从写代码到运行的完整流程。"

---

#### 🔄 编译的四个阶段

```
源代码 (.c)
    ↓  预处理（cpp）：展开宏、头文件
预处理文件 (.i)
    ↓  编译（cc1）：生成汇编代码
汇编文件 (.s)
    ↓  汇编（as）：生成目标文件
目标文件 (.o)
    ↓  链接（ld）：链接库，生成可执行文件
可执行文件（a.out 或自定义名）
```

> **讲课要点：**
> 实际工作中通常一条 `gcc` 命令完成所有步骤，但理解这四个阶段有助于排查错误。

---

#### 🛠️ GCC 基本用法

```bash
# 安装 gcc（如果没有）
sudo apt install gcc g++

# 查看版本
gcc --version

# ─────────────────────────────
# 最简单的编译
gcc hello.c                  # 输出为 a.out
./a.out                      # 运行

# 指定输出文件名（-o）
gcc hello.c -o hello
./hello

# 编译 C++ 程序
g++ hello.cpp -o hello
./hello
```

---

#### 📄 完整演示代码

先用 Vim 创建以下 C 程序（结合上一章练习）：

**hello.c**
```c
#include <stdio.h>

int main() {
    printf("Hello, Linux!\n");
    printf("Welcome to the Visual Group.\n");
    return 0;
}
```

```bash
# 编译并运行
gcc hello.c -o hello
./hello
```

**带参数的程序 args.c**
```c
#include <stdio.h>

int main(int argc, char *argv[]) {
    printf("共有 %d 个参数\n", argc);
    for (int i = 0; i < argc; i++) {
        printf("argv[%d] = %s\n", i, argv[i]);
    }
    return 0;
}
```

```bash
gcc args.c -o args
./args hello world 123
```

---

#### ⚙️ 常用编译选项

```bash
# 开启警告信息（强烈推荐）
gcc -Wall hello.c -o hello
gcc -Wall -Wextra hello.c -o hello

# 开启调试信息（方便用 gdb 调试）
gcc -g hello.c -o hello

# 优化选项
gcc -O0 hello.c -o hello    # 不优化（默认）
gcc -O1 hello.c -o hello    # 轻度优化
gcc -O2 hello.c -o hello    # 推荐优化级别
gcc -O3 hello.c -o hello    # 最大优化

# 指定 C 标准
gcc -std=c11 hello.c -o hello
gcc -std=c99 hello.c -o hello

# 链接数学库（使用 math.h 时需要）
gcc calc.c -o calc -lm

# 多文件编译
gcc main.c utils.c -o program

# 分步编译（先编译为目标文件，再链接）
gcc -c main.c -o main.o
gcc -c utils.c -o utils.o
gcc main.o utils.o -o program
```

---

#### 🗂️ 多文件项目结构

**项目结构示例：**

```
project/
├── main.c
├── math_utils.c
└── math_utils.h
```

**math_utils.h**
```c
#ifndef MATH_UTILS_H
#define MATH_UTILS_H

int add(int a, int b);
int multiply(int a, int b);

#endif
```

**math_utils.c**
```c
#include "math_utils.h"

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}
```

**main.c**
```c
#include <stdio.h>
#include "math_utils.h"

int main() {
    printf("3 + 4 = %d\n", add(3, 4));
    printf("3 * 4 = %d\n", multiply(3, 4));
    return 0;
}
```

```bash
# 编译多文件项目
gcc main.c math_utils.c -o calculator
./calculator
```

---

#### 📦 Makefile 入门

当项目文件变多，手动输入 `gcc` 命令会很麻烦，**Makefile** 可以自动化这个过程。

**基本语法：**

```makefile
目标: 依赖文件
[Tab键] 编译命令
```

**示例 Makefile：**

```makefile
# 变量定义
CC = gcc
CFLAGS = -Wall -O2

# 默认目标（make 不带参数时执行）
all: calculator

# 生成最终可执行文件
calculator: main.o math_utils.o
	$(CC) main.o math_utils.o -o calculator

# 编译各目标文件
main.o: main.c math_utils.h
	$(CC) $(CFLAGS) -c main.c -o main.o

math_utils.o: math_utils.c math_utils.h
	$(CC) $(CFLAGS) -c math_utils.c -o math_utils.o

# 清理编译产物
clean:
	rm -f *.o calculator
```

```bash
# 使用 Makefile
make            # 编译整个项目
make clean      # 清除编译产物
make calculator # 只编译 calculator 目标
```

> **讲课要点：**
> 强调 Makefile 中命令行前面**必须是 Tab 键**，不能是空格，否则会报错。

---

#### 🐛 读懂编译错误

```bash
# 示例：忘记写分号
# error: expected ';' before 'return'
#   → 找到报错的行号，检查上一行结尾

# 示例：变量未声明
# error: 'x' undeclared (first use in this function)
#   → 检查变量名拼写，或者是否在使用前声明了

# 示例：函数未定义
# undefined reference to 'add'
#   → 检查是否链接了对应的 .c 文件或库

# 示例：头文件找不到
# fatal error: math_utils.h: No such file or directory
#   → 检查头文件路径是否正确

# 加 -Wall 让编译器给出更多警告
gcc -Wall main.c -o main
```

> **讲课要点：**
> 让学弟学妹故意写一个有错误的程序，看报错信息，然后找到错误并修正。这是培养独立调试能力最直接的方式。

---

### 5.2 综合实战练习

> 完成以下完整项目：
>
> **任务：** 编写一个简单计算器程序
>
> 1. 用 Vim 创建 `calculator.c`，实现加减乘除四种运算，接收命令行参数 `./calc 10 + 3`
> 2. 编译时加上 `-Wall` 选项
> 3. 运行并测试所有运算
> 4. 编写 `Makefile`，让 `make` 自动完成编译，`make clean` 清理文件
>
> **参考程序结构：**
> ```c
> // ./calc 10 + 3
> // 输出：10 + 3 = 13
> #include <stdio.h>
> #include <stdlib.h>
>
> int main(int argc, char *argv[]) {
>     if (argc != 4) {
>         printf("用法: %s <数字> <运算符> <数字>\n", argv[0]);
>         return 1;
>     }
>     double a = atof(argv[1]);
>     double b = atof(argv[3]);
>     char op = argv[2][0];
>     // 补全 switch 分支...
>     return 0;
> }
> ```

---

## 📝 课后总结

### 知识点回顾

| 模块 | 核心掌握点 |
|------|-----------|
| 文件系统 | 目录树结构、绝对/相对路径、常用目录含义 |
| 文件权限 | rwx 三级权限、chmod 数字/符号方式、chown |
| 常用指令 | ls/cd/cp/mv/rm、grep/find、管道/重定向 |
| Vim | 三种模式切换、基本移动编辑、保存退出 |
| 代码编译 | gcc 基本用法、常用编译选项、Makefile 基础 |

---

### 推荐学习资源

- **命令行练习：** `vimtutor`（终端直接输入，Vim 官方教程）
- **Linux 文档：** `man <命令名>`（本地手册）
- **在线平台：**
  - [Linux Command（linuxcommand.org）](http://linuxcommand.org)
  - [OverTheWire Bandit](https://overthewire.org/wargames/bandit/)（趣味关卡式学习）
  - [explainshell.com](https://explainshell.com)（粘贴命令即可解释每个参数）

---

### 给主讲人的建议

1. **每个章节先演示，再让学员跟做**，不要一口气讲完才演示
2. 准备一台已经配好环境的机器作为**备用演示机**，防止临时环境问题
3. 遇到学员问"为什么要这样做"，优先用**实际场景**回答而不是技术原理
4. 多用 **Tab 自动补全**，让学员看到这个功能有多方便
5. 课程结束前留 **10 分钟 Q&A**，鼓励提问

---

*教案版本：v1.0 | 制作日期：2026年4月*