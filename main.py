import os
import json
import time
import random
import asyncio
import requests
from datetime import datetime
from aiohttp import web
from dotenv import load_dotenv

# Load .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OXAPAY_KEY = os.getenv("OXAPAY_KEY")
CHANNEL = os.getenv("CHANNEL")  # @scriptdropx
DONATION_LINK = os.getenv("DONATION_LINK")
GOAL = 500.0  # USD

# File to store donations
DONATION_FILE = "donations.json"

# Update intervals
PROGRESS_INTERVAL = 120  # seconds
MOTIVATION_INTERVAL = 30  # seconds

# Motivation messages
MOTIVATION_MSGS = [
    "🚀 Be part of the elite! Donate & join the team.",
    "💪 Your contribution keeps the scripts alive.",
    "🔥 Every donation counts! Let’s hit the goal together.",
    "🎯 Support the project & get early updates.",
    "💰 Donate now & be part of the top donors!",
    "📈 Help push the community forward!",
    "💎 Exclusive scripts will be unlocked with your support.",
    "🤝 Join the movement: donate, support, succeed.",
    "⚡ Every $ counts! Don’t wait.",
    "🎉 Be featured as a top donor in the channel!"
]

# In-memory store of last posted messages to delete
last_motivation_msg_id = None
last_progress_msg_id = None

# Load donations from file
if os.path.exists(DONATION_FILE):
    with open(DONATION_FILE, "r") as f:
        donations = json.load(f)
else:
    donations = []

# Helper functions
def save_donations():
    with open(DONATION_FILE, "w") as f:
        json.dump(donations, f, indent=2)

def total_received():
    return sum(d["amount"] for d in donations)

def remaining_amount():
    return max(0, GOAL - total_received())

def get_progress_bar():
    total_blocks = 10
    filled = int((total_received() / GOAL) * total_blocks)
    bar = "🟩" * filled + "⬜" * (total_blocks - filled)
    return bar

def top_donors():
    sorted_list = sorted(donations, key=lambda x: x["amount"], reverse=True)
    return sorted_list[:3]

def format_progress_message():
    msg = f"💰 Donation Tracker\nGoal: ${GOAL:.2f}\n\n"
    msg += f"Received: ${total_received():.2f}\n"
    msg += f"Remaining: ${remaining_amount():.2f}\n\n"
    msg += f"Progress: {get_progress_bar()}"
    return msg

def format_donor_message(donor):
    name = donor.get("name") or "Anonymous"
    amt = donor["amount"]
    return f"🎉 {name} just donated ${amt:.2f}! Thanks for supporting the project! 🚀"

# Telegram helpers
def telegram_send(text, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_to:
        data["reply_to_message_id"] = reply_to
    resp = requests.post(url, data=data)
    if resp.ok:
        return resp.json()["result"]["message_id"]
    return None

def telegram_edit(message_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {
        "chat_id": CHANNEL,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

def telegram_delete(message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
    data = {
        "chat_id": CHANNEL,
        "message_id": message_id
    }
    requests.post(url, data=data)

# Donation callback server
async def handle_callback(request):
    try:
        data = await request.json()
        # Example: data = {"name": "user", "amount": 10.0}
        donor_name = data.get("name", "Anonymous")
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return web.json_response({"status": "ignored"})
        donation = {"name": donor_name, "amount": amount, "time": datetime.utcnow().isoformat()}
        donations.append(donation)
        save_donations()
        # Send donation received message
        telegram_send(format_donor_message(donation))
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "detail": str(e)})

# Background tasks
async def progress_updater():
    global last_progress_msg_id
    while True:
        msg = format_progress_message()
        if last_progress_msg_id:
            try:
                telegram_edit(last_progress_msg_id, msg)
            except:
                last_progress_msg_id = telegram_send(msg)
        else:
            last_progress_msg_id = telegram_send(msg)
        await asyncio.sleep(PROGRESS_INTERVAL)

async def motivation_poster():
    global last_motivation_msg_id
    while True:
        msg = random.choice(MOTIVATION_MSGS) + f"\nDonate here: {DONATION_LINK}"
        msg_id = telegram_send(msg)
        if last_motivation_msg_id:
            telegram_delete(last_motivation_msg_id)
        last_motivation_msg_id = msg_id
        await asyncio.sleep(MOTIVATION_INTERVAL)

# Run server + tasks
async def main():
    app = web.Application()
    app.router.add_post("/callback", handle_callback)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()
    print("Server running on port", os.environ.get("PORT", 10000))

    # Start background tasks
    await asyncio.gather(progress_updater(), motivation_poster())

if __name__ == "__main__":
    asyncio.run(main())
