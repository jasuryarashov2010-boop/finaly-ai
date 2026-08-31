# V999 Engineering Audit

## Arxitektura qarorlari
1. PostgreSQL — source of truth. Users, plans, conversations, messages, tickets, ratings, feedback, referrals, knowledge, prompts, lessons, broadcasts and audit logs are persisted here.
2. Render Key Value — ephemeral state/cache/rate limits/daily usage counters only. The code intentionally does not rely on it for business-critical history.
3. FastAPI webhook + aiogram dispatcher provides a single Render web service.
4. AI provider is isolated in `app/services/ai.py`, so provider/model changes do not require rewriting handlers.
5. User and admin UI are separated with inline keyboards and a persistent bottom keyboard. Admin buttons are only generated for configured admin IDs.
6. UZ/RU/EN main keyboard labels are localized.

## V999 functional surface
- Mandatory subscription gate
- Language selection after subscription
- AI workspace
- Conversation history
- Daily feature quotas
- Voice transcription
- PDF/DOCX/TXT/CSV/XLSX analysis
- Image generation
- Support ticket creation/list/status
- Rating and feedback
- Profile, usage stats, plans and referral
- Admin dashboard
- User search, plan assignment and block toggle
- Required channel management
- Knowledge base
- Ticket management
- AI Learning Center
- Prompt coach / builder / improver / analyzer
- AI lesson generator
- Telegram post generator
- Prompt library
- Broadcast segmentation
- Analytics, quality, audit logs, health

## Admin AI Learning boundary
The learning system is intentionally about prompt engineering, workflow design, evaluation and responsible AI use. It does not attempt to expose private credentials, hidden system prompts or private chain-of-thought.

## Validation performed
- Python `compileall` completed successfully after fixes.
- SQLAlchemy model declaration loads successfully and exposes 16 tables.
- Full runtime dependency installation could not be executed in this environment because outbound package-network access is unavailable. Render will install from `requirements.txt` during deployment.

## Production hardening recommended after MVP
- Alembic migrations instead of `create_all` for schema evolution
- Persistent object storage for user-uploaded files
- Background worker for large broadcasts / heavy AI jobs
- Better semantic retrieval for Knowledge Base (e.g. pgvector on paid Postgres)
- Stronger operator role/permission matrix and real-time ticket relay
- External monitoring and alerting
- Paid persistent Postgres/Key Value for production workloads
