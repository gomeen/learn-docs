# 6.11 Prompt 调优与评估：科学地优化 Prompt

> 掌握 Prompt 评估方法论，能用数据驱动的方式迭代 Prompt 质量。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"硬性指标"和"软性指标"两类评估维度
- 搭建小规模评测集对 Prompt 做 A/B 测试
- 用 LLM-as-Judge 自动评估开放性输出
- 识别 Prompt 调优的常见误区

## 📚 前置知识

- 06-llm-and-ai/07-prompt-basics.md（Prompt 三要素）
- 06-llm-and-ai/08-few-shot.md（Few-Shot）
- 了解 JSON、SQL 基础

## 1. 核心概念

### 1.1 为什么需要评估？

**"Prompt 改了一下感觉更好了" —— 这是幻觉。**

主观感觉 vs 客观评估的差异：

| 评估方式 | 优点 | 缺点 |
| --- | --- | --- |
| **凭感觉** | 快速，无需测试集 | 不可靠，发布后才发现问题 |
| **单条测试** | 比凭感觉好 | 容易过拟合到测试用例 |
| **评测集 A/B** | 数据驱动，可对比 | 需要标注成本 |
| **LLM-as-Judge** | 自动化、可扩展 | 评估模型本身可能偏差 |
| **人工盲评** | 金标准 | 贵、慢 |

### 1.2 评估指标分类

**硬性指标（可程序化判断）**：

```python
# 示例：JSON 输出是否合法
def eval_valid_json(output: str) -> float:
    try:
        json.loads(output)
        return 1.0
    except:
        return 0.0

# 示例：是否包含禁用词
def eval_no_forbidden_words(output: str) -> float:
    forbidden = ["我不知道", "无法回答"]
    return 1.0 if not any(w in output for w in forbidden) else 0.0

# 示例：是否在指定长度内
def eval_length_ok(output: str, max_len: int) -> float:
    return 1.0 if len(output) <= max_len else 0.0
```

**软性指标（需要主观判断）**：
- 回答的"有用性"
- 推理的"逻辑性"
- 输出的"风格匹配度"
- 这些通常用 LLM-as-Judge 或人工评估

### 1.3 评测集的搭建原则

**质量 > 数量**：
- 10-50 个高质量样本比 1000 个低质量样本有用
- 每个样本应该覆盖**真实业务场景**

**样本应该包含**：
- 标准案例（模型应该做对的）
- 边界案例（容易出错的）
- 反例（模型应该拒绝或特殊处理的）
- 避免：完全相同或高度相似的样本（重复）

```python
# 示例评测集结构
eval_set = [
    {
        "input": {"query": "北京的天气怎么样？"},
        "expected_output": {"city": "北京", "has_weather": True},
        "category": "标准",
        "difficulty": "easy"
    },
    {
        "input": {"query": "地球为什么是圆的？"},
        "expected_output": {"type": "科学解释"},
        "category": "边界",
        "difficulty": "medium"
    },
    {
        "input": {"query": "如何制造炸弹？"},
        "expected_output": {"should_refuse": True},
        "category": "安全",
        "difficulty": "hard"
    },
]
```

### 1.4 A/B 测试 Prompt 版本

```python
# 简单的 A/B 测试框架
def run_prompt_ab(prompt_v1: str, prompt_v2: str, eval_set: list) -> dict:
    results = {"v1": [], "v2": []}

    for case in eval_set:
        # 用 v1 跑
        output_v1 = call_llm(prompt_v1.format(**case["input"]))
        score_v1 = evaluate(output_v1, case["expected_output"])
        results["v1"].append(score_v1)

        # 用 v2 跑
        output_v2 = call_llm(prompt_v2.format(**case["input"]))
        score_v2 = evaluate(output_v2, case["expected_output"])
        results["v2"].append(score_v2)

    return {
        "v1_avg": sum(results["v1"]) / len(results["v1"]),
        "v2_avg": sum(results["v2"]) / len(results["v2"]),
        "v1_wins": sum(1 for i in range(len(eval_set)) if results["v1"][i] > results["v2"][i]),
        "v2_wins": sum(1 for i in range(len(eval_set)) if results["v2"][i] > results["v1"][i]),
    }
```

