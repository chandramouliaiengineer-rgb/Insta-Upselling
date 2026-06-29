from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.freebie import Freebie

DUMMY_FREEBIES = [
    {
        "topic": "mindset",
        "title": "5 Daily Habits for Mental Clarity",
        "type": "guide",
        "file_url": "https://drive.google.com/file/d/dummy-mindset-guide",
        "threshold": 30,
    },
    {
        "topic": "fitness",
        "title": "10 Minute Home Workout Guide",
        "type": "guide",
        "file_url": "https://drive.google.com/file/d/dummy-fitness-guide",
        "threshold": 30,
    },
    {
        "topic": "pricing",
        "title": "Beginner Investment Starter Guide",
        "type": "guide",
        "file_url": "https://drive.google.com/file/d/dummy-pricing-guide",
        "threshold": 25,
    },
    {
        "topic": "general",
        "title": "StartNow 365 Success Starter Kit",
        "type": "guide",
        "file_url": "https://drive.google.com/file/d/dummy-general-guide",
        "threshold": 30,
    },
    {
        "topic": "skincare",
        "title": "Morning Skincare Routine Guide",
        "type": "guide",
        "file_url": "https://drive.google.com/file/d/dummy-skincare-guide",
        "threshold": 30,
    },
]


async def seed_freebies(db: AsyncSession):
    for f in DUMMY_FREEBIES:
        existing = await db.execute(
            select(Freebie).where(Freebie.topic == f["topic"])
        )
        if existing.scalar_one_or_none():
            continue
        freebie = Freebie(**f)
        db.add(freebie)
    await db.commit()
    print("Freebies seeded successfully")
