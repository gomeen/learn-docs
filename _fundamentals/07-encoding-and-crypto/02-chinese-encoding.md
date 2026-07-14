# 1.2 常见编码：GBK / GB2312 / Big5

> 中文编码有多种方案：GB2312、GBK、GB18030、Big5。理解差异能避免乱码问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 GB2312、GBK、GB18030 的关系
- 知道 Big5 用于繁体中文
- 识别中文乱码的原因
- 选择合适的中文编码

## 📚 前置知识

- 01-encoding.md
- Unicode 基础

## 1. 核心概念

### 1.1 中文编码族谱

```
GB2312 (1980)        → 6,763 个简体汉字
   ↓ 扩展
GBK (1995)           → 21,886 个汉字（简体 + 繁体 + 日韩）
   ↓ 扩展
GB18030 (2000)       → 27,533 个汉字（覆盖所有 Unicode）
```

### 1.2 各种编码对比

| 编码 | 字符数 | 兼容 | 用途 |
|------|--------|------|------|
| GB2312 | 6,763 | ASCII | 老系统 |
| GBK | 21,886 | GB2312 | Windows 中文 |
| GB18030 | 27,533 | GBK | 国家强制标准 |
| Big5 | 13,053 | ASCII | 台湾、香港繁体 |
| UTF-8 | 全 Unicode | ASCII | 现代互联网首选 |

### 1.3 GBK 的双字节编码

GBK 用两个字节表示一个汉字：
- 第一字节：`0x81-0xFE`
- 第二字节：`0x40-0xFE`（除 `0x7F`）
- 不依赖 ASCII 单字节，所以英文字符和汉字混合不会出现歧义

### 1.4 何时用 GB 系列？

- **不推荐新项目使用**——UTF-8 是主流
- **遗留系统兼容**——老数据库、CSV 文件
- **Windows 内部**——Windows 默认 GBK（中文版）

## 2. 代码示例

### 2.1 Python 中文编码

```python
text = "中文"

# UTF-8 编码（推荐）
utf8_bytes = text.encode("utf-8")
print(f"UTF-8: {utf8_bytes.hex()}")    # e4b8ade69687

# GBK 编码
gbk_bytes = text.encode("gbk")
print(f"GBK: {gbk_bytes.hex()}")       # d6d0cec4

# GB2312 编码
gb2312_bytes = text.encode("gb2312", errors="strict")
print(f"GB2312: {gb2312_bytes.hex()}") # 同 GBK

# Big5 编码（繁体）
big5_bytes = "繁體".encode("big5")
print(f"Big5: {big5_bytes.hex()}")     # b9c4bb6f
```

### 2.2 乱码分析

```python
# 原始 UTF-8 字节
text = "中文"
utf8 = text.encode("utf-8")  # b'\xe4\xb8\xad\xe6\x96\x87'

# ❌ 用 GBK 解码 UTF-8 字节 → 乱码
print(utf8.decode("gbk", errors="replace"))
# 输出类似：涓枃

# ❌ 用 UTF-8 解码 GBK 字节 → 乱码
gbk = text.encode("gbk")     # b'\xd6\xd0\xce\xc4'
print(gbk.decode("utf-8", errors="replace"))
# 输出类似：����

# ✅ 正确：用什么编码就用什么解码
print(utf8.decode("utf-8"))  # 中文
```

### 2.3 文件编码检测

```python
import chardet

# 检测文件编码
with open("unknown.txt", "rb") as f:
    raw = f.read()

result = chardet.detect(raw)
print(f"检测结果: {result}")
# {'encoding': 'UTF-8', 'confidence': 0.99, 'language': ''}

# 用检测到的编码解码
text = raw.decode(result["encoding"])
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 ruoyi 的 MySQL 配置（utf8mb4）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/`
**核心代码**：

```sql
-- ruoyi 建表语句
CREATE TABLE system_users (
    username VARCHAR(30) NOT NULL,
    nickname VARCHAR(30) NOT NULL,
    email VARCHAR(50)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '用户表';
```

**解读**：
- `utf8mb4`：MySQL 的真正 UTF-8（4 字节完整支持）
- MySQL 的 `utf8` 是 3 字节阉割版，不能存 emoji
- ruoyi 用 utf8mb4 是正确选择

### 3.2 dify 的 Python 编码

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
def hash_password(password_str: str, salt_byte: bytes):
    """密码哈希——使用 UTF-8 编码字符串"""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password_str.encode("utf-8"),  # 明确 UTF-8
        salt_byte,
        10000,
    )
    return binascii.hexlify(dk)
```

**解读**：
- 第 5 行：明确 UTF-8 编码，避免跨平台问题
- Python 3 字符串默认是 Unicode，无需额外处理

## 4. 关键要点总结

- GB2312 → GBK → GB18030 是中文编码演进
- Big5 是繁体中文（台湾、香港）
- 新项目用 UTF-8，不用 GBK
- MySQL 用 `utf8mb4`（不是 `utf8`）
- 乱码通常是编码/解码不一致

## 5. 练习题

### 练习 1：基础
把 `"中文 + emoji 🎉"` 用 UTF-8 编码后的字节长度，与 GBK 比较。

### 练习 2：进阶
使用 `chardet` 检测一个 CSV 文件的编码，并正确读取。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/sql/`
- GB18030 标准：https://en.wikipedia.org/wiki/GB_18030

---

**文档版本**：v1.0
**最后更新**：2026-07-13