#!/usr/bin/env python3
import requests
import json
import time
import random
import logging
import os
from datetime import datetime
from typing import Optional

STORE_IDS = [
    "R426",
    "R427",
    "R469",
    "R539",
    "R597",
]

PART_NUMBERS = [
    "MYH33TH/A",
    "MYHY3TH/A",
    "MYJ13TH/A",
    "MYJ33TH/A",
]

COUNTRY = "th"
CHECK_INTERVAL = 60

TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

LINE_ENABLED = False
LINE_CHANNEL_ACCESS_TOKEN = "YOUR_LINE_CHANNEL_ACCESS_TOKEN"
LINE_USER_ID = "YOUR_LINE_USER_ID"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mac_mini_stock.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

ACCEPT_LANGUAGES = [
    "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
    "th,en-US;q=0.9,en;q=0.8",
    "en-US,en;q=0.9,th;q=0.8",
]

def build_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": f"https://www.apple.com/{COUNTRY}/shop/buy-mac/mac-mini",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
    }

def build_stock_url(store_id: str, part_numbers: list) -> str:
    parts_param = "&".join(f"parts.{i}={p}" for i, p in enumerate(part_numbers))
    return (
        f"https://www.apple.com/{COUNTRY}/shop/fulfillment-messages"
        f"?{parts_param}"
        f"&pl=true"
        f"&mts.0=compact"
        f"&mts.1=regular"
        f"&cppart=UNLOCKED"
    )

def check_stock(session: requests.Session, store_id: str) -> Optional[dict]:
    url = build_stock_url(store_id, PART_NUMBERS)
    try:
        time.sleep(random.uniform(1.5, 4.0))
        resp = session.get(url, headers=build_headers(), timeout=15)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 541:
            log.warning(f"[Store {store_id}] Got 541 – rotating session...")
            return None
        else:
            log.warning(f"[Store {store_id}] HTTP {resp.status_code}")
            return None
    except requests.RequestException as e:
        log.error(f"[Store {store_id}] Request failed: {e}")
        return None

def parse_availability(data: dict) -> list[dict]:
    available = []
    try:
        stores = (
            data.get("body", {})
                .get("content", {})
                .get("pickupMessage", {})
                .get("stores", [])
        )
        for store in stores:
            store_name = store.get("storeName", "Unknown Store")
            store_num  = store.get("storeNumber", "")
            parts_info = store.get("partsAvailability", {})
            for part_num, part_data in parts_info.items():
                pickup_search = part_data.get("pickupSearchQuote", "")
                pickup_display = part_data.get("pickupDisplay", "")
                product_title = part_data.get("messageTypes", {}).get("compact", {}).get("storePickupProductTitle", "")
                
                is_available = (
                    pickup_display == "available"
                    or "today" in pickup_search.lower()
                    or " น " in pickup_search
                )
                
                if is_available:
                    available.append({
                        "store_name": store_name,
                        "store_id": store_num,
                        "part_number": part_num,
                        "product_title": product_title,
                        "pickup_quote": pickup_search,
                    })
    except Exception as e:
        log.error(f"Failed to parse availability: {e}")
    return available

def send_telegram(message: str) -> bool:
    if not TELEGRAM_ENABLED or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        log.info("[Telegram] Skipped (not configured)")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            log.info("[Telegram] Notification sent!")
            return True
        else:
            log.error(f"[Telegram] Failed: {resp.status_code} {resp.text}")
    except Exception as e:
        log.error(f"[Telegram] Error: {e}")
    return False

def send_line(message: str) -> bool:
    if not LINE_ENABLED or LINE_CHANNEL_ACCESS_TOKEN == "YOUR_LINE_CHANNEL_ACCESS_TOKEN":
        log.info("[LINE] Skipped (not configured)")
        return False
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}],
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            log.info("[LINE] Notification sent!")
            return True
        else:
            log.error(f"[LINE] Failed: {resp.status_code} {resp.text}")
    except Exception as e:
        log.error(f"[LINE] Error: {e}")
    return False

def build_notification(available_items: list[dict]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    lines = [
        "<b>Mac mini M4 — STOCK ALERT!</b>",
        f"{now}",
        "",
        "<b>พร้อมรับ:</b>",
    ]
    for item in available_items:
        lines.append(
            f"<b>{item['product_title']}</b>\n"
            f"{item['store_name']}\n"
            f"{item['part_number']}\n"
            f"{item['pickup_quote']}"
        )
    lines += [
        "",
        "https://www.apple.com/th/shop/buy-mac/mac-mini",
        "รีบก่อนหมด!",
    ]
    return "\n".join(lines)

def notify(available_items: list[dict]):
    message = build_notification(available_items)
    plain_message = (message
        .replace("<b>", "").replace("</b>", "")
        .replace("<i>", "").replace("</i>", ""))
        
    if TELEGRAM_ENABLED:
        send_telegram(message)
    if LINE_ENABLED:
        send_line(plain_message)

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(build_headers())
    adapter = requests.adapters.HTTPAdapter(max_retries=2)
    session.mount("https://", adapter)
    return session

def run():
    log.info("=" * 60)
    log.info(" Mac mini M4 Stock Checker Started")
    log.info(f" Stores : {', '.join(STORE_IDS)}")
    log.info(f" Parts : {', '.join(PART_NUMBERS)}")
    log.info(f" Interval: {CHECK_INTERVAL}s")
    log.info("=" * 60)

    notified_keys = set()
    session = create_session()
    session_created = time.time()

    while True:
        log.info(f" Checking stock... [{datetime.now().strftime('%H:%M:%S')}]")

        if time.time() - session_created > 600:
            session = create_session()
            session_created = time.time()
            log.info(" Session rotated")

        all_available = []
        for store_id in STORE_IDS:
            data = check_stock(session, store_id)
            if data:
                items = parse_availability(data)
                if items:
                    log.info(f" [{store_id}] Found {len(items)} available item(s)")
                    all_available.extend(items)
                else:
                    log.info(f" [{store_id}] No stock available")
            else:
                log.warning(f" [{store_id}] Could not fetch data")

            time.sleep(random.uniform(2, 5))

        new_items = []
        for item in all_available:
            key = f"{item['store_id']}_{item['part_number']}"
            if key not in notified_keys:
                new_items.append(item)
                notified_keys.add(key)

        if new_items:
            log.info(f" ALERT: {len(new_items)} new available item(s) found!")
            notify(new_items)

        log.info(f" Next check in {CHECK_INTERVAL}s...\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run()
