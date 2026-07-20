# 3.2 ruoyi 的 Java 模板

> 深入解读 ruoyi 全部 Java 模板的内部结构与关键占位符。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 全部 15 个 Java 模板及其作用
- 解释每个模板中**核心占位符**的含义
- 理解 Controller / Service / Mapper / DO 模板的相互引用关系
- 独立修改一个 Java 模板

## 📚 前置知识

- Velocity（详见 [Velocity](./12-velocity.md)）
- 总览（详见 [总览](./01-overview.md)）
- Spring Boot 三层架构（详见 [MVC 分层](../07-business-modules/02-mvc-layers.md)）

## 1. 核心概念

### 1.1 15 个 Java 模板总览

```
codegen/java/
├── controller/
│   ├── controller.vm       # 主 Controller
│   └── vo/
│       ├── pageReqVO.vm    # 分页查询入参（非树表）
│       ├── listReqVO.vm    # 列表查询入参（树表）
│       ├── respVO.vm       # 响应 VO
│       ├── saveReqVO.vm    # 创建/修改入参（合并）
│       ├── importExcelVO.vm  # Excel 导入模板
│       └── importRespVO.vm   # 导入响应
├── service/
│   ├── service.vm          # Service 接口
│   └── serviceImpl.vm      # Service 实现
├── dal/
│   ├── do.vm               # 主表 DO
│   ├── do_sub.vm           # 子表 DO
│   ├── mapper.vm           # 主表 Mapper
│   ├── mapper_sub.vm       # 子表 Mapper
│   └── mapper.xml.vm       # MyBatis XML 桩
├── enums/
│   └── errorcode.vm        # 错误码常量
└── test/
    └── serviceTest.vm      # ServiceImpl 单元测试
```

### 1.2 生成路径

所有 Java 模板都生成到 `yudao-module-{moduleName}-server/src/main/java/{basePackage}/module/{moduleName}/` 下的对应目录。

## 2. 代码示例

### 2.1 Controller 模板生成效果（简化）

**输入**：表 `system_dict_type` → 类名 `DictType` → 模块 `system` → 业务 `dict`

**输出**：`AdminDictTypeController.java`

```java
package cn.iocoder.yudao.module.system.controller.admin.dict;

@RestController
@RequestMapping("/system/dict-type")
public class AdminDictTypeController {

    @Resource
    private DictTypeService dictTypeService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('system:dict-type:create')")
    public CommonResult<Long> createDictType(@Valid @RequestBody AdminDictTypeSaveReqVO createReqVO) {
        return success(dictTypeService.createDictType(createReqVO));
    }

    @GetMapping("/page")
    public CommonResult<PageResult<AdminDictTypeRespVO>> getDictTypePage(
        @Valid AdminDictTypePageReqVO pageReqVO) {
        PageResult<DictTypeDO> pageResult = dictTypeService.getDictTypePage(pageReqVO);
        return success(BeanUtils.toBean(pageResult, AdminDictTypeRespVO.class));
    }
    // ...
}
```

## 3. 关键要点总结

- 15 个 Java 模板分 6 个目录：`controller/vo`, `service`, `dal`, `enums`, `test`
- **每个模板的 package 路径都由 `${basePackage}.module.${moduleName}.${业务子目录}` 组成**
- 关键占位符几乎都来自 `CodegenEngine.initBindingMap`
- Controller 和 Service 模板都用 `#if` 控制**树表/非树表**、**ERP/非 ERP** 分支
- DO 模板的字段直接遍历 `columns`，主键加 `@TableId`
- Mapper 模板用 `LambdaQueryWrapperX`（ruoyi 自定义扩展）拼接查询条件

---

**文档版本**：v1.0
**最后更新**：2026-07-13
