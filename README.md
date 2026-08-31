# AI Supporter Bot — V999

Premium Telegram AI assistant + Support CRM + Ticketing + AI Learning Center.

## Core modules
- Mandatory subscription with admin-managed channels
- UZ/RU/EN interface
- Premium HTML/keyboard UX
- AI conversations and chat history
- Daily quotas per plan
- Voice transcription
- PDF/DOCX/TXT/CSV/XLSX analysis
- Image generation
- Support tickets and ratings
- Referral tracking
- Admin dashboard
- User search / block / plan assignment
- Plans: Free / Comfort / Pro / Premium
- Knowledge Base
- AI Learning Center: coach, prompt builder, improve, analyze, lessons, post generator, prompt library
- Broadcast segmentation
- Analytics / quality / audit logs / health

## Data architecture
PostgreSQL stores permanent data: users, plans, subscriptions via user plan fields, conversations, messages, tickets, ratings, knowledge, prompts, broadcasts and audit logs.

Render Key Value (Redis-compatible) is used only for ephemeral state, cache, rate limits and daily counters. Do not treat it as the source of truth on the Free plan.

## Run
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows
# or cp .env.example .env
uvicorn app.main:app --reload
```

## Environment
Set BOT_TOKEN, ADMIN_IDS, DATABASE_URL, REDIS_URL and optionally OPENAI_API_KEY.

## Telegram webhook
Set PUBLIC_BASE_URL to the public Render URL. The app configures `/telegram/webhook` automatically at startup.

## Admin AI Learning
The AI Learning Center is designed as a prompt-engineering lab. It teaches role/goal/context/constraints/output-format design, prompt improvement, evaluation, examples, structured output and responsible AI usage. It intentionally does not expose private credentials, hidden system prompts or private chain-of-thought.

## Render Free caveat
Render documents Free Web Services, Free Postgres and Free Key Value as test/hobby infrastructure with important limitations. Free Postgres expires after 30 days, while Free Key Value is in-memory only and loses its data on restart. Permanent application data is therefore kept in Postgres and Redis is ephemeral.
