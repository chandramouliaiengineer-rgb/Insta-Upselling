from fastapi import APIRouter, Request, HTTPException
from app.config import settings
from app.models.user import User
from app.models.comment import Comment
from app.models.post import Post
from app.models.freebie import DeliveredFreebie
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.services.interest import log_signal, update_profile, get_profile
from app.services.freebie import deliver_repo_reply
import hmac
import hashlib
import json
import asyncio

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.META_WEBHOOK_VERIFY_TOKEN:
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def receive_webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                value = change.get("value", {})
                comment_id = value.get("id")
                comment_text = value.get("text")
                username = value.get("from", {}).get("username")
                user_igsid = value.get("from", {}).get("id")
                post_id = value.get("media", {}).get("id")

                print(f"New comment from {username}: {comment_text}")

                async def save_comment(
                    comment_id=comment_id,
                    comment_text=comment_text,
                    username=username,
                    user_igsid=user_igsid,
                    post_id=post_id,
                ):
                    async with AsyncSessionLocal() as db:
                        if username == "startnow_365":
                            return

                        result = await db.execute(
                            select(User).where(User.username == username)
                        )
                        user = result.scalar_one_or_none()
                        if not user:
                            user = User(
                                instagram_user_id=user_igsid,
                                username=username,
                            )
                            db.add(user)
                            await db.flush()

                        post_result = await db.execute(
                            select(Post).where(Post.instagram_post_id == post_id)
                        )
                        post = post_result.scalar_one_or_none()

                        existing = await db.execute(
                            select(Comment).where(
                                Comment.instagram_comment_id == comment_id
                            )
                        )
                        if existing.scalar_one_or_none():
                            return

                        from app.services.ai_service import generate_reply, classify_comment
                        from app.services.meta_api import post_comment_reply, send_private_reply, send_button_message

                        classification = await classify_comment(comment_text)
                        topic = classification.get("topic", "general")
                        print(f"Classification: {classification}")

                        await log_signal(
                            db, str(user.id), username, topic,
                            "question", 10,
                        )

                        profile = await update_profile(db, str(user.id), username)
                        print(f"Interest profile: topic={profile.primary_topic}, score={profile.total_score}")

                        comment = Comment(
                            instagram_comment_id=comment_id,
                            post_id=post.id if post else None,
                            user_id=user.id,
                            text=comment_text,
                            username=username,
                        )
                        db.add(comment)

                        post_caption = post.caption if post else ""
                        reply_text = await generate_reply(comment_text, post_caption)
                        print(f"Generated reply: {reply_text}")

                        try:
                            await post_comment_reply(comment_id, reply_text)
                            comment.replied = True
                            comment.our_reply_text = reply_text
                            print("Reply posted successfully")
                        except Exception as e:
                            print(f"Failed to post reply: {e}")

                        topic_label = topic.replace("_", " ")
                        opener_text = f"Hey! I saw your comment about {topic_label} 👋"

                        try:
                            dm_response = await send_private_reply(comment_id, opener_text)
                            print(f"Private reply sent: {opener_text}")

                            recipient_id = dm_response.get("recipient_id")
                            if recipient_id:
                                user.messaging_psid = recipient_id
                                print(f"Captured messaging_psid: {recipient_id}")

                            if recipient_id:
                                await send_button_message(
                                    recipient_id,
                                    "I've got a great open-source repo that might help — want me to send it over?",
                                    [{"title": "Send me the repo", "payload": "GET_REPO"}]
                                )
                                print("Button message sent")
                        except Exception as e:
                            print(f"DM/button flow failed: {e}")

                        try:
                            await db.commit()
                            print(f"Comment saved to DB: {comment_id}")
                        except Exception as e:
                            await db.rollback()
                            print(f"Skipping duplicate: {comment_id}")

                asyncio.create_task(save_comment())

        for msg_event in entry.get("messaging", []):
            postback = msg_event.get("postback")
            sender_id = msg_event.get("sender", {}).get("id")

            if postback:
                payload_str = postback.get("payload")
                print(f"Button tapped by {sender_id}: {payload_str}")

                async def handle_postback(sender_id=sender_id, payload_str=payload_str):
                    from app.services.meta_api import send_dm_message

                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(User).where(
                                (User.messaging_psid == sender_id) |
                                (User.instagram_user_id == sender_id)
                            )
                        )
                        user = result.scalar_one_or_none()

                        if not user:
                            print(f"Postback from unknown user {sender_id}, ignoring")
                            return

                        profile = await get_profile(db, str(user.id))
                        topic = profile.primary_topic if profile and profile.primary_topic else "general"

                        comment_result = await db.execute(
                            select(Comment)
                            .where(Comment.user_id == user.id)
                            .order_by(Comment.created_at.desc())
                            .limit(1)
                        )
                        last_comment = comment_result.scalars().first()
                        match_text = last_comment.text if last_comment else ""

                        if payload_str == "GET_REPO":
                            await deliver_repo_reply(
                                db, str(user.id), user.username,
                                topic, sender_id, match_text
                            )
                        else:
                            await send_dm_message(sender_id, "Got it! Let me know if you'd like a repo recommendation.")

                asyncio.create_task(handle_postback())
                continue

            message_obj = msg_event.get("message", {})
            if message_obj.get("is_echo"):
                continue

            message_text = message_obj.get("text")
            if not sender_id or not message_text:
                continue

            async def handle_dm_reply(sender_id=sender_id, message_text=message_text):
                from app.services.meta_api import send_dm_message

                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(User).where(
                            (User.messaging_psid == sender_id) |
                            (User.instagram_user_id == sender_id)
                        )
                    )
                    user = result.scalar_one_or_none()

                    if not user:
                        user = User(instagram_user_id=sender_id, messaging_psid=sender_id, username=f"ig_{sender_id}")
                        db.add(user)
                        await db.flush()
                        try:
                            await db.commit()
                        except Exception:
                            await db.rollback()

                    print(f"DM (typed, not button) from {user.username}: {message_text}")

                    profile = await get_profile(db, str(user.id))
                    topic = profile.primary_topic if profile and profile.primary_topic else "general"

                    delivered_result = await db.execute(
                        select(DeliveredFreebie).where(
                            DeliveredFreebie.user_id == str(user.id),
                            DeliveredFreebie.topic == topic
                        )
                    )
                    if delivered_result.scalar_one_or_none():
                        await send_dm_message(
                            sender_id,
                            "You're all set with that one already! Let me know if you're looking for something else 🙌"
                        )
                        return

                    await deliver_repo_reply(
                        db, str(user.id), user.username,
                        topic, sender_id, message_text
                    )

            asyncio.create_task(handle_dm_reply())

    return {"status": "ok"}
