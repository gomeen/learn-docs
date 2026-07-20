# 11.5.3 Swagger 接口文档

> 掌握 Swagger/OpenAPI 3.0 的使用：查看后端接口、生成前端代码、Knife4j 等 UI 工具。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Swagger / OpenAPI 的作用
- 使用 Knife4j 查看 ruoyi 后端接口文档
- 通过 OpenAPI 自动生成前端 TypeScript 类型
- 在 ruoyi 中调试接口

## 📚 前置知识

- Axios（详见 [Axios](./23-axios.md)）
- HTTP / REST 基础

## 1. 核心概念

### 1.1 什么是 Swagger？

Swagger（现称 OpenAPI）是一套 API 描述规范 + 工具链：
- **规范**：OpenAPI Specification（OAS）3.0，用 JSON/YAML 描述 API
- **工具**：
  - Swagger UI：可视化浏览 API
  - Swagger Codegen：从规范生成客户端代码
  - Swagger Editor：编写规范文件

### 1.2 ruoyi 的 Swagger 集成

ruoyi 后端用 **Knife4j**（Swagger 的增强版，国内常用）：
- 美观的 UI
- 支持离线文档、Postman 导出
- 支持接口签名、加解密演示
- 默认地址：`http://localhost:48080/doc.html`

### 1.3 OpenAPI 规范示例

```yaml
openapi: 3.0.0
info:
  title: MES SN API
  version: 1.0.0
paths:
  /mes/wm/sn/page:
    get:
      summary: 查询 SN 码分页
      parameters:
        - name: pageNo
          in: query
          schema:
            type: integer
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PageResp_WmSnVO'
components:
  schemas:
    WmSnVO:
      type: object
      properties:
        id:
          type: integer
        snCode:
          type: string
```

### 1.4 自动生成前端代码

工具链：
- **openapi-typescript**：生成 TypeScript 类型
- **openapi-generator**：生成 axios/fetch 客户端
- **swagger-typescript-api**：专门为前端生成

```bash
# 从 swagger.json 生成 TS 类型
npx openapi-typescript http://localhost:48080/v3/api-docs -o src/api/__generated__/types.ts
```

```ts
// 生成的类型
export interface WmSnVO {
  id: number
  snCode: string
  itemId: number
}

export interface PageResp_WmSnVO {
  list: WmSnVO[]
  total: number
}
```

### 1.5 ruoyi 的接口调试

启动 ruoyi 后端后，访问：
- `http://localhost:48080/doc.html` —— Knife4j UI
- `http://localhost:48080/swagger-ui/index.html` —— 官方 Swagger UI
- `http://localhost:48080/v3/api-docs` —— 原始 OpenAPI JSON

## 2. 代码示例

### 2.1 openapi-typescript 自动生成

```bash
# 安装
npm install -D openapi-typescript

# 拉取后端文档，生成类型
npx openapi-typescript http://localhost:48080/v3/api-docs \
  --output src/api/__generated__/types.ts
```

```ts
// 生成的 types.ts
export interface paths {
  '/mes/wm/sn/page': {
    parameters: { query: { pageNo?: number; pageSize?: number; snCode?: string } }
    get: {
      responses: { 200: { content: { 'application/json': PageRespWmSnVO } } }
    }
  }
}

export interface PageRespWmSnVO {
  list: WmSnVO[]
  total: number
}

export interface WmSnVO {
  id: number
  snCode: string
  itemId: number
}
```

### 2.2 自动生成 axios 客户端

```bash
# 安装
npm install -D swagger-typescript-api

# 生成
npx swagger-typescript-api generate -p http://localhost:48080/v3/api-docs \
  -o src/api/__generated__ -n api.ts
```

```ts
// 生成的 Api.ts
import { API } from './api'

const api = new API({ baseUrl: 'http://localhost:48080' })

// 直接调用
const res = await api.mesWmSn.getSnPage({ pageNo: 1, pageSize: 10 })
```

### 2.3 在 Knife4j 中调试接口

1. 启动后端
2. 浏览器打开 `http://localhost:48080/doc.html`
3. 找到"生成 SN 码"接口
4. 点击"调试"按钮
5. 填写参数：`{ "itemId": 1, "snNum": 100 }`
6. 点击"发送" → 看响应

### 2.4 常见错误：直接复制 swagger 字段名

```ts
// ❌ 错误：snCode 用了 camelCase，但后端是 snake_case
export interface WmSnVO {
  sn_code: string  // 后端字段
}

// ✅ 正确：保持和后端一致，或用工具转换
export interface WmSnVO {
  snCode: string  // 后端如果有 @JsonProperty("snCode") 转换
}
```

## 3. 关键要点总结

- Swagger/OpenAPI = API 描述规范 + 工具链
- ruoyi 用 **Knife4j**（国内常用），地址 `/doc.html`
- openapi-typescript 可以**自动生成**前端 TS 类型（避免手写不一致）
- 前端 VO 接口与后端 VO 一一对应（camelCase）
- URL 路径与后端 Controller 一致
- API 调试可以用 Knife4j 自带的"调试"功能

---

**文档版本**：v1.0
**最后更新**：2026-07-13
