# 1.1 ASCII / Latin-1 / Unicode / UTF-8

> 字符编码是后端开发的基础。乱码问题的根源几乎都是编码不一致。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解字符集与编码的区别
- 掌握 ASCII、Latin-1、Unicode、UTF-8 的关系
- 在 Python 中正确处理字符串
- 在 dify/ruoyi 中识别编码问题

## 📚 前置知识

- Python 基础
- 字节与字符的区别

## 1. 核心概念

### 1.1 字符集 vs 编码

| 概念 | 含义 | 例子 |
|------|------|------|
| 字符集（Charset） | 字符的集合 | ASCII、Unicode |
| 编码（Encoding） | 字符到字节的映射规则 | UTF-8、UTF-16、GBK |

### 1.2 ASCII（1960s）

- 128 个字符（0-127）
- 7 位表示一个字符
- 只覆盖英文字母、数字、标点

### 1.3 Latin-1（ISO-8859-1）

- 256 个字符（0-255）
- 8 位表示一个字符
- 兼容 ASCII + 欧洲字符
- MySQL 默认字符集之一

### 1.4 Unicode

- 全球统一的字符集
- 为每个字符分配唯一码点（Code Point），如 `U+4E2D`（中）
- 涵盖 150+ 语言、emoji、数学符号

### 1.5 UTF-8（Unicode 的实现）

- **变长编码**：1-4 字节表示一个字符
- 兼容 ASCII（ASCII 字符仍是 1 字节）
- 互联网最流行的编码

| Unicode 范围 | UTF-8 字节 |
|------------|----------|
| U+0000 - U+007F | 1 字节 |
| U+0080 - U+07FF | 2 字节 |
| U+0800 - U+FFFF | 3 字节 |
| U+10000 - U+10FFFF | 4 字节 |

## 2. 代码示例

### 2.1 Python 字符串与字节

```python
# 字符串（Unicode 码点）
s = "你好"
print(len(s))           # 2（字符数）
print(s.encode("utf-8"))  # b'\xe4\xbd\xa0\xe5\xa5\xbd'（6 字节）

# 字节 → 字符串
b = b'\xe4\xbd\xa0\xe5\xa5\xbd'
print(b.decode("utf-8"))  # 你好
```

### 2.2 编码错误处理

```python
# ❌ 错误：默认编码可能不对
data = open("file.txt").read()

# ✅ 正确：显式指定编码
data = open("file.txt", encoding="utf-8").read()

# 容错处理
text = b'\xe4\xbd\xa0\xe5\xa5\xbd'
try:
    text.decode("ascii")  # ❌ ASCII 无法编码
except UnicodeDecodeError:
    print("Decode error!")

# 容错解码
text.decode("utf-8", errors="ignore")    # 跳过错误字符
text.decode("utf-8", errors="replace")   # 用 ? 替换
```

### 2.3 各编码对比

```python
text = "你好A"

print(f"UTF-8:    {text.encode('utf-8').hex()}")     # e4bda0e5a5bd41
print(f"UTF-16:   {text.encode('utf-16').hex()}")    # 包含 BOM
print(f"GBK:      {text.encode('gbk').hex()}")        # c4e3bac3 41
print(f"ASCII:    ")                                 # ❌ '你' 不在 ASCII 中
try:
    text.encode("ascii")
except UnicodeEncodeError as e:
    print(f"Error: {e}")
```

## 3. dify 仓库源码解读

### 3.1 dify 密码编码

**文件位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**（行 1-30）：

```python
import base64
import binascii
import hashlib
import re

password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"

def valid_password(password):
    """校验密码——Unicode 字符匹配"""
    if re.match(password_pattern, password):
        return password
    raise ValueError("Password must contain letters and numbers...")

def hash_password(password_str: str, salt_byte: bytes):
    """哈希密码——明确指定 UTF-8 编码"""
    dk = hashlib.pbkdf2_hmac("sha256", password_str.encode("utf-8"), salt_byte, 10000)
    return binascii.hexlify(dk)
```

**解读**：
- 第 12 行：`password_str.encode("utf-8")` 明确指定 UTF-8 编码
- 第 13 行：`hexlify` 把字节转为十六进制字符串
- **整体设计**：dify 全栈使用 UTF-8 编码

### 3.2 dify 数据库配置（PostgreSQL 默认 UTF-8）

**位置**：`/Users/xu/code/github/dify/api/configs/middleware/__init__.py`
**核心代码**：

```python
# PostgreSQL 默认 client_encoding = UTF8
SQLALCHEMY_DATABASE_URI = os.getenv(
    "DB_CONNECTION_STRING",
    "postgresql+psycopg2://postgres:difyai123456@localhost:5432/dify",
)
```

**解读**：
- PostgreSQL 默认使用 UTF-8 编码
- 支持任意 Unicode 字符（包括 emoji）

## 4. 关键要点总结

- 字符集 = 字符的集合；编码 = 字符到字节的规则
- UTF-8 是变长编码，1-4 字节，兼容 ASCII
- Python 3 默认字符串是 Unicode
- 编码不一致会导致乱码
- dify 全栈 UTF-8

## 5. 练习题

### 练习 1：基础
把 `"中文 + emoji 🎉"` 编码为 UTF-8、GBK，观察字节数差异。

### 练习 2：进阶
读取一个 UTF-8 文件并按 GBK 解码，观察乱码现象。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- Python Unicode HOWTO：https://docs.python.org/3/howto/unicode.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13