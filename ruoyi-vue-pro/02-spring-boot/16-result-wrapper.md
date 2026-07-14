# 16 统一返回结果：Result / R

> 掌握 ruoyi-vue-pro 的统一返回结果 `CommonResult<T>`，理解其设计思想和最佳实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解统一返回结果的必要性
- 掌握 `CommonResult<T>` 的使用（success / error）
- 理解 `code` + `msg` + `data` 三要素
- 能在 ruoyi-vue-pro 中读懂所有 Controller 的返回类型

## 📚 前置知识

- 13-controller.md

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 CommonResult 完整源码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
**核心代码**（行 14-90）：

```java
/**
 * 通用返回
 *
 * @param <T> 数据泛型
 */
@Data
public class CommonResult<T> implements Serializable {

    /**
     * 错误码
     *
     * @see ErrorCode#getCode()
     */
    private Integer code;
    /**
     * 错误提示，用户可阅读
     */
    private String msg;
    /**
     * 返回数据
     */
    private T data;

    /**
     * 将传入的 result 对象，转换成另外一个泛型结果的对象
     */
    public static <T> CommonResult<T> error(CommonResult<?> result) {
        return error(result.getCode(), result.getMsg());
    }

    public static <T> CommonResult<T> error(Integer code, String message) {
        Assert.notEquals(GlobalErrorCodeConstants.SUCCESS.getCode(), code, "code 必须是错误的！");
        CommonResult<T> result = new CommonResult<>();
        result.code = code;
        result.msg = message;
        return result;
    }

    public static <T> CommonResult<T> error(ErrorCode errorCode, Object... params) {
        Assert.notEquals(GlobalErrorCodeConstants.SUCCESS.getCode(), errorCode.getCode(), "code 必须是错误的！");
        CommonResult<T> result = new CommonResult<>();
        result.code = errorCode.getCode();
        result.msg = ServiceExceptionUtil.doFormat(errorCode.getCode(), errorCode.getMsg(), params);
        return result;
    }
```

**解读**：
- 第 6 行：`@Data` Lombok 注解生成 getter / setter / equals / hashCode
- 第 8 行：`implements Serializable` 支持序列化（用于 Redis 缓存）
- 第 14-19 行：三个核心字段：`code`（状态码）、`msg`（提示）、`data`（数据）
- 第 26-28 行：`error(CommonResult)` 用于泛型转换
- 第 30-37 行：`error(code, msg)` 通用失败构造
- 第 39-46 行：`error(ErrorCode, params)` 支持 `{}` 占位符格式化（如 `"用户 {} 不存在"` → `"用户 1 不存在"`）
- **第 31 行**：`Assert.notEquals` 防止用 `error(0, ...)` 构造"假错误"（应该用 `success`）

### 3.2 success 和 isSuccess

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
**核心代码**（行 72-92）：

```java
public static <T> CommonResult<T> success(T data) {
    CommonResult<T> result = new CommonResult<>();
    result.code = GlobalErrorCodeConstants.SUCCESS.getCode();
    result.data = data;
    result.msg = "";
    return result;
}

public static boolean isSuccess(Integer code) {
    return Objects.equals(code, GlobalErrorCodeConstants.SUCCESS.getCode());
}

@JsonIgnore // 避免 jackson 序列化
public boolean isSuccess() {
    return isSuccess(code);
}

@JsonIgnore // 避免 jackson 序列化
public boolean isError() {
    return !isSuccess();
}
```

**解读**：
- 第 1-7 行：`success(data)` 构造成功返回，`msg` 默认为空字符串
- 第 9-11 行：静态方法 `isSuccess(code)` 工具方法
- 第 13-16 行：实例方法 `isSuccess()`，**注意 `@JsonIgnore`** —— 避免在 JSON 序列化时多出 `success` 字段
- 第 18-21 行：`isError()` 与 `isSuccess()` 相反
- **设计细节**：成功码来自 `GlobalErrorCodeConstants.SUCCESS`，避免硬编码 `0`

### 3.3 checkError 与 ServiceException 集成

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
**核心代码**（行 94-119）：

```java
// ========= 和 Exception 异常体系集成 =========

/**
 * 判断是否有异常。如果有，则抛出 {@link ServiceException} 异常
 */
public void checkError() throws ServiceException {
    if (isSuccess()) {
        return;
    }
    // 业务异常
    throw new ServiceException(code, msg);
}

/**
 * 判断是否有异常。如果有，则抛出 {@link ServiceException} 异常
 * 如果没有，则返回 {@link #data} 数据
 */
@JsonIgnore // 避免 jackson 序列化
public T getCheckedData() {
    checkError();
    return data;
}

public static <T> CommonResult<T> error(ServiceException serviceException) {
    return error(serviceException.getCode(), serviceException.getMessage());
}
```

**解读**：
- 第 5-11 行：`checkError()` 是 RPC 调用的"异常翻译"——把远程调用的失败结果翻译成本地异常
- 第 16-20 行：`getCheckedData()` 一步完成"检查 + 获取数据"
- 第 22-24 行：从 `ServiceException` 反向构造 `CommonResult`（用于异常处理器）
- **设计精髓**：
  - RPC 调用方用 `result.checkError()` 自动抛异常
  - 异常处理器用 `CommonResult.error(ex)` 把异常转成统一返回
  - 完美闭环："远程错误 → 本地异常 → 统一返回"

### 3.4 GlobalExceptionHandler 使用 CommonResult

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
**核心代码**（行 130-160）：

```java
/**
 * 处理 ServiceException 业务异常
 */
@ExceptionHandler(value = ServiceException.class)
public CommonResult<?> serviceExceptionHandler(ServiceException ex) {
    log.warn("[serviceExceptionHandler]", ex);
    // 插入异常日志
    createExceptionLog(ex, null);
    return CommonResult.error(ex.getCode(), ex.getMessage());
}
```

**解读**：
- 第 5 行：`@ExceptionHandler(value = ServiceException.class)` 拦截所有 `ServiceException`
- 第 8 行：插入异常日志（RPC 调用）
- 第 9 行：把异常转换为 `CommonResult` 返回（前端可读的统一格式）
- **完整链路**：Service 抛 `ServiceException` → `GlobalExceptionHandler` 捕获 → 记录日志 → 返回 `CommonResult` 错误响应

## 4. 关键要点总结

- **统一返回 = code + msg + data** 三要素
- **`CommonResult.success(data)`** 构造成功
- **`CommonResult.error(code, msg)`** 构造失败
- **成功码 = 0**（来自 `GlobalErrorCodeConstants.SUCCESS`）
- **业务异常抛 `ServiceException`**，由 `GlobalExceptionHandler` 统一处理
- **`checkError()` 用于 RPC 调用** 自动翻译异常
- **`@JsonIgnore` 避免序列化辅助方法**
- ruoyi 的 `CommonResult` 与 `ServiceException` 形成完美闭环

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `ApiResult<T>` 统一返回类，包含 `code`、`msg`、`data` 字段和 `success(T data)`、`error(int code, String msg)` 静态方法。

### 练习 2：进阶

阅读 `CommonResult.checkError()` 方法，解释为什么 ruoyi 用 `ServiceException` 而不是 `BusinessException`？这种设计对 RPC 调用有什么好处？

### 练习 3：挑战（选做）

扩展 `CommonResult`，添加 `traceId` 字段（用于分布式追踪），在所有 Controller 返回时自动注入当前请求的 traceId（用 MDC）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`
- ruoyi 错误码：https://doc.iocoder.cn/error-code/
- 芋道统一返回：https://doc.iocoder.cn/spring-boot-r/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
