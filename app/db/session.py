from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from app.config import get_settings
from app.db.models import Base

settings = get_settings()
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=5,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

SEEDS = [
    ("free", "FREE", 20, 3, 3, 1, 15, False, 0, "Free basic access"),
    ("comfort", "COMFORT", 100, 20, 20, 5, 25, False, 1, "Comfort plan"),
    ("pro", "PRO", 300, 50, 50, 15, 50, True, 2, "Professional plan"),
    ("premium", "PREMIUM", 1000, 200, 100, 50, 100, True, 3, "Premium plan"),
]

LESSONS = [
    ("prompt-foundations", "Prompt asoslari", "beginner", "Role, goal, context, constraints va output formatni bitta promptga yig‘ish usuli.", ["prompt","basics"]),
    ("prompt-clarity", "Aniq topshiriq yozish", "beginner", "Noaniq so‘rovni aniq, tekshiriladigan topshiriqqa aylantirish.", ["clarity","prompt"]),
    ("few-shot", "Misollar bilan boshqarish", "intermediate", "Input/output misollaridan foydalanib model javob formatini barqarorlashtirish.", ["few-shot","examples"]),
    ("structured-output", "Structured output", "intermediate", "Javoblarni schema, table, JSON yoki qat’iy formatga keltirish.", ["json","schema"]),
    ("prompt-evaluation", "Promptni baholash", "advanced", "Accuracy, completeness, relevance va consistency mezonlari orqali promptni test qilish.", ["evals","quality"]),
    ("ai-safety", "AI bilan mas’uliyatli ishlash", "advanced", "Maxfiy ma’lumotlarni bermaslik, model cheklovlarini tushunish va xavfsiz workflow qurish.", ["safety","privacy"]),
]

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for code,name,ai,voice,file,image,max_mb,priority,sort_order,note in SEEDS:
            await conn.execute(text("""
                INSERT INTO plans(code,name,daily_ai,daily_voice,daily_file,daily_image,max_file_mb,priority_support,sort_order,price_note,active)
                VALUES (:code,:name,:ai,:voice,:file,:image,:max_mb,:priority,:sort_order,:note,true)
                ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name, daily_ai=EXCLUDED.daily_ai, daily_voice=EXCLUDED.daily_voice,
                    daily_file=EXCLUDED.daily_file, daily_image=EXCLUDED.daily_image, max_file_mb=EXCLUDED.max_file_mb,
                    priority_support=EXCLUDED.priority_support, sort_order=EXCLUDED.sort_order, price_note=EXCLUDED.price_note
            """), {"code":code,"name":name,"ai":ai,"voice":voice,"file":file,"image":image,"max_mb":max_mb,"priority":priority,"sort_order":sort_order,"note":note})
        for slug,title,level,body,tags in LESSONS:
            await conn.execute(text("""
                INSERT INTO learning_lessons(slug,title,level,body,tags,active)
                VALUES (:slug,:title,:level,:body,:tags,true)
                ON CONFLICT (slug) DO UPDATE SET title=EXCLUDED.title, level=EXCLUDED.level, body=EXCLUDED.body, tags=EXCLUDED.tags
            """), {"slug":slug,"title":title,"level":level,"body":body,"tags":tags})

async def close_db() -> None:
    await engine.dispose()
