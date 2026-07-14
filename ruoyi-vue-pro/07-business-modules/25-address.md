# 7.4.5 收货地址

> 理解 ruoyi 会员收货地址（Address）模块的设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 收货地址的设计
- 理解"默认地址"的唯一性设计
- 学会省市区级联数据结构
- 能扩展收货地址业务

## 📚 前置知识

- 21-member-auth.md
- 04-dto-vo-do.md

## 1. 核心概念

### 1.1 收货地址模型

```
[用户] 1:N [收货地址]
              ↓
          [默认地址唯一]
              ↓
      [省/市/区 级联]
```

### 1.2 核心字段

```java
public class MemberAddressDO {
    private Long id;
    private Long userId;          // 所属用户
    private String name;          // 收货人
    private String mobile;        // 收货手机
    private String provinceCode;  // 省编码
    private String provinceName;
    private String cityCode;
    private String cityName;
    private String areaCode;
    private String areaName;
    private String detailAddress; // 详细地址
    private Boolean defaultStatus; // 是否默认
    private Integer areaId;       // 区域 ID
}
```

### 1.3 默认地址设计

- 同一用户只能有一个默认地址
- 切换默认地址时**事务更新**两条记录
- 新建地址可选择是否默认

## 2. 代码示例

### 2.1 收货地址 CRUD

```java
@PostMapping("/create")
public CommonResult<Long> createAddress(@Valid @RequestBody MemberAddressSaveReqVO createReqVO) {
    return success(addressService.createAddress(getLoginUserId(), createReqVO));
}

@PutMapping("/update")
public CommonResult<Boolean> updateAddress(@Valid @RequestBody MemberAddressSaveReqVO updateReqVO) {
    addressService.updateAddress(getLoginUserId(), updateReqVO);
    return success(true);
}

@DeleteMapping("/delete")
public CommonResult<Boolean> deleteAddress(@RequestParam("id") Long id) {
    addressService.deleteAddress(getLoginUserId(), id);
    return success(true);
}

@GetMapping("/list")
public CommonResult<List<MemberAddressRespVO>> getAddressList() {
    return success(BeanUtils.toBean(addressService.getAddressList(getLoginUserId()),
            MemberAddressRespVO.class));
}
```

### 2.2 设为默认地址

```java
@PutMapping("/set-default")
public CommonResult<Boolean> setDefaultAddress(@RequestParam("id") Long id) {
    addressService.setDefaultAddress(getLoginUserId(), id);
    return success(true);
}

@Transactional
@Override
public void setDefaultAddress(Long userId, Long id) {
    // 1. 取消所有默认
    addressMapper.updateDefaultStatus(userId, false, null);
    // 2. 设置新的默认
    addressMapper.updateDefaultStatus(userId, true, id);
}
```

### 2.3 获取默认地址

```java
@GetMapping("/get-default")
public CommonResult<MemberAddressRespVO> getDefaultAddress() {
    MemberAddressDO address = addressService.getDefaultAddress(getLoginUserId());
    return success(BeanUtils.toBean(address, MemberAddressRespVO.class));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AppMemberAddressController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/app/address/AppMemberAddressController.java`

**核心代码**（简化）：

```java
@Tag(name = "用户 APP - 收货地址")
@RestController
@RequestMapping("/member/address")
@Validated
public class AppMemberAddressController {

    @Resource
    private AddressService addressService;

    @PostMapping("/create")
    @Operation(summary = "创建收货地址")
    public CommonResult<Long> createAddress(@Valid @RequestBody MemberAddressSaveReqVO createReqVO) {
        return success(addressService.createAddress(getLoginUserId(), createReqVO));
    }

    @GetMapping("/list")
    @Operation(summary = "获得收货地址列表")
    public CommonResult<List<MemberAddressRespVO>> getAddressList() {
        return success(BeanUtils.toBean(addressService.getAddressList(getLoginUserId()),
                MemberAddressRespVO.class));
    }

    @PutMapping("/set-default")
    @Operation(summary = "设置默认地址")
    public CommonResult<Boolean> setDefaultAddress(@RequestParam("id") Long id) {
        addressService.setDefaultAddress(getLoginUserId(), id);
        return success(true);
    }

    @GetMapping("/get-default")
    @Operation(summary = "获得默认地址")
    public CommonResult<MemberAddressRespVO> getDefaultAddress() {
        return success(BeanUtils.toBean(addressService.getDefaultAddress(getLoginUserId()),
                MemberAddressRespVO.class));
    }
}
```

### 3.2 创建地址

```java
@Transactional
@Override
public Long createAddress(Long userId, MemberAddressSaveReqVO createReqVO) {
    // 1. 如果是默认地址，先取消其他默认
    if (Boolean.TRUE.equals(createReqVO.getDefaultStatus())) {
        addressMapper.cancelAllDefault(userId);
    }
    // 2. 创建地址
    MemberAddressDO address = BeanUtils.toBean(createReqVO, MemberAddressDO.class);
    address.setUserId(userId);
    addressMapper.insert(address);
    return address.getId();
}
```

## 4. 关键要点总结

- 收货地址是会员的 1:N 数据
- 默认地址唯一，通过事务保证
- 省市区用 code + name 双重存储
- 详细地址是用户输入的字符串
- 地址常用于订单的下单流程

## 5. 练习题

### 练习 1：基础（必做）

打开 `MemberAddressDO.java`，列出所有字段。

### 练习 2：进阶

阅读 `AddressServiceImpl.java`，理解 `setDefaultAddress` 的事务实现。

### 练习 3：挑战（选做）

设计"地址簿导入"功能：用户上传 Excel 批量导入地址，列出实现步骤和异常处理。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/app/address/AppMemberAddressController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
