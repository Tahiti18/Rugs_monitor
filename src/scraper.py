import asyncio
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from db import init_db, insert_round

load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "https://rugs.fun")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO_MS = int(os.getenv("SLOW_MO_MS", "0"))
USER_AGENT = os.getenv("USER_AGENT", "")


DOM_SELECTORS = {
    # TODO: Adjust to actual selectors once inspected.
    # Example placeholders:
    "last_result_row": "div.results-row:first-child",
    "all_results_rows": "div.results-row",
    "multiplier_cell": ".multiplier",
    "round_id_cell": ".round-id",
    "timestamp_cell": ".ts"
}

def iso_utc_now():
    return datetime.now(timezone.utc).isoformat()

async def main():
    init_db()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO_MS)
        context = await browser.new_context(user_agent=USER_AGENT or None)
        page = await context.new_page()

        # Network sniffer: try to capture API payloads with round outcomes
        async def on_response(response):
            try:
                url = response.url
                parsed = urlparse(url)
                if any(key in url.lower() for key in ["history", "round", "crash", "result"]):
                    if "json" in (response.headers.get("content-type", "")).lower():
                        data = await response.json()
                        # Heuristic parse: look for likely fields
                        # We will dump the first few for inspection and then try structured extraction.
                        if isinstance(data, dict) or isinstance(data, list):
                            await handle_possible_payload(data)
            except Exception as e:
                # swallow but print
                print(f"[resp] error: {e}")

        page.on("response", on_response)

        # Navigate
        print(f"Navigating to {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="load", timeout=120000)

        # Minimal idle loop: read DOM every few seconds
        while True:
            try:
                await read_dom(page)
            except Exception as e:
                print(f"[dom] error: {e}")
            await asyncio.sleep(3)

async def handle_possible_payload(data):
    """Attempt to normalize common crash-game payload shapes."""
    # This is intentionally permissive; adapt to the site's API after observing logs.
    if isinstance(data, dict):
        # Look for a key that contains an array of rounds
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], (dict, int, float, str)):
                await handle_possible_payload(v)
        # Or a single round dict
        maybe = normalize_round_dict(data)
        if maybe:
            round_id, ts, mult, raw = maybe
            insert_round(round_id, ts, mult, raw_json=json.dumps(data))
            print(f"[db] + round {round_id} @ {mult}x (payload)" )
    elif isinstance(data, list):
        for item in data:
            await handle_possible_payload(item)

def normalize_round_dict(d):
    """Return (round_id, timestamp_iso, bust_multiplier, raw_json) if plausible, else None."""
    keys = {k.lower(): k for k in d.keys()}
    # Common field guesses
    rid = d.get(keys.get("round_id") or keys.get("id") or keys.get("round"))
    mult = d.get(keys.get("multiplier") or keys.get("bust") or keys.get("result"))
    ts = d.get(keys.get("timestamp") or keys.get("time") or keys.get("ts"))

    # Attempt to coerce
    if rid is None or mult is None:
        return None
    try:
        mult = float(mult)
    except Exception:
        return None
    if ts is None:
        ts_iso = datetime.now(timezone.utc).isoformat()
    else:
        # Try to parse; if not parseable, store now
        try:
            ts_iso = datetime.fromisoformat(str(ts).replace("Z","+00:00")).astimezone(timezone.utc).isoformat()
        except Exception:
            ts_iso = datetime.now(timezone.utc).isoformat()
    return (str(rid), ts_iso, mult, json.dumps(d))

async def read_dom(page):
    # Generic DOM scrape: extract latest rows if visible
    rows = await page.query_selector_all(DOM_SELECTORS["all_results_rows"])
    for row in rows[:10]:  # limit work per loop
        rid = await row.get_attribute("data-round-id")
        mult_el = await row.query_selector(DOM_SELECTORS["multiplier_cell"])
        ts_el = await row.query_selector(DOM_SELECTORS["timestamp_cell"])

        if not mult_el:
            continue
        mult_txt = (await mult_el.text_content() or "").strip().lower().replace("x","")
        try:
            mult = float(mult_txt)
        except Exception:
            continue

        if not rid:
            # try child
            rid_el = await row.query_selector(DOM_SELECTORS["round_id_cell"])
            rid = (await rid_el.text_content() or "").strip() if rid_el else None
        if not rid:
            rid = f"dom-{int(datetime.now().timestamp()*1000)}"

        ts_txt = (await ts_el.text_content() or "").strip() if ts_el else None
        if ts_txt:
            try:
                ts_iso = datetime.fromisoformat(ts_txt.replace("Z","+00:00")).astimezone(timezone.utc).isoformat()
            except Exception:
                ts_iso = datetime.now(timezone.utc).isoformat()
        else:
            ts_iso = datetime.now(timezone.utc).isoformat()

        insert_round(rid, ts_iso, mult, raw_json=None)
        print(f"[db] + round {rid} @ {mult}x (dom)")

if __name__ == "__main__":
    asyncio.run(main())
