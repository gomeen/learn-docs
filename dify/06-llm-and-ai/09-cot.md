# 1.1.9 Chain-of-Thought 提示

> 通过任务分解、可验证中间产物和工具辅助提升复杂问题表现，而不是把隐藏推理当作可靠答案。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Chain-of-Thought（CoT）为何可能改善多步任务
- 区分 zero-shot CoT、few-shot CoT、自洽采样和结构化分解
- 知道何时应要求简短依据或可验证步骤，而非暴露内部推理
- 为计算、规划和生成任务设计“分解—执行—验证”流程
- 能看懂 dify 如何把一个复杂生成任务拆成多次 LLM 调用

## 📚 前置知识

- [模型参数](./04-model-parameters.md)
- [LLM 局限](./05-llm-limitations.md)
- Prompt 角色与基础写法（详见 [Prompt 基础](./07-prompt-basics.md)）
- 外部基础：基本概率和软件验证思维

## 1. 核心概念

### 1.1 CoT 的形式与适用场景

Chain-of-Thought 是让模型在得到最终答案前进行中间推理或任务分解的提示方法。经典形式包括：

- **Zero-shot CoT**：给出“分步骤解决”等简短指令。
- **Few-shot CoT**：提供带中间步骤的示例，教模型模仿推理结构。
- **Self-consistency**：采样多条候选路径，对最终答案投票或用验证器选择。
- **Least-to-most**：先拆子问题，再按依赖顺序逐个解决。

它更适合数学、多约束规划、复杂分类或代码分析，不适合简单查事实、低延迟分类等任务。CoT 会增加输出 token、延迟和成本，而且一条看似连贯的推理链仍可能是事后编造，不能当作事实证明。

### 1.2 从“展示思维”转向“可验证推理”

生产系统应关注答案是否可检查，而不是依赖模型输出冗长的内部思维。更稳健的提示模式是：

1. 明确任务、约束和成功标准。
2. 要求输出可验证的中间产物，如公式、计划、证据 ID 或测试结果。
3. 让工具执行算术、查询和代码验证。
4. 最终只返回结论、简短依据与验证状态。

对于支持内部推理或 reasoning 的模型，不应通过提示索取隐藏的原始思维过程。可以请求“简洁解释”“关键假设”“可复现步骤”或“引用证据”，也可以使用供应商明确提供的推理摘要能力。这样既能辅助审计，也避免把未经验证的自然语言推理误当作真实过程。

## 2. 代码示例

### 2.1 用“计划—执行—校验”替代一条超长提示

```python
# 文件：verified_reasoning.py
from collections.abc import Callable


def solve_with_verification(
    problem: str,
    generate: Callable[[str], str],
    verify: Callable[[str, str], bool],
) -> str:
    plan_prompt = (
        "把问题拆成最多 4 个可验证步骤。只输出编号计划，不给最终答案。\n"
        f"问题：{problem}"
    )
    plan = generate(plan_prompt)

    answer_prompt = (
        "依据计划解决问题。输出 JSON，字段为 answer、assumptions、checks。"
        "不要输出隐藏思维，只给可复现的关键依据。\n"
        f"问题：{problem}\n计划：{plan}"
    )
    candidate = generate(answer_prompt)
    if not verify(problem, candidate):
        repair_prompt = (
            "下面候选答案未通过外部校验。修正答案并保持同一 JSON 格式。\n"
            f"问题：{problem}\n候选：{candidate}"
        )
        candidate = generate(repair_prompt)
    return candidate


# generate 可接入任意 LLM，verify 应接入 JSON Schema、计算器或业务规则。
```

**说明**：该函数把复杂任务拆成两个模型阶段，并把真实性判断交给外部验证器。计划是可控的中间产物，不要求模型泄露或声称展示其隐藏内部推理。

## 3. dify 仓库源码解读

