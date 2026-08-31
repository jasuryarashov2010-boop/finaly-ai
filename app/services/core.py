from __future__ import annotations
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import *
from app.services.redis_service import RedisService

class CoreService:
    def __init__(self, db: AsyncSession, redis_service: RedisService):
        self.db, self.redis = db, redis_service

    async def get_or_create_user(self, tg_user) -> User:
        user = await self.db.get(User, tg_user.id)
        if not user:
            user = User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name, last_name=tg_user.last_name, referral_code=secrets.token_urlsafe(8))
            self.db.add(user)
        else:
            user.username, user.first_name, user.last_name = tg_user.username, tg_user.first_name, tg_user.last_name
        user.last_active_at = datetime.now(timezone.utc)
        await self.db.commit()
        return user

    async def set_language(self, user_id: int, language: str):
        user = await self.db.get(User, user_id)
        if user:
            user.language = language
            await self.db.commit()

    async def channels(self):
        return list((await self.db.scalars(select(Channel).where(Channel.active.is_(True)).order_by(Channel.id))).all())

    async def plan(self, code: str):
        return await self.db.scalar(select(Plan).where(Plan.code == code, Plan.active.is_(True)))

    async def effective_plan(self, user: User) -> Plan:
        if user.plan_expires_at and user.plan_expires_at <= datetime.now(timezone.utc) and user.plan_code != "free":
            user.plan_code = "free"
            user.plan_expires_at = None
            await self.db.commit()
        return await self.plan(user.plan_code) or await self.plan("free")

    async def usage(self, user_id: int, feature: str) -> int:
        return await self.redis.get_daily(user_id, feature)

    async def limit_info(self, user: User, feature: str):
        plan = await self.effective_plan(user)
        limits = {"ai":plan.daily_ai,"voice":plan.daily_voice,"file":plan.daily_file,"image":plan.daily_image}
        used = await self.usage(user.id, feature)
        return used, limits.get(feature, 0)

    async def consume(self, user: User, feature: str, units: int = 1):
        used, limit = await self.limit_info(user, feature)
        if used + units > limit:
            return False, used, limit
        new_value = await self.redis.incr_daily(user.id, feature, units)
        self.db.add(UsageEvent(user_id=user.id, feature=feature, units=units))
        await self.db.commit()
        return True, new_value, limit

    async def new_conversation(self, user_id: int, title: str = "New Chat", mode: str = "auto"):
        c = Conversation(user_id=user_id, title=title[:120], mode=mode)
        self.db.add(c); await self.db.commit(); return c

    async def conversations(self, user_id: int):
        return list((await self.db.scalars(select(Conversation).where(Conversation.user_id == user_id, Conversation.archived.is_(False)).order_by(Conversation.updated_at.desc()).limit(30))).all())

    async def get_conversation(self, conv_id: int, user_id: int):
        return await self.db.scalar(select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user_id))

    async def save_message(self, conv: Conversation, role: str, content: str, meta: dict | None = None):
        self.db.add(Message(conversation_id=conv.id, role=role, content=content, meta=meta or {}))
        conv.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def recent_messages(self, conv_id: int, limit: int = 24):
        rows = list((await self.db.scalars(select(Message).where(Message.conversation_id == conv_id).order_by(Message.id.desc()).limit(limit))).all())
        return list(reversed(rows))

    async def create_ticket(self, user: User, subject: str, content: str, category="other", priority="normal", source_conversation_id=None, ai_summary=None, ai_sentiment=None, ai_confidence=None):
        ticket = Ticket(user_id=user.id, subject=subject[:255], category=category, priority=priority, language=user.language or "uz", source_conversation_id=source_conversation_id, ai_summary=ai_summary, ai_sentiment=ai_sentiment, ai_confidence=ai_confidence)
        self.db.add(ticket); await self.db.flush()
        self.db.add(TicketMessage(ticket_id=ticket.id, sender_id=user.id, sender_type="user", content=content[:20000]))
        await self.db.commit(); return ticket

    async def tickets(self, user_id: int):
        return list((await self.db.scalars(select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.updated_at.desc()).limit(30))).all())

    async def ticket(self, ticket_id: int, user_id: int | None = None):
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        if user_id is not None: stmt = stmt.where(Ticket.user_id == user_id)
        return await self.db.scalar(stmt)

    async def ticket_messages(self, ticket_id: int):
        return list((await self.db.scalars(select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.id).limit(100))).all())

    async def append_ticket_message(self, ticket: Ticket, sender_id: int, sender_type: str, content: str, attachment=None):
        self.db.add(TicketMessage(ticket_id=ticket.id, sender_id=sender_id, sender_type=sender_type, content=content[:20000], attachment=attachment or {}))
        ticket.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def add_rating(self, user_id: int, ticket_id: int, score: int, comment: str | None = None):
        self.db.add(Rating(user_id=user_id, ticket_id=ticket_id, score=score, comment=comment))
        await self.db.commit()

    async def add_feedback(self, user_id: int, category: str, content: str):
        self.db.add(Feedback(user_id=user_id, category=category, content=content[:5000])); await self.db.commit()

    async def referrals_count(self, user_id: int):
        return int(await self.db.scalar(select(func.count(Referral.id)).where(Referral.referrer_id == user_id)) or 0)

    async def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        if referrer_id == referred_id: return False
        exists = await self.db.scalar(select(Referral).where(Referral.referred_id == referred_id))
        if exists: return False
        self.db.add(Referral(referrer_id=referrer_id, referred_id=referred_id, reward_granted=False)); await self.db.commit(); return True

    async def search_users(self, query: str, limit: int = 20):
        if query.isdigit():
            stmt = select(User).where(User.id == int(query)).limit(limit)
        else:
            q = query.lstrip("@").lower()
            stmt = select(User).where(func.lower(User.username).like(f"%{q}%")).limit(limit)
        return list((await self.db.scalars(stmt)).all())

    async def audit(self, actor_id: int, action: str, target_id: str | int | None = None, details=None):
        self.db.add(AuditLog(actor_id=actor_id, action=action, target_id=str(target_id) if target_id is not None else None, details=details or {})); await self.db.commit()
