import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from collections import defaultdict, deque

import discord
import requests

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 10000))

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN 환경변수가 없습니다.")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY 환경변수가 없습니다.")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

SYSTEM_PROMPT = """
너는 디스코드 서버용 한국어 AI 봇이다.
기본적으로 한국어로 자연스럽게 답한다.
직전 대화 흐름을 이어서 답하되, 없는 기억을 지어내지 않는다.
답변은 너무 길면 핵심만 간단히 말한다.
"""

# 채널별 단기 기억
# 최근 10개의 user/assistant 메시지를 기억합니다.
memory = defaultdict(lambda: deque(maxlen=10))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot is running.".encode("utf-8"))

    def log_message(self, format, *args):
        return


def run_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    print(f"Web server running on port {PORT}")
    server.serve_forever()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    # 다른 봇 메시지 무시
    if message.author.bot:
        return

    is_mentioned = client.user in message.mentions
    starts_with_command = message.content.startswith("!ask ")

    # 멘션 또는 !ask 일 때만 반응
    if not is_mentioned and not starts_with_command:
        return

    # 사용자 입력 정리
    if starts_with_command:
        user_text = message.content[5:].strip()
    else:
        user_text = (
            message.content
            .replace(f"<@{client.user.id}>", "")
            .replace(f"<@!{client.user.id}>", "")
            .strip()
        )

    if not user_text:
        await message.channel.send("질문 내용을 써 주세요.")
        return

    try:
        channel_id = str(message.channel.id)

        # 사용자 메시지 저장
        memory[channel_id].append({"role": "user", "content": user_text})

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ] + list(memory[channel_id]),
                "temperature": 0.7
            },
            timeout=60
        )

        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"].strip()

        if len(reply) > 1900:
            reply = reply[:1900] + "..."

        # 봇 응답도 기억에 저장
        memory[channel_id].append({"role": "assistant", "content": reply})

        await message.channel.send(reply)

    except Exception as e:
        await message.channel.send(f"오류가 났습니다: {e}")


if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    client.run(DISCORD_TOKEN)
