# 7.2.5 字典管理

> 理解 ruoyi 中数据字典（Dict）的设计和实现，type + data 的两级结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 字典的两级结构（DictType + DictData）
- 理解字典在前端下拉框的使用场景
- 学会字典的查询接口设计
- 理解字典的缓存设计

## 📚 前置知识

- 06-common-result.md
- Redis 缓存基础
- 10-dept.md

## 1. 核心概念

### 1.1 字典的两级结构

ruoyi 的字典分两类：

**DictType**（字典类型）：定义一个字典的"分类"
```java
DictTypeDO { id, type, name, status }
例子：{ type: "user_status", name: "用户状态" }
```

**DictData**（字典数据）：字典的具体"项"
```java
DictDataDO { id, dictType, label, value, sort, status }
例子：{ dictType: "user_status", label: "启用", value: "0" }
                     { dictType: "user_status", label: "禁用", value: "1" }
```

### 1.2 字典的使用场景

字典常用于前端**下拉框**的选项数据：

```json
GET /system/dict-data/simple-list
[
  { "label": "启用", "value": "0" },
  { "label": "禁用", "value": "1" }
]
```

**常见字典**：
- `user_status`：用户状态（启用/禁用）
- `common_status`：通用状态
- `sex`：性别
- `menu_type`：菜单类型
- `system_notice_type`：通知类型

### 1.3 字典的缓存设计

字典数据**极少变化**，全部加载到 Redis：

```java
// 启动时全量加载
@PostConstruct
public void init() {
    // 把所有 DictData 按 type 分组缓存到 Redis
}

// 写时清空
@CacheEvict(cacheNames = "dict_data", allEntries = true)
public void updateDictData(...) { ... }
```

## 2. 代码示例

### 2.1 DictType 和 DictData 的关系

```java
// 字典类型
public class DictTypeDO {
    private Long id;
    private String type;    // 类型编码，如 "user_status"
    private String name;    // 类型名称，如 "用户状态"
    private Integer status;
}

// 字典数据
public class DictDataDO {
    private Long id;
    private String dictType;  // 关联到 DictType.type
    private String label;     // 显示文本，如 "启用"
    private String value;     // 实际值，如 "0"
    private Integer sort;
    private String colorType; // 前端标签颜色
    private String cssClass;  // CSS class
    private Integer status;
}
```

### 2.2 字典响应 VO

```java
@Data
public class DictDataSimpleRespVO {
    private String label;   // 显示文本
    private String value;   // 实际值
    private String colorType;  // 颜色
    private String cssClass;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 DictDataController 核心代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/dict/DictDataController.java`

**核心代码**（行 32-80）：

```java
@Tag(name = "管理后台 - 字典数据")
@RestController
@RequestMapping("/admin-api/system/dict-data")
@Validated
public class DictDataController {

    @Resource
    private DictDataService dictDataService;

    @PostMapping("/create")
    @Operation(summary = "新增字典数据")
    @PreAuthorize("@ss.hasPermission('system:dict:create')")
    public CommonResult<Long> createDictData(@Valid @RequestBody DictDataSaveReqVO createReqVO) {
        Long dictDataId = dictDataService.createDictData(createReqVO);
        return success(dictDataId);
    }

    @PutMapping("/update")
    @Operation(summary = "修改字典数据")
    @PreAuthorize("@ss.hasPermission('system:dict:update')")
    public CommonResult<Boolean> updateDictData(@Valid @RequestBody DictDataSaveReqVO updateReqVO) {
        dictDataService.updateDictData(updateReqVO);
        return success(true);
    }

    @DeleteMapping("/delete")
    @Operation(summary = "删除字典数据")
    @PreAuthorize("@ss.hasPermission('system:dict:delete')")
    public CommonResult<Boolean> deleteDictData(@RequestParam("id") Long id) {
        dictDataService.deleteDictData(id);
        return success(true);
    }

    @GetMapping(value = {"/list-all-simple", "simple-list"})
    @Operation(summary = "获得全部字典数据列表", description = "一般用于管理后台缓存字典数据在本地")
    // 无需添加权限认证，因为前端全局都需要
    public CommonResult<List<DictDataSimpleRespVO>> getSimpleDictDataList() {
        List<DictDataDO> list = dictDataService.getDictDataList(
                CommonStatusEnum.ENABLE.getStatus(), null);
        return success(BeanUtils.toBean(list, DictDataSimpleRespVO.class));
    }
}
```

**解读**：
- 第 6-9 行：标准 Controller 三件套
- 第 12-16 行：新增字典数据
- 第 29-33 行：精简列表接口（前端缓存字典到本地）
- 第 35-38 行：调用 `BeanUtils.toBean` 批量转换

### 3.2 DictType 控制器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/dict/DictTypeController.java`

**核心代码**（行 30-70）：

```java
@Tag(name = "管理后台 - 字典类型")
@RestController
@RequestMapping("/admin-api/system/dict-type")
@Validated
public class DictTypeController {

    @Resource
    private DictTypeService dictTypeService;

    @PostMapping("/create")
    @Operation(summary = "创建字典类型")
    @PreAuthorize("@ss.hasPermission('system:dict:create')")
    public CommonResult<Long> createDictType(@Valid @RequestBody DictTypeSaveReqVO createReqVO) {
        return success(dictTypeService.createDictType(createReqVO));
    }

    @GetMapping("/list")
    @Operation(summary = "获得字典类型列表")
    @PreAuthorize("@ss.hasPermission('system:dict:query')")
    public CommonResult<List<DictTypeRespVO>> getDictTypeList() {
        List<DictTypeDO> list = dictTypeService.getDictTypeList();
        return success(BeanUtils.toBean(list, DictTypeRespVO.class));
    }
}
```

**解读**：
- 字典类型管理较为简单，主要是 CRUD
- 字典类型分页 `getDictTypePage` 和列表 `getDictTypeList` 两个方法

## 4. 关键要点总结

- 字典分 DictType（类型）和 DictData（数据）两级
- 字典用于前端下拉框
- `/simple-list` 接口免鉴权（前端全局需要）
- 字典数据通常全量缓存到 Redis
- DictData 有 `label`（显示）+ `value`（实际值）

## 5. 练习题

### 练习 1：基础（必做）

打开 `DictDataMapper.java`，找到 `selectListByDictType` 方法，理解按 type 查询的实现。

### 练习 2：进阶

阅读 `DictDataServiceImpl.java`，理解字典数据的唯一性校验（同 type 下 value 不能重复）。

### 练习 3：挑战（选做）

设计一个"按 type 批量获取字典数据"接口，返回 `Map<String, List<DictDataSimpleRespVO>>`，要求一次查询返回所有需要的字典。说明如何避免循环查询。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/dict/DictDataController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/dict/DictTypeController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/dict/DictDataDO.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
