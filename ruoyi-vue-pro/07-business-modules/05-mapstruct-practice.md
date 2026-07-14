# 7.1.5 MapStruct 转换实战

> 掌握 ruoyi 中 MapStruct 的使用方式，能编写复杂的对象转换逻辑。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MapStruct 的原理和优势
- 掌握 `@Mapper` 注解的常用配置
- 学会编写带 `default` 方法的复杂转换
- 能在 ruoyi 中编写自定义 Convert 类

## 📚 前置知识

- Java 8 Lambda
- 04-dto-vo-do.md
- MapStruct 基础概念

## 1. 核心概念

### 1.1 MapStruct 是什么？

**MapStruct** 是一个**编译期**生成 Bean 转换代码的框架。相比反射（BeanUtils）有以下优势：
- **编译期生成**：类型安全、运行快（无反射）
- **自动映射**：同名同类型属性自动拷贝
- **复杂映射**：支持自定义方法、SpEL 表达式

**原理**：
```
@Mapper 接口 → 编译期 → 自动生成 Impl 类（继承抽象方法 + 实现 default）
```

### 1.2 ruoyi 中的 MapStruct 模式

ruoyi 使用的是 **"@Mapper + INSTANCE + default 方法"** 模式：

```java
@Mapper
public interface UserConvert {
    UserConvert INSTANCE = Mappers.getMapper(UserConvert.class);

    // 简单映射：MapStruct 自动生成
    UserVO convert(UserDO user);

    // 复杂映射：用 default 方法手写
    default List<UserVO> convertList(List<UserDO> list, Map<Long, DeptDO> deptMap) {
        // 自定义逻辑
    }
}
```

**两种用法对比**：

| 场景 | 用法 | 说明 |
|------|------|------|
| 属性名一致 | `UserVO convert(UserDO user);` | 编译期自动生成 |
| 需要额外字段 | `default UserVO convert(...)` | 自己写逻辑 |
| 列表转换 | `default List<UserVO> convertList(...)` | 遍历调用单个转换 |

### 1.3 ruoyi 常用转换工具

```java
// 单个对象
UserVO vo = BeanUtils.toBean(userDO, UserVO.class);

// 列表转换
List<UserVO> voList = BeanUtils.toBean(userList, UserVO.class);

// 复杂转换（MapStruct）
List<UserVO> voList = UserConvert.INSTANCE.convertList(userDOList, deptMap);
```

## 2. 代码示例

### 2.1 最简单的 MapStruct 用法

```java
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

@Mapper
public interface UserConvert {
    UserConvert INSTANCE = Mappers.getMapper(UserConvert.class);

    // 同名同类型自动映射
    UserRespVO convert(AdminUserDO user);
}
```

```java
// 调用
UserRespVO vo = UserConvert.INSTANCE.convert(userDO);
```

### 2.2 字段名不一致的映射

```java
@Mapper
public interface OrderConvert {
    OrderConvert INSTANCE = Mappers.getMapper(OrderConvert.class);

    @Mappings({
        @Mapping(source = "orderNo", target = "code"),
        @Mapping(source = "totalAmount", target = "amount")
    })
    OrderRespVO convert(OrderDO order);
}
```

### 2.3 集合转换的 default 方法

```java
@Mapper
public interface UserConvert {
    UserConvert INSTANCE = Mappers.getMapper(UserConvert.class);

    // 单个转换（MapStruct 生成）
    UserVO convert(UserDO user);

    // 列表转换（手写 default）
    default List<UserVO> convertList(List<UserDO> list) {
        if (list == null) {
            return Collections.emptyList();
        }
        return list.stream().map(this::convert).toList();
    }
}
```

### 2.4 复杂聚合转换

```java
@Mapper
public interface AuthConvert {
    AuthConvert INSTANCE = Mappers.getMapper(AuthConvert.class);

    default AuthPermissionInfoRespVO convert(AdminUserDO user,
                                              List<RoleDO> roleList,
                                              List<MenuDO> menuList) {
        return AuthPermissionInfoRespVO.builder()
                .user(BeanUtils.toBean(user, AuthPermissionInfoRespVO.UserVO.class))
                .roles(convertSet(roleList, RoleDO::getCode))
                .permissions(convertSet(menuList, MenuDO::getPermission))
                .menus(buildMenuTree(menuList))
                .build();
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AuthConvert 复杂聚合

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/convert/auth/AuthConvert.java`

