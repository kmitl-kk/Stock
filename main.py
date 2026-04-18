import time
import json
import requests
import random
import os

# =========================
# CONFIG
# =========================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

PROXY = os.getenv("PROXY")  # เช่น http://user:pass@host:port

PART_NUMBERS = ["MU9D3TH/A"]
ZIP_CODE = "10330"

# =========================
# LINE
# =========================
def send_line_bot(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("❌ Missing LINE config")
        return

    res = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "to": LINE_USER_ID,
            "messages": [{"type": "text", "text": message}]
        },
        timeout=10
    )

    print("LINE:", res.status_code, res.text)


# =========================
# SESSION
# =========================
def create_session():
    session = requests.Session()

    if PROXY:
        session.proxies.update({
            "http": PROXY,
            "https": PROXY
        })
        print("🌐 Using proxy")

    session.headers.update({
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        ]),
        "Accept": "application/json",
        "Referer": "https://www.apple.com/",
    })

    return session


# =========================
# FETCH
# =========================
def fetch_stock(session, part):
    url = f"https://www.apple.com/th-edu/shop/fulfillment-messages?parts.0={part}&location={ZIP_CODE}"

    for attempt in range(5):
        try:
            res = session.get(url, timeout=15)

            print(f"[{part}] status:", res.status_code)

            if res.status_code == 200:
                return res.json()

            time.sleep(5 * (attempt + 1))

        except Exception as e:
            print("error:", e)
            time.sleep(5)

    return None


# =========================
# MAIN
# =========================
def main():
    session = create_session()

    # warm up cookie
    try:
        session.get("https://www.apple.com/th-edu/shop", timeout=10)
    except:
        pass

    final_msg = ""
    found = False

    for part in PART_NUMBERS:
        print(f"\n🔍 Checking {part}")

        data = fetch_stock(session, part)

        if not data:
            print("❌ fetch failed")
            continue

        stores = data.get('body', {}).get('content', {}).get('pickupMessage', {}).get('stores', [])

        msg = f"\n📦 {part}\n"

        for s in stores:
            name = s.get("storeName", "Unknown")
            avail = s.get("partsAvailability", {}).get(part, {})
            status = avail.get("pickupDisplay")
            quote = avail.get("pickupSearchQuote", "-")

            if status == "available":
                found = True
                msg += f"✅ {name}: {quote}\n"
            else:
                msg += f"⚪ {name}: {quote}\n"

        print(msg)
        final_msg += msg

    # 👉 DEBUG MODE: ส่งเสมอ (เอาไว้เทสก่อน)
    send_line_bot("🤖 BOT RUNNING\n" + final_msg)

    # 👉 PRODUCTION MODE (เปิดใช้แทนด้านบนเมื่อมั่นใจแล้ว)
    # if found:
    #     send_line_bot("🚨 มีของ!\n" + final_msg)


if __name__ == "__main__":
    main()
