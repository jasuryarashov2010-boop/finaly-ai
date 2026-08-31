from __future__ import annotations
from datetime import datetime, timezone, timedelta
from html import escape
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func, update, delete
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import *
from app.services.core import CoreService
from app.services.redis_service import RedisService
from app.services.ai import AIService
from app.utils.ui import admin_keyboard, learning_keyboard, back

router=Router(); settings=get_settings(); redis_service=RedisService(); ai_service=AIService()

def is_admin(uid:int)->bool: return uid in settings.admin_id_set

def guard(c:CallbackQuery|Message)->bool: return is_admin(c.from_user.id)

async def send_admin_panel(message:Message):
    if not is_admin(message.from_user.id): return
    await message.answer("<b>🛠 AI SUPPORTER — ADMIN CONTROL CENTER</b>\n\nBarcha boshqaruv modullari quyida.",reply_markup=admin_keyboard(),parse_mode="HTML")

@router.callback_query(F.data=="adm:dashboard")
async def dashboard(c:CallbackQuery):
    if not guard(c): return
    async with SessionLocal() as db:
        users=await db.scalar(select(func.count(User.id))) or 0
        active=await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
        tickets=await db.scalar(select(func.count(Ticket.id)).where(Ticket.status!="closed")) or 0
        chats=await db.scalar(select(func.count(Conversation.id))) or 0
        ratings=await db.scalar(select(func.avg(Rating.score)))
        kb=await db.scalar(select(func.count(KnowledgeItem.id)).where(KnowledgeItem.active.is_(True))) or 0
    body=(f"<b>📊 DASHBOARD</b>\n\n👥 Users: <b>{users}</b>\n🟢 Active: <b>{active}</b>\n🎫 Open tickets: <b>{tickets}</b>\n💬 Conversations: <b>{chats}</b>\n⭐ Rating: <b>{float(ratings or 0):.2f}</b>\n🧠 Knowledge: <b>{kb}</b>")
    await c.message.edit_text(body,reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()

class AState(StatesGroup):
    user_query=State(); user_action=State(); channel=State(); kb=State(); operator=State(); plan=State(); broadcast=State(); learning=State(); prompt=State()

@router.callback_query(F.data=="adm:users")
async def users(c:CallbackQuery,state:FSMContext):
    if not guard(c): return
    await state.set_state(AState.user_query); await c.message.answer("🔎 User ID yoki @username yuboring:"); await c.answer()

@router.message(AState.user_query)
async def user_search(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); rows=await core.search_users((m.text or "").strip())
    if not rows: await m.answer("❌ User topilmadi."); await state.clear(); return
    b=InlineKeyboardBuilder()
    for u in rows: b.button(text=f"👤 {u.id} @{u.username or '—'}",callback_data=f"adm:user:{u.id}")
    b.adjust(1); await m.answer("👥 Natijalar:",reply_markup=b.as_markup()); await state.clear()

@router.callback_query(F.data.startswith("adm:user:"))
async def user_card(c:CallbackQuery):
    if not guard(c): return
    uid=int(c.data.split(":")[-1])
    async with SessionLocal() as db:
        u=await db.get(User,uid)
        if not u:return await c.answer("Topilmadi",show_alert=True)
        plan=await CoreService(db,redis_service).effective_plan(u)
    b=InlineKeyboardBuilder()
    for code in ["free","comfort","pro","premium"]: b.button(text=f"💎 {code.upper()}",callback_data=f"adm:setplan:{uid}:{code}")
    b.button(text="🚫 Block/Unblock",callback_data=f"adm:block:{uid}"); b.button(text="📝 Note",callback_data=f"adm:note:{uid}"); b.adjust(2,1,1)
    body=f"<b>👤 USER</b>\n\n🆔 <code>{u.id}</code>\n👤 @{escape(u.username or '—')}\n🌐 {u.language or 'uz'}\n💎 {plan.name}\n🚫 Blocked: {u.is_blocked}\n📅 Joined: {u.created_at.strftime('%Y-%m-%d')}"
    await c.message.edit_text(body,reply_markup=b.as_markup(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("adm:setplan:"))
async def set_plan(c:CallbackQuery):
    if not guard(c): return
    _,_,uid,code=c.data.split(":")
    async with SessionLocal() as db:
        u=await db.get(User,int(uid)); p=await db.scalar(select(Plan).where(Plan.code==code))
        if not u or not p:return await c.answer("Not found",show_alert=True)
        if code=="free": u.plan_code="free"; u.plan_expires_at=None
        else: u.plan_code=code; u.plan_expires_at=datetime.now(timezone.utc)+timedelta(days=30)
        await db.commit(); await CoreService(db,redis_service).audit(c.from_user.id,"plan_changed",uid,{"plan":code,"days":30 if code!="free" else 0})
    await c.answer("✅ Tarif yangilandi",show_alert=True); await c.message.answer(f"✅ User <code>{uid}</code> → <b>{code.upper()}</b>",parse_mode="HTML")

@router.callback_query(F.data.startswith("adm:block:"))
async def block(c:CallbackQuery):
    if not guard(c): return
    uid=int(c.data.split(":")[-1])
    async with SessionLocal() as db:
        u=await db.get(User,uid)
        if not u:return await c.answer("Not found",show_alert=True)
        u.is_blocked=not u.is_blocked; await db.commit(); await CoreService(db,redis_service).audit(c.from_user.id,"user_block_toggle",uid,{"blocked":u.is_blocked})
    await c.answer("✅ Updated",show_alert=True)

@router.callback_query(F.data=="adm:plans")
async def plans(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db: rows=list((await db.scalars(select(Plan).order_by(Plan.sort_order))).all())
    body="<b>💎 PLAN MANAGEMENT</b>\n\n"+"\n".join(f"{p.name}: 🤖{p.daily_ai} 🎙{p.daily_voice} 📄{p.daily_file} 🖼{p.daily_image} | {p.max_file_mb}MB" for p in rows)
    await c.message.edit_text(body,reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:channels")
async def channels(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db: rows=list((await db.scalars(select(Channel).order_by(Channel.id))).all())
    b=InlineKeyboardBuilder(); b.button(text="➕ Add channel",callback_data="adm:addchannel")
    b.button(text="🗑 Deactivate all",callback_data="adm:deactivate_channels"); b.button(text="⬅️ Admin",callback_data="adm:dashboard"); b.adjust(1)
    body="<b>📢 REQUIRED CHANNELS</b>\n\n"+"\n".join(f"#{x.id} {'🟢' if x.active else '🔴'} {escape(x.title)} • <code>{x.chat_id}</code>" for x in rows) or "Kanal yo‘q."
    await c.message.edit_text(body,reply_markup=b.as_markup(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:addchannel")
async def addchannel(c:CallbackQuery,state:FSMContext):
    if not guard(c):return
    await state.set_state(AState.channel); await c.message.answer("📢 Format:\n<code>title|chat_id|@username|invite_url</code>",parse_mode="HTML"); await c.answer()

@router.message(AState.channel)
async def savechannel(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id):return
    try:
        parts=[x.strip() for x in (m.text or "").split("|",3)]; chat_id=int(parts[1]); title=parts[0]
        username=parts[2] if len(parts)>2 and parts[2] else None; invite=parts[3] if len(parts)>3 and parts[3] else None
        async with SessionLocal() as db: db.add(Channel(title=title,chat_id=chat_id,username=username,invite_url=invite)); await db.commit()
        await m.answer("✅ Kanal qo‘shildi.")
    except Exception: await m.answer("❌ Format xato.")
    await state.clear()

@router.callback_query(F.data=="adm:deactivate_channels")
async def deactivate_channels(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db: await db.execute(update(Channel).values(active=False)); await db.commit()
    await c.answer("✅ O‘chirildi",show_alert=True)

@router.callback_query(F.data=="adm:kb")
async def kb(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db: rows=list((await db.scalars(select(KnowledgeItem).where(KnowledgeItem.active.is_(True)).order_by(KnowledgeItem.priority.desc()).limit(20))).all())
    b=InlineKeyboardBuilder(); b.button(text="➕ Add knowledge",callback_data="adm:addkb"); b.button(text="⬅️ Admin",callback_data="adm:dashboard"); b.adjust(1)
    body="<b>🧠 KNOWLEDGE BASE</b>\n\n"+"\n".join(f"#{x.id} {escape(x.title)} [{x.kind}]" for x in rows) or "Bo‘sh."
    await c.message.edit_text(body,reply_markup=b.as_markup(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:addkb")
async def addkb(c:CallbackQuery,state:FSMContext):
    if not guard(c):return
    await state.set_state(AState.kb); await c.message.answer("📚 Format: <code>title|content|tag1,tag2|priority</code>",parse_mode="HTML"); await c.answer()

@router.message(AState.kb)
async def savekb(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id):return
    try:
        p=(m.text or "").split("|",3); tags=[x.strip() for x in p[2].split(",")] if len(p)>2 else []; priority=int(p[3]) if len(p)>3 else 0
        async with SessionLocal() as db: db.add(KnowledgeItem(title=p[0][:255],content=p[1],tags=tags,priority=priority,created_by=m.from_user.id)); await db.commit()
        await m.answer("✅ Knowledge saqlandi.")
    except Exception: await m.answer("❌ Format xato.")
    await state.clear()

@router.callback_query(F.data=="adm:tickets")
async def tickets(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db: rows=list((await db.scalars(select(Ticket).order_by(Ticket.updated_at.desc()).limit(20))).all())
    b=InlineKeyboardBuilder()
    for x in rows:b.button(text=f"🎫 #{x.id} {x.status} {x.priority}",callback_data=f"adm:ticket:{x.id}")
    b.adjust(1); await c.message.edit_text("<b>🎫 TICKET MANAGEMENT</b>\n\n"+"\n".join(f"#{x.id} • user {x.user_id} • {x.category} • {x.status}" for x in rows),reply_markup=b.as_markup()); await c.answer()

@router.callback_query(F.data.startswith("adm:ticket:"))
async def ticket_card(c:CallbackQuery):
    if not guard(c):return
    tid=int(c.data.split(":")[-1])
    async with SessionLocal() as db: core=CoreService(db,redis_service); ticket=await core.ticket(tid); msgs=await core.ticket_messages(tid) if ticket else []
    if not ticket:return await c.answer("Topilmadi",show_alert=True)
    b=InlineKeyboardBuilder();
    for status in ["waiting","in_progress","closed"]: b.button(text=f"📊 {status}",callback_data=f"adm:tstatus:{tid}:{status}")
    await c.message.edit_text(f"<b>🎫 #{tid}</b>\nuser: <code>{ticket.user_id}</code>\ncategory: {ticket.category}\npriority: {ticket.priority}\nstatus: {ticket.status}\n\n"+"\n".join(f"{m.sender_type}: {escape(m.content[:800])}" for m in msgs[-8:]),reply_markup=b.as_markup(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("adm:tstatus:"))
async def ticket_status(c:CallbackQuery):
    if not guard(c):return
    _,_,tid,status=c.data.split(":")
    async with SessionLocal() as db:
        t=await db.get(Ticket,int(tid));
        if not t:return await c.answer("Topilmadi",show_alert=True)
        t.status=status; await db.commit(); await CoreService(db,redis_service).audit(c.from_user.id,"ticket_status",tid,{"status":status})
    await c.answer("✅ Status updated",show_alert=True)

@router.callback_query(F.data=="adm:operators")
async def operators(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db: rows=list((await db.scalars(select(User).where(User.role.in_(["operator","manager","admin"])).limit(30))).all())
    await c.message.edit_text("<b>👨‍💻 OPERATORS</b>\n\n"+"\n".join(f"<code>{u.id}</code> • @{u.username or '—'} • {u.role}" for u in rows) or "Operator yo‘q.",reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:learning")
async def learning(c:CallbackQuery):
    if not guard(c):return
    await c.message.edit_text("<b>🧑‍🏫 AI LEARNING CENTER</b>\n\nAdmin uchun prompt engineering, AI workflow, evaluation, creative prompting va post generation laboratoriyasi.",reply_markup=learning_keyboard(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:ai")
async def ai_center(c:CallbackQuery):
    if not guard(c):return
    await c.message.edit_text("<b>🤖 AI CENTER</b>\n\n🟢 Provider konfiguratsiyasi: " + ("READY" if ai_service.available else "NOT CONFIGURED") + "\n\nAI uchun Knowledge Base va Learning Center'dan foydalaning.",reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("learn:"))
async def learn_action(c:CallbackQuery,state:FSMContext):
    if not guard(c):return
    action=c.data.split(":",1)[1]
    prompts={"coach":"Vazifani yozing. Men sizga professional prompt, izoh, test va mashqlar tuzaman.","build":"Nima natija olmoqchi ekaningizni yozing.","improve":"Mavjud promptingizni yuboring.","analyze":"Tahlil qilinadigan promptingizni yuboring.","post":"AI mavzusida post uchun mavzuni yuboring.","lessons":"Qaysi mavzuni o‘rganmoqchisiz? (masalan: RAG, prompts, evals)"}
    if action=="library":
        async with SessionLocal() as db: rows=list((await db.scalars(select(PromptItem).where(PromptItem.created_by==c.from_user.id).order_by(PromptItem.id.desc()).limit(20))).all())
        await c.message.edit_text("<b>📋 MY PROMPTS</b>\n\n"+"\n\n".join(f"#{x.id} <b>{escape(x.title)}</b>\n{escape(x.prompt[:700])}" for x in rows) or "Library bo‘sh.",reply_markup=learning_keyboard(),parse_mode="HTML"); return await c.answer()
    await state.set_state(AState.learning); await state.update_data(action=action); await c.message.answer("🧑‍🏫 "+prompts.get(action,"Topshiriqni yozing:")); await c.answer()

@router.message(AState.learning)
async def learning_input(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id):return
    data=await state.get_data(); action=data.get("action"); lang="uz"
    try:
        if action in {"coach","build"}: result=await ai_service.coach(m.text,lang)
        elif action=="improve": result=await ai_service.improve_prompt(m.text,lang)
        elif action=="analyze": result=await ai_service.analyze_prompt(m.text,lang)
        elif action=="post": result=await ai_service.generate_post(m.text,lang)
        else: result=await ai_service.generate_lesson(m.text,lang)
    except Exception as e: result=f"⚠️ AI xatosi: {e}"
    if action in {"coach","build","improve","analyze"}:
        async with SessionLocal() as db:
            db.add(PromptItem(title=f"Learning {action}",prompt=result,explanation="Generated by AI Learning Center",tags=[action],category="learning",created_by=m.from_user.id)); await db.commit()
    await state.clear(); await m.answer(result,parse_mode=None)

@router.callback_query(F.data=="adm:broadcast")
async def broadcast(c:CallbackQuery,state:FSMContext):
    if not guard(c):return
    await state.set_state(AState.broadcast); await c.message.answer("📢 Format: <code>segment|message</code>\nsegment: all / free / comfort / pro / premium / uz / ru / en",parse_mode="HTML"); await c.answer()

@router.message(AState.broadcast)
async def broadcast_send(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id):return
    raw=m.text or ""; segment,sep,msg=raw.partition("|"); segment=segment.strip() or "all"; msg=msg.strip() if sep else raw
    async with SessionLocal() as db:
        stmt=select(User.id).where(User.is_blocked.is_(False),User.is_active.is_(True))
        if segment in {"free","comfort","pro","premium"}: stmt=stmt.where(User.plan_code==segment)
        elif segment in {"uz","ru","en"}: stmt=stmt.where(User.language==segment)
        ids=[r[0] for r in (await db.execute(stmt)).all()]
        bc=Broadcast(admin_id=m.from_user.id,segment=segment,content=msg); db.add(bc); await db.flush(); bid=bc.id; await db.commit()
    sent=failed=0
    for uid in ids:
        try: await m.bot.send_message(uid,msg); sent+=1
        except Exception: failed+=1
        await asyncio.sleep(settings.broadcast_pause_ms/1000)
    async with SessionLocal() as db:
        bc=await db.get(Broadcast,bid); bc.sent,bc.failed=sent,failed; await db.commit()
    await state.clear(); await m.answer(f"✅ Broadcast: {sent} yuborildi, {failed} xato.")

@router.callback_query(F.data=="adm:quality")
async def quality(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db:
        avg=await db.scalar(select(func.avg(Rating.score))); total=await db.scalar(select(func.count(Rating.id))) or 0
    await c.message.edit_text(f"<b>⭐ SUPPORT QUALITY</b>\n\n⭐ Average: <b>{float(avg or 0):.2f}</b>\n🧾 Ratings: <b>{total}</b>",reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:analytics")
async def analytics(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db:
        users=await db.scalar(select(func.count(User.id))) or 0; tickets=await db.scalar(select(func.count(Ticket.id))) or 0
        today=datetime.now(timezone.utc).date(); usage=await db.scalar(select(func.coalesce(func.sum(UsageEvent.units),0)).where(func.date(UsageEvent.created_at)==today)) or 0
        ai=await db.scalar(select(func.coalesce(func.sum(UsageEvent.units),0)).where(UsageEvent.feature=="ai")) or 0
    await c.message.edit_text(f"<b>📈 ANALYTICS</b>\n\n👥 Users: {users}\n🎫 Tickets: {tickets}\n⚡ Today usage: {usage}\n🤖 Total AI units: {ai}",reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:logs")
async def logs(c:CallbackQuery):
    if not guard(c):return
    async with SessionLocal() as db: rows=list((await db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(25))).all())
    await c.message.edit_text("<b>📜 AUDIT LOGS</b>\n\n"+"\n".join(f"#{x.id} {x.action} • actor {x.actor_id} • target {x.target_id or '-'}" for x in rows) or "Log yo‘q.",reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="adm:health")
async def health(c:CallbackQuery):
    if not guard(c):return
    db_ok=redis_ok=False
    try:
        async with SessionLocal() as db: await db.execute(select(1)); db_ok=True
    except Exception: pass
    try: redis_ok=await redis_service.ping()
    except Exception: pass
    await c.message.edit_text(f"<b>🩺 SYSTEM HEALTH</b>\n\n{'🟢' if db_ok else '🔴'} PostgreSQL\n{'🟢' if redis_ok else '🔴'} Render Key Value\n{'🟢' if ai_service.available else '🟡'} AI provider\n\n<i>Free Key Value vaqtinchalik state/cache uchun ishlatilishi kerak.</i>",reply_markup=admin_keyboard(),parse_mode="HTML"); await c.answer()
