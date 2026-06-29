from fastapi import APIRouter
from app.database import engine, AsyncSessionLocal
import redis.asyncio as aioredis
from app.config import settings
from app.services.meta_api import get_posts
from app.services.sync import sync_posts, sync_comments
from app.services.seed import seed_freebies

router = APIRouter()

@router.get("/health")
async def health_check():
    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "app": "ok",
        "database": db_status,
        "redis": redis_status,
    }

@router.get("/test-meta")
async def test_meta():
    try:
        posts = await get_posts()
        return {
            "status": "ok",
            "post_count": len(posts.get("data", [])),
            "first_post": posts.get("data", [])[0] if posts.get("data") else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/test-sync")
async def test_sync():
    async with AsyncSessionLocal() as db:
        posts_saved = await sync_posts(db)
        comments_saved = await sync_comments(db)
        return {
            "posts_saved": posts_saved,
            "comments_saved": comments_saved
        }

@router.get("/seed-freebies")
async def seed_freebies_endpoint():
    async with AsyncSessionLocal() as db:
        await seed_freebies(db)
        return {"status": "ok", "message": "Freebies seeded"}
