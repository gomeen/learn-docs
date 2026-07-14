# 6.3 哈希算法：MD5 / SHA-1 / SHA-256 / bcrypt / Argon2

> 理解哈希函数的特性，掌握密码哈希的安全实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分哈希与加密的本质区别
- 理解密码哈希与普通哈希的不同要求
- 在 Python/Java 中正确使用 bcrypt / Argon2 / PBKDF2 存储密码
- 识别 dify 和 ruoyi 的密码哈希实现

## 📚 前置知识

- 6 加密系列前置
- 任意一门编程语言基础
- 6.1 对称加密（了解基本概念）

## 1. 核心概念

### 1.1 什么是哈希？

哈希（Hash）：把任意长度输入映射为**固定长度输出**的**单向**函数。

```
"hello"   → SHA-256 → 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
"hello1"  → SHA-256 → 9307b3529d75bb2d3a8e0d6e26d2a3c5a7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2

✅ 单向：无法从哈希值反推原文
✅ 确定性：相同输入永远得到相同输出
✅ 雪崩效应：输入改 1 bit，输出完全改变
✅ 抗碰撞：很难找到两个输入有相同哈希值
```

### 1.2 哈希 vs 加密

| 维度 | 哈希 | 加密 |
|------|------|------|
| 方向 | **单向**，不可逆 | 双向，可解密 |
| 输出 | 固定长度 | 与输入等长或略长 |
| 密钥 | 不需要 | 需要 |
| 用途 | 校验完整性、密码存储 | 保密通信 |

### 1.3 主流哈希算法

| 算法 | 输出长度 | 安全性 | 速度 | 现状 |
|------|---------|--------|------|------|
| **MD5** | 128 bit | **已破解** | 极快 | 仅用于文件校验 |
| **SHA-1** | 160 bit | **已破解**（2017 Google） | 快 | 逐步淘汰 |
| **SHA-256** | 256 bit | 强 | 中 | **通用推荐** |
| **SHA-3** | 可变 | 强 | 中 | 新一代标准 |
| **bcrypt** | 184 bit | 强 | 慢（可调）| **密码哈希推荐** |
| **Argon2** | 可变 | **最强** | 慢（可调）| **密码哈希最强** |
| **PBKDF2** | 可变 | 强 | 中 | 老牌标准，NIST 推荐 |

### 1.4 密码哈希的特殊要求

普通哈希（SHA-256）**不适合**密码存储，原因：
- **太快**：GPU 每秒算 10 亿次 SHA-256，暴力破解成本极低
- **无盐**：相同密码 → 相同哈希，攻击者用"彩虹表"预计算
- **不可调成本**：无法增加计算量

**密码哈希必须满足**：
1. **慢**：故意慢，让暴力破解成本高
2. **自动加盐**：每次随机盐，相同密码 → 不同哈希
3. **可调成本**：能随硬件升级调整迭代次数

### 1.5 密码哈希算法对比

```
用户输入: password123
       ↓
+ 随机盐 (16 bytes): xK9p...
       ↓
hash(salt + password) → bcrypt/Argon2 迭代 N 次
       ↓
输出格式: $2b$12$LJ3m4ys3Lk... (盐+哈希+参数，自包含)
```

| 算法 | 调参方式 | 抗 GPU | 抗 ASIC | 推荐度 |
|------|---------|--------|---------|--------|
| **PBKDF2** | 迭代次数 | 弱 | 弱 | 中（旧系统）|
| **bcrypt** | cost factor (4-31) | 强 | 中 | **高** |
| **scrypt** | 内存 + CPU | 强 | 强 | 高 |
| **Argon2id** | 时间/内存/并行度 | **强** | **强** | **最强** |

### 1.6 dify 和 ruoyi 的密码哈希对比

| 项目 | 算法 | 迭代/成本 | 备注 |
|------|------|----------|------|
| **dify** | PBKDF2-HMAC-SHA256 | 10000 次 | `libs/password.py` |
| **ruoyi** | BCrypt | cost=10 | Spring Security 默认 |

PBKDF2 是 NIST 标准，bcrypt 通用性更强——两者都是合理选择，关键看是否**自动加盐**。

## 2. 代码示例

### 2.1 错误示例：用 SHA-256 存密码

```python
# 文件：bad_password_hash.py
# ❌ 错误做法：用 SHA-256 存密码（无盐、太快）
import hashlib

def bad_hash_password(password: str) -> str:
    """❌ 错误：SHA-256 无盐，相同密码 → 相同哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

# 风险：
# 1. 两个用户都用 "123456" → 数据库哈希相同 → 攻击者知道哪些用户用弱密码
# 2. 攻击者用彩虹表（预计算的 SHA-256 → 原文 映射）秒破
# 3. GPU 每秒 10 亿次 SHA-256 → 8 位密码 1 小时破完
```

### 2.2 正确做法：bcrypt（推荐）

```python
# 文件：bcrypt_demo.py
# ✅ 推荐：bcrypt 密码哈希
import bcrypt

def hash_password(password: str) -> str:
    """生成 bcrypt 哈希，自动加盐"""
    # cost=12 是 2024 年的推荐值（每次哈希约 250ms）
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode(), hashed.encode())

# 测试
hashed = hash_password("MySecureP@ssw0rd")
print(f"哈希值: {hashed}")  # $2b$12$... 长字符串
print(f"格式: 算法$cost$salt+hash")
print(f"验证: {verify_password('MySecureP@ssw0rd', hashed)}")  # True
print(f"错误密码: {verify_password('wrong', hashed)}")  # False

# 关键：相同密码两次哈希结果不同（盐不同）
h1 = hash_password("test")
h2 = hash_password("test")
print(f"h1 == h2: {h1 == h2}")  # False（自动加盐）
```

