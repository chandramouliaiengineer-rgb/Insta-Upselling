import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.post import Post
from app.models.comment import Comment
from app.models.user import User
from app.services.meta_api import get_posts, get_comments
from datetime import datetime, timezone

async def sync_posts(db: AsyncSession):
    saved = 0
    url = f"https://graph.facebook.com/v22.0/{settings.META_INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,permalink,timestamp,media_type",
        "access_token": settings.META_PAGE_ACCESS_TOKEN,
        "limit": 50
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            for p in data.get("data", []):
                existing = await db.execute(
                    select(Post).where(Post.instagram_post_id == p["id"])
                )
                if existing.scalar_one_or_none():
                    continue
                post = Post(
                    instagram_post_id=p["id"],
                    caption=p.get("caption"),
                    permalink=p.get("permalink"),
                    media_type=p.get("media_type"),
                    posted_at=datetime.fromisoformat(
                        p["timestamp"].replace("Z", "+00:00")
                    ) if p.get("timestamp") else None,
                )
                db.add(post)
                saved += 1

            await db.commit()
            next_page = data.get("paging", {}).get("next")
            url = next_page
            params = {}

    return saved

async def sync_comments(db: AsyncSession):
    result = await db.execute(select(Post))
    posts = result.scalars().all()
    saved = 0

    for post in posts:
        data = await get_comments(post.instagram_post_id)
        comments = data.get("data", [])

        for c in comments:
            existing = await db.execute(
                select(Comment).where(
                    Comment.instagram_comment_id == c["id"]
                )
            )
            if existing.scalar_one_or_none():
                continue

            # get or create user
            user_result = await db.execute(
                select(User).where(User.username == c.get("username", ""))
            )
            user = user_result.scalar_one_or_none()
            if not user:
                user = User(
                    instagram_user_id=c["id"],
                    username=c.get("username", "unknown"),
                )
                db.add(user)
                await db.flush()

            comment = Comment(
                instagram_comment_id=c["id"],
                post_id=post.id,
                user_id=user.id,
                text=c.get("text", ""),
                username=c.get("username", ""),
                timestamp=datetime.fromisoformat(
                    c["timestamp"].replace("Z", "+00:00")
                ) if c.get("timestamp") else None,
            )
            db.add(comment)
            saved += 1

    await db.commit()
    return saved
