# Instagram Upsell Automation — startnow_365

A production-grade Instagram comment automation system that monitors posts, replies to comments using AI, tracks user interest, delivers freebies, and upsells products — all running on your own server with your own database.

---

## What this system does

When someone comments on any startnow_365 Instagram post, the system:

1. Detects the comment in real time via Meta webhook
2. Classifies the comment by topic and intent using AI
3. Generates a warm, relevant reply and posts it under the comment
4. Tracks the user's interest score across all their comments over time
5. When score crosses the threshold — sends a relevant freebie via private DM
6. (Coming soon) Introduces products naturally based on user's primary interest

---

## Tech stack

Layer | Technology
--- | ---
Backend | Python 3.11 + FastAPI
Database | PostgreSQL with pgvector
Cache | Redis
AI | OpenAI GPT-4o-mini
Instagram API | Meta Graph API v22.0
Infrastructure | Docker + Docker Compose
Tunnel (dev) | ngrok

---

## Project structure

```
instagram-upsell/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment variables
│   ├── database.py          # SQLAlchemy async engine
│   ├── models/
│   │   ├── user.py          # Instagram users
│   │   ├── post.py          # Instagram posts
│   │   ├── comment.py       # Comments + replies
│   │   ├── interest.py      # Interest signals + profiles
│   │   └── freebie.py       # Freebies + delivery log
│   ├── routers/
│   │   ├── webhook.py       # Meta webhook handler
│   │   └── health.py        # Health check + test endpoints
│   ├── services/
│   │   ├── meta_api.py      # All Graph API calls
│   │   ├── ai_service.py    # OpenAI classification + reply generation
│   │   ├── interest.py      # Interest scoring engine
│   │   ├── freebie.py       # Freebie matching + delivery
│   │   ├── sync.py          # Sync posts and comments from Instagram
│   │   └── seed.py          # Seed dummy freebies
│   └── static/
│       └── freebies/        # Dummy freebie files (replace with real ones)
├── alembic/                 # Database migrations
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

---

## Database tables

Table | Purpose
--- | ---
users | Instagram users who commented
posts | Your Instagram posts (synced from API)
comments | All comments with reply status
interest_signals | One row per classified comment signal
interest_profiles | Running interest score per user
freebies | Freebie catalog with topic matching
delivered_freebies | Delivery log — prevents duplicate sends

---

## How the interest scoring works

Every comment is classified by AI into:

- **Topic** — mindset, fitness, skincare, pricing, general
- **Intent** — question, praise, price_check, objection, noise
- **Weight** — price_check=25, question=10, objection=8, praise=3, noise=0

Scores decay over time:

- Under 7 days old → full weight
- 7-30 days old → 50% weight
- Over 30 days → 20% weight

A user gets a freebie when:

1. Total score reaches 30
2. At least one comment was a question or price_check
3. They haven't received a freebie for that topic before

---

## How to run locally

**Prerequisites:** Docker Desktop, ngrok

**Start the system:**

```bash
docker compose up --build
```

**Run ngrok tunnel:**

```powershell
.\ngrok.exe http 8001
```

**Register webhook in Meta dashboard:**

- Callback URL: `https://your-ngrok-url.ngrok-free.app/api/webhook`
- Verify token: `startnow123`

**Sync existing posts and comments:**

```text
GET http://localhost:8001/api/test-sync
```

**Seed dummy freebies:**

```text
GET http://localhost:8001/api/seed-freebies
```

**Health check:**

```text
GET http://localhost:8001/api/health
```

---

## Environment variables

