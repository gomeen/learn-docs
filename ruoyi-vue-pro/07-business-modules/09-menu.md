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

## 3. ruoyi 仓库源码解读

### 3.1 MenuController 核心代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/MenuController.java`

**核心代码**（行 26-80）：

```java
@Tag(name = "管理后台 - 菜单")
@RestController
@RequestMapping("/admin-api/system/menu")
@Validated
public class MenuController {

    @Resource
    private MenuService menuService;

    @PostMapping("/create")
    @Operation(summary = "创建菜单")
    @PreAuthorize("@ss.hasPermission('system:menu:create')")
    public CommonResult<Long> createMenu(@Valid @RequestBody MenuSaveVO createReqVO) {
        Long menuId = menuService.createMenu(createReqVO);
        return success(menuId);
    }

    @GetMapping("/list")
    @Operation(summary = "获取菜单列表", description = "用于【菜单管理】界面")
    @PreAuthorize("@ss.hasPermission('system:menu:query')")
    public CommonResult<List<MenuRespVO>> getMenuList(MenuListReqVO reqVO) {
        List<MenuDO> list = menuService.getMenuList(reqVO);
        list.sort(Comparator.comparing(MenuDO::getSort));
        return success(BeanUtils.toBean(list, MenuRespVO.class));
    }

    @GetMapping({"/list-all-simple", "simple-list"})
    @Operation(summary = "获取菜单精简信息列表", description = "只包含被开启的菜单")
    // ...
}
```

**解读**：
- 第 6-9 行：标准 Controller 三件套
- 第 12-16 行：创建菜单
- 第 21-26 行：菜单列表（按 sort 排序）
- 第 28-30 行：精简列表（用于角色分配菜单）

### 3.2 菜单列表响应

```java
public CommonResult<List<MenuRespVO>> getMenuList(MenuListReqVO reqVO) {
    // 1. Service 查询菜单
    List<MenuDO> list = menuService.getMenuList(reqVO);
    // 2. 排序
    list.sort(Comparator.comparing(MenuDO::getSort));
    // 3. 转 VO 返回
    return success(BeanUtils.toBean(list, MenuRespVO.class));
}
```

### 3.3 菜单 Service 关键方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/MenuServiceImpl.java`

**核心代码**（简化版）：

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createMenu(MenuSaveVO createReqVO) {
    // 1. 校验父菜单存在
    validateParentMenu(createReqVO.getParentId(), createReqVO.getName());
    // 2. 转换 VO -> DO
    MenuDO menu = new MenuDO();
    BeanUtils.copyProperties(createReqVO, menu);
    // 3. 插入数据库
    menuMapper.insert(menu);
    return menu.getId();
}

@Override
public void deleteMenu(Long id) {
    // 1. 校验是否有子菜单
    if (menuMapper.selectCountByParentId(id) > 0) {
        throw exception(MENU_EXISTS_CHILDREN);
    }
    // 2. 删除菜单
    menuMapper.deleteById(id);
    // 3. 删除角色菜单关联
    roleMenuService.deleteByMenuId(id);
}
```

**解读**：
- 创建菜单时校验父菜单
- 删除菜单时检查是否有子菜单，**有子菜单不能删除**
- 删除菜单时同时删除角色-菜单关联

## 4. 关键要点总结

- 菜单分 3 种类型：目录、菜单、按钮
- 权限标识格式：`模块:资源:操作`
- 菜单是树形结构，通过 `parentId` 关联
- 删除菜单时要校验子菜单和关联数据
- 菜单列表通常需要按 `sort` 字段排序

## 5. 练习题

### 练习 1：基础（必做）

打开 `MenuDO.java`，列出所有字段，理解每个字段的作用（特别是 `componentName`、`keepAlive`）。

### 练习 2：进阶

阅读 `AuthConvert.buildMenuTree` 方法，理解菜单如何从扁平列表转成树形结构。

### 练习 3：挑战（选做）

如果要给菜单添加"是否外链"字段（`externalLink`），需要修改哪些文件？列出具体步骤。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/MenuController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/permission/MenuDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/enums/permission/MenuTypeEnum.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
