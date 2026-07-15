# 08 ruoyi 代码生成器生成 SQL

> ruoyi 提供强大的代码生成器，能一键生成 Controller/Service/Mapper/SQL/Vue 全套代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 代码生成器的定位与能力
- 掌握代码生成器生成的 SQL 格式
- 知道如何自定义代码生成模板
- 能基于现有表快速生成增删改查功能

## 📚 前置知识

- [01-mysql-basics.md](./01-mysql-basics.md)
- [09-mybatis-vs-mp.md](./09-mybatis-vs-mp.md)
- MyBatis Plus 注解（`@TableName`、`@TableId`；注解原理见 [04-annotation](../01-java-fundamentals/04-annotation.md)）

## 1. 核心概念

### 1.1 代码生成器的价值

```
手动开发一张表的功能：
- 建表 SQL
- 实体类 DO
- Mapper 接口
- Service + ServiceImpl
- Controller + VO
- 前端页面

→ 至少 5-7 个文件，数百行代码

代码生成器：填写表名 → 一键生成所有文件（10 秒）
```

### 1.2 ruoyi 代码生成器模块

`yudao-module-infra` 提供：
- 数据源配置（支持多种数据库）
- 代码生成模板（Velocity 模板）
- 表结构导入与预览
- 一键生成：Java + SQL + Vue

### 1.3 生成的 SQL 类型

1. **建表 DDL**：根据列信息生成
2. **初始数据 INSERT**：可配置生成菜单/权限 SQL
3. **菜单 SQL**：自动生成菜单表 + 角色权限关联 SQL

## 2. 代码示例

### 2.1 生成的建表 SQL 模板

```sql
-- 代码生成器生成的建表 SQL 示例
CREATE TABLE `system_demo` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '编号',
  `name` varchar(50) NOT NULL COMMENT '名称',
  `status` tinyint NOT NULL DEFAULT '0' COMMENT '状态',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `creator` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updater` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` bit(1) NOT NULL DEFAULT b'0' COMMENT '是否删除',
  `tenant_id` bigint NOT NULL DEFAULT '0' COMMENT '租户编号',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='示例表';
```

### 2.2 生成的菜单权限 SQL

```sql
-- 生成的菜单 SQL（同时插入 system_menu 和 system_role_menu）
INSERT INTO system_menu(id, name, permission, type, sort, parent_id, path, icon, component, status)
VALUES (2000, '示例管理', '', 'M', 1, 0, 'demo', 'ep:aim', NULL, 0);

INSERT INTO system_menu(id, name, permission, type, sort, parent_id, path, component, status)
VALUES (2001, '示例查询', 'system:demo:query', 'B', 1, 2000, '', '', 0);

-- 关联到超级管理员角色（role_id = 1）
INSERT INTO system_role_menu(role_id, menu_id, creator, updater, tenant_id)
SELECT 1, id, '1', '1', tenant_id FROM system_menu WHERE id BETWEEN 2000 AND 2099;
```

### 2.3 生成的 Mapper XML（节选）

```xml
<!-- DemoMapper.xml - 由代码生成器自动生成 -->
<mapper namespace="cn.iocoder.yudao.module.system.dal.mysql.demo.DemoMapper">

    <select id="selectById" resultType="cn.iocoder.yudao.module.system.dal.dataobject.demo.DemoDO">
        SELECT id, name, status, remark, creator, create_time, updater, update_time, deleted, tenant_id
        FROM system_demo
        WHERE id = #{id} AND deleted = false
    </select>

    <select id="selectList" resultType="cn.iocoder.yudao.module.system.dal.dataobject.demo.DemoDO">
        SELECT id, name, status, remark, creator, create_time, updater, update_time, deleted, tenant_id
        FROM system_demo
        <where>
            <if test="name != null and name != ''">AND name LIKE CONCAT('%', #{name}, '%')</if>
            <if test="status != null">AND status = #{status}</if>
            AND deleted = false
        </where>
        ORDER BY id DESC
    </select>
</mapper>
```

