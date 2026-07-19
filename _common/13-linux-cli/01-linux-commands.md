# 13.1 Linux 常用命令：`grep` / `awk` / `sed` / `find`

> 掌握 Linux 文本三剑客（grep/awk/sed）和 find 高效查找文件，能在任意代码仓库中快速定位与排查。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `grep` 搜索文件内容
- 用 `find` 定位文件
- 用 `sed` 做流编辑（替换/删除行）
- 用 `awk` 做列提取与统计
- 在代码仓库中组合使用这些命令快速调研与排查

## 📚 前置知识

- 命令行基础（cd、ls、cat）
- 正则表达式基础

## 1. 核心概念

### 1.1 命令的组合哲学

Linux 命令遵循**小而美**原则：
- 每个命令只做一件事
- 通过**管道（`|`）**把多个命令组合
- **文本流**是统一的接口

```bash
# 查找包含 "TODO" 的 Python 文件
grep -r "TODO" --include="*.py" /path/to/code | head -10

# 统计每个 Python 文件的行数并排序
find /path/to/code -name "*.py" | xargs wc -l | sort -n | tail
```

### 1.2 `grep`：文本搜索

```bash
# 基础搜索
grep "pattern" file.txt

# 常用选项
grep -i "pattern" file.txt          # 忽略大小写
grep -r "pattern" /path/to/dir      # 递归搜索目录
grep -n "pattern" file.txt          # 显示行号
grep -l "pattern" *.py              # 只显示文件名
grep -c "pattern" file.txt          # 统计匹配次数
grep -v "pattern" file.txt          # 反向（不匹配的行）
grep -E "pat1|pat2" file.txt        # 扩展正则（多个模式）
grep -A 3 "pattern" file.txt        # 显示匹配后 3 行
grep -B 3 "pattern" file.txt        # 显示匹配前 3 行
grep -C 3 "pattern" file.txt        # 显示匹配前后各 3 行

# 组合：在所有 Python 文件中找含 async def 的行
grep -rn "async def" --include="*.py" /Users/xu/code/github/dify/api/services/
```

### 1.3 `find`：文件查找

```bash
# 按文件名
find /path -name "config.yaml"

# 按扩展名
find /path -name "*.py"

# 按类型
find /path -type f           # 普通文件
find /path -type d           # 目录

# 按大小
find /path -size +10M        # 大于 10MB
find /path -size -1k         # 小于 1KB

# 按修改时间
find /path -mtime -7         # 7 天内修改
find /path -mtime +30        # 30 天前修改

# 执行命令
find /path -name "*.log" -exec rm {} \;       # 删除所有 .log
find /path -name "*.py" -exec wc -l {} \;     # 统计所有 Python 行数

# 组合：找 7 天前的大于 100MB 的日志
find /var/log -name "*.log" -size +100M -mtime +7 -exec ls -lh {} \;
```

### 1.4 `sed`：流编辑器

```bash
# 替换（原地修改）
sed -i 's/old/new/g' file.txt              # 全局替换
sed -i 's/old/new/g' *.txt                 # 所有 txt 文件

# 删除行
sed -i '/pattern/d' file.txt               # 删除匹配行
sed -i '5d' file.txt                       # 删除第 5 行
sed -i '5,10d' file.txt                    # 删除 5-10 行

# 打印指定行
sed -n '10,20p' file.txt                   # 打印 10-20 行

# 组合：删除所有空行和注释行
sed '/^$/d;/^#/d' file.txt
```

### 1.5 `awk`：列处理

```bash
# 默认按空白分割，$1 第一列，$0 整行，$NF 最后一列
awk '{print $1}' file.txt

# 指定分隔符（CSV）
awk -F',' '{print $1, $3}' data.csv

# 条件过滤
awk '$3 > 100' file.txt                    # 第 3 列 > 100
awk '/error/' file.txt                     # 包含 error 的行

# 统计
awk '{count++} END {print count}' file.txt    # 行数
awk '{sum+=$1} END {print sum}' file.txt      # 第 1 列求和

# BEGIN / END 块
awk 'BEGIN {print "start"} {print $1} END {print "done"}' file.txt
```

