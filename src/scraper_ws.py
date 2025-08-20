# scraper_ws.py
import asyncio, json, os
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from sqlalchemy import text

from db_sql import get_engine  # assuming db_sql.py is also in root

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "https://rugs.fun")
HEADLESS   = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO_MS = int(os.getenv("SLOW_MO_MS", "0"))
USER_AGENT = os.getenv("USER_AGENT", "")

def ts_now():
    return datetime.now(timezone.utc).isoformat()

async def store_round(round_id, ts_iso, mult, raw_json=None):
    eng = get_engine()
    with eng.begin() as c:
        c.execute(
            text("INSERT OR IGNORE INTO rounds (round_id, timestamp, bust_multiplier, raw_json) "
                 "VALUES (:rid, :ts, :bm, :raw)"),
            {"rid": str(round_id), "ts": ts_iso, "bm": float(mult),
             "raw": json.dumps(raw_json) if raw_json else None}
        )
    print(f"[db] + round {round_id} @ {mult}x")

async def handle_payload(obj):
    """
    Normalize incoming payloads from websocket.
    """
    if isinstance(obj, dict):
        rid  = obj.get("roundId") or obj.get("round_id") or obj.get("id") or obj.get("round")
        mult = obj.get("bust") or obj.get("bustMultiplier") or obj.get("multiplier")
        if rid and mult:
            await store_round(rid, ts_now(), mult, obj)
    elif isinstance(obj, list):
        for entry in obj:
            await handle_payload(entry)

async def run_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO_MS)
        context = await browser.new_context(user_agent=USER_AGENT or None)
        page = await context.new_page()

        async def on_ws(ws):
            ws_url = urlparse(ws.url).netloc
            print(f"[ws] connected: {ws_url}")

            ws.on("framereceived", lambda msg: asyncio.create_task(process_frame(msg)))

        async def process_frame(msg):
            try:
                payload = json.loads(msg)
                await handle_payload(payload)
            except Exception as e:
                print(f"[frame error] {e} :: {msg[:200]}")

        page.on("websocket", on_ws)
        print(f"[nav] {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until="domcontentloaded")

        await asyncio.sleep(3600)  # run for 1h, adjust as needed
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())
