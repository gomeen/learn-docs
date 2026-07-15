# 5.2 XSS 攻击与防护：存储型 / 反射型 / DOM 型

> 理解 XSS 三种类型的攻击原理，掌握 HTML 转义、CSP 白名单等防御手段。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分存储型、反射型、DOM 型 XSS 的攻击路径
- 用 HTML 转义、CSP 白名单过滤用户输入
- 识别 dify 和 ruoyi 中的 XSS 防护实现
- 在写 Web 页面时主动避免 XSS 漏洞

## 📚 前置知识

- HTML / JavaScript 基础
- HTTP 请求/响应模型
- [5.1 OWASP Top 10 概览](./01-owasp-top10.md)；Cookie 窃取相关见 [CSRF](./04-csrf.md) / [Session](../07-authentication/02-session-cookie.md)

## 1. 核心概念

### 1.1 什么是 XSS？

XSS（Cross-Site Scripting，跨站脚本攻击）指攻击者在网页中注入恶意 JavaScript 代码，当其他用户浏览该页面时执行这些代码。

**核心问题**：Web 应用把**用户输入**当作**代码**执行，违反了"数据与代码分离"原则。

### 1.2 XSS 三种类型

```
┌──────────────────────────────────────────────────────────────┐
│                       XSS 攻击分类                             │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   类型       │  注入位置     │  持久性       │  触发方式       │
├──────────────┼──────────────┼──────────────┼────────────────┤
│  存储型      │  服务器数据库  │  持久        │  其他用户访问    │
│  反射型      │  URL 参数     │  一次性      │  诱导点击链接    │
│  DOM 型      │  前端 JS     │  一次性      │  诱导点击链接    │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

#### 存储型 XSS（最危险）

```
攻击者提交评论:  <script>steal_cookie()</script>
       ↓
服务端存入数据库（未过滤）
       ↓
其他用户访问页面，服务端返回含恶意脚本的 HTML
       ↓
浏览器执行脚本，窃取用户 Cookie
```

#### 反射型 XSS

```
诱导用户点击: https://example.com/search?q=<script>steal()</script>
       ↓
服务端直接把 q 参数回显到页面
       ↓
浏览器执行脚本
```

#### DOM 型 XSS

```javascript
// 前端代码（不安全）
const url = new URL(window.location.href);
const name = url.searchParams.get("name");
document.body.innerHTML = `Hello, ${name}!`;
// 访问 ?name=<img src=x onerror=alert(1)> 即可触发
```

### 1.3 XSS 能做什么？

- 窃取 Cookie / Session
- 劫持用户账号
- 篡改页面内容（钓鱼）
- 发起 CSRF 请求
- 挖矿（浏览器挖矿脚本）
- 蠕虫传播（微博、空间 XSS 蠕虫）

### 1.4 防御手段

| 手段 | 原理 | 适用场景 |
|------|------|---------|
| HTML 转义 | `<` → `&lt;` | 任何用户输入回显 |
| CSP 策略 | 限制可执行脚本来源 | 整站 HTTP Header |
| 输入过滤 | 黑名单过滤 `<script>` | 已过时，不推荐 |
| 输出编码 | 按上下文编码（HTML/JS/URL） | 模板渲染时 |
| 富文本白名单 | Jsoup 等库按白名单过滤 | 富文本编辑器 |

## 2. 代码示例

### 2.1 反射型 XSS 漏洞示例

```python
# 文件：xss_vulnerable.py
# ❌ 故意写错的反射型 XSS 示例
from flask import Flask, request

app = Flask(__name__)

@app.route("/search")
def search():
    keyword = request.args.get("q", "")
    # ❌ 直接把用户输入嵌入 HTML，未转义
    return f"""
    <html>
      <body>
        <h1>搜索结果: {keyword}</h1>
      </body>
    </html>
    """
# 攻击：访问 /search?q=<script>alert(document.cookie)</script>
# 浏览器会执行 alert 并弹出用户的 Cookie
```

### 2.2 修正：使用 Jinja2 自动转义

```python
# 文件：xss_secure.py
# ✅ 正确做法：使用模板引擎自动转义
from flask import Flask, request, render_template_string

app = Flask(__name__)

TEMPLATE = """
<html>
  <body>
    <h1>搜索结果: {{ keyword }}</h1>
  </body>
</html>
"""

@app.route("/search")
def search():
    keyword = request.args.get("q", "")
    # ✅ Jinja2 默认开启自动转义：< → &lt;
    return render_template_string(TEMPLATE, keyword=keyword)
```

### 2.3 富文本场景：使用白名单库

```python
# 文件：rich_text_clean.py
# ✅ 富文本必须使用白名单过滤（不能简单转义，否则样式全没了）
import bleach

def clean_rich_text(html: str) -> str:
    """白名单过滤：只允许安全的标签和属性"""
    allowed_tags = ["p", "br", "strong", "em", "u", "ul", "ol", "li", "a"]
    allowed_attrs = {
        "a": ["href", "title", "target"],
    }
    cleaned = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=["http", "https", "mailto"],  # 只允许这些 URL 协议
        strip=True,  # 不允许的标签直接删除
    )
    return cleaned

