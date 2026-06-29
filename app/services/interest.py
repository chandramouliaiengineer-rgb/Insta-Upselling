from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.interest import InterestSignal, InterestProfile
from datetime import datetime, timezone, timedelta


async def log_signal(
    db: AsyncSession,
    user_id: str,
    username: str,
    topic: str,
    intent: str,
    weight: int,
    source: str = "comment"
):
    if not topic or intent == "noise" or weight == 0:
        return

    signal = InterestSignal(
        user_id=user_id,
        username=username,
        topic=topic,
        intent=intent,
        weight=weight,
        source=source,
    )
    db.add(signal)
    await db.flush()


async def update_profile(db: AsyncSession, user_id: str, username: str):
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(InterestSignal).where(InterestSignal.user_id == user_id)
    )
    signals = result.scalars().all()

    topic_scores = {}
    total_score = 0.0
    price_check_count = 0

    for signal in signals:
        age = now - signal.created_at.replace(tzinfo=timezone.utc)

        if age.days < 7:
            decay = 1.0
        elif age.days < 30:
            decay = 0.5
        else:
            decay = 0.2

        weighted = signal.weight * decay
        topic = signal.topic or "general"

        if topic not in topic_scores:
            topic_scores[topic] = 0.0
        topic_scores[topic] += weighted
        total_score += weighted

        if signal.intent == "price_check":
            price_check_count += 1

    primary_topic = max(topic_scores, key=topic_scores.get) if topic_scores else None

    existing = await db.execute(
        select(InterestProfile).where(InterestProfile.user_id == user_id)
    )
    profile = existing.scalar_one_or_none()

    if profile:
        profile.primary_topic = primary_topic
        profile.topic_scores = topic_scores
        profile.total_score = total_score
        profile.price_check_count = price_check_count
        profile.last_updated = now
    else:
        profile = InterestProfile(
            user_id=user_id,
            username=username,
            primary_topic=primary_topic,
            topic_scores=topic_scores,
            total_score=total_score,
            price_check_count=price_check_count,
        )
        db.add(profile)

    await db.flush()
    return profile


async def get_profile(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(InterestProfile).where(InterestProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()
