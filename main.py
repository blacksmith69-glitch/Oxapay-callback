import os
import json
import time
import random
import asyncio
from aiohttp import web, ClientSession
from dotenv import load_dotenv

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = os.getenv("CHANNEL")
OXAPAY_LINK = os.getenv("OXAPAY_LINK")

DONATION_FILE = "donations.json"
GOAL = 500
PROGRESS_BAR_LEN = 10
MOTIVATOR_INTERVAL = 30  # seconds
PROGRESS_INTERVAL = 120   # seconds

# Motivator messages
MOTIVATORS = [
    "🔥 Join the movement! Your contribution brings the script closer to release!",
    "🚀 Every $1 counts! Be part of the top donors.",
    "💎 Secure your spot in the top 3 donors — donate now!",
    "🎯 Let's hit the goal! Your support matters.",
    "💡 Want to see the script live? Contribute today!",
    "🎉 Donate now and be recognized in the community!",
    "⚡ Fast-track the release by chipping in.",
    "🌟 Your donation = more features + faster updates!",
    "💰 Give $5, $10, or more — every bit helps!",
    "📈 Be part of the progress bar: every dollar counts!",
    "💪 Show your support and join the top donors list.",
    "🎁 Special perks for early donors!",
    "🏆 Donate & claim your name in the hall of fame!",
    "✍️ Contribute and leave a mark in our community!",
    "🔔 Every donation pushes us closer to $500!"
]

# Ensure donations file exists
if not os.path.exists(DONATION_FILE):
    with open(DONATION_FILE, "w") as f:
        json.dump([], f)

async def send_telegram(session, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": f"@{CHANNEL}", "text": text, "parse_mode": "Markdown"}
    async with session.post(url, data=data) as resp:
        return await resp.json()

async def edit_telegram(session, msg_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {"chat_id": f"@{CHANNEL}", "message_id": msg_id, "text": text, "parse_mode": "Markdown"}
    async with session.post(url, data=data) as resp:
        return await resp.json()

def load_donations():
    with open(DONATION_FILE) as f:
        return json.load(f)

def save_donations(donations):
    with open(DONATION_FILE, "w") as f:
        json.dump(donations, f, indent=2)

def calculate_total(donations):
    return sum(d["amount"] for d in donations)

def progress_bar(total):
    filled = int((total/GOAL)*PROGRESS_BAR_LEN)
    return "🟩"*filled + "⬜"*(PROGRESS_BAR_LEN - filled)

def top_donors(donations):
    sorted_d = sorted(donations, key=lambda x: x["amount"], reverse=True)
    return sorted_d[:3]

async def progress_loop():
    async with ClientSession() as session:
        msg_id = None
        while True:
            donations = load_donations()
            total = calculate_total(donations)
            bar = progress_bar(total)
            top = top_donors(donations)
            top_text = "\n".join([f"🏅 {d['name']} → ${d['amount']}" for d in top])
            text = f"💰 Donation Tracker\nGoal: ${GOAL}\n\nReceived: ${total}\nRemaining: ${GOAL-total}\n\nProgress: {bar}\n\nTop Donors:\n{top_text if top_text else 'None yet'}"
            if msg_id is None:
                resp = await send_telegram(session, text)
                msg_id = resp.get("result", {}).get("message_id")
            else:
                await edit_telegram(session, msg_id, text)
            await asyncio.sleep(PROGRESS_INTERVAL)

async def motivator_loop():
    async with ClientSession() as session:
        last_msg_id = None
        while True:
            msg = random.choice(MOTIVATORS) + f"\nDonate: {OXAPAY_LINK}"
            resp = await send_telegram(session, msg)
            # Delete previous motivator
            if last_msg_id:
                await session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                                   data={"chat_id": f"@{CHANNEL}", "message_id": last_msg_id})
            last_msg_id = resp.get("result", {}).get("message_id")
            await asyncio.sleep(MOTIVATOR_INTERVAL)

# Oxapay callback
async def callback(request):
    data = await request.json()
    name = data.get("name", "Anonymous")
    amount = float(data.get("amount", 0))
    donations = load_donations()
    donations.append({"name": name, "amount": amount})
    save_donations(donations)

    # Thank message
    async with ClientSession() as session:
        total = calculate_total(donations)
        await send_telegram(session, f"🎉 {name} just donated ${amount}!\nTotal donated: ${total}")

    return web.json_response({"status": "ok"})

app = web.Application()
app.add_routes([web.post("/callback", callback)])

async def main():
    await asyncio.gather(progress_loop(), motivator_loop())
    
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # Start background tasks
    asyncio.ensure_future(main())
    # Run web server for callback
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
