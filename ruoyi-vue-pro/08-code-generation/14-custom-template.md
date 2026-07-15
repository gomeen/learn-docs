# 3.5 自定义模板

> 学习如何为 ruoyi 代码生成器添加自定义的 Velocity 模板。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 ruoyi 代码生成器的扩展点
- 注册一个自定义 Java 模板
- 注册一个自定义 Vue 模板
- 修改全局变量影响所有模板

## 📚 前置知识

- 模板引擎与生成模板（详见 [Velocity](./10-velocity.md)、[Java 模板](./11-java-template.md)、[Vue 模板](./12-vue-template.md)）
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

```velocity
## 文件: src/main/resources/codegen/java/service/exportAsyncTask.vm
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

## 3. ruoyi 仓库源码解读

### 3.1 CodegenEngine 注册位置

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java` 行 69-99

```java
private static final Map<String, String> SERVER_TEMPLATES = MapUtil.<String, String>builder(new LinkedHashMap<>())
    .put(javaTemplatePath("controller/vo/pageReqVO"), javaModuleImplVOFilePath("PageReqVO"))
    .put(javaTemplatePath("controller/vo/listReqVO"), javaModuleImplVOFilePath("ListReqVO"))
    // ...
    .put(javaTemplatePath("service/serviceImpl"),
         javaModuleImplMainFilePath("service/${table.businessName}/${table.className}ServiceImpl"))
    .put(javaTemplatePath("service/service"),
         javaModuleImplMainFilePath("service/${table.businessName}/${table.className}Service"))
    // SQL
    .put("codegen/sql/sql.vm", "sql/sql.sql")
    .put("codegen/sql/h2.vm", "sql/h2.sql")
    .build();
```

**解读**：
- 使用 `LinkedHashMap` 保持顺序（生成文件按此顺序）
- 模板路径（左）和输出路径（右）都是模板字符串
- 输出路径中可以引用 bindingMap 变量（用 `${var}` 占位符）

### 3.2 全局变量初始化

**位置**：`CodegenEngine.java` 行 329-362

```java
@PostConstruct
@VisibleForTesting
void initGlobalBindingMap() {
    // 全局配置
    globalBindingMap.put("basePackage", codegenProperties.getBasePackage());
    globalBindingMap.put("baseFrameworkPackage", codegenProperties.getBasePackage()
            + '.' + "framework");
    globalBindingMap.put("jakartaPackage", jakartaEnable ? "jakarta" : "javax");
    globalBindingMap.put("voType", codegenProperties.getVoType());
    // ...
    // 全局 Java Bean
    globalBindingMap.put("CommonResultClassName", CommonResult.class.getName());
    globalBindingMap.put("PageResultClassName", PageResult.class.getName());
    // ...
    // Util 工具类
    globalBindingMap.put("ServiceExceptionUtilClassName", ServiceExceptionUtil.class.getName());
    // ...
}
```

**解读**：
- 在 `@PostConstruct` 时初始化（应用启动后）
- 想加新全局变量 → 在这里 `.put("xxx", value)`
- 模板中可用 `${xxx}` 直接引用

### 3.3 CodegenProperties 自定义属性

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/framework/codegen/config/CodegenProperties.java`

```java
@Data
@Component
@ConfigurationProperties(prefix = "yudao.codegen")
public class CodegenProperties {

    private String basePackage;
    private String baseFrameworkPackage;
    private Integer voType;
    private Integer frontType;
    private Boolean unitTestEnable;
    private Boolean deleteBatchEnable;
    private Boolean importEnable;
}
```

**解读**：
- 用户在 `application.yml` 配 `yudao.codegen.xxx` 即可生效
- 想加新配置 → 在这里加字段，然后在 `initGlobalBindingMap` 引用

### 3.4 模板中的条件控制

**位置**：`CodegenEngine.java` 行 588-600

```java
// 如果禁用单元测试，则移除对应的模版
if (Boolean.FALSE.equals(codegenProperties.getUnitTestEnable())) {
    templates.remove(javaTemplatePath("test/serviceTest"));
    templates.remove("codegen/sql/h2.vm");
}
// 如果禁用 VO 类型，则移除对应的模版
if (ObjectUtil.notEqual(codegenProperties.getVoType(), CodegenVOTypeEnum.VO.getType())) {
    templates.remove(javaTemplatePath("controller/vo/respVO"));
    templates.remove(javaTemplatePath("controller/vo/saveReqVO"));
}
```

**解读**：
- 可以在 `getTemplates` 中根据 `CodegenProperties` 动态决定生成哪些模板
- 这是"功能开关"型扩展的常用位置

## 4. 关键要点总结

- 自定义模板的两条路线：**新增模板**（要注册）或**修改现有模板**（直接改 .vm）
- 全局变量在 `initGlobalBindingMap` 注册，模板中可直接用 `${var}` 引用
- 新增配置属性在 `CodegenProperties` 加字段 + `application.yml` 配置
- 模板按 `LinkedHashMap` 顺序生成，**顺序就是文件出现的顺序**
- 模板路径和输出路径都可以用 bindingMap 变量做模板字符串

## 5. 练习题

### 练习 1：基础（必做）

修改 `controller.vm`，给所有 Controller 加一个 `@ApiOperation` 注解到类上。写出修改后的代码片段。

### 练习 2：进阶

为"树表"增加一个"移动节点"接口 `/move`（请求参数：`{id, newParentId}`）。需要修改哪个 .vm 文件？写出新增的方法代码。

### 练习 3：挑战（选做）

新增一个全局变量 `author`（从 application.yml 读取，缺省值"芋道源码"），在所有 .vm 中可通过 `${author}` 引用。列出需要修改的所有文件。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/inner/CodegenEngine.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/framework/codegen/config/CodegenProperties.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/controller.vm`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