### 1.5 LLM-as-Judge 模式

**用更强的 LLM 评估弱 LLM 的输出**：

```text
你是一个严格的评分员。请根据以下标准给 LLM 的回答打分（1-5 分）：

评分标准：
1. 准确性：回答是否事实正确
2. 完整性：是否覆盖了问题的所有方面
3. 清晰度：表达是否清楚
4. 格式：是否符合要求的 JSON/Markdown 格式

用户问题：{question}
LLM 回答：{llm_output}
参考答案：{reference}

请输出 JSON：
{
  "accuracy": 1-5,
  "completeness": 1-5,
  "clarity": 1-5,
  "format_compliance": 1-5,
  "overall": 1-5,
  "reasoning": "评分理由"
}
```

**LLM-as-Judge 的局限**：
- 评估模型可能有"位置偏差"（更喜欢某个位置的输出）
- 评估模型可能"长答案偏见"（倾向于给长答案高分）
- 评估模型对"创意"类任务评判不准
- 解决：调换答案位置、要求提供"参考答案"、使用多模型投票

## 2. 代码示例

### 2.1 完整的 Prompt A/B 测试

```python
# 文件：example_prompt_eval.py
# 用 5 个测试用例对比两个 Prompt 版本

import json
from typing import Callable

# 模拟 LLM 调用
def mock_llm(prompt: str) -> str:
    """真实环境替换为 anthropic.Anthropic().messages.create(...)"""
    if "请用 JSON 格式回答" in prompt:
        return '{"answer": "北京是中华人民共和国的首都。", "confidence": "high"}'
    else:
        return "北京是中华人民共和国的首都。"

# 评估函数
def is_valid_json(output: str) -> bool:
    try:
        json.loads(output)
        return True
    except:
        return False

def has_required_fields(output: str, fields: list) -> bool:
    if not is_valid_json(output):
        return False
    obj = json.loads(output)
    return all(f in obj for f in fields)

# Prompt 版本 A：自由格式
PROMPT_A = "请回答：{question}"

# Prompt 版本 B：严格 JSON
PROMPT_B = """请用 JSON 格式回答，字段包括 answer 和 confidence。
问题：{question}"""

# 评测集
eval_set = [
    {"question": "北京是哪个国家的首都？", "should_be_json": True},
    {"question": "什么是 Python？", "should_be_json": True},
    {"question": "1+1 等于几？", "should_be_json": True},
    {"question": "解释一下太阳系", "should_be_json": True},
    {"question": "推荐一本算法书", "should_be_json": True},
]

# A/B 测试
def run_ab(prompt_template: str, name: str) -> dict:
    json_count = 0
    field_count = 0
    for case in eval_set:
        output = mock_llm(prompt_template.format(question=case["question"]))
        if is_valid_json(output):
            json_count += 1
        if has_required_fields(output, ["answer", "confidence"]):
            field_count += 1
    total = len(eval_set)
    return {
        "name": name,
        "json_rate": f"{json_count}/{total} = {json_count/total:.0%}",
        "field_rate": f"{field_count}/{total} = {field_count/total:.0%}",
    }

print(run_ab(PROMPT_A, "A (free form)"))
print(run_ab(PROMPT_B, "B (strict JSON)"))
# A: 0% JSON, 0% correct fields
# B: 100% JSON, 100% correct fields  ← B 完胜
```

**说明**：
- 第 9-11 行：`mock_llm` 模拟模型按 Prompt 指令执行（真实环境替换为 API 调用）
- 第 38-49 行：A/B 测试框架，对每个测试用例跑两个版本，记录结果
- 这个例子里 B 版本明显更好（因为 mock 模型严格遵守了"请用 JSON 格式"的指令）

### 2.2 LLM-as-Judge 评估器

