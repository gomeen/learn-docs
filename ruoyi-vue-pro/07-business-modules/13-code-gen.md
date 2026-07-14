# 7.3.1 代码生成器

> 理解 ruoyi 的代码生成器（CodeGen）原理，能从数据库表自动生成 CRUD 代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 代码生成器的工作流程
- 理解如何从数据库表生成 Controller / Service / DAO
- 学会配置代码生成的模板
- 能使用代码生成器提高开发效率

## 📚 前置知识

- Velocity / Freemarker 模板引擎
- 01-module-structure.md
- 02-mvc-layers.md

## 1. 核心概念

### 1.1 代码生成器的作用

**传统开发**：
1. 设计数据库表
2. 写 DO 实体类（10+ 字段重复劳动）
3. 写 Mapper、Service、Controller
4. 写 ReqVO、RespVO
5. 写 Convert、菜单 SQL

**代码生成器**：
- 选表 → 配置 → 一键生成
- 自动生成符合 ruoyi 规范的代码

### 1.2 ruoyi 代码生成器工作流

```
[数据库表] → [导入表] → [编辑配置] → [生成代码] → [下载 ZIP 包]
```

**核心步骤**：
1. **导入表结构**：从 MySQL `information_schema` 读表和字段
2. **编辑配置**：设置生成信息（模块名、业务名、作者）
3. **预览生成**：前端实时预览要生成的代码
4. **下载代码**：打包成 ZIP 供下载

### 1.3 生成的代码内容

ruoyi 默认会生成以下文件：

```
yudao-module-{module}/
├── controller/admin/{business}/
│   ├── {Business}Controller.java
│   └── vo/{Business}SaveReqVO.java
│   └── vo/{Business}RespVO.java
│   └── vo/{Business}PageReqVO.java
├── service/{business}/
│   ├── {Business}Service.java
│   └── {Business}ServiceImpl.java
├── dal/
│   ├── dataobject/{business}/{Business}DO.java
│   └── mysql/{business}/{Business}Mapper.java
├── convert/{business}/{Business}Convert.java
└── sql/
    └── {business}_menu.sql  # 菜单权限 SQL
```

## 2. 代码示例

### 2.1 导入表请求

```java
@PostMapping("/create-list")
@Operation(summary = "创建基于数据库表的代码生成")
public CommonResult<Boolean> createCodegenList(@Valid @RequestBody List<CodegenCreateListReqVO> reqs) {
    codegenService.createCodegenList(reqs);
    return success(true);
}
```

### 2.2 CodegenCreateListReqVO

```java
@Data
public class CodegenCreateListReqVO {
    @Schema(description = "表名", requiredMode = Schema.RequiredMode.REQUIRED)
    private String tableName;
    @Schema(description = "模块名", requiredMode = Schema.RequiredMode.REQUIRED)
    private String moduleName;
    @Schema(description = "业务名", requiredMode = Schema.RequiredMode.REQUIRED)
    private String businessName;
    @Schema(description = "作者", requiredMode = Schema.RequiredMode.REQUIRED)
    private String author;
    // ... 更多配置
}
```

### 2.3 生成的 Controller 示例

```java
@Tag(name = "管理后台 - 商品")
@RestController
@RequestMapping("/admin-api/mall/product")
@Validated
public class ProductController {

    @Resource
    private ProductService productService;

    @PostMapping("/create")
    @Operation(summary = "创建商品")
    @PreAuthorize("@ss.hasPermission('mall:product:create')")
    public CommonResult<Long> createProduct(@Valid @RequestBody ProductSaveReqVO createReqVO) {
        return success(productService.createProduct(createReqVO));
    }

    @GetMapping("/page")
    @Operation(summary = "获得商品分页")
    @PreAuthorize("@ss.hasPermission('mall:product:query')")
    public CommonResult<PageResult<ProductRespVO>> getProductPage(@Valid ProductPageReqVO pageVO) {
        return success(productService.getProductPage(pageVO));
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 CodegenController 核心接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/codegen/CodegenController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 代码生成")
@RestController
@RequestMapping("/infra/codegen")
@Validated
public class CodegenController {

    @Resource
    private CodegenService codegenService;

    @GetMapping("/db/table/list")
    @Operation(summary = "获得数据库自带的表 definition")
    public CommonResult<List<DatabaseTableRespVO>> getDatabaseTableList(
            @RequestParam(value = "name", required = false) String name,
            @RequestParam(value = "comment", required = false) String comment) {
        return success(codegenService.getDatabaseTableList(name, comment));
    }

    @PostMapping("/create-list")
    @Operation(summary = "创建基于数据库表的代码生成")
    public CommonResult<Boolean> createCodegenList(
            @Valid @RequestBody List<CodegenCreateListReqVO> reqs) {
        codegenService.createCodegenList(reqs);
        return success(true);
    }

    @GetMapping("/download")
    @Operation(summary = "下载代码生成代码")
    public void downloadCodegen(@RequestParam("id") Long id, HttpServletResponse response) {
        byte[] data = codegenService.downloadCodegen(id);
        // 输出 ZIP 流
    }
}
```

**解读**：
- 第 13-18 行：获取数据库所有表（用于选择要生成的表）
- 第 21-26 行：导入选中的表，生成代码配置
- 第 29-32 行：下载生成的 ZIP 包

### 3.2 代码生成器实现思路

ruoyi 的代码生成器基于 **Velocity 模板引擎**：

```java
// 1. 读取数据库表结构
DatabaseTable table = dbMetaData.getTable(tableName);
List<Column> columns = dbMetaData.getColumns(tableName);

// 2. 加载模板
Template controllerTpl = ve.getTemplate("controller.java.vm");

// 3. 绑定数据
VelocityContext context = new VelocityContext();
context.put("table", table);
context.put("columns", columns);
context.put("moduleName", "mall");
context.put("businessName", "product");

// 4. 渲染
StringWriter writer = new StringWriter();
controllerTpl.merge(context, writer);
String code = writer.toString();

// 5. 写入 ZIP
```

## 4. 关键要点总结

- ruoyi 代码生成器读取数据库表结构
- 基于 Velocity 模板引擎生成代码
- 支持生成 Controller、Service、DAO、VO、SQL
- 生成的代码符合 ruoyi 命名规范
- 可以提高 80% 的开发效率

## 5. 练习题

### 练习 1：基础（必做）

打开 `CodegenController.java`，列出所有接口，理解代码生成器的完整工作流。

### 练习 2：进阶

在 ruoyi 仓库中查找 `codegen` 目录下的 Velocity 模板文件（`.vm`），理解模板中可用的变量。

### 练习 3：挑战（选做）

思考：如果要支持生成"主子表"代码（一个主表带多个子表），代码生成器需要做哪些扩展？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/codegen/CodegenController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/CodegenService.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
