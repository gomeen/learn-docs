# 07 - 业务模块

> ruoyi-vue-pro 包含 20+ 业务模块。本分类讲解核心模块的设计与实现。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 模块 7.1 模块结构

- [ ] [1.1 ruoyi 的业务模块划分](./01-module-structure.md)
- [ ] [1.2 单模块的 MVC 分层](./02-mvc-layers.md)
- [ ] [1.3 Controller / Service / DAO 命名规范](../../_common/20-engineering/01-naming.md)
- [ ] [1.4 DTO / VO / DO / BO 转换](./03-dto-vo-do.md)
- [ ] [1.5 MapStruct 转换实战](./04-mapstruct-practice.md)
- [ ] [1.6 通用 CRUD：PageResult / CommonResult](./05-common-result.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [06-*-module-structure: 业务模块结构与分层](./06-*-module-structure.md)
  - 覆盖：01-module-structure.md, 02-mvc-layers.md, 03-dto-vo-do.md, 04-mapstruct-practice.md, 05-common-result.md


## 模块 7.2 系统管理（system）

- [ ] [2.1 用户管理](./07-user.md)
- [ ] [2.2 角色管理](./08-role.md)
- [ ] [2.3 菜单管理](./09-menu.md)
- [ ] [2.4 部门管理：树形结构](./10-dept.md)
- [ ] [2.5 字典管理](./11-dict.md)
- [ ] [2.6 通知公告](./12-notify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [13-*-system: 系统管理：用户角色菜单部门](./13-*-system.md)
  - 覆盖：07-user.md, 08-role.md, 09-menu.md, 10-dept.md, 11-dict.md, 12-notify.md


## 模块 7.3 基础设施（infra）

- [ ] [3.1 代码生成器](./14-code-gen.md)
- [ ] [3.2 定时任务](./15-job.md)
- [ ] [3.3 文件存储：本地/S3/MinIO/阿里云/腾讯云/七牛云](./16-file-storage.md)
- [ ] [3.4 API 日志](./17-api-log.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [18-*-infra: 基础设施：代码生成 / 任务 / 文件 / API 日志](./18-*-infra.md)
  - 覆盖：14-code-gen.md, 15-job.md, 16-file-storage.md, 17-api-log.md

- [ ] [3.5 配置管理：动态配置](./19-config.md)
- [ ] [3.6 邮件发送](./20-email.md)
- [ ] [3.7 短信发送：阿里云/腾讯云](./21-sms.md)
- [ ] [3.8 站内信](./22-in-site-message.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [23-*-infra-notify: 配置 / 邮件 / 短信 / 站内信](./23-*-infra-notify.md)
  - 覆盖：19-config.md, 20-email.md, 21-sms.md, 22-in-site-message.md


## 模块 7.4 会员中心（member）

- [ ] [4.1 会员注册/登录](./24-member-auth.md)
- [ ] [4.2 会员等级](./25-member-level.md)
- [ ] [4.3 积分系统](./26-points.md)
- [ ] [4.4 签到](./27-sign-in.md)
- [ ] [4.5 收货地址](./28-address.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [29-*-member: 会员中心](./29-*-member.md)
  - 覆盖：24-member-auth.md, 25-member-level.md, 26-points.md, 27-sign-in.md, 28-address.md


## 模块 7.5 商城系统（mall）

- [ ] [5.1 商品 SPU/SKU 设计](./30-spu-sku.md)
- [ ] [5.2 商品分类](./31-category.md)
- [ ] [5.3 购物车](./32-cart.md)
- [ ] [5.4 订单流程：创建/支付/发货/收货/退款](./33-order.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [34-*-mall: 商城：商品 / 分类 / 购物车 / 订单](./34-*-mall.md)
  - 覆盖：30-spu-sku.md, 31-category.md, 32-cart.md, 33-order.md

- [ ] [5.5 支付集成：支付宝/微信](./35-payment.md)
- [ ] [5.6 营销活动：优惠券/秒杀/拼团](./36-promotion.md)
- [ ] [5.7 分销](./37-distribution.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [38-*-mall-pay: 商城：支付 / 营销 / 分销](./38-*-mall-pay.md)
  - 覆盖：35-payment.md, 36-promotion.md, 37-distribution.md


## 模块 7.6 工作流（BPM）

- [ ] [6.1 流程定义：Modeler](./39-process-def.md)
- [ ] [6.2 表单设计：动态表单](./40-dynamic-form.md)
- [ ] [6.3 流程发起/审批](./41-process-instance.md)
- [ ] [6.4 任务分配：角色/部门/用户](./42-task-assign.md)
- [ ] [6.5 会签/或签](./43-vote.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [44-*-bpm-business: 业务侧工作流模块](./44-*-bpm-business.md)
  - 覆盖：39-process-def.md, 40-dynamic-form.md, 41-process-instance.md, 42-task-assign.md, 43-vote.md


## 模块 7.7 其他模块

- [ ] [7.1 CRM 客户管理](./45-crm.md)
- [ ] [7.2 ERP 采购/销售/库存](./46-erp.md)
- [ ] [7.3 IoT 物联网：设备/产品/规则](./47-iot.md)
- [ ] [7.4 IM 即时通讯：WebSocket](./48-im.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [49-*-other-biz: CRM / ERP / IoT / IM](./49-*-other-biz.md)
  - 覆盖：45-crm.md, 46-erp.md, 47-iot.md, 48-im.md

- [ ] [7.5 微信公众号](./50-wechat-mp.md)
- [ ] [7.6 报表：积木报表](./51-report.md)
- [ ] [7.7 大屏设计器](./52-dashboard.md)
- [ ] [7.8 AI 大模型（Spring AI）](./53-ai.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [54-*-report-ai: 微信公众号 / 报表 / 大屏 / AI](./54-*-report-ai.md)
  - 覆盖：50-wechat-mp.md, 51-report.md, 52-dashboard.md, 53-ai.md


## 🎯 ruoyi-vue-pro 仓库对应位置

- 系统模块：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 基础设施：`yudao-module-infra/`
- 业务模块：`yudao-module-mall/`、`yudao-module-crm/`、`yudao-module-erp/` 等
- 每个模块标准结构：`src/main/java/.../{controller,service,dal}/`
