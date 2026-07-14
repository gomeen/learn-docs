# 4.2 API 签名：HMAC / Sign

> API 签名用于验证请求的**完整性**和**真实性**，防止篡改和重放攻击。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 API 签名的原理
- 掌握 HMAC 算法
- 防止常见的 API 攻击（重放、中间人）
- 在 dify/ruoyi 中实现 API 签名

## 📚 前置知识

- 08-hash.md
- 11-digital-signature.md

## 1. 核心概念

### 1.1 API 签名解决什么问题？

| 威胁 | 签名如何防御 |
|------|------------|
| 篡改 | 哈希校验 |
| 重放攻击 | 时间戳 + nonce |
| 中间人 | HTTPS + 签名 |
| 越权 | access key |

### 1.2 HMAC（Hash-based Message Authentication Code）

```
HMAC(K, M) = H((K ⊕ opad) || H((K ⊕ ipad) || M))
```

- K：密钥（双方共享）
- M：消息
- H：哈希函数（SHA-256）

**特点**：需要密钥，无法被篡改（篡改后哈希值不匹配）。

### 1.3 常见 API 签名方案

**方案 1：HMAC 签名**
```
signature = HMAC-SHA256(secret, "method\npath\nbody\ntimestamp")
```

**方案 2：阿里云签名 v3**
```
signature = HMAC-SHA256(secret, sorted_query_string)
```

**方案 3：JWT**
- 自带签名（HMAC 或 RSA）
- 支持过期时间

### 1.4 防止重放攻击

签名 + 时间戳 + nonce：
- 时间戳在窗口内（如 ±5 分钟）
- nonce 单次有效（Redis 去重）

## 2. 代码示例

### 2.1 简单 HMAC 签名

```python
import hmac
import hashlib

def sign_request(secret: str, message: str) -> str:
    """生成 HMAC 签名"""
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# 客户端
secret = "shared-secret-key"
message = "GET\n/api/users\n2026-07-13T10:00:00Z"
signature = sign_request(secret, message)

# 发送：headers["X-Signature"] = signature
```

### 2.2 完整签名方案（防重放）

```python
import hmac
import hashlib
import time
import secrets

def sign_request_v2(secret: str, method: str, path: str, body: str) -> dict:
    """完整签名 + 时间戳 + nonce"""
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(8)

    # 签名内容
    message = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
    signature = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    return {
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }


# 服务端验证
def verify_request_v2(secret: str, method: str, path: str, body: str,
                      timestamp: str, nonce: str, signature: str,
                      max_age: int = 300) -> bool:
    # 1. 检查时间戳
    if abs(int(time.time()) - int(timestamp)) > max_age:
        return False  # 请求过期

    # 2. 检查 nonce（用 Redis）
    # if redis.exists(f"nonce:{nonce}"): return False
    # redis.setex(f"nonce:{nonce}", max_age, 1)

    # 3. 验证签名
    expected = hmac.new(
        secret.encode(),
        f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
```

### 2.3 阿里云风格签名

```python
import hmac
import hashlib
import urllib.parse

def sign_aliyun(access_key_secret: str, params: dict) -> str:
    """阿里云风格签名——按字典序排序参数"""
    # 1. 按字典序排序
    sorted_params = sorted(params.items())
    # 2. 构造规范化字符串
    canonical = "&".join(f"{k}={v}" for k, v in sorted_params)
    # 3. HMAC 签名
    return hmac.new(
        (access_key_secret + "&").encode(),  # 注意末尾的 &
        canonical.encode(),
        hashlib.sha1,
    ).hexdigest()
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的内部 API 签名

**位置**：`/Users/xu/code/github/dify/api/controllers/console/`
**核心代码**：

```python
import hmac
import hashlib
from flask import request, abort

API_SECRET = "shared-secret"

def verify_signature():
    """验证内部 API 调用"""
    signature = request.headers.get("X-Dify-Signature")
    timestamp = request.headers.get("X-Dify-Timestamp")
    if not signature or not timestamp:
        abort(401)

    # 计算签名
    body = request.get_data()
    message = f"{request.path}\n{timestamp}\n{body.decode()}"
    expected = hmac.new(
        API_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        abort(401)
```

**解读**：
- dify 用 HMAC-SHA256 验证内部 API
- `hmac.compare_digest` 防时间攻击

### 3.2 ruoyi 的 API 签名

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
**核心代码**：

```java
// ruoyi 用 Sa-Token 框架处理认证
// 内置签名机制：Token + 时间戳 + 签名
@Component
public class SaTokenConfig {
    @Bean
    public SaInterceptor saInterceptor() {
        return new SaInterceptor(handle -> {
            // 验证 Token 签名
            StpUtil.checkLogin();
            // 验证 Token 时效
            StpUtil.checkTimeout();
        });
    }
}
```

**解读**：
- ruoyi 用 Sa-Token（类似 JWT）
- 自动处理签名、过期、刷新

## 4. 关键要点总结

- API 签名 = HMAC + 时间戳 + nonce
- HMAC 防止篡改
- 时间戳 + nonce 防止重放
- dify 用 HMAC-SHA256，ruoyi 用 Sa-Token
- HTTPS 是另一层防线（防中间人）

## 5. 练习题

### 练习 1：基础
实现 HMAC 签名：客户端签、服务端验，并测试篡改检测。

### 练习 2：进阶
实现完整的签名方案：HMAC + 时间戳窗口 + Redis nonce 去重。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- HMAC RFC：https://tools.ietf.org/html/rfc2104

---

**文档版本**：v1.0
**最后更新**：2026-07-13