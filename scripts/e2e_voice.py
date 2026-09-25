"""
E2E browser test for the voice-entry flow (Phase 5D verification).

Uses Chromium with a fake microphone:
  --use-fake-ui-for-media-stream   → auto-grant mic permission
  --use-fake-device-for-media-stream → feed a fake audio stream

Run while the dev server is up on :8070:
  python scripts/e2e_voice.py
"""

from __future__ import annotations

import re
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8070"


def login(page):
    page.goto(f"{BASE}/auth/login/")
    page.fill('input[name="phone"]', "09000000000")
    page.click('button[type="submit"]')
    page.wait_for_url("**/auth/otp/")
    # DEBUG code appears as «کد: 123456» on the verify page — not the phone!
    m = re.search(r"کد:\s*(\d{6})", page.inner_text("body"))
    page.fill('input[name="code"]', m.group(1))
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard/")
    print("✓ logged in →", page.url)


def main() -> int:
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
            ],
        )
        page = browser.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        login(page)

        page.goto(f"{BASE}/ai/voice/")
        page.wait_for_selector("text=ثبت با صدا")
        print("✓ voice page loaded")

        # Start recording with the fake mic
        page.click("text=🎙️ ضبط از میکروفن")
        page.wait_for_timeout(2500)  # record ~2.5s
        recording = page.locator("text=⏹ پایان ضبط")
        print("recording UI visible:", recording.count() > 0)

        # Stop → triggers upload
        page.click("text=⏹ پایان ضبط")
        page.wait_for_timeout(1500)

        # Expect a voice note card to appear and finish transcribing
        page.wait_for_selector("#voice-notes-list .card", timeout=8000)
        body = page.inner_text("#voice-notes-list")
        print("card after upload (first 120 chars):", body.strip()[:120].replace("\n", " | "))
        ok_transcribed = "رونویسی" in body
        print("transcription finished in card:", ok_transcribed)

        if errors:
            print("\nJS ERRORS CAPTURED:")
            for e in errors[:10]:
                print("  ✗", e[:200])
        else:
            print("no JS errors")

        browser.close()
        return 0 if (ok_transcribed and not errors) else 1


if __name__ == "__main__":
    sys.exit(main())
