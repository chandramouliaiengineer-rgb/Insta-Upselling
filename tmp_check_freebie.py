import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.interest import log_signal, update_profile
from app.services.freebie import check_and_deliver_freebie


async def main():
    async with AsyncSessionLocal() as db:
        username = 'tester_probe_001'
        user = User(instagram_user_id='tester_probe_001', username=username)
        db.add(user)
        await db.flush()
        for _ in range(3):
            await log_signal(db, str(user.id), username, 'mindset', 'question', 10)
        profile = await update_profile(db, str(user.id), username)
        print(f'profile topic={profile.primary_topic} score={profile.total_score}')
        await check_and_deliver_freebie(db, str(user.id), username, 'dummy-comment-id')
        await db.rollback()


asyncio.run(main())
