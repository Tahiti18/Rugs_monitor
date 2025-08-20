import asyncio
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from db_sql import init_db, get_engine
from sqlalchemy import text

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "https://rugs.fun")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO_MS = int(os.getenv("SLOW_MO_MS", "0"))
USER_AGENT = os.getenv("USER_AGENT", "")

def ts_now():
    return datetime.now(timezone.utc).isoformat()

async def store_round(round_id, ts_iso, mult, raw_json=None):
    eng = get_engine()
    with eng.begin() as c:
        c.execute(text(
            "INSERT OR IGNORE INTO rounds (round_id, timestamp, bust_multiplier, raw_json) VALUES (:rid, :ts, :bm, :raw)"
        ), {"rid": str(round_id), "ts": ts_iso, "bm": float(mult), "raw": json.dumps(raw_json) if raw_json else None})

async def main():
    init_db()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO_MS)
        context = await browser.new_context(user_agent=USER_AGENT or None)
        page = await context.new_page()

        # Log all WS frames (received). You will refine the filter after observing payloads.
        async def on_ws(ws):
            async def on_frame(frame):
                try:
                    data = frame.payload
                    # Some frames are JSON strings; try to parse
                    try:
                        obj = json.loads(data)
                        await handle_payload(obj)
                    except Exception:
                        pass
                except Exception as e:
                    print("[ws] frame error:", e)
            ws.on("framereceived", on_frame)
        context.on("websocket", on_ws)

        async def on_response(resp):
            try:
                ctype = (resp.headers.get("content-type","")).lower()
                if "json" in ctype:
                    url = resp.url.lower()
                    if any(k in url for k in ["history", "round", "crash", "result", "game"]):
                        obj = await resp.json()
                        await handle_payload(obj)
            except Exception as e:
                print("[xhr] error:", e)
        page.on("response", on_response)

        await page.goto(TARGET_URL, wait_until="load", timeout=120000)

        # Fallback DOM polling (you will tune selectors after first inspection)
        while True:
            try:
                rows = await page.query_selector_all("div,li,span")
                for el in rows[:200]:
                    txt = (await el.text_content() or "").strip().lower()
                    # Heuristic: look for "x" suffix like "2.45x"
                    if txt.endswith("x"):
                        try:
                            val = float(txt[:-1])
                            rid = f"dom-{int(datetime.now().timestamp()*1000)}"
                            await store_round(rid, ts_now(), val, raw_json={"source":"dom"})
                        except Exception:
                            pass
            except Exception as e:
                print("[dom] error:", e)
            await asyncio.sleep(3)

async def handle_payload(obj):
    # Best-effort normalization; refine after you see real keys.
    if isinstance(obj, dict):
        # Check for single round
        rid = obj.get("round_id") or obj.get("id") or obj.get("round")
        mult = obj.get("bust_multiplier") or obj.get("bust") or obj.get("multiplier") or obj.get("result")
        ts = obj.get("timestamp") or obj.get("ts") or None
        if rid is not None and mult is not None:
            try:
                mult = float(mult)
                ts_iso = ts if isinstance(ts, str) else datetime.now(timezone.utc).isoformat()
                await store_round(rid, ts_iso, mult, raw_json=obj)
            except Exception:
                pass
        # Recurse into arrays in dict
        for k,v in obj.items():
            if isinstance(v, list):
                for item in v:
                    await handle_payload(item)
    elif isinstance(obj, list):
        for item in obj:
            await handle_payload(item)

if __name__ == "__main__":
    asyncio.run(main())
