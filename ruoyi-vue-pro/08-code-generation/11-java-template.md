# 3.2 ruoyi 的 Java 模板

> 深入解读 ruoyi 全部 Java 模板的内部结构与关键占位符。

## 🎯 学习目标

完成本文档后，你将能够：
- 列出 ruoyi 全部 15 个 Java 模板及其作用
- 解释每个模板中**核心占位符**的含义
- 理解 Controller / Service / Mapper / DO 模板的相互引用关系
- 独立修改一个 Java 模板

## 📚 前置知识

- Velocity（详见 [Velocity](./10-velocity.md)）
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

## 3. ruoyi 仓库源码解读

### 3.1 controller.vm 关键片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/controller.vm`

```velocity
package ${basePackage}.module.${table.moduleName}.controller.${sceneEnum.basePackage}.${table.businessName};

import org.springframework.web.bind.annotation.*;
#if ($importEnable)
import org.springframework.web.multipart.MultipartFile;
#end
import ${jakartaPackage}.annotation.Resource;
## 只在管理后台加 @PreAuthorize
#if ($sceneEnum.scene == 1)
import org.springframework.security.access.prepost.PreAuthorize;
#end

@Tag(name = "${sceneEnum.name} - ${table.classComment}")
@RestController
@RequestMapping("/${table.moduleName}/${simpleClassName_strikeCase}")
@Validated
public class ${sceneEnum.prefixClass}${table.className}Controller {

    @Resource
    private ${table.className}Service ${classNameVar}Service;
```

**关键占位符**：
- `${basePackage}` → `cn.iocoder.yudao`（基础包）
- `${table.moduleName}` → `system`（一级目录）
- `${sceneEnum.basePackage}` → `admin` 或 `app`
- `${table.businessName}` → `dict`（二级目录）
- `${importEnable}` → 全局配置（application.yml）
- `${jakartaPackage}` → `jakarta` 或 `javax`（JDK 17 切换）
- `${sceneEnum.scene}` → 1=管理后台, 2=用户 APP
- `${sceneEnum.name}` → "管理后台" / "用户 APP"
- `${table.classComment}` → "字典类型"
- `${simpleClassName_strikeCase}` → `dict-type`（短横线分隔）
- `${sceneEnum.prefixClass}` → "" (admin) / "App" (app)
- `${table.className}` → `DictType`
- `${classNameVar}` → `dictType`（首字母小写）

### 3.2 service.vm 关键片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/service.vm`

```velocity
package ${basePackage}.module.${table.moduleName}.service.${table.businessName};

import ${basePackage}.module.${table.moduleName}.controller.${sceneEnum.basePackage}.${table.businessName}.vo.*;
import ${basePackage}.module.${table.moduleName}.dal.dataobject.${table.businessName}.${table.className}DO;

public interface ${table.className}Service {

    ${primaryColumn.javaType} create${simpleClassName}(@Valid ${saveReqVOClass} ${saveReqVOVar});

    void update${simpleClassName}(@Valid ${updateReqVOClass} ${updateReqVOVar});

    void delete${simpleClassName}(${primaryColumn.javaType} id);

#if ( $table.templateType != 2 && $deleteBatchEnable)
    void delete${simpleClassName}ListByIds(List<${primaryColumn.javaType}> ids);
#end

    ${table.className}DO get${simpleClassName}(${primaryColumn.javaType} id);

#if ( $table.templateType != 2 )
    PageResult<${table.className}DO> get${simpleClassName}Page(${sceneEnum.prefixClass}${table.className}PageReqVO pageReqVO);
#else
    List<${table.className}DO> get${simpleClassName}List(${sceneEnum.prefixClass}${table.className}ListReqVO listReqVO);
#end
}
```

**关键占位符**：
- `${primaryColumn.javaType}` → 主键的 Java 类型（如 `Long`）
- `${saveReqVOClass}` → `AdminDictTypeSaveReqVO`
- `${saveReqVOVar}` → `createReqVO`
- `${table.templateType != 2 && $deleteBatchEnable}` → 树表 + 启用批量删除 才生成批量删除接口

### 3.3 serviceImpl.vm 关键片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`

