from __future__ import annotations
from html import escape
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Conversation
from app.services.core import CoreService
from app.services.redis_service import RedisService
from app.services.ai import AIService
from app.services.i18n import t
from app.utils.ui import ai_keyboard, back, chat_modes, esc

router=Router(); settings=get_settings(); redis_service=RedisService(); ai_service=AIService()

class AIState(StatesGroup):
    conversation=State()
    file=State()
    image=State()

async def render_ai_menu(target):
    user=target.from_user
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(user); plan=await core.effective_plan(u)
        ai_used=await redis_service.get_daily(u.id,"ai")
    body=(f"<b>🤖 AI WORKSPACE</b>\n\n"
          f"💎 Tarif: <b>{escape(plan.name)}</b>\n"
          f"⚡ AI usage: <b>{ai_used}/{plan.daily_ai}</b>\n\n"
          f"<i>Chat, voice, fayl, rasm va kreativ vositalar bitta oynada.</i>")
    if isinstance(target,Message): await target.answer(body,reply_markup=ai_keyboard(),parse_mode="HTML")
    else: await target.message.edit_text(body,reply_markup=ai_keyboard(),parse_mode="HTML")

@router.callback_query(F.data=="menu:ai")
async def menu_ai(c: CallbackQuery): await render_ai_menu(c); await c.answer()

@router.callback_query(F.data=="ai:new")
async def new_chat(c: CallbackQuery,state:FSMContext):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); conv=await core.new_conversation(u.id)
    await state.update_data(conversation_id=conv.id); await state.set_state(AIState.conversation)
    await c.message.edit_text("<b>💬 YANGI CHAT</b>\n\nSavolingizni yozing. <i>/stop</i> bilan chat rejimidan chiqishingiz mumkin.",parse_mode="HTML",reply_markup=back("menu:ai")); await c.answer()

@router.callback_query(F.data=="ai:history")
async def history(c: CallbackQuery):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); rows=await core.conversations(u.id)
    b=InlineKeyboardBuilder()
    for x in rows[:20]: b.button(text=f"💬 #{x.id} {x.title[:35]}",callback_data=f"ai:open:{x.id}")
    b.button(text="➕ Yangi chat",callback_data="ai:new"); b.button(text="⬅️ AI",callback_data="menu:ai"); b.adjust(1)
    body="<b>🗂 CHAT HISTORY</b>\n\n" + ("\n".join(f"💬 #{x.id} • {esc(x.title)}" for x in rows) if rows else "Hozircha chat yo‘q.")
    await c.message.edit_text(body,reply_markup=b.as_markup(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("ai:open:"))
async def open_chat(c: CallbackQuery,state:FSMContext):
    cid=int(c.data.split(":")[-1])
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(c.from_user); conv=await core.get_conversation(cid,u.id)
        msgs=await core.recent_messages(cid,12) if conv else []
    if not conv: return await c.answer("Chat topilmadi",show_alert=True)
    await state.update_data(conversation_id=cid); await state.set_state(AIState.conversation)
    text="<b>💬 CHAT #%s</b>\n\n%s"%(cid,"\n\n".join(f"<b>{escape(m.role)}</b>: {escape(m.content[:900])}" for m in msgs) or "Yangi chat.")
    await c.message.edit_text(text,parse_mode="HTML",reply_markup=back("ai:history")); await c.answer()

@router.message(AIState.conversation, F.text)
async def chat_message(m: Message,state:FSMContext):
    if (m.text or "").strip().lower()=="/stop": await state.clear(); return await m.answer("✅ Chat rejimi yopildi.")
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(m.from_user); data=await state.get_data(); cid=data.get("conversation_id")
        conv=await core.get_conversation(cid,u.id) if cid else await core.new_conversation(u.id)
        if not conv: conv=await core.new_conversation(u.id)
        ok,used,limit=await core.consume(u,"ai")
        if not ok: return await m.answer(t(u.language,"limit",feature="AI",used=used,limit=limit),parse_mode="HTML")
        await core.save_message(conv,"user",m.text)
        history=await core.recent_messages(conv.id,20)
        from app.db.models import KnowledgeItem
        knowledge_rows=list((await db.scalars(select(KnowledgeItem).where(KnowledgeItem.active.is_(True)).order_by(KnowledgeItem.priority.desc()).limit(10))).all())
        knowledge="\n\n".join(x.title+": "+x.content[:1200] for x in knowledge_rows)
    answer=await ai_service.chat([{"role":x.role,"content":x.content} for x in history],u.language or "uz",knowledge)
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); conv=await core.get_conversation(conv.id,u.id); 
        if conv: await core.save_message(conv,"assistant",answer)
    await m.answer(answer,parse_mode=None)

