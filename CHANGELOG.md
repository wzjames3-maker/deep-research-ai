# Changelog

## V1.1.0 (2026-07-01) — LangGraph Orchestration

### Research Module (Refactor)
- **LangGraph StateGraph** full-flow orchestration replaces pure asyncio
  - `plan_generation_node` → `human_review_node`(interrupt) → `dispatch_node`(Send API) → `aggregate_node`
  - Sub-agent subgraph: `search → dedup → analyze → conditional` loop
- **PostgresSaver checkpointer** for graph state persistence + crash recovery
- **interrupt() Human-in-the-loop**: Plan-phase pause/resume via `Command(resume=...)`
- **Send API parallel dispatch**: Native fan-out to sub-agent subgraphs
- **Hybrid cancel mechanism**: `update_state` (persistent) + `asyncio.Event` (real-time)
- `exec_engine.py` rewritten from 437 → 159 lines (thin graph wrapper)
- `service_plan.py` updated: create/revise/confirm → graph invoke/resume

### Tests
- **224 tests pass** (+39 new graph-specific tests)
- 33 unit tests for graph nodes (sub_agent, research, checkpoint, interrupt, cancel)
- 52 integration tests (including LangGraph E2E + crash recovery)

### Infrastructure
- `idle_in_transaction_session_timeout=5s` on DB engines to prevent zombie transactions
- Test isolation fixes for LangGraph module-level globals

### Spec
- 7 spec files updated (specs/research/00~08) for LangGraph migration
- 16 task files (tasks/phase-7-lg/33~48.md)
- `docs/tech-decision.md` decision 4: LangGraph confirmed as sole orchestration

---

## V1.0.0 (2026-06-30) — Initial Release

### Auth Module
- Register/Login with bcrypt password hashing + JWT authentication
- 5-failure account locking with auto-unlock after expiry
- Token refresh with 5-second grace period for old tokens
- SSE ticket-based auth for streaming connections
- Rate limiting: 5/min for register, 10/min for login, per-IP
- Unified error codes (INVALID_USERNAME, INVALID_PASSWORD, USERNAME_EXISTS, ACCOUNT_LOCKED, TOKEN_INVALID, RATE_LIMITED)

### Research Module
- Auto-generate research plans with 3-5 sub-agents via LLM
- Interactive plan revision (up to 10 rounds)
- Multi-agent parallel execution engine
- Real-time SSE progress streaming (8 event types)
- MCP protocol integration for Brave Search web search
- Fallback search via Tavily when Brave is unavailable
- Research cancellation with partial results preserved
- Markdown report generation with multi-round aggregation
- Soft delete for research records
- Token usage tracking per sub-agent and per research

### Frontend
- Login/Register pages with client-side validation
- Dashboard with token statistics cards + recent researches
- New research creation with template selection
- PlanPanel with chat-style revision interface
- ProgressDashboard with real-time SSE agent status cards
- ReportView with Markdown rendering, tabbed interface, copy actions
- History page with pagination + soft delete
- Hydration-based auth state restoration
- Axios interceptors with JWT auto-refresh + refresh lock
- Protected route guards
- Responsive design via Tailwind CSS 4 + shadcn/ui

### Infrastructure
- Docker Compose multi-service setup (nginx, app, db, brave-mcp)
- FastAPI with async SQLAlchemy + Alembic migrations
- Structured logging with structlog
- Nginx reverse proxy with CORS
- PostgreSQL 16 with healthcheck-based service dependencies
