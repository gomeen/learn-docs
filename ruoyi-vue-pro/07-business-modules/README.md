# 07 - 业务模块

> ruoyi-vue-pro 包含 20+ 业务模块。本分类讲解核心模块的设计与实现。

## 模块 7.1 模块结构

- [ ] [1.1 ruoyi 的业务模块划分](./01-module-structure.md)
- [ ] [1.2 单模块的 MVC 分层](./02-mvc-layers.md)
- [ ] [1.3 Controller / Service / DAO 命名规范](./03-naming.md)
- [ ] [1.4 DTO / VO / DO / BO 转换](./04-dto-vo-do.md)
- [ ] [1.5 MapStruct 转换实战](./05-mapstruct-practice.md)
- [ ] [1.6 通用 CRUD：PageResult / CommonResult](./06-common-result.md)

## 模块 7.2 系统管理（system）

- [ ] [2.1 用户管理](./07-user.md)
- [ ] [2.2 角色管理](./08-role.md)
- [ ] [2.3 菜单管理](./09-menu.md)
- [ ] [2.4 部门管理：树形结构](./10-dept.md)
- [ ] [2.5 字典管理](./11-dict.md)
- [ ] [2.6 通知公告](./12-notify.md)

## 模块 7.3 基础设施（infra）

- [ ] [3.1 代码生成器](./13-code-gen.md)
- [ ] [3.2 定时任务](./14-job.md)
- [ ] [3.3 文件存储：本地/S3/MinIO/阿里云/腾讯云/七牛云](./15-file-storage.md)
- [ ] [3.4 API 日志](./16-api-log.md)
- [ ] [3.5 配置管理：动态配置](./17-config.md)
- [ ] [3.6 邮件发送](./18-email.md)
- [ ] [3.7 短信发送：阿里云/腾讯云](./19-sms.md)
- [ ] [3.8 站内信](./20-in-site-message.md)

## 模块 7.4 会员中心（member）

- [ ] [4.1 会员注册/登录](./21-member-auth.md)
- [ ] [4.2 会员等级](./22-member-level.md)
- [ ] [4.3 积分系统](./23-points.md)
- [ ] [4.4 签到](./24-sign-in.md)
- [ ] [4.5 收货地址](./25-address.md)

## 模块 7.5 商城系统（mall）

- [ ] [5.1 商品 SPU/SKU 设计](./26-spu-sku.md)
- [ ] [5.2 商品分类](./27-category.md)
- [ ] [5.3 购物车](./28-cart.md)
- [ ] [5.4 订单流程：创建/支付/发货/收货/退款](./29-order.md)
- [ ] [5.5 支付集成：支付宝/微信](./30-payment.md)
- [ ] [5.6 营销活动：优惠券/秒杀/拼团](./31-promotion.md)
- [ ] [5.7 分销](./32-distribution.md)

## 模块 7.6 工作流（BPM）

- [ ] [6.1 流程定义：Modeler](./33-process-def.md)
- [ ] [6.2 表单设计：动态表单](./34-dynamic-form.md)
- [ ] [6.3 流程发起/审批](./35-process-instance.md)
- [ ] [6.4 任务分配：角色/部门/用户](./36-task-assign.md)
- [ ] [6.5 会签/或签](./37-vote.md)

## 模块 7.7 其他模块

- [ ] [7.1 CRM 客户管理](./38-crm.md)
- [ ] [7.2 ERP 采购/销售/库存](./39-erp.md)
- [ ] [7.3 IoT 物联网：设备/产品/规则](./40-iot.md)
- [ ] [7.4 IM 即时通讯：WebSocket](./41-im.md)
- [ ] [7.5 微信公众号](./42-wechat-mp.md)
- [ ] [7.6 报表：积木报表](./43-report.md)
- [ ] [7.7 大屏设计器](./44-dashboard.md)
- [ ] [7.8 AI 大模型（Spring AI）](./45-ai.md)

## 🎯 ruoyi-vue-pro 仓库对应位置

- 系统模块：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/`
- 基础设施：`yudao-module-infra/`
- 业务模块：`yudao-module-mall/`、`yudao-module-crm/`、`yudao-module-erp/` 等
- 每个模块标准结构：`src/main/java/.../{controller,service,dal}/`
