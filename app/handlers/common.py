from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Referral
from app.services.core import CoreService
from app.services.redis_service import RedisService
from app.services.i18n import t, normalize_lang
from app.utils.ui import language_keyboard, required_channels, main_keyboard, esc

router=Router(); settings=get_settings(); redis_service=RedisService()

async def subscription_ok(bot, user_id: int, channels) -> bool:
    for ch in channels:
        try:
            member=await bot.get_chat_member(ch.chat_id,user_id)
            if member.status in {"left","kicked","restricted"} and getattr(member,"is_member",False) is not True:
                return False
        except Exception:
            return False
    return True

async def start_flow(message: Message, ref: str|None=None):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); user=await core.get_or_create_user(message.from_user); channels=await core.channels()
        if ref and ref.startswith("ref_") and ref[4:].isdigit(): await core.add_referral(int(ref[4:]),user.id)
        lang=user.language
    if channels and not await subscription_ok(message.bot,message.from_user.id,channels):
        await message.answer(t(lang or "uz","subscribe"),reply_markup=required_channels(channels),parse_mode="HTML")
        return
    if not lang:
        await message.answer(t("uz","choose_language"),reply_markup=language_keyboard(),parse_mode="HTML")
    else:
        await message.answer(t(lang,"welcome"),reply_markup=main_keyboard(message.from_user.id in settings.admin_id_set, lang),parse_mode="HTML")

@router.message(CommandStart())
async def start(message: Message):
    args=(message.text or "").split(maxsplit=1)
    ref=args[1] if len(args)>1 else None
    await start_flow(message,ref)

@router.callback_query(F.data=="sub:check")
async def check_subscription(c: CallbackQuery):
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); user=await core.get_or_create_user(c.from_user); channels=await core.channels(); lang=user.language
    if not await subscription_ok(c.bot,c.from_user.id,channels):
        await c.answer(t(lang or "uz","not_subscribed"),show_alert=True); return
    await c.message.edit_text(t(lang or "uz","choose_language"),reply_markup=language_keyboard(),parse_mode="HTML") if not lang else await c.message.edit_text(t(lang,"welcome"),parse_mode="HTML")
    await c.message.answer(t(lang or "uz","welcome"),reply_markup=main_keyboard(c.from_user.id in settings.admin_id_set),parse_mode="HTML") if lang else c.answer()
    await c.answer()

@router.callback_query(F.data.startswith("lang:"))
async def language(c: CallbackQuery):
    lang=c.data.split(":",1)[1]
    async with SessionLocal() as db:
        core=CoreService(db,redis_service); await core.set_language(c.from_user.id,lang)
    await c.message.edit_text(t(lang,"welcome"),parse_mode="HTML")
    await c.message.answer("✅",reply_markup=main_keyboard(c.from_user.id in settings.admin_id_set, lang))
    await c.answer()

@router.message(F.text.in_({"🔄 Yangilash","🔄 Обновить","🔄 Refresh"}))
async def refresh(message: Message):
    await start_flow(message)

@router.message(F.text.in_({"🤖 AI Yordamchi","🤖 AI-Помощник","🤖 AI Assistant"}))
async def ai_menu(message: Message):
    from app.handlers.ai import render_ai_menu
    await render_ai_menu(message)

@router.message(F.text.in_({"💬 Support","💬 Поддержка"}))
async def support_menu(message: Message):
    from app.handlers.support import render_support_menu
    await render_support_menu(message)

@router.message(F.text.in_({"👤 Profil","👤 Профиль","👤 Profile"}))
async def profile_menu(message: Message):
    from app.handlers.profile import render_profile
    await render_profile(message)

@router.message(F.text.in_({"🛠 Admin Panel","🛠 Админ-панель"}))
async def admin_panel(message: Message):
    from app.handlers.admin import send_admin_panel
    await send_admin_panel(message)
