from fastapi import APIRouter, Request, HTTPException
from app.config import settings
from app.models.user import User
from app.models.comment import Comment
from app.models.post import Post
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.services.interest import log_signal, update_profile, get_profile
from app.services.freebie import check_and_deliver_freebie
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

                async def save_comment():
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

                        from app.services.ai_service import generate_reply, classify_comment, generate_dm_opener
                        from app.services.meta_api import post_comment_reply, send_private_reply

                        classification = await classify_comment(comment_text)
                        print(f"Classification: {classification}")

                        if classification.get("intent") == "noise":
                            return

                        await log_signal(
                            db,
                            str(user.id),
                            username,
                            classification.get("topic", "general"),
                            classification.get("intent"),
                            classification.get("weight", 0),
                        )

                        profile = await update_profile(db, str(user.id), username)
                        print(f"Interest profile: topic={profile.primary_topic}, score={profile.total_score}")

                        await check_and_deliver_freebie(
                            db,
                            str(user.id),
                            username,
                            comment_id
                        )

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

                        if classification.get("intent") in ["question", "price_check"]:
                            try:
                                dm_text = await generate_dm_opener(
                                    comment_text,
                                    classification.get("topic", "general")
                                )
                                await send_private_reply(comment_id, dm_text)
                                print(f"Private reply sent: {dm_text}")
                            except Exception as e:
                                print(f"Private reply failed: {e}")

                        try:
                            await db.commit()
                            print(f"Comment saved to DB: {comment_id}")
                        except Exception as e:
                            await db.rollback()
                            print(f"Skipping duplicate: {comment_id}")

                asyncio.create_task(save_comment())

    return {"status": "ok"}