## 3. ruoyi 仓库源码解读

### 3.1 代码生成器入口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/`

代码生成器的核心流程：
1. `CodegenTableServiceImpl`：表管理（导入、删除、预览）
2. `CodegenEngine`：核心引擎，调度各生成器
3. `CodegenBuilder`：模板构建（SQL、Java、Vue）

**核心代码（节选）**：

```java
// CodegenTableServiceImpl.java（节选）
public List<String> generateCode(Long tableId) {
    // 1. 校验表是否已导入
    CodegenTableDO table = validateCodegenTableExists(tableId);

    // 2. 加载表的列信息
    List<CodegenColumnDO> columns = codegenColumnMapper.selectListByTableId(tableId);

    // 3. 调用生成引擎
    return codegenEngine.generate(table, columns);
}
```

**解读**：
- 第 5 行：`validateCodegenTableExists(tableId)` —— 防止对不存在的表生成代码
- 第 8 行：`selectListByTableId` —— 加载表的列定义
- 第 11 行：`codegenEngine.generate` —— 调用生成引擎（模板渲染）

### 3.2 代码生成配置表

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`

```sql
-- 代码生成表（用于保存生成配置）
CREATE TABLE `infra_codegen_table` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '编号',
  `data_source_config_id` bigint NOT NULL COMMENT '数据源配置的编号',
  `scene` tinyint NOT NULL DEFAULT '1' COMMENT '生成场景（1管理后台 2用户 APP）',
  `table_name` varchar(200) NOT NULL COMMENT '表名称',
  `table_comment` varchar(500) DEFAULT NULL COMMENT '表描述',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `module_name` varchar(30) NOT NULL COMMENT '模块名',
  `business_name` varchar(30) NOT NULL COMMENT '业务名',
  `class_name` varchar(100) NOT NULL COMMENT '类名称',
  `class_comment` varchar(50) NOT NULL COMMENT '类描述',
  `author` varchar(50) NOT NULL COMMENT '作者',
  `template_type` tinyint NOT NULL DEFAULT '1' COMMENT '模板类型（1单表 2树表 3主子表）',
  `parent_menu_id` bigint DEFAULT NULL COMMENT '父菜单编号',
  ...
  `creator` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `updater` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` bit(1) NOT NULL DEFAULT b'0',
  PRIMARY KEY (`id`)
) COMMENT='代码生成表';
```

**解读**：
- 第 4 行：`data_source_config_id` —— 关联数据源配置，支持从其他数据库导入表
- 第 6 行：`scene` —— 不同场景生成不同的前端代码（管理后台 / 用户 APP）
- 第 13 行：`template_type` —— 单表 / 树表 / 主子表三种模板
- 第 14 行：`parent_menu_id` —— 自动挂到指定父菜单下

## 4. 关键要点总结

- ruoyi 代码生成器是「**最佳实践封装**」：生成的代码完全符合项目规范
- 生成的 SQL 模板：建表 DDL + 初始数据 + 菜单权限
- 支持场景：管理后台、用户 APP；支持模板：单表、树表、主子表
- 自定义模板：通过 Velocity 模板语法修改 `CodegenBuilder` 内部模板

## 5. 练习题

### 练习 1：基础（必做）

启动 ruoyi，进入「系统工具 → 代码生成」，导入任意一张表，预览生成的 SQL，理解每一段 SQL 的作用。

### 练习 2：进阶

修改代码生成器模板（找到 `CodegenBuilder.java` 中 SQL 模板），给生成的 DDL 添加一行注释头：`-- Generated by Yudao at ${currentTime}`。

### 练习 3：挑战（选做）

为 ruoyi 扩展「主子表」生成器：除了生成主表代码，还要生成子表 DO/Mapper/Service，并自动包含主子表关联查询 SQL。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/sql/mysql/ruoyi-vue-pro.sql`（`infra_codegen_table` 表）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/codegen/`
- ruoyi 官方文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13