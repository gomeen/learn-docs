# 4.1 生成单表 CRUD

> 实战演练：使用 ruoyi 代码生成器为一个简单单表生成完整模块。

## 🎯 学习目标

完成本文档后，你将能够：
- 完整走通"导入表 → 配置 → 预览 → 下载 → 集成" 5 步流程
- 理解单表 CRUD 模块生成的所有文件及其作用
- 把生成的代码无缝集成到 yudao-module-system 中

## 📚 前置知识

- 总览 / 导入表（详见 [总览](./01-overview.md)、[导入表](./03-table-import.md)）
- Spring Boot 项目结构（详见 [模块结构](../07-business-modules/01-module-structure.md)）

## 1. 核心概念

### 1.1 实战场景

我们为一张**新表** `system_demo` 生成完整 CRUD：
- 字段：`id, name, status, remark, create_time, update_time, creator, updater`
- 业务：系统演示表
- 模板类型：单表（ONE）

### 1.2 单表 CRUD 的生成产物

```
yudao-module-system/yudao-module-system-server/src/main/java/cn/iocoder/yudao/module/system/
├── controller/admin/demo/
│   ├── DemoController.java                    # 主 Controller
│   └── vo/
│       ├── DemoPageReqVO.java                 # 分页查询
│       ├── DemoRespVO.java                    # 响应
│       └── DemoSaveReqVO.java                 # 创建/修改
├── service/demo/
│   ├── DemoService.java                       # Service 接口
│   └── DemoServiceImpl.java                   # Service 实现
├── dal/
│   ├── dataobject/demo/DemoDO.java            # 数据库实体
│   └── mysql/demo/DemoMapper.java             # MyBatis Mapper
└── src/main/resources/
    └── mapper/demo/DemoMapper.xml             # MyBatis XML

yudao-ui-admin-vue3/src/views/system/demo/
├── index.vue                                  # 列表页
└── DemoForm.vue                               # 表单页
```

## 2. 代码示例

### 2.1 建表 SQL

```sql
CREATE TABLE system_demo (
    id           BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(50)  NOT NULL COMMENT '名称',
    status       TINYINT      NOT NULL DEFAULT 0 COMMENT '状态（0=启用, 1=禁用）',
    remark       VARCHAR(500) DEFAULT NULL COMMENT '备注',
    creator      VARCHAR(64)  DEFAULT '',
    create_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater      VARCHAR(64)  DEFAULT '',
    update_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted      BIT          NOT NULL DEFAULT 0 COMMENT '是否删除'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统演示';
```

### 2.2 通过前端创建代码生成

```json
POST /admin-api/infra/codegen/create-list
{
  "dataSourceConfigId": 1,
  "tableNames": ["system_demo"],
  "author": "芋道源码"
}
```

## 3. ruoyi 仓库源码解读

### 3.1 创建代码生成接口

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/codegen/CodegenController.java` 行 60-80

```java
@PostMapping("/create-list")
@Operation(summary = "创建代码生成（导入表）")
@PreAuthorize("@ss.hasPermission('infra:codegen:create')")
public CommonResult<List<Long>> createCodegenList(@Valid @RequestBody CodegenCreateListReqVO reqVO) {
    return success(codegenService.createCodegenList("芋道源码", reqVO));
}
```

**解读**：
- 路由：`POST /admin-api/infra/codegen/create-list`
- 入参：`dataSourceConfigId` + `tableNames[]` + `author`
- 出参：新建的 `CodegenTableDO` 的 ID 列表

### 3.2 Service 创建逻辑

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/CodegenServiceImpl.java` 行 68-100

```java
@Override
@Transactional(rollbackFor = Exception.class)
public List<Long> createCodegenList(String author, CodegenCreateListReqVO reqVO) {
    List<Long> ids = new ArrayList<>(reqVO.getTableNames().size());
    reqVO.getTableNames().forEach(tableName ->
        ids.add(createCodegen(author, reqVO.getDataSourceConfigId(), tableName)));
    return ids;
}

private Long createCodegen(String author, Long dataSourceConfigId, String tableName) {
    // 1. 从数据源读取
    TableInfo tableInfo = databaseTableService.getTable(dataSourceConfigId, tableName);
    // 2. 转元数据 + 入库
    return createCodegen0(author, dataSourceConfigId, tableInfo);
}
```

### 3.3 编辑配置

**位置**：`CodegenServiceImpl.java` 行 100-160

```java
@Override
public void updateCodegen(CodegenUpdateReqVO updateReqVO) {
    // 1. 校验表存在
    CodegenTableDO table = validateCodegenTableExists(updateReqVO.getId());
    // 2. 更新表配置
    CodegenTableDO updateTable = CodegenConvert.INSTANCE.convert(updateReqVO);
    codegenTableMapper.updateById(updateTable);
    // 3. 更新字段配置
    List<CodegenColumnDO> columns = CodegenConvert.INSTANCE.convertList2(updateReqVO.getColumns());
    columns.forEach(c -> {
        c.setTableId(table.getId());
        c.setUpdater(null);
        c.setUpdateTime(null);
    });
    codegenColumnMapper.deleteByTableId(table.getId());
    columns.forEach(codegenColumnMapper::insert);
}
```

**解读**：
- 编辑配置是**全删全插**——简单但会改变字段 ID
- 实际项目可以优化为 diff 更新

### 3.4 预览/下载

**位置**：`CodegenController.java` 行 130-155

```java
@GetMapping("/preview")
@Operation(summary = "预览代码")
@PreAuthorize("@ss.hasPermission('infra:codegen:preview')")
public CommonResult<List<CodegenPreviewRespVO>> previewCodegen(@RequestParam("id") Long id) {
    Map<String, String> codes = codegenService.generateCode(id);
    return success(convertMap(codes.entrySet(), Map.Entry::getKey, Map.Entry::getValue));
}

@GetMapping("/download")
@Operation(summary = "下载代码（zip）")
@PreAuthorize("@ss.hasPermission('infra:codegen:download')")
public void downloadCodegen(@RequestParam("id") Long id, HttpServletResponse response) throws IOException {
    byte[] data = codegenService.downloadCode(id);
    // 设置响应头，前端触发下载
    writeAttachment(response, "codegen.zip", data);
}
```

**解读**：
- `/preview` 返回文件路径 + 内容的 Map
- `/download` 返回 zip 压缩包
- `writeAttachment` 设置 `Content-Disposition: attachment; filename=...`

## 4. 关键要点总结

- 单表 CRUD 生成 = 1 个 Controller + 1 个 Service/Impl + 1 个 Mapper + 1 个 DO + 3 个 VO + Vue 2 文件
- **编辑配置是全删全插**字段，性能略差但代码简单
- 预览返回 `Map<文件路径, 内容>`，下载返回 zip
- 生成后需执行 SQL 脚本把菜单接入后台
- **业务代码接入流程**：解压 → 复制到对应模块 → 执行 SQL → 重启服务

## 5. 练习题

### 练习 1：基础（必做）

在测试库执行 `system_demo` 建表 SQL，然后用 ruoyi 前端执行导入表操作，**记录**每一步的截图。

### 练习 2：进阶

把生成的 `DemoController` 复制到 `yudao-module-system-server` 的 demo 包下，启动项目，访问 `http://localhost:48080/admin-api/system/demo/page` 看是否返回正确。

### 练习 3：挑战（选做）

写一个 `CodegenServiceImplTest`，**不启动 Spring** 也能测试 `createCodegenList` 方法。提示：用 Mockito 模拟 `databaseTableService` 和 `codegenTableMapper`。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/codegen/CodegenController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/CodegenServiceImpl.java`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
