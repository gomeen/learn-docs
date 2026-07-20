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

## 3. 关键要点总结

- 单表 CRUD 生成 = 1 个 Controller + 1 个 Service/Impl + 1 个 Mapper + 1 个 DO + 3 个 VO + Vue 2 文件
- **编辑配置是全删全插**字段，性能略差但代码简单
- 预览返回 `Map<文件路径, 内容>`，下载返回 zip
- 生成后需执行 SQL 脚本把菜单接入后台
- **业务代码接入流程**：解压 → 复制到对应模块 → 执行 SQL → 重启服务

---

**文档版本**：v1.0
**最后更新**：2026-07-13
