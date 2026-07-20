# 7.2.3 菜单管理

> 理解 ruoyi 中菜单（权限点）的设计，菜单的树形结构和权限标识。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 菜单模型的设计（目录/菜单/按钮）
- 理解菜单的树形结构构建
- 学会权限标识（permission）的生成规则
- 能看懂菜单管理的完整代码

## 📚 前置知识

- 用户 / 角色（详见 [用户](./07-user.md)、[角色](./08-role.md)）
- 树形结构基础
- RBAC 权限模型（详见 [RBAC](../../_common/08-authorization/01-rbac.md)）

## 1. 核心概念

### 1.1 菜单的三种类型

ruoyi 的菜单分为 3 种类型，对应不同的 UI 表现：

| 类型 | 枚举值 | 说明 | 例子 |
|------|--------|------|------|
| 目录 | `DIR (1)` | 容器，不显示页面 | "系统管理" |
| 菜单 | `MENU (2)` | 显示具体页面 | "用户管理" |
| 按钮 | `BUTTON (3)` | 页面内的按钮 | "新增用户" |

### 1.2 菜单核心字段

```java
public class MenuDO {
    private Long id;                  // 菜单编号
    private String name;              // 菜单名称
    private String permission;        // 权限标识，如 system:user:create
    private Integer type;             // 类型：1-目录 2-菜单 3-按钮
    private Integer sort;             // 排序
    private Long parentId;            // 父菜单 ID
    private String path;              // 路由地址
    private String icon;              // 图标
    private String component;         // 组件路径
    private String componentName;     // 组件名
    private Integer status;           // 状态
    private Boolean visible;          // 是否可见
    private Boolean keepAlive;        // 是否缓存
    private Boolean alwaysShow;       // 是否总是显示
}
```

### 1.3 权限标识命名规范

格式：`模块:资源:操作`

```
system:user:create      // 创建用户
system:user:update      // 修改用户
system:user:delete      // 删除用户
system:user:query       // 查询用户
system:user:export      // 导出用户
system:user:import      // 导入用户
```

**规则**：
- 冒号分隔三段
- 全部小写
- 动词在前

## 2. 代码示例

### 2.1 菜单的树形结构

菜单是典型的树形结构，每个菜单有 `parentId`：

```java
@Data
public class MenuRespVO {
    private Long id;
    private Long parentId;
    private String name;
    private List<MenuRespVO> children;  // 子菜单
}
```

### 2.2 构建菜单树

```java
public List<MenuRespVO> buildMenuTree(List<MenuDO> menuList) {
    if (CollUtil.isEmpty(menuList)) return Collections.emptyList();
    // 排序
    menuList.sort(Comparator.comparing(MenuDO::getSort));
    // 转 Map
    Map<Long, MenuRespVO> treeNodeMap = new LinkedHashMap<>();
    menuList.forEach(menu -> treeNodeMap.put(menu.getId(),
            BeanUtils.toBean(menu, MenuRespVO.class)));
    // 处理父子关系
    treeNodeMap.values().stream()
        .filter(node -> ObjUtil.notEqual(node.getParentId(), ID_ROOT))
        .forEach(childNode -> {
            MenuRespVO parentNode = treeNodeMap.get(childNode.getParentId());
            if (parentNode != null) {
                if (parentNode.getChildren() == null) {
                    parentNode.setChildren(new ArrayList<>());
                }
                parentNode.getChildren().add(childNode);
            }
        });
    // 返回根节点
    return filterList(treeNodeMap.values(), node -> ID_ROOT.equals(node.getParentId()));
}
```

## 3. 关键要点总结

- 菜单分 3 种类型：目录、菜单、按钮
- 权限标识格式：`模块:资源:操作`
- 菜单是树形结构，通过 `parentId` 关联
- 删除菜单时要校验子菜单和关联数据
- 菜单列表通常需要按 `sort` 字段排序

---

**文档版本**：v1.0
**最后更新**：2026-07-13
