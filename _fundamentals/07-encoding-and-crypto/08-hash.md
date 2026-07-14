# 3.1 哈希算法：MD5 / SHA-1 / SHA-256 / bcrypt

> 哈希算法是密码学的基石，分为**普通哈希**（快速）和**密码哈希**（慢速）两类。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解哈希算法的特性
- 区分 MD5、SHA-1、SHA-256 的差异
- 知道 bcrypt 是密码哈希（不是普通哈希）
- 在 dify/ruoyi 中选择合适的哈希算法

## 📚 前置知识

- 01-encoding.md
- 加密学基础

## 1. 核心概念

### 1.1 哈希算法特性

| 特性 | 说明 |
|------|------|
| 单向性 | 不可逆，无法从哈希值反推原文 |
| 确定性 | 相同输入产生相同输出 |
| 抗碰撞 | 很难找到两个不同输入产生相同输出 |
| 雪崩效应 | 输入微小变化导致输出巨大变化 |

### 1.2 主流哈希算法对比

| 算法 | 输出长度 | 速度 | 用途 | 安全性 |
|------|---------|------|------|--------|
| MD5 | 128 位 | 极快 | 文件校验 | ❌ 已破解 |
| SHA-1 | 160 位 | 快 | 文件校验 | ❌ 已破解 |
| SHA-256 | 256 位 | 中 | 文件校验、签名 | ✅ 安全 |
| SHA-512 | 512 位 | 中 | 高安全场景 | ✅ 安全 |
| bcrypt | 可变 | 慢 | **密码哈希** | ✅ 安全 |
| scrypt | 可变 | 慢 | **密码哈希** | ✅ 安全 |
| Argon2 | 可变 | 慢 | **密码哈希** | ✅ 安全 |

### 1.3 普通哈希 vs 密码哈希

**普通哈希（MD5、SHA-256）**：
- 极快（每秒百万次）
- 适合**完整性校验、签名**
- **不适合密码**（彩虹表攻击）

**密码哈希（bcrypt、Argon2）**：
- 慢（每秒几次）
- 内置 salt
- **适合密码存储**

## 2. 代码示例

### 2.1 普通哈希

```python
import hashlib

# MD5（已不推荐用于安全场景）
md5 = hashlib.md5(b"hello").hexdigest()
print(f"MD5:    {md5}")  # 5d41402abc4b2a76b9719d911017c592

# SHA-1（已不推荐）
sha1 = hashlib.sha1(b"hello").hexdigest()
print(f"SHA-1:  {sha1}")  # aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d

# SHA-256（推荐）
sha256 = hashlib.sha256(b"hello").hexdigest()
print(f"SHA-256:{sha256}")  # 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# 雪崩效应
print(hashlib.sha256(b"hello").hexdigest())
print(hashlib.sha256(b"hellp").hexdigest())  # 仅差 1 个字符，输出完全不同
```

### 2.2 密码哈希（bcrypt）

```python
import bcrypt

# 生成哈希（自动加 salt）
password = b"my_secret_123"
salt = bcrypt.gensalt(rounds=12)  # cost factor
hashed = bcrypt.hashpw(password, salt)
print(f"Bcrypt hash: {hashed}")
# b'$2b$12$...'（60 字符，包含算法 + cost + salt + hash）

# 验证密码
is_valid = bcrypt.checkpw(password, hashed)
print(f"Password valid: {is_valid}")  # True

# 错误密码
is_valid = bcrypt.checkpw(b"wrong", hashed)
print(f"Wrong valid: {is_valid}")    # False
```

### 2.3 PBKDF2（dify 用的）

```python
import hashlib

def hash_password_pbkdf2(password: str, salt: bytes) -> bytes:
    """PBKDF2——dify 用的密码哈希"""
    return hashlib.pbkdf2_hmac(
        "sha256",                # 底层哈希算法
        password.encode("utf-8"),
        salt,
        iterations=10000,         # 迭代次数（越大越慢）
    )

# 使用
salt = b"random_salt_123"
hashed = hash_password_pbkdf2("my_password", salt)
print(f"PBKDF2 hash: {hashed.hex()}")
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 用 PBKDF2（密码哈希）

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**（行 1-30）：

```python
import hashlib

def hash_password(password_str: str, salt_byte: bytes):
    """dify 密码哈希：PBKDF2-HMAC-SHA256，10,000 轮"""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password_str.encode("utf-8"),
        salt_byte,
        10000,
    )
    return binascii.hexlify(dk)


def compare_password(password_str, password_hashed_base64, salt_base64):
    """验证密码"""
    return hash_password(password_str, base64.b64decode(salt_base64)) == base64.b64decode(password_hashed_base64)
```

**解读**：
- PBKDF2 + HMAC-SHA256 + 10000 轮——密码哈希标准做法
- salt 单独存储
- **整体设计**：dify 不直接用 bcrypt（避免额外依赖）

### 3.2 ruoyi 用 BCrypt（Spring Security）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
**核心代码**：

```java
@Bean
public PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder();  // Spring Security 默认
}
```

**解读**：
- Spring Security 内置 BCryptPasswordEncoder
- 自动加 salt（每个密码 salt 不同）
- cost factor 默认 10

### 3.3 dify / ruoyi 的差异

| 维度 | dify | ruoyi |
|------|------|-------|
| 算法 | PBKDF2-HMAC-SHA256 | BCrypt |
| 轮数 | 10,000 | 默认 10 |
| salt | 单独存储 | 内嵌哈希中 |
| 库 | 标准库 hashlib | Spring Security |

**两种都安全**——BCrypt 更主流。

## 4. 关键要点总结

- 普通哈希：MD5、SHA-256（用于校验、签名）
- 密码哈希：bcrypt、Argon2、PBKDF2（用于密码）
- 密码哈希要慢、要加 salt
- dify 用 PBKDF2，ruoyi 用 BCrypt
- MD5/SHA-1 不再用于安全场景

## 5. 练习题

### 练习 1：基础
用 SHA-256 哈希文件，验证文件完整性。

### 练习 2：进阶
用 bcrypt 实现用户注册和登录（哈希存储 + 验证）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- OWASP 密码存储指南：https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13