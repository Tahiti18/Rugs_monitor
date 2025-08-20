# src/scraper_ws.py
import os, json, asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from sqlalchemy import text

# IMPORTANT: your code lives under src/, so import via src.<module>
from src.db_sql import get_engine, init_db

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "https://rugs.fun")
HEADLESS   = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO_MS = int(os.getenv("SLOW_MO_MS", "0"))
USER_AGENT = os.getenv("USER_AGENT", "")

# -------------------- DB helpers --------------------

def ts_now() -> str:
    return datetime.now(timezone.utc).isoformat()

async def store_round(round_id, ts_iso, mult, raw_json=None):
    eng = get_engine()
    with eng.begin() as c:
        c.execute(
            text(
                "INSERT OR IGNORE INTO rounds "
                "(round_id, timestamp, bust_multiplier, raw_json) "
                "VALUES (:rid, :ts, :bm, :raw)"
            ),
            {
                "rid": str(round_id),
                "ts": ts_iso,
                "bm": float(mult),
                "raw": json.dumps(raw_json) if raw_json is not None else None,
            },
        )
    print(f"[db] + round {round_id} @ {mult}x")

# -------------------- Normalization --------------------

ASYNC_PRINT_SAMPLE = True  # first few frames/JSONs will print for inspection

async def handle_payload(obj):
    """
    Normalize common shapes into (round_id, timestamp_iso, multiplier).
    Extend this once you see rugs.fun real keys in logs.
    """
    if isinstance(obj, dict):
        # Try common key names
        rid = (
            obj.get("roundId") or obj.get("round_id") or obj.get("id") or obj.get("round")
        )
        mult = (
            obj.get("bust") or obj.get("bustMultiplier") or
            obj.get("multiplier") or obj.get("result") or obj.get("crashPoint")
        )
        ts  = obj.get("timestamp") or obj.get("ts") or None

        if rid is not None and mult is not None:
            try:
                mult = float(mult)
                ts_iso = (
                    ts if isinstance(ts, str)
                    else datetime.now(timezone.utc).isoformat()
                )
                await store_round(rid, ts_iso, mult, raw_json=obj)
            except Exception as e:
                print("[normalize] error storing round:", e)

        # Recurse into nested lists/dicts
        for v in obj.values():
            if isinstance(v, list):
                for item in v:
                    await handle_payload(item)
            elif isinstance(v, dict):
                await handle_payload(v)

    elif isinstance(obj, list):
        for item in obj:
            await handle_payload(item)

# -------------------- Scraper core --------------------

async def run_scraper():
    init_db()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO_MS)
        context = await browser.new_context(user_agent=USER_AGENT or None)
        page = await context.new_page()

        # WebSocket frames
        async def on_ws(ws):
            print(f"[ws] connected: {urlparse(ws.url).netloc}")

            async def on_frame(frame):
                data = frame.payload
                # Only try JSON-ish frames
                if not data:
                    return
                # Quick gate: frames that start with { or [
                if isinstance(data, str) and data[:1] in ("{", "["):
                    try:
                        obj = json.loads(data)
                        # Print a few samples for key discovery
                        global ASYNC_PRINT_SAMPLE
                        if ASYNC_PRINT_SAMPLE:
                            print("[ws sample]", str(obj)[:500])
                            ASYNC_PRINT_SAMPLE = False
                        await handle_payload(obj)
                    except Exception:
                        pass

            ws.on("framereceived", on_frame)

        context.on("websocket", on_ws)

        # XHR/Fetch JSON responses
        async def on_response(resp):
            try:
                ctype = (resp.headers.get("content-type") or "").lower()
                if "json" in ctype:
                    url = resp.url.lower()
                    if any(k in url for k in ["history", "round", "crash", "result", "game"]):
                        obj = await resp.json()
                        # Print a sample once for discovery
                        global ASYNC_PRINT_SAMPLE
                        if ASYNC_PRINT_SAMPLE:
                            print("[xhr sample]", str(obj)[:500])
                            ASYNC_PRINT_SAMPLE = False
                        await handle_payload(obj)
            except Exception as e:
                print("[xhr] error:", e)

        page.on("response", on_response)

        print(f"[nav] {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until="load", timeout=120_000)

        # Fallback DOM scan (grabs text like "2.34x" if present)
        async def dom_poll():
            try:
                nodes = await page.query_selector_all("body *")
                for el in nodes[:400]:
                    try:
                        txt = (await el.text_content() or "").strip().lower()
                    except Exception:
                        continue
                    if txt.endswith("x") and len(txt) <= 8:
                        # crude filter for values like "2.34x"
                        num = txt[:-1]
                        try:
                            val = float(num)
                            rid = f"dom-{int(datetime.now().timestamp() * 1000)}"
                            await store_round(rid, ts_now(), val, {"source": "dom"})
                        except Exception:
                            pass
            except Exception as e:
                print("[dom] error:", e)

        # Main loop
        while True:
            await dom_poll()
            await asyncio.sleep(3)

# -------------------- Entrypoint --------------------

if __name__ == "__main__":
    asyncio.run(run_scraper())
