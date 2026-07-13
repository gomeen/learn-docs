# 5.4.3 哈希算法：MD5 / SHA / bcrypt

> 理解哈希算法与密码学哈希的差异，掌握密码哈希的特殊要求。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解普通哈希 vs 密码学哈希的差异
- 掌握 MD5 / SHA-256 / bcrypt / scrypt / Argon2 的安全性
- 理解 Salt 的作用
- 能用 Python 实现 PBKDF2 / bcrypt 密码哈希

## 📚 前置知识

- 21-symmetric-encryption.md
- Python 基础

## 1. 核心概念

### 1.1 什么是哈希？

哈希 = 把任意输入映射为**定长输出**的函数。

```
input: "hello" → SHA-256 → 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
input: "world" → SHA-256 → 486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8e5a6c65260e9cb8a7
```

**性质**：
- 单向：不能从哈希反推输入
- 抗碰撞：极难找到两个不同输入有相同哈希

### 1.2 普通哈希 vs 密码哈希

| 维度 | 普通哈希（MD5/SHA） | 密码哈希（bcrypt/Argon2） |
|------|---------------------|-------------------------|
| 速度 | 极快（纳秒级） | 故意慢（百毫秒级） |
| 抗 GPU 暴力 | 弱 | 强 |
| 抗彩虹表 | 弱（需要盐） | 强（自带盐） |
| 用途 | 文件校验、签名 | 密码存储 |

**关键**：存密码**不能**用 SHA-256，必须用 bcrypt / Argon2 / PBKDF2。

### 1.3 算法对比

| 算法 | 安全性 | 速度 | 推荐 |
|------|--------|------|------|
| MD5 | 已破解 | 极快 | 禁止 |
| SHA-1 | 已破解 | 极快 | 禁止 |
| SHA-256 | 安全 | 快 | 文件/签名 |
| PBKDF2 | 安全 | 中等 | dify 用 |
| bcrypt | 安全 | 慢 | 通用 |
| Argon2 | 最安全 | 慢（可调） | 新项目首选 |

## 2. 代码示例

### 2.1 普通哈希（SHA-256）

```python
import hashlib

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

# 文件校验
file_hash = sha256_hex(open("app.zip", "rb").read())
print(file_hash)  # 64 字符 hex 字符串
```

### 2.2 密码哈希（PBKDF2）

```python
import hashlib, os, base64

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """用 PBKDF2-HMAC-SHA256 哈希密码。"""
    if salt is None:
        salt = os.urandom(16)  # 16 字节随机盐
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.b64encode(salt).decode(), base64.b64encode(dk).decode()


def verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    """验证密码。"""
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    # ⚠️ 应使用恒定时间比较避免侧信道攻击
    return hashlib.compare_digest(dk, expected)


# 使用
salt, hash_val = hash_password("my-secret-password")
print(f"盐: {salt}\n哈希: {hash_val}")
print(verify_password("my-secret-password", salt, hash_val))  # True
```

### 2.3 密码哈希（bcrypt）

```python
import bcrypt

def bcrypt_hash(password: str) -> bytes:
    salt = bcrypt.gensalt(rounds=12)  # 2^12 次迭代
    return bcrypt.hashpw(password.encode(), salt)

def bcrypt_verify(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)

# 使用
hashed = bcrypt_hash("secret123")
bcrypt_verify("secret123", hashed)  # True
bcrypt_verify("wrong", hashed)     # False
```

### 2.4 常见错误：用 SHA-256 存密码

```python
# ❌ 错误：SHA-256 存密码
import hashlib
db.users.password = hashlib.sha256(password.encode()).hexdigest()
# GPU 每秒可算数十亿次 SHA-256 → 几小时破解

# ✅ 正确：bcrypt / Argon2
db.users.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

## 3. dify 仓库源码解读

### 3.1 密码哈希与验证

**文件位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**（行 1-26）：

```python
import base64
import binascii
import hashlib
import re

password_pattern = r"^(?=.*[a-zA-Z])(?=.*\d).{8,}$"


def valid_password(password):
    # Define a regex pattern for password rules
    pattern = password_pattern
    # Check if the password matches the pattern
    if re.match(pattern, password) is not None:
        return password

    raise ValueError("Password must contain letters and numbers, and the length must be at least 8 characters.")


def hash_password(password_str: str, salt_byte: bytes):
    dk = hashlib.pbkdf2_hmac("sha256", password_str.encode("utf-8"), salt_byte, 10000)
    return binascii.hexlify(dk)


def compare_password(password_str, password_hashed_base64, salt_base64):
    # compare password for login
    return hash_password(password_str, base64.b64decode(salt_base64)) == base64.b64decode(password_hashed_base64)
```

**解读**：
- 第 6 行：`password_pattern` —— 强密码策略（8+ 位、含字母和数字）
- 第 17-19 行：`hash_password` 用 **PBKDF2-HMAC-SHA256**，10000 轮迭代
- 第 23-24 行：`compare_password` 用 `==` 直接比较哈希（**应该用 `compare_digest` 避免时序攻击**）
- **dify 选择 PBKDF2** 而非 bcrypt：依赖标准库（无需额外依赖），但 PBKDF2 不如 bcrypt / Argon2 安全
- **改进建议**：10000 轮偏低（OWASP 推荐 600000+），可考虑升级到 bcrypt

### 3.2 密码正则校验

**文件位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**（行 9-16）：

```python
def valid_password(password):
    # Define a regex pattern for password rules
    pattern = password_pattern
    # Check if the password matches the pattern
    if re.match(pattern, password) is not None:
        return password

    raise ValueError("Password must contain letters and numbers, and the length must be at least 8 characters.")
```

**解读**：
- 第 1 行：`valid_password` 强密码校验函数
- 第 4 行：`re.match` 检查是否符合 `password_pattern`
- 第 7 行：不符合抛 `ValueError`
- **设计意图**：把密码策略集中在 `libs/password.py`，业务代码统一调用

## 4. 关键要点总结

- MD5 / SHA-1 已破解，禁止用于安全场景
- **密码必须用慢哈希**：PBKDF2 / bcrypt / Argon2
- **Salt 防止彩虹表攻击**：每个用户独立随机盐
- dify 用 PBKDF2-HMAC-SHA256，10000 轮迭代（可考虑升级）
- 密码比较应该用 `compare_digest` 防时序攻击
- 密码策略：8+ 位 + 字母 + 数字（dify 的最低要求）

## 5. 练习题

### 练习 1：基础（必做）

用 PBKDF2 实现 `hash_password(pwd)` 和 `verify_password(pwd, salt, hash)`，要求 100000 轮迭代 + 16 字节随机盐 + `compare_digest` 验证。

### 练习 2：进阶

阅读 `api/libs/password.py:24-26`，解释为什么 `==` 直接比较哈希**不安全**？如何用 `compare_digest` 修复？

### 练习 3：挑战（选做）

升级 dify 的密码哈希到 bcrypt：写一个迁移脚本，把 PBKDF2 哈希的用户密码**首次登录时**升级到 bcrypt。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- OWASP 密码存储：https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- PBKDF2 推荐：https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#pbkdf2
- bcrypt vs Argon2：https://auth0.com/blog/hashing-in-action-an-understanding-of-bcrypt/

---

**文档版本**：v1.0
**最后更新**：2026-07-13