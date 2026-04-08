import os
import discord
import requests

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

SYSTEM_PROMPT = """
너는 디스코드 서버용 한국어 AI 봇이다.
기본적으로 한국어로 답하고,
너무 길면 1900자 이내로 줄여서 답해라.
"""

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # 봇 멘션이나 !ask 로 시작할 때만 반응
    is_mentioned = client.user in message.mentions
    starts_with_command = message.content.startswith("!ask ")

    if not is_mentioned and not starts_with_command:
        return

    user_text = message.content
    if starts_with_command:
        user_text = message.content[5:].strip()
    else:
        user_text = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()

    if not user_text:
        await message.channel.send("질문 내용을 써 주세요.")
        return

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.7
            },
            timeout=60
        )

        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]

        if len(reply) > 1900:
            reply = reply[:1900] + "..."

        await message.channel.send(reply)

    except Exception as e:
        await message.channel.send(f"오류가 났습니다: {e}")

client.run(DISCORD_TOKEN)
