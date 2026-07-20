# 3.5 自定义模板

> 学习如何为 ruoyi 代码生成器添加自定义的 Velocity 模板。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 ruoyi 代码生成器的扩展点
- 注册一个自定义 Java 模板
- 注册一个自定义 Vue 模板
- 修改全局变量影响所有模板

## 📚 前置知识

- 模板引擎与生成模板（详见 [Velocity](./12-velocity.md)、[Java 模板](./13-java-template.md)、[Vue 模板](./14-vue-template.md)）
- 总览（详见 [总览](./01-overview.md)）
- Java 类加载机制

## 1. 核心概念

### 1.1 三大扩展点

| 扩展点 | 位置 | 影响范围 |
|--------|------|---------|
| 新增 `.vm` 文件 | `src/main/resources/codegen/...` | 模板本身 |
| 注册模板到 `CodegenEngine` | `SERVER_TEMPLATES` / `FRONT_TEMPLATES` | 启用该模板 |
| 添加新变量到 `bindingMap` | `CodegenEngine.initBindingMap` 或 `initGlobalBindingMap` | 模板可用变量 |
| 添加新枚举 | `enums/codegen/` | 模板分支判断 |

### 1.2 自定义模板的两条路线

**路线 A：完全新增模板**（如生成 `DTO.java`）
1. 写一个 `xxx.vm` 文件到 `resources/codegen/...`
2. 在 `CodegenEngine` 注册模板路径和输出路径
3. 模板中用 `${...}` 引用 bindingMap 变量

**路线 B：扩展现有模板**（如给 Controller 加新接口）
1. 找到对应 `xxx.vm` 文件
2. 用 `#if` / `#foreach` 加新逻辑
3. **不需要**注册到 `CodegenEngine`

## 2. 代码示例

### 2.1 自定义一个导出 Excel 多线程异步的 Service

#### 文件：`src/main/resources/codegen/java/service/exportAsyncTask.vm`

```velocity
package ${basePackage}.module.${table.moduleName}.service.${table.businessName};

import jakarta.annotation.Resource;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

@Component
public class ${table.className}ExportAsyncTask {

    @Resource
    private ${table.className}Service ${classNameVar}Service;

    @Async
    public void exportToFile(String filePath, ${sceneEnum.prefixClass}${table.className}PageReqVO reqVO) {
        // 调用 Service 查询
        // 写入 Excel 到 filePath
    }
}
```

### 2.2 在 CodegenEngine 注册

```java
// 在 CodegenEngine.SERVER_TEMPLATES 中加一行
.put(javaTemplatePath("service/exportAsyncTask"),
     javaModuleImplMainFilePath("service/${table.businessName}/${table.className}ExportAsyncTask"))
```

## 3. 关键要点总结

- 自定义模板的两条路线：**新增模板**（要注册）或**修改现有模板**（直接改 .vm）
- 全局变量在 `initGlobalBindingMap` 注册，模板中可直接用 `${var}` 引用
- 新增配置属性在 `CodegenProperties` 加字段 + `application.yml` 配置
- 模板按 `LinkedHashMap` 顺序生成，**顺序就是文件出现的顺序**
- 模板路径和输出路径都可以用 bindingMap 变量做模板字符串

---

**文档版本**：v1.0
**最后更新**：2026-07-13
