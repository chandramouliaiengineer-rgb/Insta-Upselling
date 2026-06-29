from fastapi import FastAPI
from app.config import settings
from app.routers import health, webhook
from app.models import User, Post, Comment

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(webhook.router, prefix="/api", tags=["webhook"])

@app.get("/")
async def root():
    return {"message": "Instagram Upsell API is running"}
