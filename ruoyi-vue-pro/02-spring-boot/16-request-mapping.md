# 14 请求映射：@RequestMapping / @GetMapping

> 掌握 Spring MVC 的请求映射注解，能在 ruoyi-vue-pro 中正确编写 RESTful URL。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 `@RequestMapping`、`@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`
- 掌握路径变量、Ant 风格通配符、参数条件
- 能在 ruoyi-vue-pro 中读懂 URL 路径前缀机制
- 理解 HTTP 方法的语义（GET 幂等、POST 非幂等）

## 📚 前置知识

- [15-controller.md](./15-controller.md)

## 1. 核心概念

### 1.1 请求映射注解的层级关系

```
@RequestMapping
    ├── @GetMapping    (method = GET)
    ├── @PostMapping   (method = POST)
    ├── @PutMapping    (method = PUT)
    ├── @DeleteMapping (method = DELETE)
    └── @PatchMapping  (method = PATCH)
```

### 1.2 HTTP 方法语义

| 方法 | 语义 | 幂等 | 安全 |
|------|------|------|------|
| GET | 查询资源 | ✅ | ✅ |
| POST | 创建资源 | ❌ | ❌ |
| PUT | 全量更新 | ✅ | ❌ |
| PATCH | 部分更新 | ❌ | ❌ |
| DELETE | 删除资源 | ✅ | ❌ |

- **幂等**：多次执行结果相同（如 `GET /user/1` 永远返回用户 1）
- **安全**：不修改服务端状态

### 1.3 路径匹配模式

| 模式 | 匹配 | 例子 |
|------|------|------|
| `/user` | 精确路径 | `/user` |
| `/user/*` | 单层通配 | `/user/123` ✅，`/user/123/orders` ❌ |
| `/user/**` | 多层通配 | `/user`、`/user/123`、`/user/123/orders` ✅ |
| `/user/{id}` | 路径变量 | `/user/123` |
| `/user/{id:\\d+}` | 正则约束 | `/user/123` ✅，`/user/abc` ❌ |

## 2. 代码示例

### 2.1 基础映射

```java
// 文件：OrderController.java
@RestController
@RequestMapping("/admin-api/order")
public class OrderController {

    @GetMapping("/list")
    public CommonResult<List<OrderVO>> list() { ... }

    @GetMapping("/{id}")
    public CommonResult<OrderVO> get(@PathVariable Long id) { ... }

    @PostMapping("/create")
    public CommonResult<Long> create(@RequestBody OrderCreateReqVO req) { ... }

    @PutMapping("/update")
    public CommonResult<Boolean> update(@RequestBody OrderUpdateReqVO req) { ... }

    @DeleteMapping("/{id}")
    public CommonResult<Boolean> delete(@PathVariable Long id) { ... }
}
```

### 2.2 条件映射（headers / params / produces）

```java
@GetMapping(value = "/get", params = "type=vip")
public CommonResult<UserVO> getVipUser(@RequestParam Long id) { ... }

@PostMapping(value = "/create",
             consumes = MediaType.APPLICATION_JSON_VALUE,
             produces = MediaType.APPLICATION_JSON_VALUE)
public CommonResult<Long> create(@RequestBody UserCreateReqVO req) { ... }
```

### 2.3 路径变量 + 正则

```java
@GetMapping("/user/{id:\\d+}")
public CommonResult<UserVO> getUser(@PathVariable Long id) { ... }

@GetMapping("/files/{name:.+}")
public void download(@PathVariable String name, HttpServletResponse response) { ... }
```

## 3. 关键要点总结

- **专用注解优先**：`@GetMapping` > `@RequestMapping(method=GET)`
- **HTTP 方法语义**：GET 幂等、POST 非幂等、DELETE 幂等
- **路径变量**：`@PathVariable`，正则约束 `\\d+`
- **Ant 通配符**：`*` 单层、`**` 多层
- **ruoyi 路径前缀**：`/admin-api`（后台）、`/app-api`（前台），通过 `WebProperties` 配置
- **ruoyi 用 `WebMvcRegistrations` 统一设置前缀**，避免在每个 Controller 重复写

---

**文档版本**：v1.0
**最后更新**：2026-07-13
