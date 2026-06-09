"""
Indeed Job Scraper
------------------
Searches Indeed for jobs and returns listings matching your config.
Indeed is more scraper-friendly than LinkedIn but still uses bot detection.
"""

import asyncio
import random
from urllib.parse import urlencode
from playwright.async_api import async_playwright


INDEED_URL = "https://www.indeed.com/jobs"


async def human_delay(min_ms=800, max_ms=2500):
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def search_indeed(config: dict) -> list[dict]:
    """Search Indeed for jobs matching config. Returns list of job dicts."""
    indeed_config = config.get("indeed", {})
    search_config = config.get("search", {})

    keywords = " ".join(search_config.get("keywords", ["software engineer"]))
    location = search_config.get("location", "United States")
    max_jobs = indeed_config.get("max_jobs_per_run", 20)
    remote_only = search_config.get("remote_only", False)

    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=indeed_config.get("browser_profile_path", "./browser_profile_indeed"),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            no_viewport=True,
        )

        page = await browser.new_page()

        params = {"q": keywords, "l": location}
        if remote_only:
            params["remotejob"] = "032b3046-06a3-4876-8dfd-474eb5e7ed11"

        url = f"{INDEED_URL}?{urlencode(params)}"
        await page.goto(url)
        await human_delay(2000, 4000)

        # Handle cookie consent if present
        try:
            consent_btn = await page.wait_for_selector("button#onetrust-accept-btn-handler", timeout=3000)
            if consent_btn:
                await consent_btn.click()
                await human_delay()
        except Exception:
            pass

        collected = 0
        page_num = 0

        while collected < max_jobs:
            # Wait for job cards
            try:
                await page.wait_for_selector(".job_seen_beacon, .tapItem", timeout=8000)
            except Exception:
                print("  Indeed: No job cards found (possible CAPTCHA or layout change)")
                break

            job_cards = await page.query_selector_all(".job_seen_beacon, .tapItem")

            for card in job_cards:
                if collected >= max_jobs:
                    break
                try:
                    title_el = await card.query_selector("h2.jobTitle span[title], h2.jobTitle a span")
                    company_el = await card.query_selector("[data-testid='company-name'], .companyName")
                    location_el = await card.query_selector("[data-testid='text-location'], .companyLocation")
                    link_el = await card.query_selector("h2.jobTitle a")

                    if not title_el or not link_el:
                        continue

                    title = (await title_el.inner_text()).strip()
                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                    loc = (await location_el.inner_text()).strip() if location_el else "Unknown"
                    href = await link_el.get_attribute("href")

                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://www.indeed.com" + href

                    # Filter excluded companies
                    excluded = config.get("filters", {}).get("exclude_companies", [])
                    if any(exc.lower() in company.lower() for exc in excluded):
                        continue

                    # Indeed doesn't have "Easy Apply" — all applications go through their system
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": href,
                        "easy_apply": True,  # Indeed has its own apply flow
                        "source": "indeed",
                    })
                    collected += 1

                except Exception:
                    continue

            # Paginate
            page_num += 1
            next_url = f"{INDEED_URL}?{urlencode({**params, 'start': page_num * 10})}"
            await page.goto(next_url)
            await human_delay(2500, 4500)

        await browser.close()

    return jobs
