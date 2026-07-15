# 7.2.4 部门管理：树形结构

> 理解 ruoyi 中部门（Dept）树形结构的设计和管理。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握部门树形结构的设计（parentId）
- 理解部门缓存的设计（@Cacheable / @CacheEvict）
- 学会部门创建/更新/删除时的级联校验
- 能构建部门树形结构

## 📚 前置知识

- 树形结构（详见 [菜单](./09-menu.md)）
- Spring Cache（详见 [@Cacheable 等](../05-cache-and-mq/09-cache-annotation.md)）
- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 数据权限与部门范围（详见 [数据权限](../06-security/29-ruoyi-data-permission.md)）

## 1. 核心概念

### 1.1 部门的树形结构

部门也是典型的树形结构：

```
总公司 (parentId = 0)
├── 北京分公司
│   ├── 研发部
│   │   ├── 后端组
│   │   └── 前端组
│   └── 销售部
└── 上海分公司
    └── 运营部
```

**核心字段**：
- `parentId`：父部门 ID（0 表示根）
- `name`：部门名称
- `sort`：排序
- `leaderUserId`：部门负责人
- `phone`、`email`：联系方式
- `status`：状态

### 1.2 ruoyi 的部门缓存设计

部门数据是读多写少的，ruoyi 使用 **Spring Cache + Redis** 缓存：

```java
@Cacheable(cacheNames = "dept", key = "#id")
public DeptDO getDept(Long id) { ... }

@CacheEvict(cacheNames = "dept", allEntries = true)
public void updateDept(...) { ... }
```

**关键设计**：
- `@Cacheable`：查询时缓存到 Redis
- `@CacheEvict`：写操作时清空缓存（allEntries = true）
- **写操作影响多个缓存键时，用 `allEntries = true` 清空整个 cacheName**

### 1.3 部门唯一性校验

部门名称在**同一父部门下**必须唯一：

```
总公司 / 研发部      ✅ 允许
北京分公司 / 研发部  ✅ 允许（不同父部门）
北京分公司 / 研发部  ❌ 重复
```

## 2. 代码示例

### 2.1 部门 DO

```java
@TableName("system_dept")
@Data
public class DeptDO extends TenantBaseDO {
    @TableId
    private Long id;
    private String name;
    private Long parentId;       // 父部门 ID（0 = 根）
    private Integer sort;        // 排序
    private Long leaderUserId;   // 部门负责人
    private String phone;
    private String email;
    private Integer status;
    public static final Long PARENT_ID_ROOT = 0L;
}
```

### 2.2 部门树形响应

```java
@Data
public class DeptRespVO {
    private Long id;
    private String name;
    private Long parentId;
    private List<DeptRespVO> children;  // 子部门
}
```

### 2.3 构建部门树

```java
public List<DeptRespVO> buildDeptTree(List<DeptDO> deptList) {
    // 1. 排序
    deptList.sort(Comparator.comparing(DeptDO::getSort));
    // 2. 转 Map
    Map<Long, DeptRespVO> treeMap = new LinkedHashMap<>();
    deptList.forEach(dept -> treeMap.put(dept.getId(),
            BeanUtils.toBean(dept, DeptRespVO.class)));
    // 3. 关联父子
    treeMap.values().stream()
        .filter(node -> !DeptDO.PARENT_ID_ROOT.equals(node.getParentId()))
        .forEach(child -> {
            DeptRespVO parent = treeMap.get(child.getParentId());
            if (parent != null) {
                if (parent.getChildren() == null) {
                    parent.setChildren(new ArrayList<>());
                }
                parent.getChildren().add(child);
            }
        });
    // 4. 返回根节点
    return filterList(treeMap.values(), node -> DeptDO.PARENT_ID_ROOT.equals(node.getParentId()));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 DeptServiceImpl 核心方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/dept/DeptServiceImpl.java`

**核心代码**（行 40-90）：

```java
@Override
@CacheEvict(cacheNames = RedisKeyConstants.DEPT_CHILDREN_ID_LIST,
        allEntries = true) // allEntries 清空所有缓存
public Long createDept(DeptSaveReqVO createReqVO) {
    if (createReqVO.getParentId() == null) {
        createReqVO.setParentId(DeptDO.PARENT_ID_ROOT);
    }
    // 校验父部门的有效性
    validateParentDept(null, createReqVO.getParentId());
    // 校验部门名的唯一性
    validateDeptNameUnique(null, createReqVO.getParentId(), createReqVO.getName());

    // 插入部门
    DeptDO dept = BeanUtils.toBean(createReqVO, DeptDO.class);
    deptMapper.insert(dept);
    return dept.getId();
}

@Override
@CacheEvict(cacheNames = RedisKeyConstants.DEPT_CHILDREN_ID_LIST, allEntries = true)
public void deleteDept(Long id) {
    // 校验是否存在
    validateDeptExists(id);
    // 校验是否有子部门
    if (deptMapper.selectCountByParentId(id) > 0) {
        throw exception(DEPT_EXITS_CHILDREN);
    }
    // 删除部门
    deptMapper.deleteById(id);
}
```

**解读**：
- 第 2-3 行：`@CacheEvict` 清空所有缓存
- 第 4-6 行：父部门默认为 ROOT（0）
- 第 7-8 行：校验父部门存在
- 第 9 行：校验**同父部门下**的名称唯一
- 第 19-22 行：删除时**先校验子部门**，有子部门不能删除

### 3.2 部门唯一性校验

```java
private void validateDeptNameUnique(Long id, Long parentId, String name) {
    DeptDO dept = deptMapper.selectByParentIdAndName(parentId, name);
    if (dept == null) {
        return;
    }
    // 如果 id 为空，说明重复；否则 id 不匹配也说明重复
    if (id == null || !dept.getId().equals(id)) {
        throw exception(DEPT_NAME_DUPLICATE);
    }
}
```

### 3.3 缓存注解

```java
@Cacheable(cacheNames = RedisKeyConstants.DEPT, key = "#id")
public DeptDO getDept(Long id) {
    return deptMapper.selectById(id);
}

@Cacheable(cacheNames = RedisKeyConstants.DEPT_CHILDREN_ID_LIST, key = "#parentId")
public Set<Long> getDeptChildIds(Long parentId) {
    // 递归查询所有子部门
    List<DeptDO> deptList = deptMapper.selectListByParentId(parentId);
    Set<Long> result = convertSet(deptList, DeptDO::getId);
    // 递归
    for (DeptDO dept : deptList) {
        result.addAll(getDeptChildIds(dept.getId()));
    }
    return result;
}
```

## 4. 关键要点总结

- 部门是树形结构，通过 `parentId` 关联
- 部门名称在**同父部门下**必须唯一
- 删除部门时要校验子部门
- 读多写少场景使用 `@Cacheable` + `@CacheEvict`
- 写操作影响多个缓存键时用 `allEntries = true`

## 5. 练习题

### 练习 1：基础（必做）

打开 `DeptController.java`，列出所有接口和权限标识。

### 练习 2：进阶

阅读 `getDeptChildIds` 方法，理解如何递归查询所有子部门 ID 并缓存。

### 练习 3：挑战（选做）

设计一个"批量调整部门"接口：把部门 A 下的所有员工转移到部门 B 下，需要注意哪些问题？（事务、缓存、用户关联等）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/dept/DeptServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/dept/DeptController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/dept/DeptDO.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
