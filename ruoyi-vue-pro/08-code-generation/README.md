# 08 - 代码生成器

> ruoyi-vue-pro 最大的亮点之一：可视化代码生成器，一键生成前后端代码 + SQL 脚本。

> **学习顺序**：按下方清单**从上到下**进行——读完一组文档后立刻做紧随其后的「✅ 小验证」，再继续下一组。练习已穿插在路径中间，不要把文档全部读完再回头找练习。

## 模块 8.1 代码生成器基础

- [ ] [1.1 ruoyi 代码生成器概述](./01-overview.md)
- [ ] [1.2 数据源配置](./02-datasource.md)
- [ ] [1.3 表结构导入](./03-table-import.md)
- [ ] [1.4 字段类型映射](./04-type-mapping.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [05-*-codegen-basics: 代码生成器基础](./05-*-codegen-basics.md)
  - 覆盖：01-overview.md, 02-datasource.md, 03-table-import.md, 04-type-mapping.md


## 模块 8.2 模板配置

- [ ] [2.1 模板分组：CRUD/树/主子表](./06-template-group.md)
- [ ] [2.2 字段配置：列表/查询/表单](./07-field-config.md)
- [ ] [2.3 字典/枚举/用户组件](./08-component-config.md)
- [ ] [2.4 校验规则配置](./09-validation-config.md)
- [ ] [2.5 关联字段配置](./10-relation-config.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [11-*-template-config: 生成模板配置](./11-*-template-config.md)
  - 覆盖：06-template-group.md, 07-field-config.md, 08-component-config.md, 09-validation-config.md, 10-relation-config.md


## 模块 8.3 模板引擎

- [ ] [3.1 Velocity 模板引擎](./12-velocity.md)
- [ ] [3.2 ruoyi 的 Java 模板](./13-java-template.md)
- [ ] [3.3 ruoyi 的 Vue 模板](./14-vue-template.md)
- [ ] [3.4 ruoyi 的 SQL 模板](./15-sql-template.md)
- [ ] [3.5 自定义模板](./16-custom-template.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [17-*-template-engine: Velocity 模板与产物](./17-*-template-engine.md)
  - 覆盖：12-velocity.md, 13-java-template.md, 14-vue-template.md, 15-sql-template.md, 16-custom-template.md


## 模块 8.4 实战演练

- [ ] [4.1 生成单表 CRUD](./18-gen-single.md)
- [ ] [4.2 生成树表](./19-gen-tree.md)
- [ ] [4.3 生成主子表](./20-gen-master-slave.md)
- [ ] [4.4 自定义生成规则](./21-custom-gen.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [22-*-gen-practice: 生成实战：单表 / 树 / 主子表](./22-*-gen-practice.md)
  - 覆盖：18-gen-single.md, 19-gen-tree.md, 20-gen-master-slave.md, 21-custom-gen.md


## 🎯 ruoyi-vue-pro 仓库对应位置

- 代码生成模块：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/`
- 模板路径：`yudao-module-infra/.../dal/mysql/`
- 模板文件：搜索 `*.vm`（Velocity 模板）
- 生成器服务：`yudao-module-infra/.../service/codegen/`
