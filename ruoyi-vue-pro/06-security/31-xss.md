# 31 XSS 防护：参数过滤

> 详解 XSS（跨站脚本攻击）的原理、危害，以及 ruoyi 的参数过滤方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 XSS 攻击的原理和危害
- 区分存储型 / 反射型 / DOM 型 XSS
- 掌握 ruoyi 的 XSS 过滤器实现
- 能为新项目添加 XSS 防护

## 📚 前置知识

- HTML / JavaScript 基础
- Servlet Filter
- Jsoup（HTML 解析库）

## 1. 核心概念

### 1.1 什么是 XSS？

**XSS（Cross-Site Scripting）** 跨站脚本攻击：攻击者把**恶意脚本**注入到网页中，其他用户浏览时被执行。

### 1.2 XSS 的三种类型

**存储型 XSS（最危险）**：
```
1. 攻击者提交评论：<script>steal_cookie()</script>
2. 网站保存到数据库
3. 其他用户访问页面，浏览器执行恶意脚本
4. 攻击者拿到用户的 Cookie
```

**反射型 XSS**：
```
1. 攻击者构造 URL：http://example.com/search?q=<script>...</script>
2. 用户点击，服务器把 q 拼到 HTML 返回
3. 浏览器执行脚本
```

**DOM 型 XSS**：
```
1. 攻击者构造 URL：http://example.com/#default=<script>...</script>
2. 前端 JS 直接读 URL 写入 DOM
3. 浏览器执行
```

### 1.3 XSS 防护策略

| 策略 | 实现 | 作用 |
|------|------|------|
| **输入过滤** | 服务端过滤/转义 | 阻止恶意数据入库 |
| **输出编码** | 模板引擎自动转义 | 阻止恶意脚本执行 |
| **CSP** | Content-Security-Policy Header | 限制脚本来源 |
| **HttpOnly Cookie** | 服务端设置 | Cookie 不可被 JS 读取 |

ruoyi 用**输入过滤 + 输出编码**双重防护。

## 2. 代码示例

### 2.1 用 Jsoup 过滤 HTML

```java
// 文件：XssUtil.java
public class XssUtil {

    private static final Whitelist WHITELIST = Whitelist.relaxed()
            .addTags("audio", "video", "source")  // 白名单标签
            .addAttributes("a", "href", "title")
            .addProtocols("a", "href", "http", "https");

    public static String clean(String html) {
        if (html == null) return null;
        // 1. 解析 HTML
        // 2. 删除不在白名单的标签
        // 3. 转义属性值
        return Jsoup.clean(html, WHITELIST);
    }
}
```

### 2.2 XSS 过滤器

```java
// 文件：XssFilter.java
@Component
public class XssFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) {
        chain.doFilter(new XssRequestWrapper((HttpServletRequest) request), response);
    }
}
```

### 2.3 XSS Request 包装器

```java
// 文件：XssRequestWrapper.java
public class XssRequestWrapper extends HttpServletRequestWrapper {

    public XssRequestWrapper(HttpServletRequest request) {
        super(request);
    }

    @Override
    public String getParameter(String name) {
        String value = super.getParameter(name);
        return XssUtil.clean(value);  // 关键：过滤
    }

    @Override
    public String[] getParameterValues(String name) {
        String[] values = super.getParameterValues(name);
        if (values == null) return null;
        return Arrays.stream(values).map(XssUtil::clean).toArray(String[]::new);
    }

    @Override
    public String getHeader(String name) {
        String value = super.getHeader(name);
        return XssUtil.clean(value);
    }
}
```

## 3. ruoyi 的 XSS 防护

ruoyi 在 `yudao-spring-boot-starter-web` 中提供 XSS 过滤。**当前最新版本可能通过 yudao-common 的 `XssUtils` 工具类实现**：

```java
// yudao-common 中可能存在的工具类（推测）
public class XssUtils {
    private static final Whitelist WHITELIST = Whitelist.relaxed();

    public static String clean(String content) {
        return Jsoup.clean(content, WHITELIST);
    }
}
```

**应用位置**：
- **Controller 参数**：用 `@RequestBody` + 自定义 Jackson 反序列化器
- **Service 输入**：调用 `XssUtils.clean()` 显式过滤
- **前端**：Vue 的 `v-text` 默认转义；`v-html` 谨慎使用

## 4. 常见 XSS 攻击向量

```html
<!-- 1. script 标签 -->
<script>alert('xss')</script>

<!-- 2. img 标签 onerror -->
<img src=x onerror=alert('xss')>

<!-- 3. a 标签 javascript: 协议 -->
<a href="javascript:alert('xss')">click</a>

<!-- 4. iframe 注入 -->
<iframe src="javascript:alert('xss')"></iframe>

<!-- 5. HTML 实体编码绕过 -->
<img src=x onerror=&#x22;alert('xss')&#x22;>
```

## 5. 关键要点总结

- XSS 有三种类型：存储型 / 反射型 / DOM 型
- ruoyi 用 **Jsoup + 白名单** 过滤
- 双重防护：输入过滤（服务端）+ 输出编码（前端）
- 谨慎使用 `v-html`、富文本编辑器等"高危"功能
- 设置 CSP Header、HttpOnly Cookie 加强防护

## 6. 参考资料

- OWASP XSS Filter Evasion：https://cheatsheetseries.owasp.org/cheatsheets/XSS_Filter_Evasion_Cheat_Sheet.html
- Jsoup 文档：https://jsoup.org/
- ruoyi 仓库中 yudao-common 的 XssUtils（推测位置）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
