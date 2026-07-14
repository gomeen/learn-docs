# 7.1.4 DTO / VO / DO / BO 转换

> 理解 ruoyi 中四种对象的定位和转换方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 DO / VO / DTO / BO 的职责和使用场景
- 掌握 ruoyi 中 `BeanUtils.toBean` 的使用方法
- 理解对象转换在 ruoyi 业务中的最佳实践
- 能编写正确的对象转换代码

## 📚 前置知识

- Java Bean 规范
- Lombok 基础（@Data、@Builder）
- 02-mvc-layers.md

## 1. 核心概念

### 1.1 四种对象的定义

| 对象 | 全称 | 用途 | 命名 |
|------|------|------|------|
| **DO** | Data Object | 数据库表映射 | `XxxDO` |
| **VO** | View Object | HTTP 请求/响应 | `XxxReqVO` / `XxxRespVO` |
| **DTO** | Data Transfer Object | 内部服务间数据传输 | `XxxDTO` |
| **BO** | Business Object | 业务聚合对象 | `XxxBO` |

### 1.2 为什么要转换？

**场景**：用户详情页要返回给前端

```json
{
  "id": 1024,
  "username": "admin",
  "nickname": "芋道",
  "deptId": 1,
  "deptName": "研发部",   // ← 数据库里没有，要从 dept 表 JOIN
  "roleNames": ["管理员"]   // ← 多对多关系，需要查询
}
```

**DO 形态**（数据库原貌）：
```java
AdminUserDO { id, username, nickname, deptId, password, ... }
```

**VO 形态**（前端需要的）：
```java
UserRespVO { id, username, nickname, deptId, deptName, roleNames }
```

**转换过程**：
```
AdminUserDO + DeptDO + List<RoleDO>  →  UserRespVO
```

### 1.3 ruoyi 的对象转换工具

| 工具 | 用途 | 特点 |
|------|------|------|
| `BeanUtils.toBean(A, B.class)` | 简单属性拷贝 | 基于 Spring BeanUtils |
| `MapStruct` | 复杂转换 | 编译期生成代码 |
| `CollectionUtils.convertList` | 列表转换 | 配合 Lambda |
| `MapUtils.findAndThen` | Map 查找后操作 | 找不到不抛异常 |

## 2. 代码示例

### 2.1 BeanUtils.toBean 基本用法

```java
import cn.iocoder.yudao.framework.common.util.object.BeanUtils;

// 单个对象转换
UserRespVO vo = BeanUtils.toBean(userDO, UserRespVO.class);

// 列表转换
List<UserRespVO> voList = BeanUtils.toBean(userList, UserRespVO.class);
```

### 2.2 带额外字段的转换

```java
public class UserConvert {
    public UserRespVO convert(AdminUserDO user, DeptDO dept) {
        // 1. 先复制基本属性
        UserRespVO vo = BeanUtils.toBean(user, UserRespVO.class);
        // 2. 再设置额外字段
        if (dept != null) {
            vo.setDeptName(dept.getName());
        }
        return vo;
    }
}
```

### 2.3 集合转换的 Lambda 写法

```java
import static cn.iocoder.yudao.framework.common.util.collection.CollectionUtils.convertList;

// 列表转换
List<UserRespVO> voList = convertList(userList, user -> {
    UserRespVO vo = BeanUtils.toBean(user, UserRespVO.class);
    vo.setDeptName(deptMap.get(user.getDeptId()).getName());
    return vo;
});
```

### 2.4 Map 条件赋值

```java
import cn.iocoder.yudao.framework.common.util.collection.MapUtils;

// 当 deptMap 中存在 key 时执行赋值
MapUtils.findAndThen(deptMap, user.getDeptId(), dept -> {
    userVO.setDeptName(dept.getName());
});
```

## 3. ruoyi 仓库源码解读

### 3.1 UserConvert 转换器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/convert/user/UserConvert.java`

**核心代码**（行 22-45）：

```java
@Mapper
public interface UserConvert {

    UserConvert INSTANCE = Mappers.getMapper(UserConvert.class);

    default List<UserRespVO> convertList(List<AdminUserDO> list, Map<Long, DeptDO> deptMap) {
        return CollectionUtils.convertList(list, user -> convert(user, deptMap.get(user.getDeptId())));
    }

    default UserRespVO convert(AdminUserDO user, DeptDO dept) {
        UserRespVO userVO = BeanUtils.toBean(user, UserRespVO.class);
        if (dept != null) {
            userVO.setDeptName(dept.getName());
        }
        return userVO;
    }

    default List<UserSimpleRespVO> convertSimpleList(List<AdminUserDO> list, Map<Long, DeptDO> deptMap) {
        return CollectionUtils.convertList(list, user -> {
            UserSimpleRespVO userVO = BeanUtils.toBean(user, UserSimpleRespVO.class);
            MapUtils.findAndThen(deptMap, user.getDeptId(), dept -> userVO.setDeptName(dept.getName()));
            return userVO;
        });
    }
}
```

**解读**：
- 第 1 行：`@Mapper` 标记为 MapStruct 转换器
- 第 4 行：通过 `Mappers.getMapper` 获取单例实例
- 第 6-8 行：批量转换，传入 `deptMap` 用于查找
- 第 10-16 行：单个转换，先 `BeanUtils.toBean` 复制基础字段，再设置关联字段
- 第 18-24 行：精简版转换，使用 `MapUtils.findAndThen` 避免空指针

### 3.2 Service 中调用转换器

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
- 第 7 行：先调用 Service 拿到 DO 列表
- 第 8-10 行：空集合短路返回
- 第 12-13 行：批量查询所有部门，转成 `Map<id, dept>`（**N+1 优化**）
- 第 14 行：调用 `UserConvert.INSTANCE.convertList` 把 DO 转 VO

### 3.3 N+1 查询优化

```java
// ❌ 错误：每个用户都查一次部门（产生 N+1 查询）
List<UserRespVO> voList = userList.stream().map(user -> {
    DeptDO dept = deptService.getDept(user.getDeptId());  // N 次查询
    return UserConvert.INSTANCE.convert(user, dept);
}).toList();

// ✅ 正确：先批量查询，转 Map
List<Long> deptIds = convertList(userList, AdminUserDO::getDeptId);
Map<Long, DeptDO> deptMap = deptService.getDeptMap(deptIds);  // 1 次查询
List<UserRespVO> voList = UserConvert.INSTANCE.convertList(userList, deptMap);
```

## 4. 关键要点总结

- DO 是数据库映射，VO 是 HTTP 接口对象
- ruoyi 用 `BeanUtils.toBean` 进行基础属性拷贝
- 复杂转换写在 `XxxConvert` 类中，使用 `@Mapper` + `INSTANCE` 模式
- **N+1 优化**：批量查询关联表，转 Map 后 O(1) 查找
- `MapUtils.findAndThen` 避免空指针

## 5. 练习题

### 练习 1：基础（必做）

阅读 `DeptConvert.java`（在 `yudao-module-system` 下），找出它处理了哪些对象之间的转换。

### 练习 2：进阶

阅读 `OrderConvert.java`（在 `yudao-module-mall` 下），理解订单模块如何把 `OrderDO` + `OrderItemDO` 列表转换为 `OrderRespVO`。

### 练习 3：挑战（选做）

假设需要返回"用户的角色列表"，其中角色用 `,` 拼接的字符串。设计转换方法，避免在 Lambda 中产生 N+1 查询。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/convert/user/UserConvert.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/object/BeanUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
