# Instagram Upsell — Project Documentation

## Overview
This repository powers an Instagram "upsell" automation that responds to comments on posts, opens a qualifying private message to ask what the user is looking for, and (on user reply or button tap) delivers a relevant open-source repo from a seeded catalog.

Main goals:
- Reply to every qualifying comment publicly.
- Open a short private DM asking if the user wants a repo.
- Use a button or typed reply to trigger semantic matching and deliver the best repo via DM.

Tech stack:
- FastAPI (HTTP API)
- SQLAlchemy 2.x (async) + Postgres (pgvector image used in compose)
- Redis (caching/health checks)
- Docker + docker-compose for local deployment
- OpenAI (via `openai.AsyncOpenAI`) for reply generation, DM openers, and semantic repo matching
- HTTPX for Meta Graph API calls


## Repo layout (key files)
- `app/main.py` — FastAPI app & router wiring
- `app/config.py` — Pydantic Settings / environment variables
- `app/database.py` — SQLAlchemy async engine, sessionmaker, base
- `app/routers/webhook.py` — Instagram webhook handler (comments, messaging postbacks/DMs)
- `app/routers/health.py` — health, sync, and manual seeding endpoints
- `app/models/` — DB models: `user.py`, `post.py`, `comment.py`, `freebie.py`, `interest.py`
- `app/services/` — business logic
  - `ai_service.py` — LLM prompts: `generate_reply`, `generate_dm_opener`, `classify_comment`, `match_best_repo`
  - `meta_api.py` — Meta Graph API helpers: comment replies, private replies, DM messages, button templates
  - `freebie.py` — freebie selection & delivery (`deliver_repo_reply`, `check_and_deliver_freebie`)
  - `seed.py` — JSON seeder for repository freebies
  - `sync.py` — optional helpers to sync posts/comments from Meta
  - `interest.py` — logging signals and computing interest profiles
- `seed_data/repos_seed.json` — canonical list of ~928 repo freebies used by `seed_repos`
- `docker-compose.yml`, `Dockerfile`, `requirements.txt` — runtime & dependency config


## Database models (summary)
- `users` — `id (UUID)`, `instagram_user_id`, `messaging_psid`, `username`, `lead_score`, `status`, timestamps
- `posts` — `instagram_post_id`, `caption`, `media_type`, `permalink`, timestamps
- `comments` — `instagram_comment_id`, `post_id`, `user_id`, `text`, `username`, `replied`, `our_reply_text`, timestamps
- `freebies` — `topic`, `title`, `type` (`repo`), `file_url`, `threshold`, `active`
- `delivered_freebies` — records of deliveries to avoid duplicates
- `interest_signals` — per-comment signals logged (topic, intent, weight)
- `interest_profiles` — computed running scores and primary topic per user


## Core flows & responsibilities

1) Incoming comment webhook (fast path in `app/routers/webhook.py`):
   - Webhook verifies `X-Hub-Signature-256` with your `META_APP_SECRET`.
   - For comment changes (`change.field == 'comments'`), it:
     - Ensures a `User` row exists for the commenter.
     - Calls `ai_service.classify_comment()` to get a `topic` (topic-only classifier).
     - Logs one signal via `interest.log_signal()` (weight=10, fixed `question` intent).
     - Updates the profile via `interest.update_profile()`.
     - Creates a `Comment` DB row.
     - Generates a public reply via `ai_service.generate_reply()` and posts it (`meta_api.post_comment_reply`).
     - Sends a private reply opener (`meta_api.send_private_reply`) and attempts to capture the returned `recipient_id` (messaging PSID) into `user.messaging_psid`.
     - If a `recipient_id` is available, sends a Button Template invitation (`meta_api.send_button_message`) so the user can tap one-button to request the repo.

2) DM / Button handling (in `webhook.py` messaging loop):
   - Messaging events are processed in two ways:
     - `postback` (button tap): treated as a request to send the repo — server looks up the `User` (by `messaging_psid` or `instagram_user_id`), finds the user's `primary_topic` and the last comment text, and calls `deliver_repo_reply()` with the message text as the match input.
     - `message` (typed DM): treated similarly — if the user has not already received a repo for that topic, `deliver_repo_reply()` is invoked with the typed message as the match input.

3) Repo selection & delivery (`app/services/freebie.py` -> `deliver_repo_reply`):
   - Checks `delivered_freebies` to avoid duplicate deliveries per topic.
   - Loads all candidate `Freebie` rows for the user's `topic` (falling back to `general` if none exist).
   - If the user provided reply text (typed or inferred from last comment), `ai_service.match_best_repo()` is called with a numbered list of candidate titles. The LLM returns a single number indicating best match.
   - If `match_best_repo` returns a valid choice, that repo is chosen; otherwise the first repo in the list is used as a fallback.
   - The chosen repo is delivered via `meta_api.send_dm_message()` and a `DeliveredFreebie` record is created.


## LLM usage (prompts & intent)
- `generate_reply(comment_text, post_caption)` — produces a short public reply (<150 chars).
- `generate_dm_opener(comment_text, topic)` — writes a friendly DM opener inviting a reply.
- `classify_comment(comment_text)` — simplified topic-only classifier; returns JSON with `{"topic":"<topic>"}`.
- `match_best_repo(message_text, candidates)` — builds a numbered list of candidate repo titles and asks the model to pick exactly one number (or 0). This is used to semantically map a user's reply to the seeded repos.


