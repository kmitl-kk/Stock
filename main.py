import time
import json
import requests
import random
from playwright.sync_api import sync_playwright

# ==========================================
# CONFIGURATION
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = "KfiECdbjwSpb0Hb4gr4mE/FDEftCdD8lPLr49ajgGVauoFZYqyLyT6Qr0ukzPw/fCsBNLfAX+Isofj1i7i288H8TTNyiwQ9AMWGQW8J1IoFzqANuK2gzCWWd1VvtLiFlzJQ3xQJInXvT3NPzEcxu9AdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "U83db35d35e737360f33c01f9705772c1"

PART_NUMBER = "MU9D3TH/A"
ZIP_CODE = "10330"

def send_line_bot(message):
    """ฟังก์ชันส่งข้อความผ่าน LINE Messaging API"""
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
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if response.status_code == 200:
            print(f"✅ LINE Bot: ส่งข้อความสำเร็จ")
        else:
            print(f"❌ LINE Bot Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ ไม่สามารถเชื่อมต่อกับ LINE API ได้: {e}")

def check_stock_and_report():
    """เช็คสต็อกและส่งสรุปผลเข้า LINE ทันที"""
    with sync_playwright() as p:
        print(f"--- [{time.strftime('%H:%M:%S')}] เริ่มตรวจสอบสต็อก Apple Store ---")
        
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        api_url = f"https://www.apple.com/th-edu/shop/fulfillment-messages?parts.0={PART_NUMBER}&location={ZIP_CODE}"
        
        try:
            # 1. Landing (พรางตัว)
            page.goto("https://www.apple.com/th-edu/shop/buy-mac/mac-mini", wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(2, 3))

            # 2. ดึงข้อมูลสต็อก
            response = page.goto(api_url, wait_until="domcontentloaded", timeout=20000)
            
            if response.status == 541:
                send_line_bot("🚨 บอทถูกบล็อก (Error 541): Apple ตรวจพบการเข้าถึงผิดปกติ")
                return

            raw_text = page.inner_text("body")
            if page.locator("pre").count() > 0:
                raw_text = page.locator("pre").inner_text()

            data = json.loads(raw_text)
            stores = data.get('body', {}).get('content', {}).get('pickupMessage', {}).get('stores', [])
            
            found_any = False
            report_msg = f"🤖 รายงานสถานะสินค้า\nรหัส: {PART_NUMBER}\nเวลา: {time.strftime('%H:%M')}\n"
            report_msg += "--------------------------\n"

            for store in stores:
                name = store.get('storeName', '')
                avail = store.get('partsAvailability', {}).get(PART_NUMBER, {})
                status = avail.get('pickupDisplay') # 'available' หรือ 'unavailable'
                quote = avail.get('pickupSearchQuote', 'ไม่มีข้อมูล')

                if status == "available":
                    found_any = True
                    report_msg += f"✅ {name}: {quote}\n"
                else:
                    report_msg += f"⚪ {name}: {quote}\n"

            if found_any:
                report_msg = "🚨 [พบสินค้ามีของ!] 🚨\n" + report_msg
            
            # ส่งผลลัพธ์เข้า LINE
            send_line_bot(report_msg)
            print("--- ตรวจสอบเรียบร้อยและส่ง LINE แล้ว ---")

        except Exception as e:
            err_text = f"⚠️ บอทเกิดข้อผิดพลาด: {str(e)}"
            print(err_text)
            send_line_bot(err_text)
        finally:
            browser.close()

if __name__ == "__main__":
    # รันการเช็คและส่งข้อมูลทันที
    check_stock_and_report()