## 2. 代码示例

### 2.1 在 dify 中查找异步函数定义

```bash
# 查找所有 async def 函数
grep -rn "^async def" /Users/xu/code/github/dify/api/ --include="*.py" | head -10

# 输出：
# /Users/xu/code/github/dify/api/services/async_workflow_service.py:53:    def trigger_workflow_async(
# ...
```

### 2.2 统计代码量

```bash
# 统计 dify 后端 Python 代码行数
find /Users/xu/code/github/dify/api -name "*.py" -not -path "*/migrations/*" | xargs wc -l | tail -1
```

### 2.3 批量替换字符串

```bash
# 把所有 .py 文件中的旧 API 路径改成新路径
find /path -name "*.py" -exec sed -i 's|old.api.com|new.api.com|g' {} \;

# 删除所有 .pyc 缓存文件
find /path -name "*.pyc" -delete
```

### 2.4 常见错误：`find` 路径错误

```bash
# ❌ 错误：忘记加 -name，所有文件都匹配
find /path | xargs rm  # 危险！会删所有东西

# ✅ 正确：先打印确认
find /path -name "*.tmp" | head
# 确认后再删除
find /path -name "*.tmp" -delete
```

## 3. dify 仓库源码解读

### 3.1 用 grep 调研 dify 的 API 端点

```bash
# 查找所有 Flask 路由定义
grep -rn "@.*\.route\|@.*\.get\|@.*\.post" /Users/xu/code/github/dify/api/controllers/ --include="*.py" | head -10

# 输出：
# /Users/xu/code/github/dify/api/controllers/console/app/app.py:42:    @console_ns.route("/apps")
# /Users/xu/code/github/dify/api/controllers/console/app/app.py:55:    class AppListApi(Resource):
# ...
```

**解读**：
- `controllers/` 目录包含所有 REST API 端点
- `console_ns.route(...)` 注册路由路径
- **`grep -rn` 是调研大型代码库的最快方式**

### 3.2 用 find + awk 分析项目结构

```bash
# 统计 dify 各模块文件数量
find /Users/xu/code/github/dify/api -type d -not -path "*/.*" | \
    awk -F/ '{print NF, $0}' | \
    sort -n | \
    tail -20

# 统计每个 Python 文件的行数（找出最大的 10 个）
find /Users/xu/code/github/dify/api -name "*.py" -not -path "*/migrations/*" | \
    xargs wc -l | \
    sort -rn | \
    head -10
```

**解读**：
- 第一个命令找出最深的目录嵌套（看项目分层）
- 第二个命令找出最大的文件（潜在的复杂模块，需要重点理解）

## 4. 关键要点总结

- `grep` 搜内容，`find` 找文件，`sed` 编辑文本，`awk` 处理列
- `grep -rn "pattern" --include="*.py"` 是搜索代码的万能模式
- `find -exec cmd {} \;` 批量处理文件
- `sed -i 's/old/new/g'` 全局替换
- `awk` 默认按空白分割列，`-F','` 指定分隔符
- **管道 `|`** 是命令组合的灵魂：每个命令处理文本流的一部分

## 5. 练习题

### 练习 1：基础（必做）

用一条命令统计 `/Users/xu/code/github/dify/api/services/` 下所有 `.py` 文件的行数。

### 练习 2：进阶

用 `grep -rn` 找出 dify 后端所有调用 `requests.get` 或 `requests.post` 的位置（dify 主要用 aiohttp，requests 调用通常是需要重构的旧代码）。

### 练习 3：挑战（选做）

写一个 bash 函数 `dify_search()`：接受关键词参数，自动在 `api/` 目录下递归搜索 `.py` 文件，显示文件名、行号、匹配内容，支持可选的 `--type=async|class|def` 过滤。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/`（仓库根目录）
- GNU grep 文档：https://www.gnu.org/software/grep/manual/
- GNU find 文档：https://www.gnu.org/software/findutils/manual/
- sed & awk 简明教程：https://www.grymoire.com/Unix/Sed.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13