### 3.1 复杂规则生成被拆成多个可检查步骤

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`  
**核心代码**（行 528-549）：

```python
        try:
            try:
                # the first step to generate the task prompt
                prompt_content: LLMResult = model_instance.invoke_llm(
                    prompt_messages=list(prompt_generate_messages), model_parameters=model_parameters, stream=False
                )
            except InvokeError as e:
                error = str(e)
                error_step = "generate prefix prompt"
                rule_config["error"] = f"Failed to {error_step}. Error: {error}" if error else ""

                return rule_config

            rule_config["prompt"] = prompt_content.message.get_text_content()

            parameter_generate_prompt = parameter_template.format(
                inputs={
                    "INPUT_TEXT": prompt_content.message.get_text_content(),
                },
                remove_template_variables=False,
            )
            parameter_messages: list[PromptMessage] = [UserPromptMessage(content=parameter_generate_prompt)]
```

**解读**：
- 第 530-533 行：第一步只生成任务提示，而不是一次请求完成所有规则字段。
- 第 534-539 行：阶段失败会记录具体 `error_step` 并提前返回，便于定位问题。
- 第 541-549 行：第一步产物成为下一步的显式输入，这比不可见的“在脑中多想”更容易观测和测试。

### 3.2 后续步骤分别生成变量与开场语

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`  
**核心代码**（行 551-574）：

```python
            # the second step to generate the task_parameter and task_statement
            statement_generate_prompt = statement_template.format(
                inputs={
                    "TASK_DESCRIPTION": args.instruction,
                    "INPUT_TEXT": prompt_content.message.get_text_content(),
                },
                remove_template_variables=False,
            )
            statement_messages: list[PromptMessage] = [UserPromptMessage(content=statement_generate_prompt)]

            try:
                parameter_content: LLMResult = model_instance.invoke_llm(
                    prompt_messages=list(parameter_messages), model_parameters=model_parameters, stream=False
                )
                rule_config["variables"] = re.findall(r'"\s*([^"]+)\s*"', parameter_content.message.get_text_content())
            except InvokeError as e:
                error = str(e)
                error_step = "generate variables"

            try:
                statement_content: LLMResult = model_instance.invoke_llm(
                    prompt_messages=list(statement_messages), model_parameters=model_parameters, stream=False
                )
                rule_config["opening_statement"] = statement_content.message.get_text_content()
```

**解读**：
- 第 551-559 行：开场语生成同时使用原始任务和第一阶段提示，保留明确依赖。
- 第 561-574 行：变量与开场语分别调用、分别解析、分别记录失败步骤。
- 整体设计意图：把复合目标拆成小任务，用显式中间结果形成可观察的应用级推理链。

## 4. 关键要点总结

- CoT 可能改善多步推理，但会增加 token、延迟和成本
- 自然语言推理链可能同样出错，不能自动视作证据
- 生产环境更应输出关键依据、假设、证据和验证结果
- 将任务拆成多次调用能获得可重试、可测试的中间产物
- dify 的规则生成通过分阶段调用实现应用级“分解—执行”

## 5. 练习题

### 练习 1：基础（必做）

把“为三天旅行制定预算”改写为一个包含约束、计划、最终表格和检查项的提示，避免要求输出隐藏思维。

**参考答案**：见 `solutions/09-cot.md`

### 练习 2：进阶

为示例实现 JSON Schema 校验器，并在答案中的金额合计不一致时调用 Python 重新计算，再把错误反馈给修复提示。

### 练习 3：挑战（选做）

参考 dify 的 `generate_rule_config`，设计一个可恢复的三阶段生成器：每阶段记录 usage、错误和中间产物，支持只重试失败阶段，并比较它与单次长提示的成本和成功率。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`
- Chain-of-Thought Prompting：https://arxiv.org/abs/2201.11903
- Self-Consistency Improves Chain of Thought Reasoning：https://arxiv.org/abs/2203.11171
- Least-to-Most Prompting：https://arxiv.org/abs/2205.10625
- ReAct：https://arxiv.org/abs/2210.03629

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
