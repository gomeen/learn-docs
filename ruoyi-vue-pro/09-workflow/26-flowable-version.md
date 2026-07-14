# 6.4 Flowable 6 vs Flowable 7

> 理解 Flowable 6 与 Flowable 7 的主要区别，及 ruoyi 选择的版本考量。

## 🎯 学习目标

完成本文档后，你将能够：
- 知道 Flowable 的版本历史
- 理解 Flowable 6 和 7 的主要区别
- 知道 ruoyi 选择 Flowable 6 的原因
- 能在升级时识别 breaking changes

## 📚 前置知识

- 01-bpmn.md（BPMN 基础）
- 02-flowable-concepts.md（Flowable 核心对象）

## 1. 核心概念

### 1.1 Flowable 版本简史

| 版本 | 发布时间 | 主要特性 |
|------|---------|---------|
| **6.0** | 2016 | 从 Activiti 分离 |
| **6.4+** | 2018+ | `ProcessInstanceBuilder`、`IdentityLink` 改进 |
| **6.5+** | 2020+ | CMMN、DMN 集成 |
| **7.0** | 2022 | 模块化重构、新 API |
| **7.x** | 2023- | 持续迭代 |

### 1.2 Flowable 6 vs 7 的主要区别

| 维度 | Flowable 6 | Flowable 7 |
|------|-----------|-----------|
| **API 兼容性** | 兼容 Activiti 5/6 | 重写 API，破坏性变更 |
| **模块化** | 一个大 jar | 拆分为多个小 jar |
| **性能** | 标准 | 优化 30%+ |
| **Spring Boot 集成** | 2.x | 3.x（**要求 Java 17+**） |
| **历史表** | `act_hi_*`（带下划线） | 同 6（保留兼容） |
| **JDK 要求** | Java 8+ | Java 17+ |
| **稳定版** | 6.8.x（长期维护） | 7.x（持续迭代） |

### 1.3 ruoyi 选择的版本

查看 `pom.xml`：

```xml
<dependency>
    <groupId>org.flowable</groupId>
    <artifactId>flowable-spring-boot-starter-process</artifactId>
</dependency>
```

**版本来源**：ruoyi 父 pom 中定义（`yudao-dependencies` BOM），**当前为 Flowable 6.8.x**。

**为什么用 6 而非 7？**
- ruoyi 的 Java 版本仍是 Java 8/11（**Flowable 7 要求 Java 17+**）
- 6.8.x 是**长期稳定版**，社区生态成熟
- ruoyi 的核心扩展（Behavior / Listener）与 6 紧密耦合，**升级到 7 工作量大**

## 2. 代码示例

### 2.1 检查当前 Flowable 版本

```bash
# 查看依赖树
mvn dependency:tree | grep flowable

# 输出
[INFO] +- org.flowable:flowable-spring-boot-starter-process:jar:6.8.0
```

### 2.2 Flowable 6 的典型 API

```java
// 启动流程（6.x）
ProcessInstance pi = runtimeService.startProcessInstanceByKey("leave", variables);

// 创建任务查询（6.x）
List<Task> tasks = taskService.createTaskQuery()
    .taskAssignee("101")
    .list();
```

### 2.3 Flowable 7 的 API 变化

```java
// Flowable 7：ProcessInstanceBuilder 是默认推荐方式
ProcessInstance pi = runtimeService.createProcessInstanceBuilder()
    .processDefinitionKey("leave")
    .variables(variables)
    .start();
```

**区别**：7 强化了**流式 API**，但底层兼容性保留（6 的代码在 7 仍能编译运行）。

### 2.4 常见错误：升级 Flowable 6 → 7 时直接替换 jar

```xml
<!-- ❌ 错误：直接改版本号 -->
<dependency>
    <groupId>org.flowable</groupId>
    <artifactId>flowable-spring-boot-starter-process</artifactId>
    <version>7.0.0</version>  <!-- 升级 -->
</dependency>

<!-- 后果：编译错误，Java 17+ 要求，Spring Boot 3.x 要求 -->
```

## 3. ruoyi 仓库源码解读

