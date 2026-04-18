import time
import json
import requests
import random
import os
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# ==========================================
# CONFIGURATION
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
PART_NUMBER = "MU9D3TH/A"
ZIP_CODE = "10330"

def send_line_bot(message):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("❌ Missing LINE configuration")
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except Exception as e:
        print(f"⚠️ LINE Error: {e}")

def check_stock_and_report():
    with sync_playwright() as p:
        print(f"--- [{time.strftime('%H:%M:%S')}] Starting Stealth Check ---")
        
        # ใช้ Browser ปกติ (ไม่ใช่ Headless แบบโต้งๆ)
        browser = p.chromium.launch(headless=True)
        
        # สุ่ม User-Agent เพื่อพรางตัว
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]

        context = browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        # ใช้ Stealth Mode เพื่อลบตัวแปรที่บ่งบอกว่าเป็นบอท
        stealth_sync(page)

        try:
            # Step 1: เข้าหน้าเว็บหลักก่อน เพื่อหลอกว่าเราเป็นคนเข้ามาดูสินค้าจริงๆ
            print("🔗 Visiting Apple Store page...")
            page.goto("https://www.apple.com/th-edu/shop/buy-mac/mac-mini", wait_until="networkidle")
            time.sleep(random.uniform(5, 10)) # รอเหมือนคนกำลังอ่านหน้าเว็บ

            # Step 2: เรียก API ข้อมูลสต็อก
            api_url = f"https://www.apple.com/th-edu/shop/fulfillment-messages?parts.0={PART_NUMBER}&location={ZIP_CODE}"
            print("📡 Fetching stock data...")
            response = page.goto(api_url)

            if response.status == 541:
                print("🚨 Error 541: Still blocked by Apple.")
                # ถ้ายังโดนบล็อก อาจพิจารณาส่งแจ้งเตือนเข้า LINE แค่วันละครั้งพอ จะได้ไม่รบกวน
                return

            raw_text = page.inner_text("body")
            if page.locator("pre").count() > 0:
                raw_text = page.locator("pre").inner_text()

            data = json.loads(raw_text)
            stores = data.get('body', {}).get('content', {}).get('pickupMessage', {}).get('stores', [])
            
            found_any = False
            report_msg = f"🤖 รายงานสต็อก {PART_NUMBER}\n"
            
            for store in stores:
                name = store.get('storeName', '')
                avail = store.get('partsAvailability', {}).get(PART_NUMBER, {})
                status = avail.get('pickupDisplay')
                quote = avail.get('pickupSearchQuote', 'ไม่มีข้อมูล')

                if status == "available":
                    found_any = True
                    report_msg += f"✅ {name}: {quote}\n"
                else:
                    report_msg += f"⚪ {name}: {quote}\n"

            if found_any:
                send_line_bot("🚨 [พบสินค้า!] 🚨\n" + report_msg)
                print("✅ Found stock! Message sent.")
            else:
                print("⚪ Out of stock. No message sent to avoid spam.")

        except Exception as e:
            print(f"⚠️ Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_stock_and_report()
