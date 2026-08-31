from html import escape
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def esc(value) -> str:
    return escape(str(value or ""))


def main_keyboard(is_admin: bool, lang: str = "uz") -> ReplyKeyboardMarkup:
    labels = {
        "uz": {"ai":"🤖 AI Yordamchi","support":"💬 Support","profile":"👤 Profil","refresh":"🔄 Yangilash","admin":"🛠 Admin Panel"},
        "ru": {"ai":"🤖 AI-Помощник","support":"💬 Поддержка","profile":"👤 Профиль","refresh":"🔄 Обновить","admin":"🛠 Админ-панель"},
        "en": {"ai":"🤖 AI Assistant","support":"💬 Support","profile":"👤 Profile","refresh":"🔄 Refresh","admin":"🛠 Admin Panel"},
    }.get(lang, {})
    rows = [[KeyboardButton(text=labels["ai"]), KeyboardButton(text=labels["support"])],
            [KeyboardButton(text=labels["profile"])],
            [KeyboardButton(text=labels["refresh"])]]
    if is_admin:
        rows[-1].append(KeyboardButton(text=labels["admin"]))
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def language_keyboard() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    b.button(text="🇺🇿 O‘zbek",callback_data="lang:uz")
    b.button(text="🇷🇺 Русский",callback_data="lang:ru")
    b.button(text="🇬🇧 English",callback_data="lang:en")
    b.adjust(1)
    return b.as_markup()


def required_channels(channels) -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    for ch in channels:
        label=f"📢 {ch.title[:36]}"
        url=ch.invite_url or (f"https://t.me/{ch.username.lstrip('@')}" if ch.username else None)
        if url: b.button(text=label,url=url)
    b.button(text="✅ Obunani tekshirish",callback_data="sub:check")
    b.adjust(1)
    return b.as_markup()


def ai_keyboard() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    for text,data in [("💬 Chat","ai:new"),("🎙 Voice","ai:voice"),("📄 Fayl tahlili","ai:file"),("🖼 Rasm yaratish","ai:image"),("🗂 Chatlarim","ai:history"),("⚡ AI Mode","ai:mode")]:
        b.button(text=text,callback_data=data)
    b.adjust(2,2,2)
    return b.as_markup()


def chat_modes() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    for text,data in [("⚡ Auto","mode:auto"),("🏎 Fast","mode:fast"),("🎯 Accurate","mode:accurate"),("🧠 Deep","mode:deep")]:b.button(text=text,callback_data=data)
    b.adjust(2)
    return b.as_markup()


def back(data="home") -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder(); b.button(text="⬅️ Orqaga",callback_data=data); return b.as_markup()


def support_keyboard() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    for text,data in [("💬 Yangi murojaat","support:new"),("🎫 Mening ticketlarim","support:list"),("⭐ Baholash","support:rate"),("📝 Feedback","support:feedback")]:b.button(text=text,callback_data=data)
    b.adjust(2,2)
    return b.as_markup()


def ticket_categories() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    cats=[("💳 To‘lov","payment"),("🤖 AI","ai"),("👤 Account","account"),("💎 Tarif","plan"),("🐞 Texnik","technical"),("❓ Boshqa","other")]
    for text,data in cats:b.button(text=text,callback_data=f"ticket:cat:{data}")
    b.adjust(2,2,2); return b.as_markup()


def profile_keyboard() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    for text,data in [("📊 Statistika","profile:stats"),("💎 Tarifim","profile:plans"),("🔗 Referral","profile:referral"),("💬 Chatlarim","ai:history"),("🎫 Ticketlarim","support:list"),("🔔 Bildirishnomalar","profile:notifications"),("⚙️ Sozlamalar","profile:settings")]:b.button(text=text,callback_data=data)
    b.adjust(2,2,2,1); return b.as_markup()


def admin_keyboard() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    items=[("📊 Dashboard","adm:dashboard"),("👥 Users","adm:users"),("🎫 Tickets","adm:tickets"),("👨‍💻 Operators","adm:operators"),("💎 Plans","adm:plans"),("📢 Channels","adm:channels"),("🤖 AI Center","adm:ai"),("🧠 Knowledge","adm:kb"),("🧑‍🏫 AI Learning","adm:learning"),("📢 Broadcast","adm:broadcast"),("⭐ Quality","adm:quality"),("📈 Analytics","adm:analytics"),("📜 Logs","adm:logs"),("🩺 Health","adm:health")]
    for text,data in items:b.button(text=text,callback_data=data)
    b.adjust(2,2,2,2,2,2,2)
    return b.as_markup()


def learning_keyboard() -> InlineKeyboardMarkup:
    b=InlineKeyboardBuilder()
    for text,data in [("💬 AI Coach","learn:coach"),("✨ Prompt Builder","learn:build"),("🔧 Improve Prompt","learn:improve"),("🔍 Analyze Prompt","learn:analyze"),("📝 Generate Post","learn:post"),("📚 Lessons","learn:lessons"),("📋 My Prompt Library","learn:library")]:b.button(text=text,callback_data=data)
    b.adjust(2,2,2,1); return b.as_markup()
