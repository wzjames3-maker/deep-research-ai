# Changelog

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
