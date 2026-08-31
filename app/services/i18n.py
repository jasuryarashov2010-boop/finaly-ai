TEXTS = {
    "uz": {
        "choose_language": "🌐 <b>Tilni tanlang</b>\n\nQuyidagi tillardan birini tanlang:",
        "subscribe": "📢 <b>Botdan foydalanish uchun kanallarga obuna bo‘ling</b>\n\nObuna bo‘lgach <b>✅ Tekshirish</b> tugmasini bosing.",
        "not_subscribed": "❌ Hali barcha kanallarga obuna bo‘lmagansiz.",
        "welcome": "✨ <b>AI SUPPORTER</b>\n\nSizning shaxsiy AI yordamchingiz. Chat, voice, fayl, rasm, support va boshqa imkoniyatlar bitta joyda.",
        "ai": "🤖 <b>AI YORDAMCHI</b>",
        "support": "💬 <b>SUPPORT MARKAZI</b>",
        "profile": "👤 <b>PROFIL</b>",
        "referral": "🔗 <b>REFERRAL</b>\n\nTaklif havolangiz:\n<code>{link}</code>\n\n👥 Takliflar: <b>{count}</b>",
        "limit": "⚡ <b>Kunlik limit</b>\n{feature}: <b>{used}/{limit}</b>\n\n💎 Tarifni oshirsangiz limit kengayadi.",
    },
    "ru": {
        "choose_language": "🌐 <b>Выберите язык</b>",
        "subscribe": "📢 <b>Подпишитесь на обязательные каналы</b>\n\nПосле подписки нажмите <b>✅ Проверить</b>.",
        "not_subscribed": "❌ Вы подписались не на все каналы.",
        "welcome": "✨ <b>AI SUPPORTER</b>\n\nВаш персональный AI-помощник: чат, voice, файлы, изображения и support.",
        "ai": "🤖 <b>AI-ПОМОЩНИК</b>",
        "support": "💬 <b>ЦЕНТР ПОДДЕРЖКИ</b>",
        "profile": "👤 <b>ПРОФИЛЬ</b>",
        "referral": "🔗 <b>РЕФЕРАЛ</b>\n\nВаша ссылка:\n<code>{link}</code>\n\n👥 Приглашено: <b>{count}</b>",
        "limit": "⚡ <b>Дневной лимит</b>\n{feature}: <b>{used}/{limit}</b>",
    },
    "en": {
        "choose_language": "🌐 <b>Choose your language</b>",
        "subscribe": "📢 <b>Subscribe to the required channels</b>\n\nAfter subscribing press <b>✅ Check</b>.",
        "not_subscribed": "❌ You have not subscribed to all required channels.",
        "welcome": "✨ <b>AI SUPPORTER</b>\n\nYour personal AI assistant for chat, voice, files, images and support.",
        "ai": "🤖 <b>AI ASSISTANT</b>",
        "support": "💬 <b>SUPPORT CENTER</b>",
        "profile": "👤 <b>PROFILE</b>",
        "referral": "🔗 <b>REFERRAL</b>\n\nYour link:\n<code>{link}</code>\n\n👥 Invited: <b>{count}</b>",
        "limit": "⚡ <b>Daily limit</b>\n{feature}: <b>{used}/{limit}</b>",
    },
}

def normalize_lang(lang: str | None) -> str:
    return lang if lang in TEXTS else "uz"

def t(lang: str | None, key: str, **kwargs) -> str:
    data = TEXTS.get(normalize_lang(lang), TEXTS["uz"])
    return data.get(key, key).format(**kwargs)