@router.callback_query(F.data=="ai:mode")
async def modes(c: CallbackQuery): await c.message.edit_text("<b>⚡ AI MODE</b>\n\nModel behaviorini tanlang:",reply_markup=chat_modes(),parse_mode="HTML"); await c.answer()

@router.callback_query(F.data.startswith("mode:"))
async def set_mode(c: CallbackQuery,state:FSMContext):
    mode=c.data.split(":",1)[1]; await state.update_data(mode=mode); await c.answer(f"✅ {mode}"); await render_ai_menu(c)

@router.callback_query(F.data=="ai:voice")
async def voice(c: CallbackQuery,state:FSMContext): await state.set_state(AIState.conversation); await c.message.answer("🎙 Voice yuboring. Men uni matnga aylantirib, AI bilan ishlayman."); await c.answer()

@router.message(AIState.conversation, F.voice)
async def voice_receive(m: Message,state:FSMContext):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(m.from_user); ok,used,limit=await core.consume(u,"voice")
    if not ok: return await m.answer(t(u.language,"limit",feature="Voice",used=used,limit=limit),parse_mode="HTML")
    file=await m.bot.get_file(m.voice.file_id); from io import BytesIO; buf=BytesIO(); await m.bot.download_file(file.file_path,buf); buf.seek(0)
    transcript=await ai_service.transcribe(buf,"voice.ogg")
    if not transcript: return await m.answer("⚠️ Voice provider sozlanmagan yoki transkripsiya ishlamadi.")
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(m.from_user); conv=await core.new_conversation(u.id,"Voice Chat"); await core.save_message(conv,"user",transcript,{"source":"voice"})
    answer=await ai_service.chat([{"role":"user","content":transcript}],u.language or "uz")
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); conv=await core.get_conversation(conv.id,u.id); await core.save_message(conv,"assistant",answer,{"source":"voice"})
    await m.answer(f"🎙 <b>Transkript:</b>\n{escape(transcript[:3000])}\n\n<b>🤖 AI:</b>\n{answer}",parse_mode="HTML")

@router.callback_query(F.data=="ai:file")
async def file_start(c: CallbackQuery,state:FSMContext): await state.set_state(AIState.file); await c.message.answer("📄 PDF, DOCX, TXT, CSV yoki XLSX fayl yuboring."); await c.answer()

@router.message(AIState.file, F.document)
async def file_receive(m: Message,state:FSMContext):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(m.from_user); plan=await core.effective_plan(u); ok,used,limit=await core.consume(u,"file")
    if not ok: return await m.answer(t(u.language,"limit",feature="File",used=used,limit=limit),parse_mode="HTML")
    if m.document.file_size and m.document.file_size > plan.max_file_mb*1024*1024: return await m.answer(f"❌ Maksimal hajm: {plan.max_file_mb} MB")
    f=await m.bot.get_file(m.document.file_id); from io import BytesIO; buf=BytesIO(); await m.bot.download_file(f.file_path,buf); data=buf.getvalue()
    result=await ai_service.summarize_file(m.document.file_name or "file",data,u.language or "uz")
    await state.clear(); await m.answer(result,parse_mode=None)

@router.callback_query(F.data=="ai:image")
async def image_start(c: CallbackQuery,state:FSMContext): await state.set_state(AIState.image); await c.message.answer("🖼 Rasm tavsifini yozing:"); await c.answer()

@router.message(AIState.image, F.text)
async def image_make(m: Message,state:FSMContext):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); u=await core.get_or_create_user(m.from_user); ok,used,limit=await core.consume(u,"image")
    if not ok: return await m.answer(t(u.language,"limit",feature="Image",used=used,limit=limit),parse_mode="HTML")
    url,data=await ai_service.generate_image(m.text)
    await state.clear()
    if data: await m.answer_photo(BufferedInputFile(data,filename="generated.png"),caption="🖼 Tayyor")
    elif url: await m.answer_photo(url,caption="🖼 Tayyor")
    else: await m.answer("⚠️ Image provider sozlanmagan.")