**核心代码**（行 32-80）：

```java
default AuthPermissionInfoRespVO convert(AdminUserDO user, List<RoleDO> roleList, List<MenuDO> menuList) {
    return AuthPermissionInfoRespVO.builder()
            .user(BeanUtils.toBean(user, AuthPermissionInfoRespVO.UserVO.class))
            .roles(convertSet(roleList, RoleDO::getCode))
            // 权限标识信息
            .permissions(convertSet(menuList, MenuDO::getPermission))
            // 菜单树
            .menus(buildMenuTree(menuList))
            .build();
}

/**
 * 将菜单列表，构建成菜单树
 */
default List<AuthPermissionInfoRespVO.MenuVO> buildMenuTree(List<MenuDO> menuList) {
    if (CollUtil.isEmpty(menuList)) {
        return Collections.emptyList();
    }
    // 移除按钮
    menuList.removeIf(menu -> menu.getType().equals(MenuTypeEnum.BUTTON.getType()));
    // 排序
    menuList.sort(Comparator.comparing(MenuDO::getSort));

    // 构建菜单树（使用 LinkedHashMap 保持顺序）
    Map<Long, AuthPermissionInfoRespVO.MenuVO> treeNodeMap = new LinkedHashMap<>();
    menuList.forEach(menu -> treeNodeMap.put(menu.getId(),
            BeanUtils.toBean(menu, AuthPermissionInfoRespVO.MenuVO.class)));
    // 处理父子关系
    treeNodeMap.values().stream().filter(node -> ObjUtil.notEqual(node.getParentId(), ID_ROOT)).forEach(childNode -> {
        AuthPermissionInfoRespVO.MenuVO parentNode = treeNodeMap.get(childNode.getParentId());
        if (parentNode == null) {
            LoggerFactory.getLogger(getClass()).error("[buildRouterTree][resource({}) 找不到父资源({})]",
                    childNode.getId(), childNode.getParentId());
            return;
        }
        if (parentNode.getChildren() == null) {
            parentNode.setChildren(new ArrayList<>());
        }
        parentNode.getChildren().add(childNode);
    });
    // 获得到所有的根节点
    return filterList(treeNodeMap.values(), node -> ID_ROOT.equals(node.getParentId()));
}
```

**解读**：
- 第 2-9 行：聚合 3 个数据源到一个 VO（用户、角色、菜单）
- 第 16-19 行：构建菜单树的算法：
  - 第 16-17 行：先转成 `Map<id, node>` 用于 O(1) 查找
  - 第 20-30 行：遍历非根节点，找到父节点，把自己加到父节点的 `children`
  - 第 32 行：返回所有 parentId == 0 的根节点

### 3.2 UserConvert 单对象转换

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
}
```

**解读**：
- 第 7-9 行：列表转换，每个 user 调 `convert(user, dept)`
- 第 11-16 行：先 `BeanUtils.toBean` 拷贝基础字段，再设置额外字段 `deptName`
- **优点**：转换逻辑集中在一处，Controller 只需要一行 `INSTANCE.convertList(...)`

## 4. 关键要点总结

- MapStruct 是**编译期**生成代码的 Bean 映射框架
- ruoyi 用 `@Mapper` + `INSTANCE` + `default` 混合模式
- 简单映射用接口方法（MapStruct 自动生成）
- 复杂映射用 `default` 方法（自己写逻辑）
- MapStruct 编译期生成代码，运行效率高

## 5. 练习题

### 练习 1：基础（必做）

打开 `TenantConvert.java`，找出至少 2 个 default 方法，理解它们的转换逻辑。

### 练习 2：进阶

阅读 `AuthConvert.buildMenuTree` 的实现，画出"扁平菜单列表 → 树形结构"的转换过程。

### 练习 3：挑战（选做）

写一个 `OrderConvert`，把 `OrderDO` + `List<OrderItemDO>` 列表转换为 `OrderRespVO`（包含 items 字段）。要求使用 `@Mapper` 注解 + default 方法。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/convert/user/UserConvert.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/convert/auth/AuthConvert.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/convert/tenant/TenantConvert.java`
- MapStruct 官方文档：https://mapstruct.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
