# 7.5.3 购物车

> 理解 ruoyi 商城购物车（Cart）的设计与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 购物车的设计
- 理解购物车的持久化和缓存策略
- 学会购物车商品数量、选中状态管理
- 能扩展购物车业务

## 📚 前置知识

- 21-member-auth.md
- 26-spu-sku.md
- Redis 基础

## 1. 核心概念

### 1.1 购物车设计

**两种存储方式**：

| 方式 | 适用场景 | 优缺点 |
|------|----------|--------|
| 登录前 - LocalStorage | 未登录用户 | 简单，但不跨设备 |
| 登录后 - 数据库 | 登录用户 | 跨设备同步 |

ruoyi 同时支持：
- 登录后使用 DB 持久化
- 未登录时使用 Redis 临时存储

### 1.2 购物车表

```sql
CREATE TABLE trade_cart (
    id BIGINT PRIMARY KEY,
    user_id BIGINT,
    spu_id BIGINT,
    sku_id BIGINT,
    count INT,                -- 数量
    selected BOOLEAN,         -- 是否选中
    create_time DATETIME
);
```

### 1.3 核心字段

```java
public class CartDO {
    private Long id;
    private Long userId;
    private Long spuId;
    private Long skuId;
    private Integer count;
    private Boolean selected;
    private LocalDateTime createTime;
}
```

## 2. 代码示例

### 2.1 添加购物车

```java
@PostMapping("/add")
public CommonResult<Boolean> addCart(@Valid @RequestBody AppCartAddReqVO addReqVO) {
    cartService.addCart(getLoginUserId(), addReqVO);
    return success(true);
}

@Override
@Transactional
public void addCart(Long userId, AppCartAddReqVO addReqVO) {
    // 1. 校验 SKU
    ProductSkuDO sku = skuService.getSku(addReqVO.getSkuId());
    if (sku == null || sku.getStock() < addReqVO.getCount()) {
        throw exception(SKU_NOT_ENOUGH_STOCK);
    }
    // 2. 查询是否已存在
    CartDO cart = cartMapper.selectByUserIdAndSkuId(userId, addReqVO.getSkuId());
    if (cart == null) {
        // 3. 新增
        cart = new CartDO();
        cart.setUserId(userId);
        cart.setSpuId(sku.getSpuId());
        cart.setSkuId(sku.getId());
        cart.setCount(addReqVO.getCount());
        cart.setSelected(true);
        cartMapper.insert(cart);
    } else {
        // 4. 累加数量
        cart.setCount(cart.getCount() + addReqVO.getCount());
        cartMapper.updateById(cart);
    }
}
```

### 2.2 购物车列表

```java
@GetMapping("/list")
public CommonResult<List<AppCartRespVO>> getCartList() {
    return success(cartService.getCartList(getLoginUserId()));
}
```

### 2.3 修改数量

```java
@PutMapping("/update-count")
public CommonResult<Boolean> updateCartCount(@RequestParam("id") Long id,
                                              @RequestParam("count") Integer count) {
    cartService.updateCartCount(getLoginUserId(), id, count);
    return success(true);
}
```

### 2.4 选中/取消选中

```java
@PutMapping("/update-selected")
public CommonResult<Boolean> updateCartSelected(@Valid @RequestBody AppCartSelectedReqVO reqVO) {
    cartService.updateCartSelected(getLoginUserId(), reqVO);
    return success(true);
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AppCartController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/controller/app/cart/`

**核心代码**（简化）：

```java
@Tag(name = "用户 APP - 购物车")
@RestController
@RequestMapping("/trade/cart")
@Validated
public class AppCartController {

    @Resource
    private CartService cartService;

    @PostMapping("/add")
    @Operation(summary = "添加商品到购物车")
    public CommonResult<Boolean> addCart(@Valid @RequestBody AppCartAddReqVO addReqVO) {
        cartService.addCart(getLoginUserId(), addReqVO);
        return success(true);
    }

    @GetMapping("/list")
    @Operation(summary = "获得购物车列表")
    public CommonResult<List<AppCartRespVO>> getCartList() {
        return success(cartService.getCartList(getLoginUserId()));
    }

    @PutMapping("/update-count")
    @Operation(summary = "修改购物车商品数量")
    public CommonResult<Boolean> updateCartCount(@RequestParam("id") Long id,
                                                  @RequestParam("count") Integer count) {
        cartService.updateCartCount(getLoginUserId(), id, count);
        return success(true);
    }

    @DeleteMapping("/delete")
    public CommonResult<Boolean> deleteCart(@RequestParam("ids") List<Long> ids) {
        cartService.deleteCart(getLoginUserId(), ids);
        return success(true);
    }
}
```

### 3.2 购物车数据

```java
public class AppCartRespVO {
    private Long id;
    private Long spuId;
    private String spuName;
    private String picUrl;
    private Long skuId;
    private String skuProperties;  // 规格
    private BigDecimal price;
    private Integer count;
    private Boolean selected;
    private Integer stock;
    private Boolean inStock;       // 是否有货
}
```

## 4. 关键要点总结

- 购物车是会员的 1:N 数据
- 通过 (userId, skuId) 唯一索引防重
- 选中状态独立维护
- 库存独立校验
- 删除可以批量

## 5. 练习题

### 练习 1：基础（必做）

打开 `CartDO.java`，列出所有字段。

### 练习 2：进阶

阅读 `CartServiceImpl.java`，理解 `addCart` 的去重逻辑。

### 练习 3：挑战（选做）

设计"未登录购物车合并"功能：用户未登录时把购物车存 LocalStorage，登录后合并到数据库。列出实现思路。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mall/yudao-module-trade/src/main/java/cn/iocoder/yudao/module/trade/controller/app/cart/AppCartController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
