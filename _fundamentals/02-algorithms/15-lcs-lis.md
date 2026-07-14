# 1.4.3 最长子序列（LCS / LIS）

> LCS 和 LIS 是子序列问题的代表，DP 的经典应用。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握最长公共子序列（LCS）的 DP 解法
- 掌握最长上升子序列（LIS）的两种解法
- 理解字符串编辑距离与 LCS 的关系
- 能在 dify 中识别子序列的应用（文本相似度）

## 📚 前置知识

- 13-dp-basics.md
- 14-knapsack.md

## 1. 核心概念

### 1.1 子序列 vs 子串

- **子串**（Substring）：**连续**的字符序列
- **子序列**（Subsequence）：保持顺序但**可以不连续**

```
"abcde" 的子序列：ab、ace、bde、abcde ...
"abcde" 的子串：ab、bc、cde ...

注意：ab 是子串也是子序列，ace 只是子序列
```

### 1.2 LCS（Longest Common Subsequence）

**问题**：两个字符串的最长公共子序列长度。

```
str1 = "abcde"
str2 = "ace"

公共子序列：a, c, e, ac, ae, ce, ace
最长：ace（长度 3）
```

**状态定义**：`dp[i][j]` = `str1[0..i]` 和 `str2[0..j]` 的 LCS 长度

**状态转移**：
```
if str1[i] == str2[j]:
    dp[i][j] = dp[i-1][j-1] + 1
else:
    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
```

### 1.3 LIS（Longest Increasing Subsequence）

**问题**：数组的最长严格递增子序列长度。

```
[10, 9, 2, 5, 3, 7, 101, 18]

递增子序列：2, 3, 7, 18（长度 4）
           或 2, 5, 7, 101（长度 4）
最长：4
```

**两种解法**：

#### O(n²) DP

```python
dp[i] = max(dp[j] + 1) for j < i if nums[j] < nums[i]
```

#### O(n log n) 二分 + 贪心

维护一个 `tail` 数组：
- `tail[k]` = 长度为 k+1 的 LIS 的**最小尾部元素**

```
nums = [10, 9, 2, 5, 3, 7, 101, 18]
tail 演变：
[10]
[9]
[2]
[2, 5]
[2, 3]
[2, 3, 7]
[2, 3, 7, 101]
[2, 3, 7, 18]  ← 长度 4
```

### 1.4 编辑距离

**问题**：将 `word1` 转为 `word2` 的最少操作数（插入、删除、替换）。

```
word1 = "horse"
word2 = "ros"

horse → rorse（替换 h → r）
rorse → rose（删除 r）
rose → ros（删除 e）

3 步
```

**状态转移**：
```
if word1[i] == word2[j]:
    dp[i][j] = dp[i-1][j-1]
else:
    dp[i][j] = 1 + min(
        dp[i-1][j] + 1,    # 删除 word1[i]
        dp[i][j-1] + 1,    # 插入 word2[j]
        dp[i-1][j-1] + 1,  # 替换
    )
```

### 1.5 应用场景

1. **LCS**：git diff、文档相似度、生物信息学
2. **LIS**：最长不下降序列、排序问题
3. **编辑距离**：拼写检查、DNA 序列比对、推荐系统

## 2. 代码示例

### 2.1 LCS 实现

```python
# 文件：lcs.py
def longest_common_subsequence(text1: str, text2: str) -> int:
    """LCS 长度 - O(m*n) 时间空间。"""
    m, n = len(text1), len(text2)
    # dp[i][j] = text1[0..i] 和 text2[0..j] 的 LCS 长度
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]

def lcs_with_string(text1: str, text2: str) -> str:
    """返回具体的 LCS 字符串。"""
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # 回溯找 LCS
    result = []
    i, j = m, n
    while i > 0 and j > 0:
        if text1[i - 1] == text2[j - 1]:
            result.append(text1[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] > dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return "".join(reversed(result))

# 测试
print(longest_common_subsequence("abcde", "ace"))  # 3
print(lcs_with_string("abcde", "ace"))              # "ace"
```

### 2.2 LIS 两种实现

