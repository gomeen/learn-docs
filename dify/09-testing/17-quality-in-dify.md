# 22 dify 的 lint / type-check / test 三件套

> 全面理解 dify 的质量保障三件套：`make test` / `make lint` / `make type-check`，掌握三者的协作与权衡。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 dify 三个核心质量命令的用法
- 理解三者在 CI 中的协作流程
- 能根据失败信息定位问题根源
- 应用：能独立完成 dify 的"提交前 + 提交后"质量门禁

## 📚 前置知识

- 09-testing/14-lint-tools.md
- 09-testing/15-type-check.md
- 09-testing/06-pytest-in-dify.md

## 1. 核心概念

### 1.1 dify 质量保障三件套

```
                ┌─────────────────┐
                │   git commit    │
                └────────┬────────┘
                         ↓
              ┌──────────────────────┐
              │   pre-commit hook    │  ← 详见 [Pre-commit Hook](./16-pre-commit.md)
              │   (Ruff auto-fix)    │
              └──────────┬───────────┘
                         ↓
                ┌─────────────────┐
                │   git push       │
                └────────┬────────┘
                         ↓
       ┌─────────────────────────────────────┐
       │             CI Pipeline             │  ← 详见 [CI/CD 概念](../../_common/11-cicd/01-concepts.md)
       │                                     │     / [GitHub Actions](../../_common/11-cicd/02-github-actions.md)
       │   1. make lint     ← 风格 / 错误    │
       │   2. make type-check ← 类型一致性   │
       │   3. make test      ← 行为正确性    │
       │                                     │
       └─────────────────────────────────────┘
                         ↓
                ┌─────────────────┐
                │   全部通过？     │
                │  ✓ 合并 PR      │
                │  ✗ 阻止合并     │
                └─────────────────┘
```

### 1.2 三个命令的层次关系

| 命令 | 检查内容 | 速度 | 严格度 | 失败代价 |
|------|----------|------|--------|----------|
| `make lint` | 风格、语法、潜在 bug | 快（秒级） | 中 | 低（可自动修复） |
| `make type-check` | 类型一致性 | 中（10秒级） | 高 | 中（需手动修复） |
| `make test` | 行为正确性 | 慢（分钟级） | 极高 | 高（需调试） |

### 1.3 三个命令的协作

```
                   ┌─────────────────┐
                   │  dev/reformat   │  ← 开发本地（自动修复）
                   └────────┬────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │                                       │
        │  提交前：pre-commit 自动跑 ruff        │
        │                                       │
        └───────────────────┬───────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │                                       │
        │  提交后：CI 跑 三件套                 │
        │                                       │
        │  lint → type-check → test             │
        │   ↓          ↓           ↓            │
        │  风格       类型        行为          │
        │                                       │
        └───────────────────────────────────────┘
```

## 2. 代码示例

### 2.1 本地开发的标准流程

```bash
# 1. 开发代码
$ vim api/services/billing_service.py

# 2. 本地自动修复 lint
$ dev/reformat
# 或者手动
$ uv run --project api --dev ruff format ./api
$ uv run --project api --dev ruff check --fix ./api

# 3. 运行测试
$ cd api && uv run --project api --dev pytest api/tests/unit_tests/services/test_billing_service.py -v

# 4. 类型检查
$ make type-check

# 5. 完整 lint 检查
$ make lint

# 6. 提交（pre-commit hook 自动触发）
$ git commit -m "feat: add billing refund"
```

### 2.2 CI 流程（伪代码）

```yaml
# CI 中按顺序执行
steps:
  - name: Lint
    run: make lint
    # 失败 → 直接拒绝，节省后续步骤时间

  - name: Type Check
    run: make type-check
    # 失败 → 拒绝，类型不一致的代码不应进入测试

  - name: Unit Tests
    run: make test
    # 失败 → 拒绝，行为不正确不能合并

  - name: Integration Tests
    run: make test-integration
    # 失败 → 警告（不阻塞合并），但应在合并后修复
```

### 2.3 三个命令的输出风格对比

**lint 输出**（人类友好，带代码位置）：

```
api/services/billing_service.py:42:5: E501 Line too long (135 > 120)
api/services/billing_service.py:55:1: F401 `os` imported but unused
Found 2 errors.
```

**type-check 输出**（类型错误，含类型签名）：

```
api/services/billing_service.py:42: error: Argument 1 to "send_request" has incompatible type "str"; expected "int"  [arg-type]
    def send_request(user_id: int, ...) -> Response:
                        ^
api/services/billing_service.py:55: error: "os" is unbound  [used-before-def]
```

**test 输出**（详细的断言和回溯）：

```
======================== FAILURES ========================
_______ test_billing_service_refund _______
api/tests/unit_tests/services/test_billing_service.py:88: in test_billing_service_refund
    result = BillingService.refund(user_id=42)
api/services/billing_service.py:120: in refund
    raise ValueError("user not found")
E   ValueError: user not found
```

## 3. 关键要点总结

- dify 三件套：`make lint`（风格）+ `make type-check`（类型）+ `make test`（行为）
- pre-commit hook 自动跑 Ruff，把质量门禁前置
- CI 顺序：lint → type-check → test（**快速失败在前**）
- `make test` 只跑单元测试，`make test-all` 跑全部
- Controller 测试单独跑，避开 xdist 的路由冲突
- `make lint` 不只是 Ruff，还包含 importlinter、契约检查、dotenv-linter

---

**文档版本**：v1.0
**最后更新**：2026-07-13
