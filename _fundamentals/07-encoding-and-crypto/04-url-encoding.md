# 1.4 URL 编码（Percent Encoding）

> URL 编码（Percent Encoding）让 URL 能包含任意字符，是 HTTP 协议的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 URL 编码的原理
- 掌握 URL 编码的规则（哪些字符需要编码）
- 在 Python/Java 中正确处理 URL
- 区分 URL 编码 vs Base64

## 📚 前置知识

- 01-encoding.md
- HTTP 基础

## 1. 核心概念

### 1.1 为什么需要 URL 编码？

URL 只能使用有限的字符集：
- ASCII 字母、数字、少数符号
- 中文、空格、特殊字符必须编码
- 编码格式：`%XX`（XX 是 16 进制 ASCII）

### 1.2 哪些字符需要编码？

| 类别 | 字符 | 是否编码 |
|------|------|---------|
| 字母数字 | A-Z, a-z, 0-9 | ❌ 不编码 |
| 保留字符 | `:/?#[]@!$&'()*+,;=` | 部分编码（看上下文） |
| 不安全字符 | 空格、中文、`<>` | ✅ 编码 |
| 控制字符 | 换行、回车 | ✅ 编码 |

### 1.3 编码规则

```
空格 → %20（或 +，但 + 在 query 中表示空格）
中文 "你" → %E4%BD%A0
+ → %2B
/ → %2F
? → %3F
```

### 1.4 URL 编码 vs Base64

| 维度 | URL 编码 | Base64 |
|------|---------|--------|
| 输出 | `%XX` 形式 | A-Za-z0-9+/= |
| 可读性 | 中（%XX） | 高（看字母） |
| 长度膨胀 | 1 字节 → 3 字符（UTF-8） | 3 字节 → 4 字符 |
| 用途 | URL 参数 | 二进制文本化 |

## 2. 代码示例

### 2.1 Python urllib 编码

```python
from urllib.parse import quote, unquote

# URL 编码
text = "你好，世界！"
encoded = quote(text)
print(encoded)  # %E4%BD%A0%E5%A5%BD%EF%BC%8C%E4%B8%96%E7%95%8C%EF%BC%81

# URL 解码
decoded = unquote(encoded)
print(decoded)  # 你好，世界！

# 路径编码（保留 /）
encoded_path = quote("/api/users/张三", safe="/")
print(encoded_path)  # /api/users/%E5%BC%A0%E4%B8%89
```

### 2.2 Query String 编码

```python
from urllib.parse import urlencode, parse_qs

# 构造 query string
params = {"name": "Alice", "city": "北京", "tags": ["python", "AI"]}
query = urlencode(params, doseq=True)
print(query)  # name=Alice&city=%E5%8C%97%E4%BA%AC&tags=python&tags=AI

# 解析 query string
parsed = parse_qs(query)
print(parsed)
# {'name': ['Alice'], 'city': ['北京'], 'tags': ['python', 'AI']}
```

### 2.3 常见错误

```python
from urllib.parse import quote

# ❌ 错误：手动拼接 URL（未编码）
url = f"https://api.example.com/search?q={query}"
# 如果 query 含空格或中文，URL 会被破坏

# ✅ 正确：用 quote 编码参数
url = f"https://api.example.com/search?q={quote(query)}"
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 URL 提取（编码相关）

**位置**：`/Users/xu/code/github/dify/api/services/account_service.py`（或类似）
**核心代码**：

```python
import re
from urllib.parse import urlparse, parse_qs

def extract_url_params(url: str) -> dict:
    """提取 URL 参数"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return params
```

**解读**：
- `urlparse` 自动处理 URL 编码
- `parse_qs` 解析 query string（自动解码 %XX）

### 3.2 ruoyi 的 HTTP 请求（URL 编码）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/`
**核心代码**：

```java
// Spring WebClient URL 编码
String encoded = UriComponentsBuilder
    .fromUriString("https://api.example.com/search")
    .queryParam("q", "你好世界")
    .build()
    .encode()  // 自动编码
    .toUriString();

// 结果：https://api.example.com/search?q=%E4%BD%A0%E5%A5%BD%E4%B8%96%E7%95%8C
```

**解读**：
- Spring `UriComponentsBuilder` 自动处理 URL 编码
- 中文参数自动转 `%XX`

## 4. 关键要点总结

- URL 编码 = `%XX` 形式
- 字母数字不编码，特殊字符编码
- Python `urllib.parse.quote/unquote`
- Java Spring `UriComponentsBuilder` 自动编码
- 不要手动拼接 URL（易出错）

## 5. 练习题

### 练习 1：基础
把 `"https://example.com/search?q=你好"` 编码为合法的 URL。

### 练习 2：进阶
解析一个复杂的 URL（含 query + fragment + 中文），提取所有参数。

## 6. 参考资料

- RFC 3986：https://tools.ietf.org/html/rfc3986
- Python urllib：https://docs.python.org/3/library/urllib.parse.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13