```velocity
@Service
@Validated
public class ${table.className}ServiceImpl implements ${table.className}Service {

    @Resource
    private ${table.className}Mapper ${classNameVar}Mapper;

    @Override
    public ${primaryColumn.javaType} create${simpleClassName}(${saveReqVOClass} ${saveReqVOVar}) {
        // 1. 校验
        validate${simpleClassName}ForCreateOrUpdate(${saveReqVOVar});
        // 2. 转换
        ${table.className}DO ${classNameVar} = BeanUtils.toBean(${saveReqVOVar}, ${table.className}.class);
        // 3. 插入
        ${classNameVar}Mapper.insert(${classNameVar});
        // 4. 返回主键
        return ${classNameVar}.getId();
    }
    // ...
}
```

### 3.4 do.vm 关键片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/dal/do.vm`

```velocity
package ${basePackage}.module.${table.moduleName}.dal.dataobject.${table.businessName};

import ${basePackage}.module.${table.moduleName}.${BaseDOClassName};
import com.baomidou.mybatisplus.annotation.KeySequence;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * ${table.classComment} DO
 */
@TableName("${table.tableName.toLowerCase()}")
@KeySequence("${table.tableName.toLowerCase()}_seq")
@Data
public class ${table.className}DO extends BaseDO {

#foreach($column in $columns)
## 主键字段
#if($column.primaryKey)
    /** $column.columnComment */
    @TableId
    private $column.javaType $column.javaField;
## 普通字段
#else
    /** $column.columnComment */
    private $column.javaType $column.javaField;
#end

#end
}
```

**解读**：
- `@TableName` 的值是表名小写
- `@KeySequence` 是 Oracle/PG 等需要的序列（MySQL 也加但不影响）
- 每个字段遍历 `columns`，主键加 `@TableId`

### 3.5 mapper.vm 关键片段

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/dal/mapper.vm`

```velocity
package ${basePackage}.module.${table.moduleName}.dal.mysql.${table.businessName};

import ${basePackage}.module.${table.moduleName}.dal.dataobject.${table.businessName}.${table.className}DO;
import ${baseMapperClassName};
import ${QueryWrapperClassName};

public interface ${table.className}Mapper extends BaseMapperX<${table.className}DO> {

    default PageResult<${table.className}DO> selectPage(${sceneEnum.prefixClass}${table.className}PageReqVO reqVO) {
        return selectPage(reqVO, new LambdaQueryWrapperX<${table.className}DO>()
                .eqIfPresent(${table.className}DO::getStatus, reqVO.getStatus())
                // ... 其他字段
                .betweenIfPresent(${table.className}DO::getCreateTime, reqVO.getCreateTime())
                .orderByDesc(${table.className}DO::getId));
    }
}
```

**关键占位符**：
- `${BaseMapperClassName}` → `cn.iocoder.yudao.framework.mybatis.core.mapper.BaseMapperX`
- `${QueryWrapperClassName}` → `cn.iocoder.yudao.framework.mybatis.core.query.LambdaQueryWrapperX`

## 4. 关键要点总结

- 15 个 Java 模板分 6 个目录：`controller/vo`, `service`, `dal`, `enums`, `test`
- **每个模板的 package 路径都由 `${basePackage}.module.${moduleName}.${业务子目录}` 组成**
- 关键占位符几乎都来自 `CodegenEngine.initBindingMap`
- Controller 和 Service 模板都用 `#if` 控制**树表/非树表**、**ERP/非 ERP** 分支
- DO 模板的字段直接遍历 `columns`，主键加 `@TableId`
- Mapper 模板用 `LambdaQueryWrapperX`（ruoyi 自定义扩展）拼接查询条件

## 5. 练习题

### 练习 1：基础（必做）

打开 `controller.vm`，在 IDEA 中**高亮**所有 `${...}` 占位符（`Ctrl+F` 搜 `$`），统计一共有多少个不同的占位符。

### 练习 2：进阶

修改 `serviceImpl.vm`，在 `createXxx` 方法的"校验"和"转换"之间加一行 `logger.info("创建: {}", createReqVO);`。写出修改后的 `#if` 块。

### 练习 3：挑战（选做）

仿照 `mapper.vm`，写一个 `mapper_count.vm` 模板，**额外生成**一个 `countByXxx` 方法（按某个字段统计数量），需要在 `CodegenEngine.SERVER_TEMPLATES` 注册。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/controller/controller.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/service.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/service/serviceImpl.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/dal/do.vm`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/resources/codegen/java/dal/mapper.vm`
- 官方文档：https://doc.iocoder.cn/codegen/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
