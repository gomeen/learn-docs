# 1.3 表结构导入

> 理解 ruoyi 如何把数据库表结构转换为内部元数据 `CodegenTableDO`。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释"导入表"动作背后的两个步骤：读表结构 → 写元数据
- 掌握 `CodegenTableDO` / `CodegenColumnDO` 的所有字段含义
- 区分 `CreateReqVO` / `UpdateReqVO` / `RespVO` 各自的字段差异
- 跟踪一次完整导入的代码路径

## 📚 前置知识

- 阅读过 `01-overview.md` 和 `02-datasource.md`
- 了解 MyBatis-Plus 的 `TableInfo` / `TableField` API

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

## 3. ruoyi 仓库源码解读

### 3.1 import_reqVO / RespVO

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/codegen/vo/CodegenCreateListReqVO.java`
**核心代码**：

```java
@Schema(description = "管理后台 - 代码生成表创建 Request VO")
@Data
public class CodegenCreateListReqVO {

    @Schema(description = "数据源配置的编号", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotNull(message = "数据源不能为空")
    private Long dataSourceConfigId;

    @Schema(description = "表名数组", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotEmpty(message = "表名不能为空")
    private List<String> tableNames;

    @Schema(description = "作者", example = "芋道源码")
    @NotEmpty(message = "作者不能为空")
    private String author;
}
```

**解读**：
- 入参极简：3 个字段
- 一次请求可导入**多张表**（前端可多选）
- 不需要传 `scene` / `frontType`——会从 `CodegenProperties` 全局配置读

### 3.2 字段元数据

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenColumnDO.java`
**核心代码**（行 100-135）：

```java
// ========== CRUD 相关字段 ==========

/** 是否为 Create 创建操作的字段 */
private Boolean createOperation;
/** 是否为 Update 更新操作的字段 */
private Boolean updateOperation;
/** 是否为 List 查询操作的字段 */
private Boolean listOperation;
/** List 查询操作的条件类型 */
private String listOperationCondition; // EQ / LIKE / BETWEEN / ...
/** 是否为 List 查询操作的返回字段 */
private Boolean listOperationResult;

// ========== UI 相关字段 ==========

/** 显示类型 */
private String htmlType; // input / select / radio / imageUpload / ...
```

**解读**：
- `createOperation` / `updateOperation` / `listOperation` 是**3 个开关**——决定字段是否参与某场景
- `listOperationCondition` 决定查询方式（`EQ` 精确 / `LIKE` 模糊 / `BETWEEN` 区间）
- `htmlType` 是**前端表单类型**——决定 Vue 模板用 `<el-input>` 还是 `<el-select>`

### 3.3 CodegenBuilder.buildTable 推断规则

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenBuilder.java`
**核心代码**（行 110-125）：

```java
private void initTableDefault(CodegenTableDO table) {
    // 以 system_dept 举例子。
    // moduleName = system, businessName = dept, className = Dept
    String tableName = table.getTableName().toLowerCase();

    // 第一步：第一个 _ 前面是 module
    table.setModuleName(subBefore(tableName, '_', false).toLowerCase());
    // 第一步：第一个 _ 后面是 business；第二步：转驼峰；第三步：小写
    table.setBusinessName(toCamelCase(subAfter(tableName, '_', false)).toLowerCase());
    // 驼峰 + 首字母大写
    table.setClassName(upperFirst(toCamelCase(subAfter(tableName, '_', false))));
    // 类描述：去掉"表"字
    table.setClassComment(StrUtil.removeSuffixIgnoreCase(
        sanitizeComment(table.getTableComment()), "表"));
    // 默认模板类型：单表 CRUD
    table.setTemplateType(CodegenTemplateTypeEnum.ONE.getType());
}
```

**解读**：
- 命名规则硬编码：`module_business` → `ModuleBusinessDO`（**如果表名不带下划线会出错**）
- 注释里的英文引号会被替换为中文引号，避免破坏模板里的字符串字面量
- 默认就是单表，其他模板类型需要**用户在编辑页手动切换**

## 4. 关键要点总结

- "导入表" = **读表结构 + 转元数据 + 写库**
- 一次可导入多张表，由 `CodegenCreateListReqVO.tableNames` 控制
- 字段元数据包含 3 大类：**数据库字段**、**CRUD 开关**、**UI 类型**
- 命名推断规则：`module_business` → `moduleName=module, businessName=business, className=BusinessDO`
- 默认模板类型 = `ONE`（单表），其他类型要手动切换

## 5. 练习题

### 练习 1：基础（必做）

在数据库执行 `SHOW CREATE TABLE infra_codegen_column\G`，列出**所有字段**并对应到 `CodegenColumnDO` 的 Java 字段名。

### 练习 2：进阶

模仿 `initTableDefault`，为以下表名写出推断结果：
- `mall_order` → `moduleName=?, businessName=?, className=?, classComment=?`
- `erp_finance_invoice` → 同上（多下划线情况）
- `userinfo` → 同上（无下划线情况，是否有 Bug？）

### 练习 3：挑战（选做）

如果表名有 3 段及以上（如 `erp_finance_invoice`），改进 `initTableDefault` 让 `moduleName` 始终是**第一段**，`className` 包含**剩下所有段**（驼峰）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/codegen/vo/CodegenCreateListReqVO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenColumnDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenBuilder.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
