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
            InterestSignal.intent.in_(['question', 'price_check'])
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

    # Find matching freebie — CHANGED: .limit(1) + .scalars().first()
    # since a topic can now have ~90 repos, not just one guide
    freebie_result = await db.execute(
        select(Freebie)
        .where(Freebie.topic == topic, Freebie.active == True)
        .order_by(Freebie.created_at.asc())
        .limit(1)
    )
    freebie = freebie_result.scalars().first()

    if not freebie:
        # Fall back to general freebie
        freebie_result = await db.execute(
            select(Freebie)
            .where(Freebie.topic == "general", Freebie.active == True)
            .order_by(Freebie.created_at.asc())
            .limit(1)
        )
        freebie = freebie_result.scalars().first()

    if not freebie:
        print(f"No freebie found for topic {topic}")
        return

    # Send freebie via DM
    message = f"Hey! Based on your interest in {topic}, thought this would genuinely help you: {freebie.title} 🎁\n\nCheck it out: {freebie.file_url}\n\nHope it's useful! 🙌"

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


async def deliver_repo_reply(
    db: AsyncSession,
    user_id: str,
    username: str,
    topic: str,
    recipient_id: str,
    message_text: str = ""
):
    from app.services.meta_api import send_dm_message
    from app.services.ai_service import match_best_repo

    # Don't send twice for the same topic
    delivered_result = await db.execute(
        select(DeliveredFreebie).where(
            DeliveredFreebie.user_id == user_id,
            DeliveredFreebie.topic == topic
        )
    )
    if delivered_result.scalar_one_or_none():
        print(f"Already delivered a repo to {username} for topic {topic}, skipping")
        return

    # Get all candidate repos in this topic
    candidates_result = await db.execute(
        select(Freebie)
        .where(Freebie.topic == topic, Freebie.active == True)
        .order_by(Freebie.created_at.asc())
    )
    all_repos = candidates_result.scalars().all()

    if not all_repos:
        candidates_result = await db.execute(
            select(Freebie)
            .where(Freebie.topic == "general", Freebie.active == True)
            .order_by(Freebie.created_at.asc())
        )
        all_repos = candidates_result.scalars().all()

    if not all_repos:
        print(f"No freebie found for topic {topic}, cannot reply to {username}")
        return

    freebie = None
    if message_text:
        candidates = [
            {"num": i + 1, "id": str(r.id), "title": r.title}
            for i, r in enumerate(all_repos)
        ]
        matched_id = await match_best_repo(message_text, candidates)
        if matched_id:
            freebie = next((r for r in all_repos if str(r.id) == matched_id), None)

    if not freebie:
        freebie = all_repos[0]  # fallback: highest-starred in topic

    message = (
        f"Here's the one that matches what you're looking for 🙌\n\n"
        f"{freebie.title}\n{freebie.file_url}\n\n"
        f"Hope it helps — let me know if you want something more specific!"
    )

    try:
        await send_dm_message(recipient_id, message)
        delivery = DeliveredFreebie(
            user_id=user_id,
            freebie_id=freebie.id,
            username=username,
            topic=topic,
        )
        db.add(delivery)
        await db.flush()
        await db.commit()
        print(f"Repo delivered via DM reply to {username}: {freebie.title}")
    except Exception as e:
        print(f"Failed to deliver repo via DM to {username}: {e}")
