# 13 @Controller / @RestController

> 掌握 Spring MVC 中 `@Controller` 与 `@RestController` 的差异，能在 ruoyi-vue-pro 中编写标准的 RESTful API。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@Controller` 与 `@RestController` 的差异
- 掌握 Controller 的标准写法（路径、方法、返回类型）
- 能在 ruoyi-vue-pro 中读懂 Controller 的代码结构
- 掌握 `CommonResult<T>` 统一返回类型的使用

## 📚 前置知识

- 01-ioc.md
- 10-config.md

## 1. 核心概念

### 1.1 `@Controller` vs `@RestController`

| 特性 | `@Controller` | `@RestController` |
|------|--------------|-------------------|
| 用途 | MVC 控制器（返回视图） | RESTful API（返回 JSON） |
| 返回值 | 视图名 | 数据对象（自动转 JSON） |
| 等价于 | `@Controller` + 类级别 `@ResponseBody` | - |
| 适用 | 传统 Web（JSP、Thymeleaf） | 现代 API（前后端分离） |

### 1.2 Controller 的职责

- 接收 HTTP 请求（`@RequestMapping`）
- 解析参数（`@RequestParam`、`@PathVariable`、`@RequestBody`）
- 调用 Service 处理业务
- 返回数据（`CommonResult<T>`）或抛出异常

### 1.3 ruoyi-vue-pro 的 Controller 规范

```java
@RestController
@RequestMapping("/admin-api/system/user")
public class UserController {

    @GetMapping("/get")
    public CommonResult<UserVO> getUser(@RequestParam("id") Long id) { ... }

    @PostMapping("/create")
    public CommonResult<Long> createUser(@RequestBody UserCreateReqVO reqVO) { ... }
}
```

- **路径前缀**：`/admin-api`（后台）或 `/app-api`（前台）
- **模块路径**：`/system/user`（系统模块的用户管理）
- **业务路径**：`/get`、`/create`（动词或动作）
- **统一返回**：`CommonResult<T>`

## 2. 代码示例

### 2.1 基础 Controller

```java
// 文件：HelloController.java
@RestController
@RequestMapping("/admin-api/demo")
public class HelloController {

    @GetMapping("/hello")
    public CommonResult<String> hello() {
        return CommonResult.success("Hello World");
    }

    @GetMapping("/hello/{name}")
    public CommonResult<String> helloName(@PathVariable String name) {
        return CommonResult.success("Hello " + name);
    }
}
```

### 2.2 CRUD Controller

```java
// 文件：UserController.java
@RestController
@RequestMapping("/admin-api/system/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping("/page")
    public CommonResult<PageResult<UserVO>> page(@Valid UserPageReqVO req) {
        return CommonResult.success(userService.pageUser(req));
    }

    @GetMapping("/get")
    public CommonResult<UserVO> get(@RequestParam("id") Long id) {
        return CommonResult.success(userService.getUser(id));
    }

    @PostMapping("/create")
    public CommonResult<Long> create(@Valid @RequestBody UserCreateReqVO req) {
        return CommonResult.success(userService.createUser(req));
    }

    @PutMapping("/update")
    public CommonResult<Boolean> update(@Valid @RequestBody UserUpdateReqVO req) {
        userService.updateUser(req);
        return CommonResult.success(true);
    }

    @DeleteMapping("/delete")
    public CommonResult<Boolean> delete(@RequestParam("id") Long id) {
        userService.deleteUser(id);
        return CommonResult.success(true);
    }
}
```

### 2.3 返回视图的 Controller（非 ruoyi 风格）

```java
@Controller
@RequestMapping("/web")
public class WebController {

    @GetMapping("/login")
    public String loginPage() {
        return "login";  // 返回 templates/login.html
    }

    @PostMapping("/login")
    @ResponseBody
    public CommonResult<String> doLogin(@RequestBody LoginDTO dto) {
        return CommonResult.success("登录成功");
    }
}
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 DefaultController 处理未启用模块的 404

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
**核心代码**（行 1-50）：

