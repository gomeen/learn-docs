# 4.4 自定义生成规则

> 学习如何为 ruoyi 代码生成器添加高级自定义规则（多表关联、字段联动、模板分支等）。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释"自定义生成规则"的 3 大类：元数据扩展 / 模板修改 / 全局变量
- 为"非主键"的业务唯一字段添加 Service 校验
- 实现"主表创建时自动创建子表"的特殊规则
- 通过"扩展 CodegenColumnDO"添加新字段类型

## 📚 前置知识

- 阅读过 `01-overview.md`、`10-velocity.md`、`11-java-template.md`
- 阅读过 `14-custom-template.md`
- 阅读过 `17-gen-master-slave.md`

## 1. 核心概念

### 1.1 自定义规则的 4 个层次

| 层次 | 修改位置 | 影响范围 | 难度 |
|------|---------|---------|------|
| **L1 模板微调** | 直接改 .vm 文件 | 单一模板 | ⭐ |
| **L2 全局变量** | `initGlobalBindingMap` | 所有模板可用 | ⭐⭐ |
| **L3 元数据扩展** | `CodegenTableDO/ColumnDO` + 模板 | 持久化 | ⭐⭐⭐ |
| **L4 业务规则** | `CodegenBuilder` | 推断逻辑 | ⭐⭐⭐⭐ |

### 1.2 实战场景

1. **场景 A**：为"树表"添加"拖拽排序"功能
2. **场景 B**：为"订单表"添加"自动计算总金额"逻辑
3. **场景 C**：增加"业务唯一键"（如订单号）校验

## 2. 代码示例

### 2.1 场景 A：L1 模板微调 - 给 ServiceImpl 加自定义方法

**修改位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`

**目标**：所有 ServiceImpl 都加一个 `exportToCsv` 方法。

```velocity
## 在 serviceImpl.vm 末尾加
@Override
public void exportToCsv(HttpServletResponse response) throws IOException {
    List<${table.className}DO> list = ${classNameVar}Mapper.selectList();
    // 简单 CSV 导出
    StringBuilder sb = new StringBuilder();
    sb.append("id").append(",").append("name").append("\n");
    for (${table.className}DO item : list) {
        sb.append(item.getId()).append(",").append(item.getName()).append("\n");
    }
    response.setContentType("text/csv;charset=utf-8");
    response.getWriter().write(sb.toString());
}
```

### 2.2 场景 B：L2 全局变量 - 自动添加 Lombok 注解

**修改位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java`

```java
@PostConstruct
@VisibleForTesting
void initGlobalBindingMap() {
    // ... 现有代码
    // 新增：lombok 启用标记
    globalBindingMap.put("lombokEnable", true);
    globalBindingMap.put("author", "芋道源码");
}
```

**修改位置**：所有需要的 .vm 文件（如 `do.vm`）

```velocity
#if ($lombokEnable)
import lombok.Data;
import lombok.experimental.Accessors;
#end

#if ($lombokEnable)
@Data
@Accessors(chain = true)
#end
public class ${table.className}DO extends BaseDO {
```

### 2.3 场景 C：L3 元数据扩展 - 增加"业务唯一键"字段

**第 1 步**：修改 `CodegenColumnDO`

```java
// 在 CodegenColumnDO.java 加字段
/** 是否业务唯一键（用于 Service 校验） */
private Boolean businessUnique;
```

**第 2 步**：修改 `CodegenBuilder` 推断逻辑

```java
// 在 CodegenBuilder.buildColumns 中
// 业务唯一键默认为 false，可由用户在编辑页开启
column.setBusinessUnique(false);
```

**第 3 步**：修改 Service 模板

```velocity
## serviceImpl.vm 中
## 校验业务唯一键
#foreach($column in $columns)
#if ($column.businessUnique)
    private void validate${simpleClassName}ForBusinessUnique(${saveReqVOClass} reqVO) {
        ${table.className}DO exists = ${classNameVar}Mapper.selectBy${column.javaField.substring(0,1).toUpperCase()}${column.javaField.substring(1)}(reqVO.get${column.javaField.substring(0,1).toUpperCase()}${column.javaField.substring(1)}());
        if (exists != null && !exists.getId().equals(reqVO.getId())) {
            throw exception(${simpleClassName_underlineCase.toUpperCase()}_${column.javaField.toUpperCase()}_DUPLICATE);
        }
    }
#end
#end
```

**第 4 步**：增加前端编辑页开关（Vue）

```vue
<el-form-item label="业务唯一键">
  <el-switch v-model="column.businessUnique" />
</el-form-item>
```

## 3. ruoyi 仓库源码解读