```text
# App
APP_NAME=instagram-upsell
APP_ENV=development
DEBUG=true
SECRET_KEY=changethislater123

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=instagram_upsell
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@postgres:5432/instagram_upsell

# Redis
REDIS_URL=redis://redis:6379/0

# Meta
META_APP_ID=1483202316832109
META_APP_SECRET=your_app_secret
META_PAGE_ACCESS_TOKEN=EAA...your_page_token
META_INSTAGRAM_USER_TOKEN=IGAAX...your_instagram_token
META_INSTAGRAM_ACCOUNT_ID=17841467613773406
META_FACEBOOK_PAGE_ID=61560793026593
META_WEBHOOK_VERIFY_TOKEN=startnow123
META_FB_PAGE_TOKEN=EAA...your_fb_page_token

# OpenAI
OPENAI_API_KEY=your_openai_key

# Telegram (Phase 8)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## Current status — what is working

Feature | Status
--- | ---
Live comment detection via webhook | ✅ Working
AI topic and intent classification | ✅ Working
Auto-reply to comments publicly | ✅ Working
Interest signals logged per comment | ✅ Working
Interest profile built per user | ✅ Working
Freebie threshold check | ✅ Working
Freebie matching by topic | ✅ Working
Private reply DM delivery | ⏳ Pending App Review approval
Meta Business Verification | ✅ Verified
App mode | ✅ Live
App Review submitted | ⏳ Under review (up to 20 days)

---

## What happens when App Review approves

Zero code changes needed. These features activate automatically:

- **Private reply DM** to any user who comments (not just testers)
- **Freebie delivery** via DM when user crosses interest threshold
- **Comment to DM escalation** after X meaningful interactions

---

## Future stages — what to build next

### Stage 1 — Real freebies (when App Review approves)

Replace dummy freebie files with real content:

1. Create actual PDF guides for each topic:
   - mindset: daily habits guide
   - fitness: workout guide
   - skincare: skincare routine
   - pricing: investment starter guide
   - general: startnow_365 starter kit
2. Upload to Google Drive or S3 and get shareable links
3. Update the freebies table with real URLs:

```sql
UPDATE freebies SET file_url = 'real_url_here' WHERE topic = 'mindset';
```

### Stage 2 — Real products (upsell engine)

Add products table and upsell logic:

1. Create products table with name, topic, price, payment URL
2. After freebie is delivered, wait 24-48 hours
3. If user continues engaging → send soft product mention tied to same topic
4. If user shows price_check intent → send direct offer with payment link

### Stage 3 — DM conversation engine

Build multi-turn memory for DM conversations:

1. When user replies to a freebie DM → continue the conversation
2. Use conversation history to answer follow-up questions
3. Gradually introduce products based on conversation context
4. Track conversation state: new → freebie_sent → offer_sent → converted

### Stage 4 — Sales team alerts (Telegram)

When a user shows high buying intent:

1. Price check comment detected → instant Telegram alert to sales team
2. Alert contains: username, comment text, interest score, post link
3. Sales team manually follows up to close the deal

### Stage 5 — Analytics dashboard

Build a simple dashboard showing:

- Comments received per day
- Top topics across all users
- Freebie delivery rate
- Conversion funnel: comment → freebie → product → sale
- Revenue attributed to Instagram automation

### Stage 6 — Production deployment

Deploy to a VPS for 24/7 uptime:

1. Get a VPS (DigitalOcean, Hetzner — minimum 2GB RAM)
2. Install Docker on VPS
3. Copy docker-compose.yml to VPS
4. Set up Nginx with SSL via Let's Encrypt
5. Register production HTTPS URL as Meta webhook
6. Set up automatic token refresh every 50 days

---

## Important notes

**Token expiry:** The EAA Page Access Token expires every 60 days. Regenerate from Graph API Explorer → StartNow_365 Automation → StartNow 365 page → Generate Access Token. Update `META_PAGE_ACCESS_TOKEN` in `.env` and restart Docker.

**Rate limits:** Instagram API allows 200 calls per hour per account. The sync service fetches all posts and their comments — run it sparingly, not continuously.

**Webhook URL changes:** Every time ngrok restarts it gives a new URL. Update the webhook callback URL in Meta developer portal each time. For production, deploy to a VPS with a fixed domain.

**App Review:** Submitted June 28, 2026 for `instagram_manage_messages` and `instagram_business_manage_messages`. Review takes up to 20 days. Once approved, all DM features activate automatically.
