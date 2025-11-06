import asyncio
import aiohttp
from aiohttp import web
import json
from datetime import datetime
import random
import os

# -----------------------------
# CONFIGURATION
# -----------------------------
TELEGRAM_BOT_TOKEN = "8547532735:AAFbhjHqHX13SoOV5fRty33Sj1dqar99HlQ"
TELEGRAM_CHAT_ID = "@scriptdropx"
OXAPAY_CALLBACK_FILE = "donations.json"
GOAL_USD = 500
UPDATE_INTERVAL = 120  # Progress bar update interval
MOTIVATION_INTERVAL = 30  # Motivation message interval
DONATION_LINK_INTERVAL = 5  # Donation prompt post interval
TOP_DONORS_COUNT = 3

DONATION_COMMAND = "/donation"
DONATION_LINK_TEXT = f"Donate now: {DONATION_COMMAND}"

MOTIVATION_MESSAGES = [
    "🔥 Help us reach the goal! Donate now and be part of the team!",
    "💪 Every contribution counts! Join the movement!",
    "🚀 Let's heat this goal fast! Be a donor today!",
    "🌟 Your donation makes a difference! Let's go!",
    "💎 Be a top donor and get recognized!",
    "🎯 Small donation, big impact! Don't miss out!",
    "💰 Contribute now and see your name on top!",
    "⚡ Let's break records together! Donate now!",
    "🏆 Only the committed donors will be featured!",
    "💥 Every second counts! Help us reach $500!",
    "🌐 Join the exclusive donors club! Donate today!",
    "💡 Your support inspires others! Donate now!",
    "✨ Let's make this happen! Your donation matters!",
    "🔥 Heat the goal! Make your mark with a donation!",
    "💸 Don't wait! Donate and be part of history!"
]

# -----------------------------
# GLOBAL STATE
# -----------------------------
donations = []  # {"name": str, "amount": float, "time": timestamp}
last_posted_donation_ids = set()  # track donors who have been posted for repeat
last_donation_prompt_id = None
last_activity_time = datetime.utcnow().timestamp()

# -----------------------------
# UTILITIES
# -----------------------------
async def telegram_request(method, data):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            return await resp.json()

def save_donations():
    with open(OXAPAY_CALLBACK_FILE, "w") as f:
        json.dump(donations, f, indent=2)

def load_donations():
    global donations
    try:
        with open(OXAPAY_CALLBACK_FILE, "r") as f:
            donations = json.load(f)
    except FileNotFoundError:
        donations = []

def calculate_total():
    return sum(d["amount"] for d in donations)

def get_progress_bar():
    total = calculate_total()
    progress = min(total / GOAL_USD, 1)
    filled = int(progress * 10)
    empty = 10 - filled
    return "🟩" * filled + "⬜" * empty

def get_top_donors():
    return sorted(donations, key=lambda x: x["amount"], reverse=True)[:TOP_DONORS_COUNT]

# -----------------------------
# POSTING FUNCTIONS
# -----------------------------
async def send_typing():
    await telegram_request("sendChatAction", {"chat_id": TELEGRAM_CHAT_ID, "action": "typing"})
    await asyncio.sleep(1)

async def post_progress():
    await send_typing()
    total = calculate_total()
    remaining = GOAL_USD - total
    text = (
        f"💰 Donation Tracker\n"
        f"Goal: ${GOAL_USD}\n\n"
        f"Received: ${total:.2f}\n"
        f"Remaining: ${remaining:.2f}\n\n"
        f"Progress: {get_progress_bar()}\n\n"
        f"Top Donors:\n"
    )
    for donor in get_top_donors():
        text += f"⭐ {donor['name']} → ${donor['amount']:.2f}\n"
    text += f"\nDonate here: {DONATION_COMMAND}"
    await telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text})

async def post_motivation():
    await send_typing()
    message = random.choice(MOTIVATION_MESSAGES)
    msg = await telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": message})
    msg_id = msg.get("result", {}).get("message_id")
    if msg_id:
        await asyncio.sleep(5)
        await telegram_request("deleteMessage", {"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id})

async def post_new_donation(donor):
    await send_typing()
    text = (
        f"🎉 New Donation!\n"
        f"{donor['name']} just donated ${donor['amount']:.2f}!\n"
        f"Total received: ${calculate_total():.2f}\n"
        f"{get_progress_bar()}"
    )
    await telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text})

async def post_donation_prompt():
    global last_donation_prompt_id
    current_time = datetime.utcnow().timestamp()
    if current_time - last_activity_time < 60:
        return  # Skip if recent activity
    msg = await telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": DONATION_LINK_TEXT})
    last_donation_prompt_id = msg.get("result", {}).get("message_id")
    if last_donation_prompt_id:
        await asyncio.sleep(5)
        await telegram_request("deleteMessage", {"chat_id": TELEGRAM_CHAT_ID, "message_id": last_donation_prompt_id})

# -----------------------------
# CALLBACK HANDLER
# -----------------------------
async def handle_callback(request):
    global last_activity_time
    try:
        data = await request.json()
        name = data.get("name") or "Anonymous"
        amount = float(data.get("amount", 0))
        timestamp = datetime.utcnow().timestamp()
        donor = {"name": name, "amount": amount, "time": timestamp}
        donations.append(donor)
        save_donations()
        last_activity_time = timestamp
        await post_new_donation(donor)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

# -----------------------------
# BACKGROUND LOOPS
# -----------------------------
async def main_loop():
    while True:
        try:
            await post_progress()
        except Exception as e:
            print("Error posting progress:", e)
        await asyncio.sleep(UPDATE_INTERVAL)

async def motivation_loop():
    while True:
        try:
            await post_motivation()
        except Exception as e:
            print("Error posting motivation:", e)
        await asyncio.sleep(MOTIVATION_INTERVAL)

async def donation_prompt_loop():
    while True:
        try:
            await post_donation_prompt()
        except Exception as e:
            print("Error posting donation prompt:", e)
        await asyncio.sleep(DONATION_LINK_INTERVAL)

# -----------------------------
# MAIN
# -----------------------------
async def start_server():
    app = web.Application()
    app.router.add_post("/callback", handle_callback)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print("Server started on port", port)

async def main():
    load_donations()
    await asyncio.gather(
        start_server(),
        main_loop(),
        motivation_loop(),
        donation_prompt_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