### 3.1 扩展点 1：CodegenBuilder 的字段推断

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenBuilder.java`

```java
public List<CodegenColumnDO> buildColumns(Long tableId, List<TableField> tableFields) {
    List<CodegenColumnDO> columns = CodegenConvert.INSTANCE.convertList(tableFields);
    int index = 1;
    for (CodegenColumnDO column : columns) {
        column.setTableId(tableId);
        column.setOrdinalPosition(index++);
        column.setColumnComment(sanitizeComment(column.getColumnComment()));
        // ... 已有推断逻辑
        processColumnOperation(column);
        processColumnUI(column);
        processColumnExample(column);
        // ★ 可在此加自定义推断
    }
    return columns;
}
```

**自定义推断示例**：字段名以 `_at` 结尾默认为 `LocalDateTime`

```java
private void processCustomColumnType(CodegenColumnDO column) {
    if (column.getJavaField().endsWith("_at") && column.getDataType().contains("datetime")) {
        column.setJavaType("LocalDateTime");
    }
}
```

### 3.2 扩展点 2：CodegenEngine 全局变量

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java` 行 329-362

```java
@PostConstruct
@VisibleForTesting
void initGlobalBindingMap() {
    // ... 现有
    // ★ 自定义全局变量
    globalBindingMap.put("companyName", "某某科技有限公司");
    globalBindingMap.put("copyright", "Copyright © 2024");
}
```

### 3.3 扩展点 3：自定义模板路径

**位置**：`CodegenEngine.java` SERVER_TEMPLATES 段

```java
// ★ 新增：自定义 DTO 模板
.put(javaTemplatePath("controller/vo/customDTO"),
     javaModuleImplVOFilePath("CustomDTO"))
```

### 3.4 扩展点 4：模板分支 - 高级 #if 逻辑

**示例**：在 `serviceImpl.vm` 中，根据 `templateType` 加不同逻辑

```velocity
## 树表专属
#if ($table.templateType == 2)
    // 树表的额外校验
    validate${simpleClassName}Tree(reqVO);
## 主子表 NORMAL 模式
#elseif ($table.templateType == 10)
    // 主子表 NORMAL 模式
    create${subSimpleClassName}List(${classNameVar}Id, reqVO.getItems());
## 主子表 ERP 模式
#elseif ($table.templateType == 11)
    // ERP 模式子表独立处理
#end
```

### 3.5 实战：一个完整的自定义规则 - 软删除

**目标**：所有 ServiceImpl 的 `delete` 方法改为"软删除"（设置 `deleted=1` 而不是 `DELETE FROM`）。

**修改步骤**：

1. **修改 `serviceImpl.vm`**

```velocity
## 把
${classNameVar}Mapper.deleteById(id);
## 改为
${table.className}DO ${classNameVar} = ${classNameVar}Mapper.selectById(id);
if (${classNameVar} != null) {
    ${classNameVar}.setDeleted(true);
    ${classNameVar}Mapper.updateById(${classNameVar});
}
```

2. **修改 `mapper.vm`** 增加 `selectByDeleted` 方法

```velocity
default List<${table.className}DO> selectListByDeleted(boolean deleted) {
    return selectList(new LambdaQueryWrapperX<${table.className}DO>()
        .eq(${table.className}DO::getDeleted, deleted)
        .orderByDesc(${table.className}DO::getId));
}
```

3. **测试**：重新生成，验证软删除生效

## 4. 关键要点总结

- 自定义规则有 **4 个层次**：L1 模板微调 / L2 全局变量 / L3 元数据扩展 / L4 业务规则
- 模板微调**风险最低**——只影响生成结果
- 元数据扩展需要**前后端 + 数据库**同步
- 业务规则修改要谨慎——可能影响所有已生成的代码
- ruoyi 默认所有删除都是**逻辑删除**（`@TableLogic`），但 Service 模板生成的还是 `deleteById`（需要自行优化）

## 5. 练习题

### 练习 1：基础（必做）

修改 `controller.vm`，给所有 Controller 加一个 `/export-csv` 接口（不传参，直接下载 CSV）。写出新增的代码片段。

### 练习 2：进阶

在 `CodegenEngine.initGlobalBindingMap` 加一个 `copyright` 变量（值 = `"Copyright © 2024 芋道源码"`），并在所有 Java 模板的 package 注释上方加一行注释。列出需要修改的 .vm 文件清单。

### 练习 3：挑战（选做）

实现"批量插入"自定义：扩展 `CodegenColumnDO` 加 `batchInsert` 字段，修改 `service.vm` 和 `serviceImpl.vm` 生成 `batchCreateXxx` 方法。完整描述所有改动。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenBuilder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/dal/dataobject/codegen/CodegenColumnDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/framework/codegen/config/CodegenProperties.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