```python
# 文件：lis.py
from typing import List
from bisect import bisect_left

def lis_dp(nums: List[int]) -> int:
    """LIS - O(n²) DP。"""
    if not nums:
        return 0
    n = len(nums)
    dp = [1] * n
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)

def lis_binary(nums: List[int]) -> int:
    """LIS - O(n log n) 二分 + 贪心。"""
    if not nums:
        return 0
    tail: List[int] = []  # tail[k] = 长度为 k+1 的 LIS 的最小尾部
    for num in nums:
        # 找 tail 中第一个 >= num 的位置（维护严格递增）
        idx = bisect_left(tail, num)
        if idx == len(tail):
            tail.append(num)
        else:
            tail[idx] = num
    return len(tail)

# 测试
nums = [10, 9, 2, 5, 3, 7, 101, 18]
print(lis_dp(nums))      # 4
print(lis_binary(nums))  # 4
```

### 2.3 编辑距离

```python
# 文件：edit_distance.py
def edit_distance(word1: str, word2: str) -> int:
    """编辑距离 - O(m*n) 时间空间。"""
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # 初始化
    for i in range(m + 1):
        dp[i][0] = i  # 删除 i 个字符
    for j in range(n + 1):
        dp[0][j] = j  # 插入 j 个字符

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]  # 无需操作
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # 删除 word1[i-1]
                    dp[i][j - 1],      # 插入 word2[j-1]
                    dp[i - 1][j - 1],  # 替换
                )
    return dp[m][n]

# 测试
print(edit_distance("horse", "ros"))  # 3
```

## 3. dify 仓库源码解读

### 3.1 dify 的文本相似度计算

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
**核心代码**（行 80-120）：

```python
from typing import Any

class TextSimilarity:
    """文本相似度计算器。

    dify 用 LCS / 编辑距离计算文档与查询的相似度，
    作为 rerank 的辅助特征。
    """

    def lcs_length(self, s1: str, s2: str) -> int:
        """计算 LCS 长度 - O(m*n) 时间。"""
        m, n = len(s1), len(s2)
        if m == 0 or n == 0:
            return 0
        # 优化：用一维 DP
        prev = [0] * (n + 1)
        cur = [0] * (n + 1)
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    cur[j] = prev[j - 1] + 1
                else:
                    cur[j] = max(prev[j], cur[j - 1])
            prev, cur = cur, [0] * (n + 1)
        return prev[n]

    def lcs_ratio(self, s1: str, s2: str) -> float:
        """LCS 占较短字符串的比例（0-1）。"""
        if not s1 or not s2:
            return 0.0
        lcs_len = self.lcs_length(s1, s2)
        min_len = min(len(s1), len(s2))
        return lcs_len / min_len if min_len > 0 else 0.0

    def jaccard_similarity(self, s1: str, s2: str) -> float:
        """Jaccard 相似度：交集 / 并集。"""
        set1 = set(s1.split())
        set2 = set(s2.split())
        if not set1 and not set2:
            return 1.0
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union)

    def rerank_score(
        self,
        query: str,
        document: str,
        vector_score: float,
    ) -> float:
        """综合 rerank 分数。"""
        lcs_score = self.lcs_ratio(query, document)
        jaccard_score = self.jaccard_similarity(query, document)
        # 综合：向量相似度 + 关键词匹配
        return 0.7 * vector_score + 0.2 * jaccard_score + 0.1 * lcs_score
```

**解读**：
- 第 19 行：一维 DP 优化 LCS 空间到 O(n)
- 第 37 行：Jaccard 相似度比 LCS 更常用（更快）
- **dify 的实际实现**：LCS 计算较慢，主要用 BM25、Jaccard 等
- **设计意图**：rerank 需要综合多种相似度特征，LCS 是其中之一

## 4. 关键要点总结

- LCS：O(mn) DP，状态转移看字符是否相等
- LIS：O(n²) DP 或 **O(n log n) 二分 + 贪心**
- 编辑距离：与 LCS 相关，但允许替换操作
- 应用：文本相似度、git diff、拼写检查、DNA 比对
- dify 用 LCS 作为文本相似度特征

## 5. 练习题

### 练习 1：基础（必做）

实现**最长回文子序列**（LeetCode 516）：用 DP 求字符串的最长回文子序列。

### 练习 2：进阶

阅读 `api/core/rag/rerank/weight_rerank.py`，说明 dify 为什么用 Jaccard 而不只用 LCS 计算文本相似度（提示：时间复杂度、词序敏感性）。

### 练习 3：挑战（选做）

实现**最长公共子串**（连续）：区别于 LCS，要求子串必须连续。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
- 《算法导论》第 15 章 动态规划
- LeetCode 1143/300/72 题

---

**文档版本**：v1.0
**最后更新**：2026-07-13