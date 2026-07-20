# 13 @Controller / @RestController

> 掌握 Spring MVC 中 `@Controller` 与 `@RestController` 的差异，能在 ruoyi-vue-pro 中编写标准的 RESTful API。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@Controller` 与 `@RestController` 的差异
- 掌握 Controller 的标准写法（路径、方法、返回类型）
- 能在 ruoyi-vue-pro 中读懂 Controller 的代码结构
- 掌握 `CommonResult<T>` 统一返回类型的使用（统一返回专题见 [16-result-wrapper](./18-result-wrapper.md)）

## 📚 前置知识

- [01-ioc.md](./01-ioc.md)
- [11-config.md](./11-config.md)

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

## 3. 关键要点总结

- **`@RestController` = `@Controller` + `@ResponseBody`**，专用于 API
- **ruoyi 路径规范**：`/admin-api/{模块}/{业务}` 或 `/app-api/{模块}/{业务}`
- **统一返回**：`CommonResult<T>`（带 code、msg、data）
- **CRUD 命名**：`page`（分页）、`get`（详情）、`create`、`update`、`delete`
- **DefaultController 处理未启用模块的 404**
- **ruoyi 通过 `scanBasePackages` 扫描多模块**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
