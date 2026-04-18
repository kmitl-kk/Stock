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

PART_NUMBERS = [
    "MU9D3TH/A",  # เพิ่มสินค้าได้
]

ZIP_CODE = "10330"

# =========================
# LINE NOTIFY
# =========================
def send_line_bot(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("❌ Missing LINE config")
        return

    try:
        requests.post(
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
    except Exception as e:
        print("LINE error:", e)

# =========================
# FETCH STOCK
# =========================
def fetch_stock(session, part_number):
    url = f"https://www.apple.com/th-edu/shop/fulfillment-messages?parts.0={part_number}&location={ZIP_CODE}"

    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        ]),
        "Accept": "application/json",
        "Referer": "https://www.apple.com/",
    }

    # retry + backoff
    for attempt in range(5):
        try:
            res = session.get(url, headers=headers, timeout=10)

            if res.status_code == 200:
                return res.json()

            print(f"⚠️ {part_number} status {res.status_code}")
            time.sleep(5 * (attempt + 1))

        except Exception as e:
            print("error:", e)
            time.sleep(5)

    return None

# =========================
# MAIN CHECK
# =========================
def check_stock():
    session = requests.Session()

    # warm up cookie (สำคัญ)
    try:
        session.get("https://www.apple.com/th-edu/shop", timeout=10)
    except:
        pass

    final_report = ""
    found_any = False

    for part in PART_NUMBERS:
        print(f"\n🔍 Checking {part}")

        data = fetch_stock(session, part)

        if not data:
            print("❌ fetch failed")
            continue

        stores = data.get('body', {}).get('content', {}).get('pickupMessage', {}).get('stores', [])

        report = f"\n📦 {part}\n"

        for store in stores:
            name = store.get("storeName", "Unknown")
            avail = store.get("partsAvailability", {}).get(part, {})
            status = avail.get("pickupDisplay")
            quote = avail.get("pickupSearchQuote", "-")

            if status == "available":
                found_any = True
                report += f"✅ {name}: {quote}\n"
            else:
                report += f"⚪ {name}: {quote}\n"

        print(report)
        final_report += report

    if found_any:
        print("🚨 Found stock → sending LINE")
        send_line_bot("🚨 มีของแล้ว!\n" + final_report)
    else:
        print("⚪ No stock (no notification sent)")

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    check_stock()
