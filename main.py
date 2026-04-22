import time
import json
import requests
import random
import os
from playwright.sync_api import sync_playwright

# ==========================================
# ดึงค่ามาจาก GitHub Secrets
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_TOKEN")
LINE_USER_ID = "U83db35d35e737360f33c01f9705772c1"

PROXY_SERVER = os.getenv("PROXY_SERVER")
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

PART_NUMBER = "MU9D3TH/A"
ZIP_CODE = "10330"

def send_line_bot(message):
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
        print(f"⚠️ LINE API Error: {e}")

def check_stock_and_report():
    with sync_playwright() as p:
        print(f"--- [{time.strftime('%H:%M:%S')}] เริ่มตรวจสอบสต็อกผ่าน Proxy ---")
        
        # ตั้งค่า Proxy ตรงนี้
        proxy_settings = None
        if PROXY_SERVER and PROXY_USERNAME and PROXY_PASSWORD:
            proxy_settings = {
                "server": PROXY_SERVER,
                "username": PROXY_USERNAME,
                "password": PROXY_PASSWORD
            }

        browser = p.chromium.launch(
            headless=True,
            proxy=proxy_settings, # สวมรอยด้วย IP ของ Webshare
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        api_url = f"https://www.apple.com/th-edu/shop/fulfillment-messages?parts.0={PART_NUMBER}&location={ZIP_CODE}"
        
        try:
            page.goto("https://www.apple.com/th-edu/shop/buy-mac/mac-mini", wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(2, 3))

            response = page.goto(api_url, wait_until="domcontentloaded", timeout=20000)
            
            if response.status == 541:
                send_line_bot("🚨 Proxy ที่ใช้อยู่ถูก Apple บล็อก (541) ลองเปลี่ยน IP ใหม่ในโค้ด")
                return

            raw_text = page.inner_text("body")
            if page.locator("pre").count() > 0:
                raw_text = page.locator("pre").inner_text()

            data = json.loads(raw_text)
            stores = data.get('body', {}).get('content', {}).get('pickupMessage', {}).get('stores', [])
            
            found_any = False
            report_msg = f"🤖 สถานะสินค้า Mac Mini\nเวลา: {time.strftime('%H:%M')}\n"
            report_msg += "--------------------------\n"

            for store in stores:
                name = store.get('storeName', '')
                avail = store.get('partsAvailability', {}).get(PART_NUMBER, {})
                status = avail.get('pickupDisplay') 
                quote = avail.get('pickupSearchQuote', 'ไม่มีข้อมูล')

                if status == "available":
                    found_any = True
                    report_msg += f"✅ {name}: {quote}\n"

            if found_any:
                report_msg = "🚨 [พบสินค้ามีของ!] 🚨\n" + report_msg
                send_line_bot(report_msg)
                print("--- มีของ ส่ง LINE แล้ว ---")
            else:
                print("--- ไม่มีของข้ามการแจ้งเตือน ---")

        except Exception as e:
            print(f"⚠️ Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_stock_and_report()
