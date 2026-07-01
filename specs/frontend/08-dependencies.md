# 依赖关系

## 前置依赖

| 依赖模块 | 依赖内容 | 必须完成 |
|---|---|---|
| auth (backend) | Auth API 可用（register/login） | ✅ 前端可开发（mock API） |
| research (backend) | Research API 可用（所有端点） | ✅ 前端可开发（mock API） |
| research (backend) | SSE 端点可用 | ✅ 前端需要真实 SSE 流进行联调 |
| 基础设施 | Nginx 配置完成（SPA 路由 fallback） | ✅ M4-M6 |

## 后置依赖

| 依赖方 | 依赖内容 |
|---|---|
| 无 | 前端是终端模块，无后续模块依赖 |

## 外部服务依赖

| 服务 | 用途 | 降级策略 |
|---|---|---|
| 后端 API | 所有数据请求 | mock API 开发模式 |
| SSE 端点 | 实时进度 | mock SSE 事件流（开发时） |

## 构建产物

```
dist/
├── index.html
├── assets/
│   ├── index-<hash>.js
│   └── index-<hash>.css
└── ...
```

由 Nginx 配置 `try_files $uri /index.html` 处理 SPA 路由。
