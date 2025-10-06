# scripts/visit.py
import os
import random
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

# --- CONFIG ---
URL = os.environ.get("TARGET_URL", "https://example.com")  # override via env or GitHub secret
SCREENSHOT_DIR = Path("tmp_screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENTS = [
    # desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    # mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    # some common bots (if you really need them for test, but generally avoid)
    # "Googlebot/2.1 (+http://www.google.com/bot.html)",
]

def random_sleep(a=1.0, b=3.0):
    time.sleep(random.uniform(a, b))

def perform_interaction(page):
    # basic interactions: wait, scroll, try clicking some visible links
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except PWTimeoutError:
        pass

    # Scroll down gradually
    page.evaluate("""
        () => {
            const step = window.innerHeight / 2;
            let pos = 0;
            const steps = 4;
            for (let i=0;i<steps;i++){
                pos += step;
                window.scrollTo({top: pos, behavior: 'smooth'});
            }
        }
    """)
    random_sleep(0.8, 2.0)

    # Try clicking a random internal link (if any)
    anchors = page.query_selector_all("a[href]:not([href^='mailto:']):not([href^='tel:'])")
    candidates = []
    for a in anchors:
        try:
            href = a.get_attribute("href")
            # skip anchors that jump or external ones (keep some internal tests)
            if href and not href.startswith("#") and (href.startswith("/") or page.url.split("/")[2] in href):
                candidates.append(a)
        except Exception:
            continue

    if candidates:
        el = random.choice(candidates)
        try:
            el.scroll_into_view_if_needed()
            random_sleep(0.3, 1.0)
            el.click(timeout=4000)
            random_sleep(1.0, 2.0)
        except Exception:
            pass

def main():
    ua = random.choice(USER_AGENTS)
    timestamp = int(time.time())
    screenshot_path = SCREENSHOT_DIR / f"visit_{timestamp}.png"

    print(f"[info] Visiting {URL} with UA: {ua}")

    with sync_playwright() as p:
        # launch chromium headless with recommended flags for CI
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ])
        context = browser.new_context(user_agent=ua, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            print(f"[warn] goto error: {e}")

        try:
            perform_interaction(page)
        except Exception as e:
            print(f"[warn] interaction error: {e}")

        # final screenshot for debugging / artifact
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"[info] saved screenshot to {screenshot_path}")
        except Exception as e:
            print(f"[warn] screenshot failed: {e}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
