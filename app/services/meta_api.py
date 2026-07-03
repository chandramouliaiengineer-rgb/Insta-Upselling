import httpx
from app.config import settings

BASE_URL = "https://graph.facebook.com/v22.0"

async def get_posts():
    url = f"{BASE_URL}/{settings.META_INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,permalink,timestamp,media_type",
        "access_token": settings.META_PAGE_ACCESS_TOKEN,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

async def get_comments(post_id: str):
    url = f"{BASE_URL}/{post_id}/comments"
    params = {
        "fields": "id,text,username,timestamp",
        "access_token": settings.META_PAGE_ACCESS_TOKEN,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

async def post_comment_reply(comment_id: str, message: str) -> dict:
    url = f"{BASE_URL}/{comment_id}/replies"
    params = {"access_token": settings.META_PAGE_ACCESS_TOKEN}
    data = {"message": message}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, params=params, data=data)
        print(f"Meta API response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            return response.json()
        response.raise_for_status()
        return response.json()


async def send_private_reply(comment_id: str, message: str) -> dict:
    url = f"https://graph.instagram.com/v22.0/{settings.META_INSTAGRAM_ACCOUNT_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.META_INSTAGRAM_USER_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, json=data)
        print(f"Private reply response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            return response.json()
        response.raise_for_status()
        return response.json()


async def send_dm_message(recipient_id: str, message: str) -> dict:
    url = f"https://graph.instagram.com/v22.0/{settings.META_INSTAGRAM_ACCOUNT_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.META_INSTAGRAM_USER_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, json=data)
        print(f"DM message response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            return response.json()
        response.raise_for_status()
        return response.json()


async def send_button_message(recipient_id: str, text: str, buttons: list) -> dict:
    """buttons: list like [{"title": "Send me the repo", "payload": "GET_REPO"}]"""
    url = f"https://graph.instagram.com/v22.0/{settings.META_INSTAGRAM_ACCOUNT_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.META_INSTAGRAM_USER_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": [
                        {"type": "postback", "title": b["title"], "payload": b["payload"]}
                        for b in buttons
                    ]
                }
            }
        },
        "messaging_type": "RESPONSE"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, json=data)
        print(f"Button message response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            return response.json()
        response.raise_for_status()
        return response.json()