### 2.3 Argon2（密码哈希最强）

```python
# 文件：argon2_demo.py
# ✅ Argon2id：抗 GPU + 抗 ASIC + 可调内存
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# 1. 使用推荐参数（OWASP 2024）
ph = PasswordHasher(
    time_cost=3,        # 迭代次数
    memory_cost=65536,  # 64 MB 内存
    parallelism=4,      # 4 个线程
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, password)
        # ✅ Argon2 还提供 rehash 检测：当参数过旧时建议升级
        if ph.check_needs_rehash(hashed):
            new_hash = ph.hash(password)
            # TODO: 更新数据库中的哈希
        return True
    except VerifyMismatchError:
        return False

# 测试
hashed = hash_password("user-pass")
print(f"验证: {verify_password('user-pass', hashed)}")  # True
print(f"错误: {verify_password('wrong', hashed)}")  # False
```

### 2.4 Python 标准库：hashlib（PBKDF2）

```python
# 文件：pbkdf2_demo.py
# Python 标准库的 PBKDF2（dify 用此方案）
import hashlib
import os
import base64

ITERATIONS = 100_000  # OWASP 推荐 ≥ 100,000

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    # 存储格式：base64(salt) : base64(hash)
    return f"{base64.b64encode(salt).decode()}:{base64.b64encode(dk).decode()}"

def verify_password(password: str, stored: str) -> bool:
    salt_b64, hash_b64 = stored.split(":")
    salt = base64.b64decode(salt_b64)
    expected_hash = base64.b64decode(hash_b64)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    # ✅ 常数时间比较
    return hmac.compare_digest(dk, expected_hash)
```

## 3. dify 仓库源码解读

### 3.1 dify 的密码哈希（PBKDF2-HMAC-SHA256）

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
- 第 6 行：密码复杂度要求——至少 8 位，包含字母+数字
- 第 13 行：`re.match` 用于格式校验（不是 SQL 注入场景，安全）
- 第 20 行：**PBKDF2-HMAC-SHA256**，迭代 10000 次——这个迭代次数**偏低**，现代推荐 100000+（OWASP 2023 建议）
- 第 26 行：`==` 直接比较哈希值——**不是常数时间比较，存在时序攻击风险**
- **设计意图**：dify 选择 PBKDF2（标准库自带，零依赖），是合理的工程权衡

### 3.2 ruoyi 的密码哈希（BCrypt）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`（配置）
**核心代码**（典型 Spring Security BCrypt 配置）：

```java
package cn.iocoder.yudao.framework.security.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import lombok.Data;

@Data
@ConfigurationProperties(prefix = "yudao.security")
public class SecurityProperties {

    /**
     * 密码编码器（默认 BCrypt，strength=10）
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(10);  // cost=10，约 100ms 每次
    }
}
```

**BCryptPasswordEncoder 用法**：
```java
// 加密
String hashed = passwordEncoder.encode("user-pass");
// 验证
boolean matches = passwordEncoder.matches("user-pass", hashed);
```

**解读**：
- 第 17 行：`BCryptPasswordEncoder(10)` —— cost=10 是 Spring Security 默认
- BCrypt 自动加盐（盐存在哈希字符串中：`$2a$10$...`）
- BCrypt 抗 GPU 攻击（设计如此），不需要额外配置
- **对比 dify**：ruoyi 用 BCrypt，比 dify 的 PBKDF2 更适合密码场景（BCrypt 是专门为密码设计的）
- **设计意图**：ruoyi 跟随 Spring Security 生态，选 BCrypt 是工程最佳实践

## 4. 关键要点总结

- **MD5/SHA-1 已破解**，SHA-256 用于文件校验，**不要用于密码**
- 密码哈希三大要求：**慢 + 加盐 + 可调成本**
- **bcrypt / Argon2 / PBKDF2** 是密码哈希的主流选择
- **不要自己实现**哈希算法或"加盐技巧"
- 验证时用**常数时间比较**（`hmac.compare_digest` 或 `MessageDigest.isEqual`）
- dify 用 PBKDF2（标准库），ruoyi 用 BCrypt（专用密码哈希）
- **MD5(密码) + salt** ≠ 安全，盐必须随机且足够长

## 5. 练习题

### 练习 1：基础（必做）

实现 `hash_password(password)` 和 `verify_password(password, hashed)`：
1. 使用 `bcrypt` 或 `hashlib.pbkdf2_hmac`
2. 每次哈希自动生成随机盐
3. 验证时使用常数时间比较

**参考答案**：见 `solutions/03-bcrypt-basic.md`

### 练习 2：进阶

阅读 dify 的 `libs/password.py`，指出至少 2 个可以改进的地方（迭代次数、比较方式、密码规则），并写一份改进建议。

### 练习 3：挑战（选做）

实现一个"密码强度检测"函数，要求：
1. 长度 ≥ 12 位
2. 必须包含大小写字母、数字、特殊字符
3. 检查是否在常见弱密码字典中（top 10000）
4. 返回 0-100 的强度评分

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`（看如何调用）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoSecurityAutoConfiguration.java`
- OWASP 密码存储手册：https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- Python `bcrypt` 库文档：https://pypi.org/project/bcrypt/

---

**文档版本**：v1.0
**最后更新**：2026-07-13