# 测试
user_input = '<p>你好</p><script>alert(1)</script><a href="javascript:alert(1)">点我</a>'
print(clean_rich_text(user_input))
# 输出: <p>你好</p><a>点我</a>  ← script 被删，javascript: 协议被过滤
```

## 3. dify 仓库源码解读

### 3.1 dify 的 SSRF 防护（不只是 XSS，但思想通用：白名单 + 转义）

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
**核心代码**（行 145-180）：

```python
def make_request(method: str, url: str, max_retries: int = SSRF_DEFAULT_MAX_RETRIES, **kwargs: Any) -> httpx.Response:
    # Convert requests-style allow_redirects to httpx-style follow_redirects
    if "allow_redirects" in kwargs:
        allow_redirects = kwargs.pop("allow_redirects")
        if "follow_redirects" not in kwargs:
            kwargs["follow_redirects"] = allow_redirects

    if "timeout" not in kwargs:
        kwargs["timeout"] = httpx.Timeout(
            timeout=dify_config.SSRF_DEFAULT_TIME_OUT,
            connect=dify_config.SSRF_DEFAULT_CONNECT_TIME_OUT,
            read=dify_config.SSRF_DEFAULT_READ_TIME_OUT,
            write=dify_config.SSRF_DEFAULT_WRITE_TIME_OUT,
        )

    # prioritize per-call option, which can be switched on and off inside the HTTP node on the web UI
    verify_option = kwargs.pop("ssl_verify", dify_config.HTTP_REQUEST_NODE_SSL_VERIFY)
    if not isinstance(verify_option, bool):
        raise ValueError("ssl_verify must be a boolean")
    client = _get_ssrf_client(verify_option)
    ...
```

**解读**：
- 第 152 行：强制设置超时（防止慢速攻击）
- 第 161 行：把外部 URL 通过 Squid 代理转发（防御 SSRF）
- 第 162 行：参数类型校验（**输入校验是所有注入攻击的第一道防线**）
- **设计意图**：dify 的 HTTP 节点允许用户输入 URL，必须通过代理 + 超时 + 类型校验防御 SSRF/DoS

### 3.2 ruoyi 的 Jsoup XSS 清洗器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/xss/core/clean/JsoupXssCleaner.java`
**核心代码**（行 36-61）：

```java
private Safelist buildSafelist() {
    // 使用 jsoup 提供的默认的
    Safelist relaxedSafelist = Safelist.relaxed();
    // 富文本编辑时一些样式是使用 style 来进行实现的
    // 比如红色字体 style="color:red;", 所以需要给所有标签添加 style 属性
    // 注意：style 属性会有注入风险 <img STYLE="background-image:url(javascript:alert('XSS'))">
    relaxedSafelist.addAttributes(":all", "style", "class");
    // 保留 a 标签的 target 属性
    relaxedSafelist.addAttributes("a", "target");
    // 支持img 为base64
    relaxedSafelist.addProtocols("img", "src", "data");

    // 保留相对路径, 保留相对路径时，必须提供对应的 baseUri 属性，否则依然会被删除
    // WHITELIST.preserveRelativeLinks(false);

    // 移除 a 标签和 img 标签的一些协议限制，这会导致 xss 防注入失效，如 <img src=javascript:alert("xss")>
    // 虽然可以重写 WhiteList#isSafeAttribute 来处理，但是有隐患，所以暂时不支持相对路径
    // WHITELIST.removeProtocols("a", "href", "ftp", "http", "https", "mailto");
    // WHITELIST.removeProtocols("img", "src", "http", "https");
    return relaxedSafelist;
}

@Override
public String clean(String html) {
    return Jsoup.clean(html, baseUri, safelist, new Document.OutputSettings().prettyPrint(false));
}
```

**解读**：
- 第 38 行：使用 Jsoup 的 `Safelist.relaxed()` 作为基础白名单
- 第 42 行：扩展支持 `style`、`class` 属性——**但代码注释明确警示了 STYLE 注入风险**
- 第 46 行：`data` 协议白名单（让 img 支持 base64）
- 第 51-54 行的注释解释了**为什么不放行相对路径**——避免协议绕过
- 第 60 行：`Jsoup.clean` 按白名单清洗 HTML，不在白名单的标签/属性/协议全部删除
- **设计意图**：富文本场景必须在"保留样式"与"安全"之间权衡，ruoyi 选择"白名单 + 严格协议"

## 4. 关键要点总结

- XSS 分为存储型（持久）、反射型（一次性）、DOM 型（前端）
- **永远不要信任用户输入**：要么转义，要么用白名单过滤
- 富文本场景使用 Jsoup / bleach 按白名单过滤
- 模板引擎默认开启自动转义（Jinja2、React 默认转义）
- dify + ruoyi 都采用"白名单 + 严格协议"的清洗策略

## 5. 练习题

### 练习 1：基础（必做）

写一个 Flask 路由，接受用户输入的"昵称"并显示在欢迎页面上。要求：
1. 必须防御反射型 XSS
2. 测试 `<script>alert(1)</script>` 输入，确认不会执行

**参考答案**：见 `solutions/02-xss-basic.md`

### 练习 2：进阶

阅读 ruoyi 的 `JsoupXssCleaner.java` 和 `XssFilter.java`，画出完整的 XSS 防护链路：`HTTP 请求 → Filter → RequestWrapper → Controller`。

### 练习 3：挑战（选做）

实现一个 CSP（Content-Security-Policy）中间件，要求：
- 只允许加载同源脚本
- 禁止 inline `<script>` 执行
- 只允许 HTTPS 图片

提示：返回 HTTP Header `Content-Security-Policy: default-src 'self'; img-src 'self' https:; script-src 'self'`

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/ssrf_proxy.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/xss/core/clean/JsoupXssCleaner.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/xss/core/filter/XssFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/xss/core/filter/XssRequestWrapper.java`
- OWASP XSS 防护手册：https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13