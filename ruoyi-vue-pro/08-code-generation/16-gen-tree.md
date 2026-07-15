# 4.2 生成树表

> 实战演练：使用 ruoyi 代码生成器为树形结构表（如菜单、地区）生成完整模块。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释"树表"与"单表"在生成产物上的差异
- 配置树表的 `treeParentColumnId` / `treeNameColumnId`
- 理解树表 Service 中的父子关系校验
- 区分"全树查询"和"按父查询"

## 📚 前置知识

- 模板分组 / 单表生成（详见 [模板分组](./05-template-group.md)、[单表生成](./15-gen-single.md)）
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

## 3. ruoyi 仓库源码解读

### 3.1 树表 Service 校验

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`

```velocity
## 树表专属：父子关系校验
#if ($table.templateType == 2)
    private void validate${simpleClassName}ForCreateOrUpdate(${saveReqVOClass} reqVO) {
        // 1. 校验父节点存在
        if (reqVO.get${simpleClassName}.getParentId() != null && reqVO.getParentId() > 0) {
            ${table.className}DO parent = ${classNameVar}Mapper.selectById(reqVO.getParentId());
            if (parent == null) {
                throw exception(${simpleClassName_underlineCase.toUpperCase()}_PARENT_NOT_EXISTS);
            }
        }
        // 2. 校验名称唯一
        ${table.className}DO xxx = ${classNameVar}Mapper.selectBy${treeNameColumn.javaField.toUpperCase()}AndParentId(
                reqVO.get${treeNameColumn.javaField}, reqVO.getParentId());
        if (xxx != null && !xxx.getId().equals(reqVO.getId())) {
            throw exception(${simpleClassName_underlineCase.toUpperCase()}_${treeNameColumn.javaField.toUpperCase()}_DUPLICATE);
        }
        // 3. 校验父子循环
        if (reqVO.getId() != null) {
            for (${table.className}DO child : ${classNameVar}Mapper.selectListByParentId(reqVO.getId())) {
                if (child.getId().equals(reqVO.getParentId())) {
                    throw exception(${simpleClassName_underlineCase.toUpperCase()}_PARENT_IS_CHILD);
                }
            }
        }
    }
#end
```

**关键占位符**：
- `$table.templateType == 2` → 只对树表生成
- `${treeNameColumn.javaField}` → 名字段（如 `name`）
- `${simpleClassName_underlineCase.toUpperCase()}` → `REGION`（错误码前缀）

### 3.2 树表 Controller 用 list 而非 page

**位置**：`controller.vm` 行 108-139

```velocity
#if ( $table.templateType != 2 )
    @GetMapping("/page")
    public CommonResult<PageResult<${respVOClass}>> get${simpleClassName}Page(...) { ... }
## 特殊：树表专属逻辑（树不需要分页接口）
#else
    @GetMapping("/list")
    public CommonResult<List<${respVOClass}>> get${simpleClassName}List(@Valid ${sceneEnum.prefixClass}${table.className}ListReqVO listReqVO) {
        List<${table.className}DO> list = ${classNameVar}Service.get${simpleClassName}List(listReqVO);
#if ($voType == 10)
        return success(BeanUtils.toBean(list, ${respVOClass}.class));
#else
        return success(list);
#end
    }
#end
```

**解读**：
- 树表没有分页接口（`/page`），改为 `/list`
- 前端可以用 `<el-tree>` 一次性加载所有节点
- 树表过滤通过 `ListReqVO`（不是 `PageReqVO`）

### 3.3 树表 ListReqVO

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/vo/listReqVO.vm`
**完整代码**（简化）：

```velocity
@Schema(description = "${sceneEnum.name} - ${table.classComment}列表 Request VO")
@Data
public class ${sceneEnum.prefixClass}${table.className}ListReqVO {

#foreach($column in $columns)
#if ($column.listOperation)
    @Schema(description = "$column.columnComment", example = "$column.example")
    private $column.javaType $column.javaField;

#end
#end
    @Schema(description = "父节点 ID", example = "0")
    private Long parentId;
}
```

**解读**：
- `ListReqVO` 比 `PageReqVO` 简单（没有 pageNo/pageSize）
- 多了 `parentId` 字段（用于按父节点过滤）
- 仅当 `templateType == 2` 时才生成

### 3.4 Vue 端树表

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/vue3/views/index.vue.vm`
**关键代码片段**（树表部分）：

```vue
<el-table
  v-if="false"  <!-- 禁用普通表格 -->
  :data="list"
/>
<el-table
  ref="tableRef"
  v-else
  :data="list"
  row-key="id"
  :tree-props="{ children: 'children' }"
  default-expand-all
>
  <el-table-column prop="name" label="名称" />
  <!-- 其他列 -->
</el-table>
```

**解读**：
- 树表用 `row-key` + `:tree-props` 把列表渲染为树形
- `default-expand-all` 默认展开全部节点
- 树表**不显示分页**

## 4. 关键要点总结

- 树表 = `templateType=2` + 两个特殊字段（parent/name）
- 树表生成 3 大类校验：父节点存在、名称唯一、父子循环
- 树表无分页接口，用 `/list` + `<el-tree>` 展示
- 树表 Service 必须实现"防止把自己改成自己的后代"校验
- 错误码常量从 `${simpleClassName_underlineCase.toUpperCase()}` 拼接

## 5. 练习题

### 练习 1：基础（必做）

画出对表 `system_region`（含 parent_id, name）执行代码生成的完整流程图，标注每一步用户需要做的操作。

### 练习 2：进阶

阅读 `serviceImpl.vm` 的"树表校验"段，写出"用户 A 把自己的父节点改成自己的子节点 B"会发生什么（按代码逻辑一步步追踪）。

### 练习 3：挑战（选做）

为树表加"批量移动"功能（一次把多个节点移到新父节点下）。需要修改哪些 .vm 文件？写出 Service 关键方法。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/vo/listReqVO.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenTableDO.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
