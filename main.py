from flask import Flask, request, jsonify
import requests, os, json, time

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DONORS_FILE = "donors.json"

def save_donor(record):
    try:
        if os.path.exists(DONORS_FILE):
            with open(DONORS_FILE, "r") as f:
                data = json.load(f)
        else:
            data = []
        data.append(record)
        with open(DONORS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("save error:", e)

def notify_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("telegram resp:", r.status_code, r.text)
        return r
    except Exception as e:
        print("telegram send error:", e)

@app.route("/callback", methods=["POST"])
def oxapay_callback():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        print("bad json:", e)
        return jsonify({"status":"bad_request"}), 400

    print("🔔 Received callback:", data)

    amount = data.get("amount") or data.get("value") or "0"
    currency = data.get("currency") or "USDT"
    name = data.get("name") or ""
    note = data.get("note") or ""
    txid = data.get("txid") or ""

    try:
        amount_f = float(amount)
    except:
        amount_f = 0.0

    rec = {
        "time": int(time.time()),
        "amount": amount_f,
        "currency": currency,
        "name": name,
        "note": note,
        "txid": txid,
        "raw": data
    }
    save_donor(rec)

    who = note if note else (name if name else "Anonymous")
    text = (
        f"🎉 *New Donation Received*\n\n"
        f"💰 Amount: *{amount_f:.2f}* {currency}\n"
        f"👤 Donor: *{who}*\n"
        f"🧾 Note: `{note}`\n"
        f"🔗 TX: `{txid}`"
    )

    notify_telegram(text)
    return jsonify({"status":"ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return "✅ OxaPay Callback Server is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
