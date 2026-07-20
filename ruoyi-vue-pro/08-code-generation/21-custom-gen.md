# 4.4 自定义生成规则

> 学习如何为 ruoyi 代码生成器添加高级自定义规则（多表关联、字段联动、模板分支等）。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释"自定义生成规则"的 3 大类：元数据扩展 / 模板修改 / 全局变量
- 为"非主键"的业务唯一字段添加 Service 校验
- 实现"主表创建时自动创建子表"的特殊规则
- 通过"扩展 CodegenColumnDO"添加新字段类型

## 📚 前置知识

- 总览 / Velocity / Java 模板（详见 [总览](./01-overview.md)、[Velocity](./12-velocity.md)、[Java 模板](./13-java-template.md)）
- 自定义模板（详见 [自定义模板](./16-custom-template.md)）
- 主子表生成（详见 [主子表生成](./20-gen-master-slave.md)）

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

在 `serviceImpl.vm` 末尾追加：

```velocity
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

`serviceImpl.vm` 中增加业务唯一键校验：

```velocity
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

## 3. 关键要点总结

- 自定义规则有 **4 个层次**：L1 模板微调 / L2 全局变量 / L3 元数据扩展 / L4 业务规则
- 模板微调**风险最低**——只影响生成结果
- 元数据扩展需要**前后端 + 数据库**同步
- 业务规则修改要谨慎——可能影响所有已生成的代码
- ruoyi 默认所有删除都是**逻辑删除**（`@TableLogic`），但 Service 模板生成的还是 `deleteById`（需要自行优化）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
