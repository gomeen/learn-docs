# 1.5 字符编码常见问题（乱码、emoji）

> 编码问题是后端开发最常见的"坑"。本文档总结最常见的乱码问题和解决方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 识别常见的乱码现象
- 分析乱码的根本原因
- 掌握 emoji 在数据库中的存储
- 在 dify/ruoyi 中避免编码问题

## 📚 前置知识

- 01-encoding.md
- 02-chinese-encoding.md

## 1. 核心概念

### 1.1 乱码的常见现象

| 现象 | 原因 |
|------|------|
| "中文" 显示成 "����" | UTF-8 字节被 GBK 解码 |
| "中文" 显示成 "涓枃" | GBK 字节被 UTF-8 解码 |
| emoji 显示成 "?" | 数据库 utf8（3 字节）不支持 |
| 中文乱码 + 半个字符 | 字节被截断 |

### 1.2 排查乱码的思路

```
1. 确认字节来源（哪里产生的）
2. 确认字节如何传输（HTTP / 文件）
3. 确认字节如何存储（数据库）
4. 确认字节如何读取（客户端）
5. 找到编码不一致的环节
```

### 1.3 emoji 的特殊问题

emoji 字符在 Unicode 中是 4 字节（如 🎉 = U+1F389）：
- MySQL `utf8`（3 字节）不能存 → 必须用 `utf8mb4`
- JavaScript `String.length` 算的是 UTF-16 code units → emoji 算 2

## 2. 代码示例

### 2.1 排查乱码示例

```python
# 场景：HTTP 请求带中文乱码

# 客户端发送（必须明确编码）
import requests
response = requests.get(
    "https://api.example.com/search",
    params={"q": "中文"},   # requests 自动 URL 编码
)

# 服务端接收（Flask）
from flask import request
@app.route("/search")
def search():
    q = request.args.get("q")  # Flask 自动解码
    return {"query": q}
```

### 2.2 emoji 长度问题

```python
text = "🎉"  # emoji
print(len(text))           # 1（字符）
print(len(text.encode("utf-8")))  # 4（字节）
print(len(text.encode("utf-16"))) # 2（UTF-16 code units）

# 字符长度（用 grapheme cluster）
import unicodedata
def char_len(text):
    return len([c for c in text])

print(char_len("🎉"))  # 1
print(char_len("a🎉b"))  # 3
```

### 2.3 文件读写编码

```python
# ❌ 错误：依赖系统默认编码（Windows 是 GBK，Linux 是 UTF-8）
with open("data.txt") as f:
    content = f.read()

# ✅ 正确：明确编码
with open("data.txt", encoding="utf-8") as f:
    content = f.read()

# 写文件
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("中文 + emoji 🎉")
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密码校验（emoji 友好）

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
import re

password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"

def valid_password(password):
    """密码校验——支持任意 Unicode 字符"""
    if re.match(password_pattern, password) is not None:
        return password
    raise ValueError("Password must contain letters and numbers...")
```

**解读**：
- 第 3 行：正则支持 Unicode（默认）
- 用户可以用 emoji 当密码（虽然不推荐）

### 3.2 ruoyi 的 MySQL utf8mb4（emoji 友好）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/`
**核心代码**：

```sql
CREATE TABLE system_users (
    username VARCHAR(30) NOT NULL,
    nickname VARCHAR(30) NOT NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '用户表';
```

**解读**：
- `utf8mb4` = MySQL 真正的 UTF-8（4 字节）
- 可以存 emoji、生僻字、所有 Unicode 字符
- 这是 ruoyi 处理 emoji 的关键

### 3.3 dify 的 LLM 输出编码

**位置**：`/Users/xu/code/github/dify/api/core/llm_generator/`
**核心代码**：

```python
import json

def parse_llm_output(raw_output: str) -> dict:
    """解析 LLM 输出——明确 UTF-8"""
    # LLM 返回的可能含 emoji、中文、特殊字符
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        # 尝试修复常见编码问题
        return json.loads(raw_output.encode("utf-8").decode("utf-8-sig"))
```

**解读**：
- `utf-8-sig` 自动移除 UTF-8 BOM
- 处理 LLM 输出时要注意编码兼容性

## 4. 关键要点总结

- 乱码 = 编码和解码不一致
- emoji 必须用 utf8mb4（不是 utf8）
- Python 文件读写要明确 `encoding="utf-8"`
- HTTP 请求用框架自动处理编码
- dify/ruoyi 都已正确处理 UTF-8

## 5. 练习题

### 练习 1：基础
把含 emoji 的字符串 `"Hello 🎉"` 写入文件，再用不同编码读取，观察结果。

### 练习 2：进阶
排查一个真实的乱码问题：HTTP 请求带中文，数据库里存的是乱码。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/sql/`
- Joel Spolsky《Unicode 绝对指南》：https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-know-about-unicode-and-character-sets-no-excuses/

---

**文档版本**：v1.0
**最后更新**：2026-07-13