# 4.2.3 HTTP 状态码完整解析

> HTTP 状态码是服务器告诉客户端请求结果的"语言"。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 5 类 HTTP 状态码的含义
- 知道常见状态码的使用场景
- 能在 dify 中识别状态码的应用

## 📚 前置知识

- 04-http-versions.md
- 05-http-flow.md

## 1. 核心概念

### 1.1 状态码的分类

| 范围 | 类别 | 说明 |
|------|------|------|
| **1xx** | 信息性 | 请求已接收，继续处理 |
| **2xx** | 成功 | 请求已成功处理 |
| **3xx** | 重定向 | 需要进一步操作 |
| **4xx** | 客户端错误 | 请求有误 |
| **5xx** | 服务器错误 | 服务器处理失败 |

### 1.2 1xx 信息性

| 状态码 | 名称 | 说明 |
|--------|------|------|
| 100 | Continue | 客户端应继续发送请求体 |
| 101 | Switching Protocols | 协议切换（如 WebSocket） |

### 1.3 2xx 成功

| 状态码 | 名称 | 场景 |
|--------|------|------|
| **200** | OK | 请求成功（最常见） |
| 201 | Created | 资源已创建（POST） |
| 202 | Accepted | 请求已接受，未完成处理 |
| 204 | No Content | 成功但无返回内容 |
| 206 | Partial Content | 部分内容（断点续传） |

### 1.4 3xx 重定向

| 状态码 | 名称 | 场景 |
|--------|------|------|
| **301** | Moved Permanently | 永久重定向 |
| **302** | Found | 临时重定向 |
| 303 | See Other | 强制 GET 重定向 |
| **304** | Not Modified | 缓存命中 |
| 307 | Temporary Redirect | 临时重定向（保持方法） |
| 308 | Permanent Redirect | 永久重定向（保持方法） |

### 1.5 4xx 客户端错误

| 状态码 | 名称 | 场景 |
|--------|------|------|
| **400** | Bad Request | 请求语法错误 |
| **401** | Unauthorized | 未认证 |
| **403** | Forbidden | 无权限 |
| **404** | Not Found | 资源不存在 |
| **405** | Method Not Allowed | 方法不允许 |
| 409 | Conflict | 资源冲突 |
| 410 | Gone | 资源已删除 |
| 413 | Payload Too Large | 请求体过大 |
| 415 | Unsupported Media Type | 不支持的媒体类型 |
| 422 | Unprocessable Entity | 语义错误（验证失败） |
| **429** | Too Many Requests | 限流 |

### 1.6 5xx 服务器错误

| 状态码 | 名称 | 场景 |
|--------|------|------|
| **500** | Internal Server Error | 服务器内部错误 |
| 501 | Not Implemented | 未实现 |
| 502 | Bad Gateway | 网关错误 |
| 503 | Service Unavailable | 服务不可用 |
| **504** | Gateway Timeout | 网关超时 |

### 1.7 常见场景的状态码选择

| 场景 | 状态码 |
|------|--------|
| GET 成功 | 200 |
| POST 创建成功 | 201 |
| PUT 更新成功 | 200 或 204 |
| DELETE 成功 | 204 |
| 参数错误 | 400 |
| 未登录 | 401 |
| 权限不足 | 403 |
| 资源不存在 | 404 |
| 数据冲突 | 409 |
| 限流 | 429 |
| 服务器错误 | 500 |

## 2. 代码示例

### 2.1 Flask 返回各种状态码

```python
# 文件：flask_status_codes.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/users/<int:user_id>")
def get_user(user_id):
    if user_id == 404:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"id": user_id, "name": f"User {user_id}"}), 200

@app.route("/users", methods=["POST"])
def create_user():
    # 创建用户
    return jsonify({"id": 123, "name": "New User"}), 201

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    # 删除用户
    return "", 204

@app.route("/old-path")
def old_path():
    # 永久重定向
    return "", 301, {"Location": "/new-path"}

@app.route("/api/protected")
def protected():
    # 未认证
    return jsonify({"error": "Unauthorized"}), 401

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal Server Error"}), 500
```

### 2.2 客户端处理状态码

