# 5.2 网关：排他/并行/包容

> 深入理解 BPMN 三大网关：排他网关、并行网关、包容网关的区别与 ruoyi 应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"排他网关"（XOR）、"并行网关"（AND）、"包容网关"（OR）
- 知道三种网关的 BPMN 表示和触发条件
- 理解 ruoyi 在哪些场景下使用哪种网关
- 能在 BPMN 设计中正确选用网关

## 📚 前置知识

- BPMN 基础（详见 [BPMN](./01-bpmn.md)）
- 流程变量（详见 [流程变量](./16-process-vars.md)）
- 多实例（详见 [多实例](./17-multi-instance.md)）

## 1. 核心概念

### 1.1 三种网关对比

| 网关 | 符号 | 行为 | 业务场景 |
|------|------|------|---------|
| **排他**（Exclusive） | ◇/X | **只走一条**满足条件的分支 | 金额判断：≤1000 走经理，>1000 走 CEO |
| **并行**（Parallel） | ◇/+ | **同时走**所有分支，最后汇合 | 多部门会审（HR + 财务 + 法务同时审） |
| **包容**（Inclusive） | ◇/O | 走**所有满足条件**的分支 | 条件可选：金额>5000 走 CEO，金额>10000 走 CFO（都满足时两个都走） |

### 1.2 排他网关详解

```xml
<exclusiveGateway id="gw"/>
<sequenceFlow sourceRef="gw" targetRef="manager">
    <conditionExpression>${amount <= 1000}</conditionExpression>
</sequenceFlow>
<sequenceFlow sourceRef="gw" targetRef="ceo">
    <conditionExpression>${amount > 1000}</conditionExpression>
</sequenceFlow>
```

**规则**：
- 评估所有出边的 conditionExpression
- 选**第一个** true 的分支
- 如果都 false，使用 default 分支

### 1.3 并行网关详解

```xml
<parallelGateway id="split"/>      <!-- 拆分 -->
<userTask id="hr" name="HR 审核"/>
<userTask id="finance" name="财务审核"/>
<parallelGateway id="join"/>       <!-- 汇合 -->
```

**规则**：
- split：所有出边**全部**激活
- join：等待**所有**入边完成后才继续

### 1.4 包容网关详解

```xml
<inclusiveGateway id="gw"/>
<sequenceFlow sourceRef="gw" targetRef="ceo">
    <conditionExpression>${amount > 5000}</conditionExpression>
</sequenceFlow>
<sequenceFlow sourceRef="gw" targetRef="cfo">
    <conditionExpression>${amount > 10000}</conditionExpression>
</sequenceFlow>
```

**规则**：
- 评估所有 conditionExpression
- 走**所有满足**的分支
- join 时等待所有激活的分支

## 2. 代码示例

### 2.1 排他网关（BPMN 完整示例）

```xml
<process id="expense" name="报销审批" isExecutable="true">
    <startEvent id="start"/>
    <userTask id="submit" name="提交报销"/>
    <exclusiveGateway id="amountCheck" name="金额判断"/>
    <userTask id="manager" name="经理审批"/>
    <userTask id="ceo" name="CEO 审批"/>
    <endEvent id="end"/>

    <sequenceFlow id="f1" sourceRef="start" targetRef="submit"/>
    <sequenceFlow id="f2" sourceRef="submit" targetRef="amountCheck"/>
    <sequenceFlow id="f3" sourceRef="amountCheck" targetRef="manager">
        <conditionExpression xsi:type="tFormalExpression">${amount &lt;= 1000}</conditionExpression>
    </sequenceFlow>
    <sequenceFlow id="f4" sourceRef="amountCheck" targetRef="ceo">
        <conditionExpression xsi:type="tFormalExpression">${amount &gt; 1000}</conditionExpression>
    </sequenceFlow>
    <sequenceFlow id="f5" sourceRef="manager" targetRef="end"/>
    <sequenceFlow id="f6" sourceRef="ceo" targetRef="end"/>
</process>
```

### 2.2 并行网关

```xml
<parallelGateway id="split"/>
<userTask id="hr"/>
<userTask id="finance"/>
<parallelGateway id="join"/>
<endEvent id="end"/>

<sequenceFlow sourceRef="split" targetRef="hr"/>
<sequenceFlow sourceRef="split" targetRef="finance"/>
<sequenceFlow sourceRef="hr" targetRef="join"/>
<sequenceFlow sourceRef="finance" targetRef="join"/>
<sequenceFlow sourceRef="join" targetRef="end"/>
```

### 2.3 常见错误：并行网关忘记 join

```xml
<!-- ❌ 错误：拆分了但没汇合，流程会"卡住" -->
<parallelGateway id="split"/>
<userTask id="hr"/>
<userTask id="finance"/>
<endEvent id="end"/>
<sequenceFlow sourceRef="split" targetRef="hr"/>
<sequenceFlow sourceRef="split" targetRef="finance"/>
<sequenceFlow sourceRef="hr" targetRef="end"/>
<!-- finance 分支跑完就结束，hr 分支也跑完就结束，永远不汇合 -->

<!-- ✅ 正确：必须有 join 网关 -->
<parallelGateway id="join"/>
<sequenceFlow sourceRef="hr" targetRef="join"/>
<sequenceFlow sourceRef="finance" targetRef="join"/>
<sequenceFlow sourceRef="join" targetRef="end"/>
```

