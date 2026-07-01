# Task 04: 速率限制中间件

## 对应 Spec
- specs/auth/03-api-contract.md（API-AUTH-001 Rate Limit: 5/min, API-AUTH-002 Rate Limit: 10/min, API-AUTH-005 Rate Limit: 30/min）
- specs/auth/05-edge-cases.md EC-AUTH-008（频控）
- specs/research/03-api-contract.md（研究接口默认也需要频控保护）

## 输入文件（Agent 需读取）
- specs/auth/03-api-contract.md（Rate Limit 配置）
- src/main.py（FastAPI app）
- src/errors.py（RateLimitedError）

## 输出文件
- `src/middleware/rate_limiter.py`（速率限制中间件实现）

## 前置任务
- Task 01（项目骨架）
- Task 03（RateLimitedError 已定义）

## 实现要求
1. **存储**: 使用 `collections.defaultdict` + 滑动窗口（内存存储，V1 不做 Redis）
2. **Key**: `{route}:{client_ip}`
3. **窗口**: 固定的 60 秒滑动窗口
4. **路由限流配置**:
   - `POST /api/v1/auth/register` → 5 次/分钟/IP
   - `POST /api/v1/auth/login` → 10 次/分钟/IP
   - `POST /api/v1/auth/refresh` → 30 次/分钟/用户（通过 `current_user.id` 而非 IP）
   - 其他 `/api/v1/auth/*` → 30 次/分钟/IP（默认）
   - `/api/v1/research/*` → 60 次/分钟/IP（默认，较宽松）
5. **实现方式**: FastAPI Depends
   ```python
   async def rate_limit(request: Request, route_limit: int = 30):
       # 检查当前 IP 在 route 上的请求计数
       # 超过阈值 → 抛出 RateLimitedError
       # 未超过 → 计数 +1，放行
   ```
6. **响应头**: 包含 `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 03 的 `RateLimitedError` 已可用
- [ ] FastAPI app 可正常启动

### 功能验收
- [ ] 连续 POST `/api/v1/auth/register` 6 次 → 前 5 次 201/409/400，第 6 次 429
- [ ] 60 秒后窗口重置 → 第 7 次请求不再返回 429
- [ ] 不同 IP 的限流独立（使用不同 `X-Forwarded-For` 头测试）

### AC 验收
- [ ] AC-AUTH-012: 同一 IP 连续 POST `/api/v1/auth/login` > 10 次/分钟 → 第 11 次返回 429 RATE_LIMITED

### 代码质量
- [ ] 限流计数器使用线程安全的数据结构
- [ ] 无内存泄漏风险（定期清理过期计数器）
- [ ] 响应头 `X-RateLimit-Remaining` 准确

### 通过判定
全部 ✅ → 任务 Done，进入 Task 05
