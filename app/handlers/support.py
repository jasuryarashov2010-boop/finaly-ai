from html import escape
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.db.session import SessionLocal
from app.db.models import Ticket
from app.services.core import CoreService
from app.services.redis_service import RedisService
from app.services.i18n import t
from app.utils.ui import support_keyboard, ticket_categories, back

router=Router(); redis_service=RedisService()
class SupportState(StatesGroup): content=State(); feedback=State(); rating_comment=State()

async def render_support_menu(target):
    if isinstance(target,Message):
        async with SessionLocal() as db: u=await CoreService(db,redis_service).get_or_create_user(target.from_user)
        await target.answer(t(u.language,"support"),reply_markup=support_keyboard(),parse_mode="HTML")
    else:
        async with SessionLocal() as db: u=await CoreService(db,redis_service).get_or_create_user(target.from_user)
        await target.message.edit_text(t(u.language,"support"),reply_markup=support_keyboard(),parse_mode="HTML")

@router.callback_query(F.data=="menu:support")
async def support_menu(c): await render_support_menu(c); await c.answer()

@router.callback_query(F.data=="support:new")
async def new_ticket(c:CallbackQuery,state:FSMContext): await c.message.edit_text("<b>🎫 MUROJAAT KATEGORIYASI</b>",reply_markup=ticket_categories(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("ticket:cat:"))
async def ticket_category(c:CallbackQuery,state:FSMContext):
    cat=c.data.split(":")[-1]; await state.update_data(category=cat); await state.set_state(SupportState.content); await c.message.answer("📝 Muammoingizni batafsil yozing. Fayl/rasm ham yuborishingiz mumkin."); await c.answer()

@router.message(SupportState.content)
async def create_ticket(m:Message,state:FSMContext):
    data=await state.get_data(); text=m.text or m.caption or "Attachment received"
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(m.from_user)
        ticket=await core.create_ticket(u,"Support request",text,data.get("category","other"),"normal")
    await state.clear(); await m.answer(f"✅ <b>Ticket #{ticket.id}</b> yaratildi.\n📊 Status: <b>waiting</b>",parse_mode="HTML")

@router.callback_query(F.data=="support:list")
async def ticket_list(c:CallbackQuery):
    async with SessionLocal() as db: core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); rows=await core.tickets(u.id)
    b=InlineKeyboardBuilder()
    for x in rows: b.button(text=f"🎫 #{x.id} • {x.status}",callback_data=f"support:open:{x.id}")
    b.button(text="⬅️ Support",callback_data="menu:support"); b.adjust(1)
    await c.message.edit_text("<b>🎫 MENING TICKETLARIM</b>\n\n"+("\n".join(f"#{x.id} • {x.category} • {x.status}" for x in rows) or "Hozircha ticket yo‘q."),reply_markup=b.as_markup(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("support:open:"))
async def open_ticket(c:CallbackQuery):
    tid=int(c.data.split(":")[-1])
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); ticket=await core.ticket(tid,u.id); msgs=await core.ticket_messages(tid) if ticket else []
    if not ticket:return await c.answer("Ticket topilmadi",show_alert=True)
    body=f"<b>🎫 Ticket #{ticket.id}</b>\n📌 {ticket.category}\n🚦 {ticket.priority}\n📊 {ticket.status}\n\n"+"\n\n".join(f"<b>{m.sender_type}</b>: {escape(m.content[:1200])}" for m in msgs[-10:])
    await c.message.edit_text(body,reply_markup=back("support:list"),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="support:rate")
async def rate_start(c:CallbackQuery,state:FSMContext):
    async with SessionLocal() as db: core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); rows=await core.tickets(u.id)
    b=InlineKeyboardBuilder()
    for x in rows[:20]: b.button(text=f"⭐ Ticket #{x.id}",callback_data=f"support:rate_ticket:{x.id}")
    b.adjust(1); await c.message.edit_text("⭐ Baholash uchun ticket tanlang",reply_markup=b.as_markup()); await c.answer()

@router.callback_query(F.data.startswith("support:rate_ticket:"))
async def choose_rating(c:CallbackQuery,state:FSMContext):
    tid=int(c.data.split(":")[-1]); await state.update_data(ticket_id=tid); b=InlineKeyboardBuilder(); [b.button(text="⭐"*i,callback_data=f"rating:{i}") for i in range(1,6)]; b.adjust(1); await c.message.edit_text("⭐ Bahoni tanlang",reply_markup=b.as_markup()); await c.answer()

@router.callback_query(F.data.startswith("rating:"))
async def save_rating(c:CallbackQuery,state:FSMContext):
    score=int(c.data.split(":")[-1]); data=await state.get_data(); tid=data.get("ticket_id")
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); ticket=await core.ticket(tid,u.id) if tid else None
        if not ticket:return await c.answer("Ticket topilmadi",show_alert=True)
        await core.add_rating(u.id,tid,score)
    await state.clear(); await c.message.edit_text("✅ Bahoyingiz saqlandi. Rahmat!"); await c.answer()

@router.callback_query(F.data=="support:feedback")
async def feedback(c:CallbackQuery,state:FSMContext): await state.set_state(SupportState.feedback); await c.message.answer("📝 Feedback yozing:"); await c.answer()

@router.message(SupportState.feedback)
async def feedback_save(m:Message,state:FSMContext):
    async with SessionLocal() as db: core=CoreService(db,redis_service); u=await core.get_or_create_user(m.from_user); await core.add_feedback(u.id,"general",m.text or m.caption or "")
    await state.clear(); await m.answer("✅ Feedback qabul qilindi.")
