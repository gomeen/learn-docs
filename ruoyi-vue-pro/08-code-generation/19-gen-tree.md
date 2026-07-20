# 4.2 生成树表

> 实战演练：使用 ruoyi 代码生成器为树形结构表（如菜单、地区）生成完整模块。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释"树表"与"单表"在生成产物上的差异
- 配置树表的 `treeParentColumnId` / `treeNameColumnId`
- 理解树表 Service 中的父子关系校验
- 区分"全树查询"和"按父查询"

## 📚 前置知识

- 模板分组 / 单表生成（详见 [模板分组](./06-template-group.md)、[单表生成](./18-gen-single.md)）
- 树形结构（递归、子父关系，业务参考 [部门](../07-business-modules/10-dept.md)）

## 1. 核心概念

### 1.1 树表与单表的 3 大差异

| 差异 | 单表 | 树表 |
|------|------|------|
| 模板类型 | `ONE` (1) | `TREE` (2) |
| 接口 | `/page` 分页 | `/list` 列表（全树） |
| 字段 | 普通字段 | + `parentId` 父字段 + `name` 名字段 |
| Service 校验 | 字段唯一性 | + 父子循环校验 + 父节点存在性 |

### 1.2 树表的两个特殊字段

```java
// 在 CodegenTableDO 中
private Long treeParentColumnId;  // 指向"父节点字段"的 CodegenColumnDO.id
private Long treeNameColumnId;    // 指向"名称字段"的 CodegenColumnDO.id
```

- `treeParentColumnId`：用于 `parent_id` 字段
- `treeNameColumnId`：用于在 `<el-tree>` 节点上显示

## 2. 代码示例

### 2.1 树表建表 SQL 示例

```sql
CREATE TABLE system_region (
    id          BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    parent_id   BIGINT       NOT NULL DEFAULT 0 COMMENT '父节点 ID（0=根）',
    name        VARCHAR(50)  NOT NULL COMMENT '地区名称',
    sort        INT          NOT NULL DEFAULT 0 COMMENT '排序',
    status      TINYINT      NOT NULL DEFAULT 0 COMMENT '状态',
    creator     VARCHAR(64)  DEFAULT '',
    create_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater     VARCHAR(64)  DEFAULT '',
    update_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted     BIT          NOT NULL DEFAULT 0 COMMENT '是否删除'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地区表';
```

### 2.2 树表 Service 校验逻辑（生成后简化）

```java
private void validateRegionForCreateOrUpdate(RegionSaveReqVO reqVO) {
    // 1. 校验父节点存在
    if (reqVO.getParentId() != null && reqVO.getParentId() > 0) {
        RegionDO parent = regionMapper.selectById(reqVO.getParentId());
        if (parent == null) {
            throw exception(REGION_PARENT_NOT_EXISTS);
        }
    }
    // 2. 校验名称唯一
    RegionDO region = regionMapper.selectByNameAndParentId(reqVO.getName(), reqVO.getParentId());
    if (region != null && !region.getId().equals(reqVO.getId())) {
        throw exception(REGION_NAME_DUPLICATE);
    }
    // 3. 校验不能把节点修改成自己的后代
    if (reqVO.getId() != null) {
        for (RegionDO child : regionMapper.selectListByParentId(reqVO.getId())) {
            if (child.getId().equals(reqVO.getParentId())) {
                throw exception(REGION_PARENT_IS_CHILD);
            }
        }
    }
}
```

## 3. 关键要点总结

- 树表 = `templateType=2` + 两个特殊字段（parent/name）
- 树表生成 3 大类校验：父节点存在、名称唯一、父子循环
- 树表无分页接口，用 `/list` + `<el-tree>` 展示
- 树表 Service 必须实现"防止把自己改成自己的后代"校验
- 错误码常量从 `${simpleClassName_underlineCase.toUpperCase()}` 拼接

---

**文档版本**：v1.0
**最后更新**：2026-07-13
