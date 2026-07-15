# 3.1 Velocity 模板引擎

> 学习 Velocity 模板语言的核心语法，能读懂 ruoyi 所有 `.vm` 文件。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 Velocity 的核心语法：`#if` / `#foreach` / `${var}` / `#set`
- 区分 Velocity 与 Thymeleaf / FreeMarker 的差异
- 阅读 ruoyi 任意一个 `.vm` 模板
- 自定义一个简单的 Velocity 模板

## 📚 前置知识

- Java 基础
- 任何一种模板引擎的使用经验（可选）
- 代码生成总览（详见 [总览](./01-overview.md)）

## 1. 核心概念

### 1.1 为什么用 Velocity？

ruoyi 选用 Velocity（封装在 hutool 中）作为代码生成器的模板引擎，原因是：
- 语法简单、容易学习
- 与 Java 生态无缝集成（`TemplateEngine`）
- 性能高（一次编译，多次渲染）
- 错误信息友好，模板出错时能定位行号

### 1.2 Velocity 三大语法

| 语法 | 用途 | 示例 |
|------|------|------|
| `${var}` | 变量引用 | `${table.className}` |
| `#指令` | 流程控制 | `#if` / `#foreach` / `#set` |
| `##` 或 `#* *#` | 注释 | `## 这是注释` |

### 1.3 核心指令速查

| 指令 | 用途 | 示例 |
|------|------|------|
| `#if / #elseif / #else / #end` | 条件分支 | `#if ($x > 0) ... #end` |
| `#foreach / #end` | 循环 | `#foreach ($item in $list) ... #end` |
| `#set` | 定义变量 | `#set ($name = "张三")` |
| `#include` | 引入子模板 | `#include("header.vm")` |
| `#parse` | 解析并执行子模板 | `#parse("macro.vm")` |
| `#macro` | 定义宏 | `#macro(myMacro) ... #end` |

## 2. 代码示例

### 2.1 基础用法

```velocity
## 设置变量
#set ($greeting = "Hello")
#set ($name = "World")

## 引用变量
${greeting}, ${name}!

## 条件判断
#if ($table.templateType == 2)
    这是树表
#else
    这是普通表
#end

## 循环
#foreach ($column in $columns)
    字段: $column.javaField ($column.javaType)
#end
```

### 2.2 在 Java 中使用

```java
// 1. 创建模板引擎
TemplateConfig config = new TemplateConfig();
config.setResourceMode(TemplateConfig.ResourceMode.CLASSPATH);
TemplateEngine engine = new VelocityEngine(config);

// 2. 准备变量
Map<String, Object> binding = new HashMap<>();
binding.put("name", "芋道源码");
binding.put("items", Arrays.asList("Java", "Vue", "SQL"));

// 3. 渲染模板
String templatePath = "codegen/java/controller/controller.vm";
String content = engine.getTemplate(templatePath).render(binding);

System.out.println(content);
```

## 3. ruoyi 仓库源码解读

### 3.1 CodegenEngine 中的 Velocity 初始化

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java` 行 308-327

```java
/**
 * 模板引擎，由 hutool 实现
 */
private final TemplateEngine templateEngine;

