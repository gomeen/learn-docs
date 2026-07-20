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
- MVC 分层（详见 [MVC 分层](./02-mvc-layers.md)）
- MapStruct 实战（详见 [MapStruct](./04-mapstruct-practice.md)）

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

## 3. 关键要点总结

- DO 是数据库映射，VO 是 HTTP 接口对象
- ruoyi 用 `BeanUtils.toBean` 进行基础属性拷贝
- 复杂转换写在 `XxxConvert` 类中，使用 `@Mapper` + `INSTANCE` 模式
- **N+1 优化**：批量查询关联表，转 Map 后 O(1) 查找
- `MapUtils.findAndThen` 避免空指针

---

**文档版本**：v1.0
**最后更新**：2026-07-13
