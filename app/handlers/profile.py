from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Conversation, Ticket, Rating, Plan, User
from app.services.core import CoreService
from app.services.redis_service import RedisService
from app.services.i18n import t
from app.utils.ui import profile_keyboard

router=Router(); redis_service=RedisService(); settings=get_settings()

async def render_profile(target):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(target.from_user); plan=await core.effective_plan(u)
        tickets=await db.scalar(select(func.count(Ticket.id)).where(Ticket.user_id==u.id)) or 0
        chats=await db.scalar(select(func.count(Conversation.id)).where(Conversation.user_id==u.id)) or 0
        rating=await db.scalar(select(func.avg(Rating.score)).where(Rating.user_id==u.id))
        refs=await core.referrals_count(u.id)
        usage={x:await redis_service.get_daily(u.id,x) for x in ["ai","voice","file","image"]}
    body=(f"<b>👤 PROFIL</b>\n\n🆔 <code>{u.id}</code>\n👤 @{u.username or '—'}\n🌐 {(u.language or 'uz').upper()}\n\n"
          f"💎 Tarif: <b>{plan.name}</b>\n"
          f"📅 Tugash: <b>{u.plan_expires_at.strftime('%Y-%m-%d') if u.plan_expires_at else '—'}</b>\n\n"
          f"🎫 Tickets: <b>{tickets}</b>\n💬 Chats: <b>{chats}</b>\n⭐ Rating: <b>{float(rating or 0):.1f}</b>\n👥 Referrals: <b>{refs}</b>\n\n"
          f"<b>⚡ Bugungi usage</b>\n🤖 {usage['ai']}/{plan.daily_ai}  🎙 {usage['voice']}/{plan.daily_voice}\n📄 {usage['file']}/{plan.daily_file}  🖼 {usage['image']}/{plan.daily_image}")
    if isinstance(target,Message): await target.answer(body,reply_markup=profile_keyboard(),parse_mode="HTML")
    else: await target.message.edit_text(body,reply_markup=profile_keyboard(),parse_mode="HTML")

@router.callback_query(F.data=="menu:profile")
async def profile(c): await render_profile(c); await c.answer()

@router.callback_query(F.data=="profile:stats")
async def stats(c): await render_profile(c); await c.answer("📊 Yangilandi")

@router.callback_query(F.data=="profile:plans")
async def plans(c):
    async with SessionLocal() as db: rows=list((await db.scalars(select(Plan).where(Plan.active.is_(True)).order_by(Plan.sort_order))).all())
    b=InlineKeyboardBuilder()
    for p in rows: b.button(text=f"💎 {p.name}",callback_data=f"plan:ask:{p.code}")
    b.button(text="⬅️ Profil",callback_data="menu:profile"); b.adjust(1)
    body="<b>💎 TARIFLAR</b>\n\n"+"\n\n".join(f"<b>{p.name}</b>\n🤖 {p.daily_ai}/day • 🎙 {p.daily_voice} • 📄 {p.daily_file} • 🖼 {p.daily_image}\n📝 {p.price_note or 'Admin orqali'}" for p in rows)
    await c.message.edit_text(body,reply_markup=b.as_markup(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("plan:ask:"))
async def plan_ask(c:CallbackQuery): await c.message.answer(f"💎 Tanlangan tarif: <b>{c.data.split(':')[-1].upper()}</b>\n\n📞 Admin bilan bog‘laning.\n🆔 <code>{c.from_user.id}</code>",parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="profile:referral")
async def referral(c:CallbackQuery):
    async with SessionLocal() as db: core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); count=await core.referrals_count(u.id)
    me=await c.bot.get_me(); link=f"https://t.me/{me.username}?start=ref_{u.id}"
    await c.message.edit_text(t(u.language,"referral",link=link,count=count),parse_mode="HTML",reply_markup=profile_keyboard()); await c.answer()

@router.callback_query(F.data=="profile:notifications")
async def notifications(c:CallbackQuery):
    async with SessionLocal() as db: u=await db.get(User,c.from_user.id); u.notifications_enabled=not u.notifications_enabled; await db.commit(); state=u.notifications_enabled
    await c.answer("🔔 ON" if state else "🔕 OFF",show_alert=True); await render_profile(c)

@router.callback_query(F.data=="profile:settings")
async def settings_view(c:CallbackQuery): await c.message.edit_text("<b>⚙️ SOZLAMALAR</b>\n\n🌐 Til: /start orqali\n🔔 Notification profil orqali\n🤖 AI memory: ON\n🔐 Maxfiylik: ma’lumotlar bot xizmatini ishlatish uchun saqlanadi.",reply_markup=profile_keyboard(),parse_mode="HTML"); await c.answer()