public CodegenEngine() {
    // 初始化 TemplateEngine 属性
    TemplateConfig config = new TemplateConfig();
    config.setResourceMode(TemplateConfig.ResourceMode.CLASSPATH);
    this.templateEngine = new VelocityEngine(config);
    // ...
}
```

**解读**：
- 使用 hutool 封装的 `VelocityEngine`，底层是 Apache Velocity
- `ResourceMode.CLASSPATH` 表示从 classpath 加载模板（即 `src/main/resources/codegen/...`）

### 3.2 模板执行核心逻辑

**位置**：`CodegenEngine.java` 行 411-418

```java
private void generateCode(Map<String, String> result, String vmPath,
                          String filePath, Map<String, Object> bindingMap) {
    filePath = formatFilePath(filePath, bindingMap);
    // 1. 加载模板
    // 2. 渲染（传入 bindingMap）
    String content = templateEngine.getTemplate(vmPath).render(bindingMap);
    // 3. 后处理：去除多余逗号、修正 $refs 等
    content = prettyCode(content, vmPath);
    result.put(filePath, content);
}
```

**解读**：
- `render(bindingMap)` 是核心调用，把变量灌进模板
- `prettyCode` 是后处理，让生成的代码符合 ESLint 规范

### 3.3 bindingMap：模板变量的"上下文"

**位置**：`CodegenEngine.java` 行 488-576

```java
private Map<String, Object> initBindingMap(DbType dbType, CodegenTableDO table,
                                          List<CodegenColumnDO> columns, ...) {
    Map<String, Object> bindingMap = new HashMap<>(globalBindingMap);
    bindingMap.put("dbType", dbType);
    bindingMap.put("table", table);
    bindingMap.put("columns", columns);
    bindingMap.put("primaryColumn", CollectionUtils.findFirst(columns, CodegenColumnDO::getPrimaryKey));
    bindingMap.put("sceneEnum", CodegenSceneEnum.valueOf(table.getScene()));

    // className 相关
    String className = table.getClassName();
    String simpleClassName = equalsAnyIgnoreCase(table.getClassName(), table.getModuleName())
        ? table.getClassName()
        : removePrefix(table.getClassName(), upperFirst(table.getModuleName()));
    String classNameVar = lowerFirst(simpleClassName);
    bindingMap.put("simpleClassName", simpleClassName);
    bindingMap.put("simpleClassName_underlineCase", toUnderlineCase(simpleClassName));
    bindingMap.put("classNameVar", classNameVar);
    bindingMap.put("simpleClassName_strikeCase", toSymbolCase(simpleClassName, '-'));
    // ...

    return bindingMap;
}
```

**解读**：
- `globalBindingMap` 在 `@PostConstruct` 初始化（包含 basePackage、jakartaPackage 等全局配置）
- 每个表动态计算 `simpleClassName`（去模块前缀）、`classNameVar`（首字母小写）、各种命名风格
- **这些变量决定了模板里 `${simpleClassName}` 的输出**

### 3.4 一个完整的 .vm 文件结构示例

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/dal/do.vm` 行 1-30

```velocity
package ${basePackage}.module.${table.moduleName}.dal.dataobject.${table.businessName};

## 主子表专属逻辑
#if($table.subTables)
#foreach($subTable in $table.subTables)
import ${basePackage}.module.${subTable.moduleName}.dal.dataobject.${subTable.businessName}.${subTable.className}DO;
#end
#end

import ${basePackage}.module.${table.moduleName}.${BaseDOClassName};

## VO 类型为 DO 时，DO 直接作为 VO
#if ($voType == 20)
import io.swagger.v3.oas.annotations.media.Schema;
import cn.idev.excel.annotation.ExcelProperty;
#end

import lombok.Data;
import com.baomidou.mybatisplus.annotation.KeySequence;
import com.baomidou.mybatisplus.annotation.TableName;

/**
 * ${table.classComment} DO
 */
@TableName("${table.tableName.toLowerCase()}")
@KeySequence("${table.tableName.toLowerCase()}_seq")
@Data
public class ${table.className}DO extends BaseDO {
```

**解读**：
- `${basePackage}` → `cn.iocoder.yudao`
- `${table.moduleName}` → `system`（来自表名 `system_xxx`）
- `${table.tableName.toLowerCase()}` → `system_dict_type`
- `${voType == 20}` 判断是否 DO 模式

## 4. 关键要点总结

- Velocity 三大语法：**变量**（`${}`）、**指令**（`#`）、**注释**（`##`）
- ruoyi 用 hutool 封装的 `VelocityEngine`，从 classpath 加载模板
- **bindingMap 是模板上下文**，所有变量都从 `CodegenEngine.initBindingMap` 计算
- 一个变量可以在多个模板中复用（如 `${table.className}` 在 30+ 个模板出现）
- 模板中**所有占位符都对应 bindingMap 中的 key**

## 5. 练习题

### 练习 1：基础（必做）

写一个简单的 `hello.vm` 模板：

```velocity
你好，${name}！你今年 ${age} 岁了。
#if($age >= 18)
你是成年人。
#else
你是未成年人。
#end
```

并在 Java 中渲染它（`name=芋道源码, age=18`）。

### 练习 2：进阶

阅读 `controller.vm` 的前 50 行，列出其中出现的**所有 Velocity 变量**和**所有 Velocity 指令**。

### 练习 3：挑战（选做）

`simpleClassName_strikeCase` 是什么格式？写出从 `DictTypeData` 转换到该格式的步骤（提示：用到 `toSymbolCase(name, '-')`）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/dal/do.vm`
- Velocity 官方文档：https://velocity.apache.org/
- hutool 模板文档：https://doc.hutool.cn/pages/ExtraTemplate/
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
