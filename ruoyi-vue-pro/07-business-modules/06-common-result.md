# 7.1.6 通用 CRUD：PageResult / CommonResult

> 掌握 ruoyi 中两个核心通用对象：CommonResult（统一响应）和 PageResult（分页结果）。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `CommonResult` 的设计思想和字段含义
- 掌握 `success()` / `error()` 工厂方法的使用
- 理解 `PageResult` 的分页返回结构
- 能在 Controller 中返回统一的响应格式

## 📚 前置知识

- Java 泛型
- Spring Boot 基础
- HTTP 响应基础

## 1. 核心概念

### 1.1 统一响应：CommonResult

**为什么需要统一响应？**
```json
// ❌ 直接返回对象
GET /system/user/get?id=1
{ "id": 1, "username": "admin" }
// 问题：如何表示错误？如何统一错误码？前端要写多种解析

// ✅ 统一包装
GET /system/user/get?id=1
{
  "code": 0,
  "msg": "",
  "data": { "id": 1, "username": "admin" }
}
// 好处：code 0 表示成功，非 0 表示错误
```

**CommonResult 的字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | Integer | 错误码（0 成功） |
| `msg` | String | 提示信息（错误时给用户看） |
| `data` | T | 业务数据 |

### 1.2 分页结果：PageResult

**为什么需要 PageResult？**
- 后端分页：避免一次性查 100 万条
- 前后端约定：必须同时返回**总条数**和**当前页数据**

```java
{
  "code": 0,
  "data": {
    "total": 100,        // 总条数
    "list": [ {...}, ... ] // 当前页数据
  }
}
```

### 1.3 ruoyi 的 Controller 返回规范

**所有 Controller 方法必须返回 `CommonResult<T>`**：

```java
@PostMapping("/create")
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    Long id = userService.createUser(reqVO);
    return success(id);  // 包装成 CommonResult
}
```

**统一拦截器**：`GlobalResponseBodyHandler` 把所有返回值包装成 CommonResult。

## 2. 代码示例

### 2.1 CommonResult 基础用法

```java
import static cn.iocoder.yudao.framework.common.pojo.CommonResult.success;
import static cn.iocoder.yudao.framework.common.pojo.CommonResult.error;

// 成功返回
return success(user);
return success(userList);
return success(); // 无数据

// 错误返回
return error(400, "参数错误");
return error(ErrorCode.USER_NOT_EXISTS);
return error(new ServiceException(500, "服务异常"));
```

### 2.2 PageResult 构造

```java
// 1. 完整构造
PageResult<UserRespVO> pageResult = new PageResult<>(voList, total);

// 2. 空结果
PageResult<UserRespVO> empty = new PageResult<>(0L);  // total = 0

// 3. 静态工厂
PageResult<UserRespVO> empty = PageResult.empty();
```

### 2.3 完整的分页 Controller

```java
@GetMapping("/page")
public CommonResult<PageResult<UserRespVO>> getUserPage(@Valid UserPageReqVO pageReqVO) {
    PageResult<AdminUserDO> pageResult = userService.getUserPage(pageReqVO);
    if (CollUtil.isEmpty(pageResult.getList())) {
        return success(new PageResult<>(pageResult.getTotal()));  // 空结果
    }
    // 转换为 VO
    List<UserRespVO> voList = UserConvert.INSTANCE.convertList(pageResult.getList(), deptMap);
    return success(new PageResult<>(voList, pageResult.getTotal()));
}
```

### 2.4 Service 层抛出业务异常

```java
// Service 中
public UserDO getUser(Long id) {
    UserDO user = userMapper.selectById(id);
    if (user == null) {
        throw exception(ErrorCode.USER_NOT_EXISTS);  // 业务异常
    }
    return user;
}
// 全局异常处理器自动转换为 CommonResult.error
```

## 3. ruoyi 仓库源码解读

### 3.1 CommonResult 源码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`

**核心代码**（行 19-78）：

```java
@Data
public class CommonResult<T> implements Serializable {

    /**
     * 错误码
     */
    private Integer code;
    /**
     * 错误提示
     */
    private String msg;
    /**
     * 返回数据
     */
    private T data;

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

    public static <T> CommonResult<T> success(T data) {
        CommonResult<T> result = new CommonResult<>();
        result.code = GlobalErrorCodeConstants.SUCCESS.getCode();
        result.data = data;
        result.msg = "";
        return result;
    }
}
```

