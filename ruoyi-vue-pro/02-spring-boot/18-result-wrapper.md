# 16 统一返回结果：Result / R

> 掌握 ruoyi-vue-pro 的统一返回结果 `CommonResult<T>`，理解其设计思想和最佳实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解统一返回结果的必要性
- 掌握 `CommonResult<T>` 的使用（success / error）
- 理解 `code` + `msg` + `data` 三要素
- 能在 ruoyi-vue-pro 中读懂所有 Controller 的返回类型

## 📚 前置知识

- [15-controller.md](./15-controller.md)
- 泛型（详见 [03-generics](../01-java-fundamentals/03-generics.md)）

## 1. 核心概念

### 1.1 为什么需要统一返回？

**没有统一返回时**，前端要处理各种格式：

```json
// 成功时
{"id": 1, "name": "foo"}
// 失败时
{"error": "用户不存在"}
// 异常时
"Internal Server Error"  // 500 错误页
```

**统一返回后**，前端只需处理一种格式：

```json
{
  "code": 0,
  "msg": "success",
  "data": {"id": 1, "name": "foo"}
}
```

**好处**：
- 前端处理逻辑统一（判断 `code == 0`）
- 错误信息统一（`msg` 字段）
- 业务数据在 `data` 字段

### 1.2 ruoyi 的 `CommonResult<T>`

```java
public class CommonResult<T> {
    private Integer code;   // 状态码：0 成功，其他失败
    private String msg;     // 提示信息
    private T data;         // 业务数据
}
```

**静态工厂方法**：
- `CommonResult.success(data)`：成功
- `CommonResult.error(code, msg)`：失败
- `CommonResult.error(ErrorCode, params)`：带格式化消息的失败

## 2. 代码示例

### 2.1 基础用法

```java
// 文件：UserController.java
@RestController
@RequestMapping("/admin-api/user")
public class UserController {

    @GetMapping("/get")
    public CommonResult<UserVO> get(@RequestParam Long id) {
        UserVO user = userService.getUser(id);
        return CommonResult.success(user);  // 成功
    }

    @GetMapping("/forbidden")
    public CommonResult<UserVO> forbidden() {
        return CommonResult.error(403, "禁止访问");  // 失败
    }
}
```

### 2.2 与 ServiceException 配合

```java
// 文件：UserServiceImpl.java
@Service
public class UserServiceImpl {
    public UserVO getUser(Long id) {
        UserDO user = userDao.selectById(id);
        if (user == null) {
            // 抛业务异常，由 GlobalExceptionHandler 统一处理
            throw exception(USER_NOT_EXISTS);
        }
        return UserVO.from(user);
    }
}
```

### 2.3 checkError 用于 RPC 调用

```java
CommonResult<UserVO> result = userRpc.getUser(id);
result.checkError();  // 如果 code != 0，抛 ServiceException
UserVO user = result.getCheckedData();  // 安全获取 data
```

## 3. 关键要点总结

- **统一返回 = code + msg + data** 三要素
- **`CommonResult.success(data)`** 构造成功
- **`CommonResult.error(code, msg)`** 构造失败
- **成功码 = 0**（来自 `GlobalErrorCodeConstants.SUCCESS`）
- **业务异常抛 `ServiceException`**，由 `GlobalExceptionHandler` 统一处理
- **`checkError()` 用于 RPC 调用** 自动翻译异常
- **`@JsonIgnore` 避免序列化辅助方法**
- ruoyi 的 `CommonResult` 与 `ServiceException` 形成完美闭环

---

**文档版本**：v1.0
**最后更新**：2026-07-13
