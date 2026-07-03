from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

TOPICS = [
    "ai_llm", "data_science_ml", "web_dev", "automation",
    "productivity_nocode", "devops", "cybersecurity", "game_dev",
    "blockchain_web3", "dev_tools_trending", "general",
]

async def generate_reply(comment_text: str, post_caption: str = "") -> str:
    prompt = f"""You are a helpful assistant for a tech/dev-tools Instagram page called startnow_365,
focused on AI tools, open-source projects, and developer resources.
Someone commented on one of your posts. Write a warm, friendly, genuine reply under 150 characters.
Reply with only the comment text, nothing else. No hashtags. No emojis unless natural.

Post caption: {post_caption[:200] if post_caption else 'Tech tools and open-source content'}
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
    topic_list = "|".join(TOPICS)
    prompt = f"""Classify this Instagram comment from a page about AI tools, dev resources, and open-source projects.
Return only valid JSON, nothing else.

Comment: "{comment_text}"

Return exactly this format:
{{"topic": "{topic_list}"}}

Topic guide:
- ai_llm: AI, LLMs, ChatGPT, agents, prompting
- data_science_ml: machine learning, data science, models/training
- web_dev: websites, frontend, backend, frameworks
- automation: workflow automation, n8n, zapier, bots
- productivity_nocode: no-code tools, productivity apps
- devops: deployment, CI/CD, infra, docker/k8s
- cybersecurity: security, hacking, pentesting
- game_dev: game development, engines
- blockchain_web3: crypto, blockchain, web3
- dev_tools_trending: general dev tools, anything else code-related
- general: anything else, even if not clearly tech-specific

Always pick the closest matching topic. Never leave it blank."""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=30,
        temperature=0,
    )

    import json
    text = response.choices[0].message.content.strip()
    try:
        result = json.loads(text)
        return {"topic": result.get("topic", "general")}
    except Exception:
        return {"topic": "general"}


async def match_best_repo(message_text: str, candidates: list) -> str | None:
    """
    candidates: list of dicts like [{"num": 1, "id": "...", "title": "..."}, ...]
    Returns the matched freebie id, or None if no good match.
    """
    listing = "\n".join(f"{c['num']}. {c['title']}" for c in candidates)

    prompt = f"""A user on a tech/AI Instagram page said this about what they're looking for:
\"{message_text}\"

Here is a list of available open-source repositories:
{listing}

Pick the SINGLE best matching repository for what they said.
Return ONLY the number, nothing else. If genuinely nothing matches well, return 0."""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )

    text = response.choices[0].message.content.strip()
    try:
        num = int(text)
        if num == 0:
            return None
        match = next((c for c in candidates if c["num"] == num), None)
        return match["id"] if match else None
    except Exception:
        return None


async def generate_dm_opener(comment_text: str, topic: str) -> str:
    prompt = f"""You are a helpful assistant for a tech/dev-tools Instagram page focused on AI tools and open-source resources.
A user commented: "{comment_text}"
Their topic of interest is: {topic}

Write a short, warm, personal DM opener (under 200 characters) that:

- References their comment naturally
- Offers to share something helpful (a relevant open-source repo or tool)
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
