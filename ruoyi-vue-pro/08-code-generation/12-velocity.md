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

#### 设置变量 / 引用变量 / 条件 / 循环

```velocity
#set ($greeting = "Hello")
#set ($name = "World")

${greeting}, ${name}!

#if ($table.templateType == 2)
    这是树表
#else
    这是普通表
#end

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

## 3. 关键要点总结

- Velocity 三大语法：**变量**（`${}`）、**指令**（`#`）、**注释**（`##`）
- ruoyi 用 hutool 封装的 `VelocityEngine`，从 classpath 加载模板
- **bindingMap 是模板上下文**，所有变量都从 `CodegenEngine.initBindingMap` 计算
- 一个变量可以在多个模板中复用（如 `${table.className}` 在 30+ 个模板出现）
- 模板中**所有占位符都对应 bindingMap 中的 key**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
