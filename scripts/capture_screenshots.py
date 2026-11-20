"""Capture screenshots of the synthetic Streamlit demo for the project README.

Runs against the locally launched app in CI. No private coursework data is used.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8501"
OUT = Path("screenshots")
OUT.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1600, "height": 1050}, device_scale_factor=1)
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
    page.get_by_text("Overall department performance", exact=False).first.wait_for(timeout=60000)
    page.wait_for_timeout(4500)
    page.screenshot(path=str(OUT / "dashboard.png"), full_page=True)

    page.get_by_text("Instructor explorer", exact=False).first.click()
    page.get_by_text("Instructor performance", exact=True).first.wait_for(timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "instructor-explorer.png"), full_page=True)

    assert (OUT / "dashboard.png").stat().st_size > 20000
    assert (OUT / "instructor-explorer.png").stat().st_size > 20000
    browser.close()

print("Captured screenshots/dashboard.png and screenshots/instructor-explorer.png")
