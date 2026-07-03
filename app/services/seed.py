import json
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.freebie import Freebie

REPOS_SEED_PATH = Path(__file__).resolve().parent.parent.parent / "seed_data" / "repos_seed.json"


async def seed_repos(db: AsyncSession):
    if not REPOS_SEED_PATH.exists():
        print(f"repos_seed.json not found at {REPOS_SEED_PATH}, skipping repo seed")
        return

    with open(REPOS_SEED_PATH, encoding="utf-8") as f:
        repos = json.load(f)

    # Skip entirely if already seeded (checks for one known repo type marker)
    existing = await db.execute(
        select(Freebie).where(Freebie.type == "repo").limit(1)
    )
    if existing.scalar_one_or_none():
        print("Repos already seeded, skipping")
        return

    count = 0
    for r in repos:
        desc = (r.get("description") or "").strip()
        title = f"{r['name']} — {desc[:100]}" if desc else r["name"]
        freebie = Freebie(
            topic=r["category"],
            title=title,
            type="repo",
            file_url=r["url"],
            threshold=30,
            active=True,
        )
        db.add(freebie)
        count += 1

    await db.commit()
    print(f"Seeded {count} repos into freebies table")


async def seed_freebies(db: AsyncSession):
    # Old lifestyle-topic dummy freebies — no longer used now that
    # startnow_365 is a tech/dev-tools page. Kept only for reference;
    # call seed_repos() instead in main.py / startup.
    pass