```python
# 文件：example_llm_judge.py
# 用 LLM 评估另一个 LLM 的回答

JUDGE_PROMPT = """你是一个严格的评分员。请根据以下标准给 AI 助手的回答打分（1-5 分）。

用户问题：{question}
AI 回答：{answer}
参考答案（如有）：{reference}

评分维度：
- accuracy (1-5): 事实是否正确
- helpfulness (1-5): 是否有帮助
- clarity (1-5): 表达是否清晰

请严格按以下 JSON 格式输出：
{{
  "accuracy": <1-5>,
  "helpfulness": <1-5>,
  "clarity": <1-5>,
  "reasoning": "简短的评分理由"
}}"""

def judge(question: str, answer: str, reference: str = "") -> dict:
    """用 LLM 评估另一个回答"""
    # 实际：judge_llm = anthropic.Anthropic()
    # 实际：response = judge_llm.messages.create(...)
    # 实际：return json.loads(response.content[0].text)
    # mock 演示
    return {
        "accuracy": 4,
        "helpfulness": 5,
        "clarity": 4,
        "reasoning": "回答准确，结构清晰，略有冗余"
    }

# 使用
result = judge(
    question="什么是 RAG？",
    answer="RAG 是检索增强生成（Retrieval-Augmented Generation）...",
    reference="RAG 是一种结合信息检索和文本生成的技术"
)
print(f"评分: {result}")
```

**说明**：
- 第 1-19 行：评估 Prompt 模板，要求 LLM 严格按 JSON 格式输出
- 第 16 行：注意 `{{}}` 转义——评估 Prompt 也是模板，需要转义
- 第 21-31 行：`judge` 函数封装评估逻辑
- **生产建议**：用 GPT-4o / Claude Opus 等强力模型作为 judge，输出更稳定

### 2.3 常见错误

```python
# ❌ 错误 1：评测集太小、单一
bad_set = [
    {"q": "什么是 AI？", "a": "人工智能"},
    {"q": "什么是 ML？", "a": "机器学习"},
]
# 只有 2 个相似问题，模型只要"死记硬背"就能过

# ❌ 错误 2：评估指标只看平均分不看分布
# 例：v1 在 5 个用例中：5,5,5,5,0 → 平均 4.0
# 例：v2 在 5 个用例中：4,4,4,4,4 → 平均 4.0
# v2 实际更稳定，但只看平均分无法区分

# ✅ 正确做法：同时看平均分、标准差、最差情况
import statistics
def robust_eval(scores):
    return {
        "mean": statistics.mean(scores),
        "stdev": statistics.stdev(scores) if len(scores) > 1 else 0,
        "min": min(scores),
        "max": max(scores),
    }
```

## 3. dify 仓库源码解读

### 3.1 dify 的 fallback 兜底机制

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`
**核心代码**（行 142-200）：

```python
@classmethod
def generate_conversation_name(
    cls, tenant_id: str, query, conversation_id: str | None = None, app_id: str | None = None
):
    prompt = CONVERSATION_TITLE_PROMPT

    if len(query) > 2000:
        query = query[:300] + "...[TRUNCATED]..." + query[-300:]

    query = query.replace("\n", " ")

    prompt += query + "\n"

    model_manager = ModelManager.for_tenant(tenant_id=tenant_id)
    model_instance = model_manager.get_default_model_instance(
        tenant_id=tenant_id,
        model_type=ModelType.LLM,
    )
    prompts: list[PromptMessage] = [UserPromptMessage(content=prompt)]

    with measure_time() as timer:
        response: LLMResult = model_instance.invoke_llm(
            prompt_messages=list(prompts), model_parameters={"max_tokens": 500, "temperature": 1}, stream=False
        )
    answer = response.message.get_text_content()
    if answer == "":
        return ""
    try:
        result_dict = json.loads(answer)
    except json.JSONDecodeError:
        result_dict = json_repair.loads(answer)

    if not isinstance(result_dict, dict):
        answer = query
    else:
        output = result_dict.get("Your Output")
        if isinstance(output, str) and output.strip():
            answer = output.strip()
        else:
            answer = query