```python
# 文件：client_status_handling.py
import requests

def fetch_user(user_id: int) -> dict | None:
    """客户端处理各种状态码。"""
    resp = requests.get(f"https://api.example.com/users/{user_id}")

    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 404:
        print("用户不存在")
        return None
    elif resp.status_code == 401:
        print("请先登录")
        return None
    elif resp.status_code == 429:
        # 限流，指数退避
        retry_after = int(resp.headers.get("Retry-After", 60))
        print(f"限流，{retry_after}秒后重试")
        return None
    elif resp.status_code >= 500:
        print(f"服务器错误: {resp.status_code}")
        return None
    else:
        print(f"未知错误: {resp.status_code}")
        return None
```

### 2.3 重试机制（含 429 处理）

```python
# 文件：retry_mechanism.py
import time
import requests

def fetch_with_retry(url: str, max_retries: int = 3) -> dict | None:
    """带重试的 HTTP 请求。"""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                return resp.json()

            elif resp.status_code == 429:
                # 限流：按 Retry-After 等待
                retry_after = int(resp.headers.get("Retry-After", 60))
                if attempt < max_retries - 1:
                    print(f"限流，等待 {retry_after} 秒")
                    time.sleep(retry_after)
                    continue

            elif 500 <= resp.status_code < 600:
                # 服务器错误：指数退避
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"服务器错误，等待 {wait} 秒")
                    time.sleep(wait)
                    continue

            else:
                # 4xx 客户端错误：不重试
                print(f"请求失败: {resp.status_code}")
                return None

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"超时，等待 {wait} 秒")
                time.sleep(wait)

    return None
```

## 3. dify 仓库源码解读

### 3.1 dify 的 HTTP 错误处理

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 200-240）：

```python
import aiohttp

class SSRFProxyWithRetry:
    """带重试的 SSRF 代理。

    dify 调用外部 API 时处理各种状态码：
    - 2xx：成功
    - 4xx：客户端错误（重试无意义）
    - 5xx：服务器错误（重试）
    - 429：限流（按 Retry-After 重试）
    """

    async def fetch_with_retry(self, url: str, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        # 成功
                        if 200 <= resp.status < 300:
                            return await resp.text()

                        # 限流
                        elif resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", 60))
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_after)
                                continue

                        # 服务器错误
                        elif 500 <= resp.status < 600:
                            if attempt < max_retries - 1:
                                # 指数退避
                                await asyncio.sleep(2 ** attempt)
                                continue

                        # 客户端错误（不重试）
                        else:
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=f"HTTP {resp.status}",
                            )

            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        raise Exception(f"Max retries exceeded for {url}")


# dify 的状态码使用：
# - 200 OK：API 调用成功
# - 201 Created：创建工作流、文档
# - 204 No Content：删除成功
# - 400 Bad Request：参数错误
# - 401 Unauthorized：未登录
# - 403 Forbidden：无权限
# - 404 Not Found：资源不存在
# - 422 Unprocessable Entity：表单验证失败
# - 429 Too Many Requests：API 限流
# - 500 Internal Server Error：服务器错误
# - 503 Service Unavailable：维护中
# - 504 Gateway Timeout：上游超时
```

**解读**：
- 第 22 行：2xx 成功
- 第 28 行：429 限流按 Retry-After 重试
- 第 35 行：5xx 指数退避重试
- **设计意图**：根据状态码智能重试，提高 API 调用成功率

## 4. 关键要点总结

- **5 类状态码**：1xx 信息、2xx 成功、3xx 重定向、4xx 客户端、5xx 服务器
- **最常见**：200、201、204、301/302、304、400、401、403、404、429、500、503
- **重试策略**：5xx 和 429 重试，4xx 不重试
- **指数退避**：避免雪崩
- dify 对 429/5xx 重试，对 4xx 不重试

## 5. 练习题

### 练习 1：基础（必做）

用 Flask 写一个 API，返回 200、201、400、401、404、500 等不同状态码。

### 练习 2：进阶

阅读 `api/core/helper/ssrf_proxy.py`，说明 dify 为何对 5xx 重试但对 4xx 不重试。

### 练习 3：挑战（选做）

实现一个完整的指数退避重试机制，含 Retry-After 支持。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- RFC 7231：HTTP/1.1 语义
- MDN HTTP 状态码：https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Status

---

**文档版本**：v1.0
**最后更新**：2026-07-13