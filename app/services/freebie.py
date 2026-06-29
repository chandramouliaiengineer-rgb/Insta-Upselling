from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.freebie import Freebie, DeliveredFreebie
from app.models.interest import InterestProfile, InterestSignal
from app.services.meta_api import send_private_reply


async def check_and_deliver_freebie(
    db: AsyncSession,
    user_id: str,
    username: str,
    comment_id: str
):
    # Get user's interest profile
    profile_result = await db.execute(
        select(InterestProfile).where(InterestProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile:
        return

    # Check score threshold
    if profile.total_score < 30:
        print(f"Score {profile.total_score} below threshold for {username}")
        return

    # Check at least one question or price_check signal exists
    signal_result = await db.execute(
        select(InterestSignal).where(
            InterestSignal.user_id == user_id,
            InterestSignal.intent.in_(["question", "price_check"])
        )
    )
    qualifying_signals = signal_result.scalars().all()

    if not qualifying_signals:
        print(f"No qualifying signals for {username}")
        return

    topic = profile.primary_topic or "general"

    # Check if freebie already delivered for this topic
    delivered_result = await db.execute(
        select(DeliveredFreebie).where(
            DeliveredFreebie.user_id == user_id,
            DeliveredFreebie.topic == topic
        )
    )
    if delivered_result.scalar_one_or_none():
        print(f"Freebie already delivered to {username} for topic {topic}")
        return

    # Find matching freebie
    freebie_result = await db.execute(
        select(Freebie).where(
            Freebie.topic == topic,
            Freebie.active == True
        )
    )
    freebie = freebie_result.scalar_one_or_none()

    if not freebie:
        # Fall back to general freebie
        freebie_result = await db.execute(
            select(Freebie).where(
                Freebie.topic == "general",
                Freebie.active == True
            )
        )
        freebie = freebie_result.scalar_one_or_none()

    if not freebie:
        print(f"No freebie found for topic {topic}")
        return

    # Send freebie via DM
    message = f"Hey! Based on your interest in {topic}, I thought this free resource would genuinely help you: {freebie.title} 🎁\n\nGet it here: {freebie.file_url}\n\nHope it helps! 🙌"

    try:
        await send_private_reply(comment_id, message)
        print(f"Freebie sent to {username}: {freebie.title}")

        # Log delivery
        delivery = DeliveredFreebie(
            user_id=user_id,
            freebie_id=freebie.id,
            username=username,
            topic=topic,
        )
        db.add(delivery)
        await db.flush()
        print(f"Freebie delivery logged for {username}")

    except Exception as e:
        print(f"Freebie delivery failed for {username}: {e}")
