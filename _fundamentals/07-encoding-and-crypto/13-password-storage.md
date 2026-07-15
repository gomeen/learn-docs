# 4.1 密码存储：bcrypt / argon2

> 密码存储是后端安全的核心。错误的存储方式会导致用户密码全部泄露。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解密码存储的正确方式
- 掌握 bcrypt、Argon2 的用法
- 知道为什么不能用 MD5/SHA-256 存密码
- 在 dify/ruoyi 中应用密码哈希

## 📚 前置知识

- 08-hash.md
- 14-api-signature.md（关联）

## 1. 核心概念

### 1.1 密码存储的 4 个原则

1. **绝不存明文**：数据库泄露直接完蛋
2. **使用密码哈希**：bcrypt / Argon2（不是 MD5/SHA；通用哈希见 [08-hash](./08-hash.md)）
3. **自动加 salt**：每个密码 salt 不同
4. **慢哈希**：让暴力破解代价高

### 1.2 算法对比

| 算法 | 速度 | 安全 | 推荐 |
|------|------|------|------|
| MD5 | 极快 | ❌ | 不推荐 |
| SHA-256 | 快 | ⚠️ | 不推荐（无 salt） |
| bcrypt | 慢（~10ms） | ✅ | ✅ 推荐 |
| Argon2 | 慢（可配置） | ✅✅ | ✅✅ 最推荐 |
| scrypt | 慢 | ✅ | ✅ |

### 1.3 bcrypt 的结构

```
$2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
│  │  │                        │
│  │  │                        └─ 哈希值（22 字符）
│  │  └─ Salt（22 字符）
│  └─ Cost factor（12 = 2^12 = 4096 轮）
└─ 算法标识（2b = bcrypt）
```

### 1.4 Argon2 的 3 个变体

- **Argon2d**：抗 GPU 攻击
- **Argon2i**：抗侧信道攻击
- **Argon2id**：混合版（推荐）

## 2. 代码示例

### 2.1 Python bcrypt

```python
import bcrypt

# 注册：哈希密码
password = "my_secret_123".encode("utf-8")
salt = bcrypt.gensalt(rounds=12)  # cost = 12（约 250ms）
hashed = bcrypt.hashpw(password, salt)

# 存入数据库
print(f"Stored: {hashed.decode()}")
# $2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy

# 登录：验证密码
is_valid = bcrypt.checkpw(password, hashed)
print(f"Valid: {is_valid}")  # True

# 错误密码
is_valid = bcrypt.checkpw(b"wrong_password", hashed)
print(f"Valid: {is_valid}")  # False
```

### 2.2 Python Argon2

```python
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,        # 迭代次数
    memory_cost=65536,  # 内存消耗（KB）
    parallelism=4,      # 并行度
)

# 注册
hash = ph.hash("my_password")
print(f"Argon2 hash: {hash}")
# $argon2id$v=19$m=65536,t=3,p=4$...

# 登录
try:
    ph.verify(hash, "my_password")
    print("Valid")
except Exception:
    print("Invalid")

# 自动升级（如果参数变强了）
if ph.check_needs_rehash(hash):
    new_hash = ph.hash("my_password")
```

### 2.3 自实现 PBKDF2（dify 用法）

```python
import hashlib
import os
import base64

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """PBKDF2-HMAC-SHA256"""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10000)
    return base64.b64encode(salt).decode(), base64.b64encode(dk).decode()

def verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10000)
    return dk == expected
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 用 PBKDF2

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
import hashlib
import base64

def hash_password(password_str: str, salt_byte: bytes) -> bytes:
    """密码哈希：PBKDF2-HMAC-SHA256"""
    return hashlib.pbkdf2_hmac("sha256", password_str.encode("utf-8"), salt_byte, 10000)

def compare_password(password_str, password_hashed_base64, salt_base64):
    return hash_password(password_str, base64.b64decode(salt_base64)) == base64.b64decode(password_hashed_base64)
```

**解读**：
- dify 用 PBKDF2（避免 bcrypt 依赖）
- salt 单独存储
- 10000 轮迭代

### 3.2 ruoyi 用 BCrypt

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
**核心代码**：

```java
@Bean
public PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder();
}

// 使用
@Service
public class AdminUserServiceImpl {
    public Long createUser(UserSaveReqVO reqVO) {
        AdminUserDO user = new AdminUserDO();
        user.setPassword(passwordEncoder.encode(reqVO.getPassword()));  // 自动加 salt
        userMapper.insert(user);
        return user.getId();
    }

    public boolean login(String username, String rawPassword) {
        AdminUserDO user = userMapper.selectByUsername(username);
        return passwordEncoder.matches(rawPassword, user.getPassword());  // 验证
    }
}
```

**解读**：
- `BCryptPasswordEncoder.encode()` 自动加 salt
- `BCryptPasswordEncoder.matches()` 验证（自动从 hash 提取 salt）

## 4. 关键要点总结

- 密码存储 = 慢哈希 + 自动 salt
- 推荐：bcrypt（成熟）、Argon2（最新）
- 不推荐：MD5、SHA-256（无 salt 或太快）
- dify 用 PBKDF2，ruoyi 用 BCrypt
- 两种都符合安全最佳实践

## 5. 练习题

### 练习 1：基础
用 bcrypt 实现用户注册和登录功能（哈希存储 + 验证）。

### 练习 2：进阶
对比 bcrypt 和 Argon2 的性能（每秒哈希次数），分析 trade-off。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- OWASP 密码存储：https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13