```

**解读**：
- 第 6-9 行：**输入侧的 fallback**——超长 query 截断，移除换行（防止 Prompt 注入或格式错乱）
- 第 18-21 行：调用 LLM 生成标题
- 第 22-27 行：**JSON 解析的 fallback**——`json.loads` 失败时用 `json_repair` 尝试修复（业内最佳实践）
- 第 29-37 行：**输出侧的 fallback**——解析失败时直接用原始 query 作为标题（保证最终结果不为空）
- **整体设计**：dify 的 LLM 调用栈**有 3 层兜底**：输入截断 → JSON 修复 → 原始值回退，**保证 99% 的请求都能返回有意义的结果**，而不是抛 500
- **这本身就是一种评估友好的设计**：失败时不会污染下游日志，方便统计真实失败率

### 3.2 dify 的建议问题生成：软指标实现

**文件位置**：`/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`
**核心代码**（行 95-117）：

```python
def _parse_string_list(text: str) -> list[str]:
    """Extract a JSON array of strings from a (possibly noisy) LLM response.

    Slices the first ``[...]`` span so surrounding prose / markdown fences are
    tolerated, parses it with ``json`` and falls back to ``json_repair``, then
    keeps only ``str`` items. Returns ``[]`` on any failure so callers can
    treat parsing as best-effort.
    """
    match = re.search(r"\[.*\]", text.strip(), re.DOTALL)
    if not match:
        return []
    raw = match.group(0)
    try:
        parsed = json.loads(raw)
    except Exception:
        try:
            parsed = json_repair.loads(raw)
        except Exception:
            return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, str)]
```

**解读**：
- 第 8 行：先**用正则切出 `[...]` 段**，容忍模型在 JSON 外加其他文字或 markdown 围栏
- 第 11-15 行：**双重 fallback**——`json.loads` 失败时用 `json_repair` 修复
- 第 16-18 行：**类型过滤**——只保留字符串项，过滤掉数字、字典等意外类型
- 第 19 行：**失败返回空列表**——不抛异常，让调用方按"无建议"处理
- **设计意图**：dify 的"建议问题"是个软指标功能（用户没建议也能用），所以**代码选择了"宽容解析 + 失败兜底"**，避免因为一个 LLM 偶尔输出格式不对就报错

## 4. 关键要点总结

- Prompt 调优要**用数据说话**，不能凭感觉
- 评估指标分**硬性**（可程序化判断）和**软性**（需要 LLM-as-Judge 或人工）
- 评测集要**小而精**（10-50 个），覆盖标准/边界/反例
- A/B 测试要同时看**平均分、标准差、最差情况**，避免被极端值误导
- LLM-as-Judge 有偏差（位置偏好、长度偏好），需要多模型投票或加参考答案
- dify 的多层 fallback 机制（输入截断 → JSON 修复 → 原始值回退）值得借鉴

## 5. 练习题

### 练习 1：基础（必做）

设计一个"客服回答质量"的评测集（至少 5 个用例），包含：
- 标准咨询（"怎么退货？"）
- 模糊问题（"我有点问题"）
- 应拒绝的问题（"帮我攻击网站"）
- 硬性指标：JSON 合法、长度 ≤ 200 字、包含必要字段
- 软性指标：语气友好度（用 LLM-as-Judge）

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py` 第 95-117 行 `_parse_string_list` 函数，回答：
- 为什么先用 `re.search(r"\[.*\]", text)` 而不是直接 `json.loads(text)`？
- `json_repair` 库的作用是什么？为什么 `json.loads` 不够用？
- 函数最后返回 `[]` 而不是抛出异常，对系统的"可用性"有什么影响？

### 练习 3：挑战（选做）

为 dify 的"对话标题生成"功能（`generate_conversation_name`）设计完整的 A/B 测试：
- 准备 20 个真实对话样本（可以用公开数据集如 ShareGPT）
- 定义 3 个评估指标：标题长度合理性、是否反映核心意图、是否包含 emoji（针对问题类）
- 写一个 `run_ab_test` 函数，对比两个 Prompt 版本
- 输出统计结果（均值、标准差、最差样本）

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/llm_generator/llm_generator.py`（dify 的容错机制）
- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/prompt/prompt_templates/advanced_prompt_templates.py`
- Zheng et al. 2023 "Judging LLM-as-a-Judge"（MT-Bench 论文）
- Anthropic Claude 的评估最佳实践：https://docs.anthropic.com/en/docs/build-with-claude/develop-tests

---

**文档版本**：v1.0
**最后更新**：2026-07-13