```java
package cn.iocoder.yudao.server.controller;

import cn.iocoder.yudao.framework.common.pojo.CommonResult;
import cn.iocoder.yudao.framework.common.util.servlet.ServletUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.security.PermitAll;
import javax.servlet.http.HttpServletRequest;

import static cn.iocoder.yudao.framework.common.exception.enums.GlobalErrorCodeConstants.NOT_IMPLEMENTED;

/**
 * 默认 Controller，解决部分 module 未开启时的 404 提示。
 * 例如说，/bpm/** 路径，工作流
 *
 * @author 芋道源码
 */
@RestController
@Slf4j
public class DefaultController {

    @RequestMapping("/admin-api/bpm/**")
    public CommonResult<Boolean> bpm404() {
        return CommonResult.error(NOT_IMPLEMENTED.getCode(),
                "[工作流模块 yudao-module-bpm - 已禁用][参考 https://doc.iocoder.cn/bpm/ 开启]");
    }

    @RequestMapping("/admin-api/mp/**")
    public CommonResult<Boolean> mp404() {
        return CommonResult.error(NOT_IMPLEMENTED.getCode(),
                "[微信公众号 yudao-module-mp - 已禁用][参考 https://doc.iocoder.cn/mp/build/ 开启]");
    }
```

**解读**：
- 第 21 行：`@RestController` 表示该类所有方法返回 JSON（不渲染视图）
- 第 24-28 行：`/admin-api/bpm/**` 匹配工作流模块所有路径
- **核心设计**：当 `yudao-module-bpm` 模块未启用时，访问 `/admin-api/bpm/**` 不会返回 404，而是返回"已禁用"提示
- 第 30-34 行：另一个模块（`yudao-module-mp`）的兜底处理
- **路径通配符 `**`**：匹配多级路径，是 Ant 风格路径匹配

### 3.2 测试接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
**核心代码**（行 98-112）：

```java
/**
 * 测试接口：打印 query、header、body
 */
@RequestMapping(value = { "/test" })
@PermitAll
public CommonResult<Boolean> test(HttpServletRequest request) {
    // 打印查询参数
    log.info("Query: {}", ServletUtils.getParamMap(request));
    // 打印请求头
    log.info("Header: {}", ServletUtils.getHeaderMap(request));
    // 打印请求体
    log.info("Body: {}", ServletUtils.getBody(request));
    return CommonResult.success(true);
}
```

**解读**：
- 第 3 行：`@PermitAll`（来自 Spring Security）允许匿名访问
- 第 5-11 行：通过 `ServletUtils` 工具类读取 HTTP 请求的 query / header / body
- **设计意图**：开发环境调试用接口（排查接口联调问题）
- **ruoyi 风格**：直接注入 `HttpServletRequest`，用工具类提取请求信息

### 3.3 启动类的扫描配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
**核心代码**（行 14-17）：

```java
@SuppressWarnings("SpringComponentScan") // 忽略 IDEA 无法识别 ${yudao.info.base-package}
@SpringBootApplication(scanBasePackages = {"${yudao.info.base-package}.server", "${yudao.info.base-package}.module"})
public class YudaoServerApplication {
```

**解读**：
- 第 2 行：`scanBasePackages` 扫描 `cn.iocoder.yudao.server`（当前模块）和 `cn.iocoder.yudao.module`（所有业务模块）
- **Controller 扫描路径**：所有 `cn.iocoder.yudao.module.**.controller.*` 都会被注册为 Bean
- **路径前缀**：`YudaoWebAutoConfiguration` 给 admin 包下 Controller 加 `/admin-api` 前缀，app 包下加 `/app-api` 前缀

## 4. 关键要点总结

- **`@RestController` = `@Controller` + `@ResponseBody`**，专用于 API
- **ruoyi 路径规范**：`/admin-api/{模块}/{业务}` 或 `/app-api/{模块}/{业务}`
- **统一返回**：`CommonResult<T>`（带 code、msg、data）
- **CRUD 命名**：`page`（分页）、`get`（详情）、`create`、`update`、`delete`
- **DefaultController 处理未启用模块的 404**
- **ruoyi 通过 `scanBasePackages` 扫描多模块**

## 5. 练习题

### 练习 1：基础（必做）

编写一个 `DemoController`，提供 `/admin-api/demo/hello` 接口，返回 `CommonResult<String>` 类型，内容为"Hello, yudao!"。

### 练习 2：进阶

阅读 `DefaultController`，解释为什么用 `@RequestMapping("/admin-api/bpm/**")` 通配符？这种设计的好处是什么？

### 练习 3：挑战（选做）

实现一个 `UserController`，包含 `page`、`get`、`create`、`update`、`delete` 五个接口，参数用 `@Valid` 校验（@NotBlank、@Min、@Email 等），返回统一 `CommonResult`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/controller/DefaultController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/server/YudaoServerApplication.java`
- Spring MVC 官方文档：https://docs.spring.io/spring-framework/reference/web/webmvc.html
- 芋道 Spring MVC：https://doc.iocoder.cn/spring-boot-springmvc/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