**解读**：
- 第 7-15 行：三个核心字段：code、msg、data
- 第 24-32 行：`error()` 工厂方法，断言 code 不能是 0（成功）
- 第 34-41 行：`error(ErrorCode, ...)` 支持消息模板参数化
- 第 43-49 行：`success()` 工厂方法，code 自动设为 0

### 3.2 PageResult 源码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/PageResult.java`

**核心代码**（行 12-39）：

```java
@Schema(description = "分页结果")
@Data
public final class PageResult<T> implements Serializable {

    @Schema(description = "总量", requiredMode = Schema.RequiredMode.REQUIRED)
    private Long total;

    @Schema(description = "数据", requiredMode = Schema.RequiredMode.REQUIRED)
    private List<T> list;

    public PageResult() {}

    public PageResult(List<T> list, Long total) {
        this.list = list;
        this.total = total;
    }

    public PageResult(Long total) {
        this.list = new ArrayList<>();
        this.total = total;
    }

    public static <T> PageResult<T> empty() {
        return new PageResult<>(0L);
    }

    public static <T> PageResult<T> empty(Long total) {
        return new PageResult<>(total);
    }
}
```

**解读**：
- 第 6-7 行：核心字段：`total`（总条数）和 `list`（当前页数据）
- 第 14-17 行：完整构造，传入 list 和 total
- 第 19-22 行：空数据构造，只有 total，list 是空 ArrayList
- 第 24-29 行：静态工厂方法

### 3.3 实际使用示例

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`

**核心代码**（行 102-115）：

```java
@GetMapping("/page")
@Operation(summary = "获得用户分页列表")
@PreAuthorize("@ss.hasPermission('system:user:query')")
public CommonResult<PageResult<UserRespVO>> getUserPage(@Valid UserPageReqVO pageReqVO) {
    // 获得用户分页列表
    PageResult<AdminUserDO> pageResult = userService.getUserPage(pageReqVO);
    if (CollUtil.isEmpty(pageResult.getList())) {
        return success(new PageResult<>(pageResult.getTotal()));
    }
    // 拼接数据
    Map<Long, DeptDO> deptMap = deptService.getDeptMap(
            convertList(pageResult.getList(), AdminUserDO::getDeptId));
    return success(new PageResult<>(UserConvert.INSTANCE.convertList(pageResult.getList(), deptMap),
            pageResult.getTotal()));
}
```

**解读**：
- 第 7-9 行：Service 返回 `PageResult<DO>`，需要转成 `PageResult<VO>`
- 第 10-12 行：空集合短路，直接返回只有 total 的 PageResult
- 第 14-15 行：批量查询关联数据（避免 N+1）
- 第 16-17 行：调用 Convert 转 VO 后包装成 PageResult

## 4. 关键要点总结

- `CommonResult<T>` 是 ruoyi 统一响应包装类
- `success(data)` / `error(code, msg)` 是常用工厂方法
- `PageResult<T>` 包含 `total` 和 `list` 两个字段
- 所有 Controller 必须返回 `CommonResult<T>`，由全局拦截器处理
- Service 层通过抛 `ServiceException` 实现错误返回
- 错误码定义在 `ErrorCode` 枚举中

## 5. 练习题

### 练习 1：基础（必做）

打开 `DictController.java`（在 `yudao-module-system` 下），找出 3 个返回 `CommonResult` 的方法，理解 `success()` 和 `error()` 的使用。

### 练习 2：进阶

阅读 `GlobalResponseBodyHandler.java`（在 `yudao-framework` 下），理解 ruoyi 如何**自动**把 Controller 返回值包装成 CommonResult。

### 练习 3：挑战（选做）

设计一个 `CommonResult.error()` 的扩展方法，支持传入具体的业务错误码枚举 `ErrorCode.USER_NOT_EXISTS` + 动态参数（比如用户名），让 msg 自动拼接成"用户 [admin] 不存在"。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/CommonResult.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/pojo/PageResult.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
