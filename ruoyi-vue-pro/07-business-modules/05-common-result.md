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
- HTTP 响应与统一包装（详见 [Result 包装](../02-spring-boot/18-result-wrapper.md)、[异常处理](../02-spring-boot/20-exception-handler.md)）

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

## 3. 关键要点总结

- `CommonResult<T>` 是 ruoyi 统一响应包装类
- `success(data)` / `error(code, msg)` 是常用工厂方法
- `PageResult<T>` 包含 `total` 和 `list` 两个字段
- 所有 Controller 必须返回 `CommonResult<T>`，由全局拦截器处理
- Service 层通过抛 `ServiceException` 实现错误返回
- 错误码定义在 `ErrorCode` 枚举中

---

**文档版本**：v1.0
**最后更新**：2026-07-13
