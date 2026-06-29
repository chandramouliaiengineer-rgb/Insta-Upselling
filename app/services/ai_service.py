from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_reply(comment_text: str, post_caption: str = "") -> str:
    prompt = f"""You are a helpful assistant for a motivational Instagram page called startnow_365.
Someone commented on one of your posts. Write a warm, friendly, genuine reply under 150 characters.
Reply with only the comment text, nothing else. No hashtags. No emojis unless natural.

Post caption: {post_caption[:200] if post_caption else 'Motivational content'}
User comment: {comment_text}

Reply:"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()

async def classify_comment(comment_text: str) -> dict:
    prompt = f"""Classify this Instagram comment. Return only valid JSON.

Comment: "{comment_text}"

Return exactly this format:
{{"topic": "skincare|fitness|mindset|pricing|general|noise", "intent": "question|praise|price_check|objection|noise", "weight": 0}}

Weight rules: price_check=25, question=10, praise=3, objection=8, noise=0"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0,
    )

    import json
    text = response.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception:
        return {"topic": "general", "intent": "noise", "weight": 0}


async def generate_dm_opener(comment_text: str, topic: str) -> str:
    prompt = f"""You are a helpful assistant for a motivational Instagram page.
A user commented: \"{comment_text}\"
Their topic of interest is: {topic}

Write a short, warm, personal DM opener (under 200 characters) that:
- References their comment naturally
- Offers to share something helpful
- Does NOT mention products or selling
- Feels like a real person reaching out
- Ends with a soft question to invite reply

Return only the message text."""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()