## 3. ruoyi 仓库源码解读

### 3.1 SimpleModelUtils 中的网关节点转换

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`
**核心代码**（行 41-50）：

```java
private static final Map<BpmSimpleModelNodeTypeEnum, NodeConvert> NODE_CONVERTS = MapUtil.newHashMap();

static {
    List<NodeConvert> converts = asList(new StartNodeConvert(), new EndNodeConvert(),
            new StartUserNodeConvert(), new ApproveNodeConvert(), new CopyNodeConvert(), new TransactorNodeConvert(),
            new DelayTimerNodeConvert(), new TriggerNodeConvert(),
            new ConditionBranchNodeConvert(), new ParallelBranchNodeConvert(), new InclusiveBranchNodeConvert(), new RouteBranchNodeConvert(),
            new ChildProcessConvert());
    converts.forEach(convert -> NODE_CONVERTS.put(convert.getType(), convert));
}
```

**解读**：
- 第 47 行：3 种分支转换器
  - `ConditionBranchNodeConvert` → 排他网关（conditionExpression）
  - `ParallelBranchNodeConvert` → 并行网关
  - `InclusiveBranchNodeConvert` → 包容网关
- 第 48 行：`RouteBranchNodeConvert` 是"路由分支"（即分支本身是节点，不是网关）
- **关键设计**：每种网关一个转换器类，新增网关类型零修改

### 3.2 ConditionBranchNodeConvert 的实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`（内部类）
**核心代码**（基于 service 通用结构推断）：

```java
class ConditionBranchNodeConvert implements NodeConvert {
    @Override
    public BpmSimpleModelNodeTypeEnum getType() {
        return BpmSimpleModelNodeTypeEnum.CONDITION_BRANCH;
    }

    @Override
    public FlowElement convert(BpmSimpleModelNodeVO node, ... context) {
        ExclusiveGateway gateway = new ExclusiveGateway();
        gateway.setId(node.getId());
        gateway.setName(node.getName());

        // 为每个出边生成 conditionExpression
        if (node.getConditionGroups() != null) {
            // 设置 default sequence flow
            // 设置 condition
        }
        return gateway;
    }
}
```

**解读**：
- 返回的 `ExclusiveGateway` 是 Flowable 对象
- 转换器将"前端简单配置"（如 `ConditionGroups`）翻译为 BPMN 元素
- **关键设计**：转换器不依赖 Flowable 的具体 API 接口，**只产出最终 BPMN 对象**

### 3.3 实际案例：内置 OA 流程的网关使用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/resources/processes/` 下的 `.bpmn20.xml`
**示例**（leave 流程的网关使用）：

```xml
<!-- 简化的 leave 流程 -->
<userTask id="apply" name="申请人填写"/>
<exclusiveGateway id="checkDays" name="天数判断"/>
<userTask id="manager" name="直属领导"/>
<userTask id="hr" name="HR"/>
<userTask id="boss" name="老板"/>

<!-- 排他网关：按天数分流 -->
<sequenceFlow sourceRef="checkDays" targetRef="manager">
    <conditionExpression>${days &lt;= 3}</conditionExpression>
</sequenceFlow>
<sequenceFlow sourceRef="checkDays" targetRef="hr">
    <conditionExpression>${days &gt; 3 &amp;&amp; days &lt;= 7}</conditionExpression>
</sequenceFlow>
<sequenceFlow sourceRef="checkDays" targetRef="boss">
    <conditionExpression>${days &gt; 7}</conditionExpression>
</sequenceFlow>
```

**解读**：
- ruoyi 内置的 OA 流程**只用排他网关**（最常用）
- **包容网关** 和 **并行网关** 在 ruoyi 内置流程中较少用，**需在设计器中手动配置**
- **Flowable 提供但 ruoyi 未启用**：复杂事件网关（Event Gateway）

## 4. 关键要点总结

- 排他网关：只走一条（条件判断）
- 并行网关：全部走 + 必须 join
- 包容网关：满足条件的都走
- ruoyi 内置 OA 流程只用了**排他网关**
- 复杂事件网关（Event Gateway）Flowable 提供但 ruoyi 未启用
- 网关使用 EL 表达式 `${varName}` 引用流程变量

## 5. 练习题

### 练习 1：基础（必做）

画一个"采购申请"流程：
- ≤1000 元：直属领导审批
- 1000-10000 元：部门经理审批
- >10000 元：CEO 审批
- 用排他网关

**参考答案**：见 `solutions/18-gateway.md`

### 练习 2：进阶

阅读 `SimpleModelUtils.ConditionBranchNodeConvert` 完整实现，列出它生成 `ExclusiveGateway` 时设置的所有属性。

### 练习 3：挑战（选做）

用并行网关设计一个"3 部门联合审批"流程：HR、财务、法务同时审批，全部通过后进入"老板终审"。要求用 BPMN XML 写出完整流程。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/java/cn/iocoder/yudao/module/bpm/framework/flowable/core/util/SimpleModelUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-bpm/src/main/resources/processes/`（内置流程）
- BPMN 2.0 网关规范：https://www.omg.org/spec/BPMN/2.0/#P234

---

**文档版本**：v1.0
**最后更新**：2026-07-13
