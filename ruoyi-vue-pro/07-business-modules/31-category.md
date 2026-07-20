# 7.5.2 商品分类

> 理解 ruoyi 商品分类（Category）的树形设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 商品分类的树形结构
- 理解分类的级联选择（省市区）
- 学会分类的批量获取和缓存
- 能扩展分类业务

## 📚 前置知识

- 树形结构参考（详见 [部门](./10-dept.md)）
- SPU/SKU（详见 [SPU/SKU](./30-spu-sku.md)）

## 1. 核心概念

### 1.1 商品分类模型

```
[一级分类] 电子产品
  ├── [二级分类] 手机
  │     ├── [三级分类] 智能手机
  │     └── [三级分类] 老人机
  ├── [二级分类] 电脑
  └── [二级分类] 平板

[一级分类] 服装
  ├── [二级分类] 男装
  └── [二级分类] 女装
```

### 1.2 核心字段

```java
public class ProductCategoryDO {
    private Long id;
    private Long parentId;     // 父分类 ID
    private String name;       // 分类名称
    private String icon;       // 图标
    private String picUrl;     // 图片
    private Integer sort;      // 排序
    private Integer status;    // 状态
    private String description;// 描述
    private Integer level;     // 层级（1/2/3）
}
```

## 2. 代码示例

### 2.1 分类树形接口

```java
@GetMapping("/list")
@Operation(summary = "获得商品分类列表（树形）")
public CommonResult<List<ProductCategoryRespVO>> getCategoryList() {
    // 1. 查所有分类
    List<ProductCategoryDO> list = categoryService.getCategoryList();
    // 2. 排序
    list.sort(Comparator.comparing(ProductCategoryDO::getSort));
    // 3. 转 VO
    return success(BeanUtils.toBean(list, ProductCategoryRespVO.class));
}

@GetMapping("/list-tree")
@Operation(summary = "获得商品分类树形结构")
public CommonResult<List<ProductCategoryTreeRespVO>> getCategoryTree() {
    return success(categoryService.getCategoryTree());
}
```

### 2.2 分类树构建

```java
public List<ProductCategoryTreeRespVO> getCategoryTree() {
    // 1. 查所有
    List<ProductCategoryDO> list = categoryService.getCategoryList();
    // 2. 排序
    list.sort(Comparator.comparing(ProductCategoryDO::getSort));
    // 3. 转 Map
    Map<Long, ProductCategoryTreeRespVO> map = new LinkedHashMap<>();
    list.forEach(c -> map.put(c.getId(), BeanUtils.toBean(c, ProductCategoryTreeRespVO.class)));
    // 4. 关联父子
    map.values().stream()
        .filter(c -> !Objects.equals(c.getParentId(), ROOT_ID))
        .forEach(child -> {
            ProductCategoryTreeRespVO parent = map.get(child.getParentId());
            if (parent != null) {
                if (parent.getChildren() == null) {
                    parent.setChildren(new ArrayList<>());
                }
                parent.getChildren().add(child);
            }
        });
    // 5. 返回根
    return map.values().stream()
        .filter(c -> Objects.equals(c.getParentId(), ROOT_ID))
        .collect(Collectors.toList());
}
```

### 2.3 分类级联选择器

```java
@GetMapping("/list-simple")
@Operation(summary = "获得分类精简列表", description = "用于商品发布时的级联选择")
public CommonResult<List<ProductCategorySimpleRespVO>> getSimpleCategoryList() {
    return success(BeanUtils.toBean(categoryService.getCategoryList(),
            ProductCategorySimpleRespVO.class));
}
```

## 3. 关键要点总结

- 商品分类是树形结构
- 通过 `parentId` 关联
- 同父分类下名称唯一
- 删除分类时要校验关联数据
- 级联选择器接口返回扁平列表

---

**文档版本**：v1.0
**最后更新**：2026-07-13
