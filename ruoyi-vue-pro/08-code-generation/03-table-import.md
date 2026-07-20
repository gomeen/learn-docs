# 1.3 表结构导入

> 理解 ruoyi 如何把数据库表结构转换为内部元数据 `CodegenTableDO`。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释"导入表"动作背后的两个步骤：读表结构 → 写元数据
- 掌握 `CodegenTableDO` / `CodegenColumnDO` 的所有字段含义
- 区分 `CreateReqVO` / `UpdateReqVO` / `RespVO` 各自的字段差异
- 跟踪一次完整导入的代码路径

## 📚 前置知识

- 总览与数据源（详见 [总览](./01-overview.md)、[数据源](./02-datasource.md)）
- MyBatis-Plus 的 `TableInfo` / `TableField` API（详见 [MyBatis-Plus](../03-spring-boot-starters/08-mybatis-plus.md)）

## 1. 核心概念

### 1.1 "导入表"到底做了什么？

`createCodegenList` 这个接口只做两件事：
1. **从指定数据源读取表结构**（调用 `databaseTableService.getTable`）
2. **转换为元数据并入库**（调用 `codegenBuilder.buildTable` + `buildColumns`）

之后用户才能在"代码生成列表"看到这条记录，并继续配置字段、模板类型。

### 1.2 字段的 4 大来源

| 来源 | 字段 | 谁负责填充 |
|------|------|----------|
| 数据库读取 | `tableName` / `tableComment` / `columnName` / `dataType` | `DatabaseTableService` |
| 规则推断 | `moduleName` / `businessName` / `className` / `htmlType` | `CodegenBuilder` |
| 用户填写 | `author` / `scene` / `frontType` / `parentMenuId` | 前端表单 |
| 业务计算 | `permissionPrefix` / `simpleClassName_strikeCase` | `CodegenEngine.initBindingMap` |

## 2. 代码示例

### 2.1 简化的"导入表"流程

```java
@Transactional(rollbackFor = Exception.class)
public Long createCodegen(String author, Long dataSourceConfigId, String tableName) {
    // 1. 从数据源读取
    TableInfo tableInfo = databaseTableService.getTable(dataSourceConfigId, tableName);

    // 2. 转成元数据
    CodegenTableDO table = codegenBuilder.buildTable(tableInfo);
    table.setDataSourceConfigId(dataSourceConfigId);
    table.setAuthor(author);
    table.setScene(1); // ADMIN

    // 3. 入库
    codegenTableMapper.insert(table);

    // 4. 字段也入库
    List<CodegenColumnDO> columns = codegenBuilder.buildColumns(
        table.getId(), tableInfo.getFields());
    columns.forEach(codegenColumnMapper::insert);

    return table.getId();
}
```

## 3. 关键要点总结

- "导入表" = **读表结构 + 转元数据 + 写库**
- 一次可导入多张表，由 `CodegenCreateListReqVO.tableNames` 控制
- 字段元数据包含 3 大类：**数据库字段**、**CRUD 开关**、**UI 类型**
- 命名推断规则：`module_business` → `moduleName=module, businessName=business, className=BusinessDO`
- 默认模板类型 = `ONE`（单表），其他类型要手动切换

---

**文档版本**：v1.0
**最后更新**：2026-07-13