## Meta Graph API helpers (`app/services/meta_api.py`)
- `post_comment_reply(comment_id, message)` — posts a top-level reply to a comment.
- `send_private_reply(comment_id, message)` — uses the 'recipient: {comment_id}' private reply API to open a DM thread and returns the API response (used to capture `recipient_id`).
- `send_dm_message(recipient_id, message)` — send a plain text DM message.
- `send_button_message(recipient_id, text, buttons)` — send a Button Template (postback) message to the recipient.

Notes: Button Templates result in `postback` payloads on webhook events; the code paths in `webhook.py` capture `postback.payload` and call the same delivery logic.


## Running locally (Docker)
Prereqs: Docker & Docker Compose.

1. Create a `.env` at repository root with the required variables (example keys below).
2. Start services:

```bash
docker compose up --build
```

By default the API listens on port `8001` (mapped to container `8000`).

Useful endpoints:
- `GET /` — quick health check
- `GET /api/health` — DB + Redis health
- `GET /api/test-meta` — tests Meta API connectivity
- `GET /api/test-sync` — runs a sync of posts/comments into the DB
- `GET /api/seed-repos` — manually seed `seed_data/repos_seed.json` into the `freebies` table


## Environment variables (.env)
Minimum recommended (see `app/config.py` for all):
- `DATABASE_URL` — asyncpg URL, e.g. `postgresql+asyncpg://postgres:postgres123@postgres:5432/instagram_upsell`
- `REDIS_URL` — e.g. `redis://redis:6379/0`
- `META_APP_SECRET` — App secret for webhook signature validation
- `META_WEBHOOK_VERIFY_TOKEN` — webhook verification token
- `META_INSTAGRAM_ACCOUNT_ID` — Instagram account id used for messaging endpoints
- `META_INSTAGRAM_USER_TOKEN` — long-lived user token used to send messages
- `META_PAGE_ACCESS_TOKEN` — page access token used for comment replies
- `OPENAI_API_KEY` — for LLM calls


## Database seeding
- The canonical seed data is `seed_data/repos_seed.json`.
- Use `GET /api/seed-repos` or call `app.services.seed.seed_repos()` to populate `freebies` with `type='repo'` rows. The seeder checks for existing `repo` rows and will skip if already seeded.


## Testing the end-to-end flow (recommended)
1. Ensure `freebies` contains `repo` rows (seed if needed).
2. Post a comment on an Instagram test post (or emulate webhook payload): short tech/dev comment e.g. "Something for multi-agent orchestration?"
3. The app should:
   - Post a public reply
   - Send a private opener DM asking if user wants a repo
   - When user taps "Send me the repo" (button) or replies with typed text, the webhook receives a `postback` or `message` event and `deliver_repo_reply()` runs
   - The chosen repo DM should arrive and `delivered_freebies` record be created


## Commands for DB cleanup (useful during tests)
Example to wipe old taxonomy data (intended when switching taxonomies):

```bash
docker compose exec postgres psql -U postgres -d instagram_upsell -c "DELETE FROM delivered_freebies; DELETE FROM interest_signals; DELETE FROM interest_profiles; DELETE FROM freebies WHERE type != 'repo';"
```

Per-user cleanup example:

```bash
docker compose exec postgres psql -U postgres -d instagram_upsell -c "DELETE FROM comments WHERE username='iam.priyawarrior'; DELETE FROM interest_signals WHERE username='iam.priyawarrior'; DELETE FROM interest_profiles WHERE username='iam.priyawarrior';"
```


## Notes, trade-offs and operational considerations
- Button templates (postbacks) are slightly more restrictive under Meta's App Review than text DMs. They generally work in development but consider possible gating when moving to production.
- The LLM-based `classify_comment` is intentionally topic-only (no intent gating) so every comment receives a reply and a DM opener.
- `match_best_repo` relies on the model to parse a short listing and return a single number. This is simpler than embedding-based vector similarity (pgvector) but can be changed later to a vector approach for scale and determinism.
- The seeder currently creates `Freebie` rows with `threshold=30` and `active=True` — adjust as needed.
- Error handling: most external calls are wrapped in try/except and logged; monitor container logs (`docker compose logs api --follow`) during testing.


## Where to look in source for specific behavior
- Webhook handling + DM/postback logic: `app/routers/webhook.py`
- LLM prompts & matching strategy: `app/services/ai_service.py`
- Freebie selection and delivery: `app/services/freebie.py`
- Meta Graph calls (comments, private reply, DM, buttons): `app/services/meta_api.py`
- Seeder for repo freebies: `app/services/seed.py` & `seed_data/repos_seed.json`
- Interest scoring and profiles: `app/services/interest.py`


## Running lint / quick syntax checks
Inside the project (venv activated):

```bash
python -m py_compile app/routers/webhook.py app/services/ai_service.py app/services/freebie.py app/services/meta_api.py
```


## Final tips
- Keep `.env` secure — tokens & secrets must be rotated regularly.
- If you change the model prompts, test with a few representative comments first.
- If you outgrow LLM-number matching for repo selection, consider: 1) adding an embeddings + vector search (pgvector) or 2) precomputing candidate metadata and using a deterministic similarity algorithm.


---
Generated by reading repository source files. For follow-ups I can:
- Add a developer quickstart with exact `.env` examples (without secrets)
- Add integration tests emulating webhook payloads
- Convert `match_best_repo` to vector embeddings for more deterministic matching

