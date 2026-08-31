import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update
import redis.asyncio as redis
from app.config import get_settings
from app.db.session import init_db, close_db
from app.services.redis_service import RedisService
from app.handlers.common import router as common_router
from app.handlers.ai import router as ai_router
from app.handlers.support import router as support_router
from app.handlers.profile import router as profile_router
from app.handlers.admin import router as admin_router

settings=get_settings(); logging.basicConfig(level=getattr(logging,settings.log_level.upper(),logging.INFO))
redis_client=redis.from_url(settings.redis_url,decode_responses=True)
storage=RedisStorage(redis_client)
bot=Bot(token=settings.bot_token,default=DefaultBotProperties(parse_mode="HTML"))
dp=Dispatcher(storage=storage)
dp.include_router(common_router); dp.include_router(ai_router); dp.include_router(support_router); dp.include_router(profile_router); dp.include_router(admin_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.public_base_url:
        url=settings.public_base_url.rstrip("/")+settings.webhook_path
        await bot.set_webhook(url,allowed_updates=dp.resolve_used_update_types())
        logging.info("Webhook configured: %s",url)
    yield
    try: await bot.delete_webhook(drop_pending_updates=False)
    except Exception: logging.exception("webhook cleanup failed")
    await storage.close(); await bot.session.close(); await close_db()

app=FastAPI(title="AI Supporter V999",version="999.0.0",lifespan=lifespan)

@app.get("/")
async def root(): return {"name":"AI Supporter","version":"v999","status":"ok"}

@app.get("/health")
async def health(): return {"status":"ok","service":"ai-supporter"}

@app.post(settings.webhook_path)
async def telegram_webhook(request: Request):
    try:
        data=await request.json(); update=Update.model_validate(data); await dp.feed_update(bot,update); return JSONResponse({"ok":True})
    except Exception:
        logging.exception("telegram update failed")
        return JSONResponse({"ok":False},status_code=500)
