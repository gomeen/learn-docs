# 7.7.1 CRM 客户管理

> 理解 ruoyi CRM 模块的设计与实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi CRM 客户管理的设计
- 理解线索、客户、商机、合同的关系
- 学会 CRM 业务的核心流程
- 能扩展自定义 CRM 业务

## 📚 前置知识

- 会员认证（详见 [会员认证](./21-member-auth.md)）
- MVC 分层（详见 [MVC 分层](./02-mvc-layers.md)）
- 命名规范（详见 [命名](./03-naming.md)）
- 数据权限（详见 [数据权限实现](../06-security/29-ruoyi-data-permission.md)）

## 1. 核心概念

### 1.1 CRM 业务流程

```
[线索] → 转化 → [客户] → 创建 → [商机] → 成交 → [合同]
   ↓              ↓                       ↓
跟进记录       联系人/商机             回款管理
```

### 1.2 ruoyi CRM 核心模块

| 模块 | 说明 |
|------|------|
| 线索 | 销售线索（潜在客户） |
| 客户 | 已成交或跟进中客户 |
| 联系人 | 客户下的联系人 |
| 商机 | 销售机会 |
| 合同 | 销售合同 |
| 回款 | 合同回款记录 |
| 跟进 | 跟进记录 |
| 业绩 | 销售业绩统计 |

### 1.3 CRM 核心表

```sql
-- 客户表
CREATE TABLE crm_customer (
    id BIGINT,
    name VARCHAR(255),
    source_id INT,           -- 客户来源
    industry_id INT,         -- 行业
    level INT,               -- 客户等级
    owner_user_id BIGINT,    -- 负责人
    contact_next_time DATETIME, -- 下次联系时间
    status INT
);
```

## 2. 代码示例

### 2.1 客户管理

```java
@PostMapping("/create")
@PreAuthorize("@ss.hasPermission('crm:customer:create')")
public CommonResult<Long> createCustomer(@Valid @RequestBody CrmCustomerSaveReqVO createReqVO) {
    return success(customerService.createCustomer(createReqVO));
}

@GetMapping("/page")
public CommonResult<PageResult<CrmCustomerRespVO>> getCustomerPage(@Valid CrmCustomerPageReqVO pageVO) {
    return success(customerService.getCustomerPage(pageVO));
}
```

### 2.2 线索管理

```java
@PostMapping("/create")
public CommonResult<Long> createClue(@Valid @RequestBody CrmClueSaveReqVO createReqVO) {
    return success(clueService.createClue(createReqVO));
}

@PostMapping("/transform")
@Operation(summary = "线索转化为客户")
public CommonResult<Long> transformClue(@Valid @RequestBody CrmClueTransformReqVO reqVO) {
    return success(clueService.transformClue(reqVO));
}
```

### 2.3 跟进记录

```java
@PostMapping("/create")
public CommonResult<Long> createFollowUpRecord(@Valid @RequestBody CrmFollowUpSaveReqVO createReqVO) {
    return success(followUpService.createFollowUpRecord(createReqVO));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 CRM 模块结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-crm/src/main/java/cn/iocoder/yudao/module/crm/`

```
yudao-module-crm/
├── controller/admin/
│   ├── clue/             # 线索
│   ├── customer/         # 客户
│   ├── contact/          # 联系人
│   ├── business/         # 商机
│   ├── contract/         # 合同
│   ├── receivable/       # 回款
│   ├── followup/         # 跟进
│   ├── product/          # CRM 产品
│   ├── statistics/       # 统计
│   └── operatelog/       # 操作日志
├── convert/
├── dal/
└── service/
```

### 3.2 客户 Controller

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-crm/src/main/java/cn/iocoder/yudao/module/crm/controller/admin/customer/`

```java
@Tag(name = "管理后台 - CRM 客户")
@RestController
@RequestMapping("/crm/customer")
@Validated
public class CrmCustomerController {

    @Resource
    private CrmCustomerService customerService;

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('crm:customer:create')")
    public CommonResult<Long> createCustomer(@Valid @RequestBody CrmCustomerSaveReqVO createReqVO) {
        return success(customerService.createCustomer(createReqVO));
    }

    @PutMapping("/update")
    @PreAuthorize("@ss.hasPermission('crm:customer:update')")
    public CommonResult<Boolean> updateCustomer(@Valid @RequestBody CrmCustomerSaveReqVO updateReqVO) {
        customerService.updateCustomer(updateReqVO);
        return success(true);
    }

    @GetMapping("/page")
    public CommonResult<PageResult<CrmCustomerRespVO>> getCustomerPage(@Valid CrmCustomerPageReqVO pageVO) {
        return success(customerService.getCustomerPage(pageVO));
    }
}
```

### 3.3 数据权限

CRM 通常有**数据权限**（只看自己的客户）：

```java
@DataPermission(enable = true)  // 启用数据权限
public PageResult<CrmCustomerDO> getCustomerPage(CrmCustomerPageReqVO pageVO) {
    return customerMapper.selectPage(pageVO);
}
```

## 4. 关键要点总结

- ruoyi CRM 是独立业务模块
- 线索→客户→商机→合同是核心流程
- CRM 强调数据权限（销售只看自己）
- 跟进记录是 CRM 的核心数据
- 业绩统计是 CRM 的核心报表

## 5. 练习题

### 练习 1：基础（必做）

阅读 `CrmCustomerDO.java` 字段。

### 练习 2：进阶

阅读 `CrmClueServiceImpl.java`，理解线索转化为客户的实现。

### 练习 3：挑战（选做）

设计"客户撞库"功能：导入新客户时，自动检查是否已存在（按手机号/邮箱匹配）。列出实现方案。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-crm/src/main/java/cn/iocoder/yudao/module/crm/controller/admin/customer/`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