### 3.1 yudao-module-bpm 的 pom 依赖

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/pom.xml`
**核心代码**（行 16-77）：

```xml
<description>
    bpm 包下，业务流程管理（Business Process Management），我们放工作流的功能。
    例如说：流程定义、表单配置、审核中心（我的申请、我的待办、我的已办）等等
    bpm 解释：https://baike.baidu.com/item/BPM/1933

    工作流基于 Flowable 6 实现，分成流程定义、流程表单、流程实例、流程任务等功能模块。
</description>

<dependencies>
    <dependency>
        <groupId>cn.iocoder.boot</groupId>
        <artifactId>yudao-module-system</artifactId>
        <version>${revision}</version>
    </dependency>

    <!-- Flowable 工作流相关 -->
    <dependency>
        <groupId>org.flowable</groupId>
        <artifactId>flowable-spring-boot-starter-process</artifactId>
    </dependency>
    <dependency>
        <groupId>org.flowable</groupId>
        <artifactId>flowable-spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

**解读**：
- 第 20 行：注释明确写"工作流基于 Flowable 6 实现"
- 第 72 行：`flowable-spring-boot-starter-process` 是核心 jar
- 第 76 行：`flowable-spring-boot-starter-actuator` 提供健康检查、metrics
- **没有指定版本号**：从父 pom 的 BOM 继承

### 3.2 Flowable 6 API 在 ruoyi 中的使用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
**核心代码**（行 47-80）：

```java
import org.flowable.bpmn.constants.BpmnXMLConstants;
import org.flowable.bpmn.model.*;
import org.flowable.engine.HistoryService;
import org.flowable.engine.RuntimeService;
import org.flowable.engine.history.HistoricActivityInstance;
import org.flowable.engine.history.HistoricProcessInstance;
import org.flowable.engine.history.HistoricProcessInstanceQuery;
import org.flowable.engine.repository.ProcessDefinition;
import org.flowable.engine.runtime.Execution;
import org.flowable.engine.runtime.ProcessInstance;
import org.flowable.engine.runtime.ProcessInstanceBuilder;
import org.flowable.engine.task.Attachment;
import org.flowable.task.api.Task;
import org.flowable.task.api.history.HistoricTaskInstance;
```

**解读**：
- `import org.flowable.*`：所有 API 来自 `org.flowable` 包（Flowable 6 标准）
- `ProcessInstanceBuilder` 是 6.4+ 引入的流式 API
- **如果升级到 Flowable 7**：包名可能变为 `org.flowable.*` 子模块，import 需调整

### 3.3 Flowable 6 的表结构

**Flowable 6 仍使用**：
- `act_ru_*`（运行时）
- `act_hi_*`（历史）
- `act_re_*`（仓库）
- `act_ge_*`（通用）
- `act_id_*`（身份，ruoyi 不用）

**Flowable 7 的变化**：
- 表前缀**保留兼容**（仍用 `act_*`）
- **新增**一些事件表（`act_evt_*`）
- **优化索引**（部分查询性能提升 30%+）

## 4. 关键要点总结

- ruoyi 用 **Flowable 6.8.x**（长期稳定版）
- Flowable 7 要求 **Java 17+** 和 **Spring Boot 3.x**，升级成本高
- ruoyi 核心扩展（Behavior / Listener）与 Flowable 6 深度耦合
- 表结构 `act_*` 在 6 和 7 中**保持兼容**
- **升级策略**：等 Flowable 7 生态成熟 + ruoyi 升级 Java 17 一起做
- Flowable 提供但 ruoyi 未启用：CMMN（Case Management）、DMN（Decision Management）

## 5. 练习题

### 练习 1：基础（必做）

回答：
1. ruoyi 用的是 Flowable 几？
2. Flowable 7 对 Java 版本的要求？
3. ruoyi 为什么用 6 而非 7？

**参考答案**：见 `solutions/26-flowable-version.md`

### 练习 2：进阶

阅读 `yudao-module-bpm/pom.xml`，列出 ruoyi 引入的所有 Flowable 相关依赖（artifactId）。

### 练习 3：挑战（选做）

如果要把 ruoyi 升级到 Flowable 7，列出至少 5 个需要修改的代码点（如 import、JDK 配置、Spring Boot 版本等）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/pom.xml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/service/task/BpmProcessInstanceServiceImpl.java`
- Flowable 官方升级指南：https://www.flowable.com/open-source/docs/migration/
- Flowable 7 发布说明：https://blog.flowable.com/2022/10/13/flowable-7-0-0-ga-released/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
