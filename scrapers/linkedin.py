"""
LinkedIn Job Scraper
--------------------
Searches LinkedIn Jobs and returns listings that match your config.
Uses Playwright in headful mode so you stay logged in via your browser profile.

NOTE: LinkedIn actively detects bots. This scraper:
  - Uses your real browser profile (you must be logged in)
  - Adds human-like delays between actions
  - Stops and waits if a CAPTCHA is detected
"""

import asyncio
import random
from playwright.async_api import async_playwright


LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"


async def human_delay(min_ms=800, max_ms=2200):
    """Random delay to mimic human browsing."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def search_linkedin(config: dict) -> list[dict]:
    """Search LinkedIn for jobs matching config. Returns list of job dicts."""
    li_config = config.get("linkedin", {})
    search_config = config.get("search", {})

    keywords = " ".join(search_config.get("keywords", ["software engineer"]))
    location = search_config.get("location", "United States")
    max_jobs = li_config.get("max_jobs_per_run", 20)
    easy_apply_only = li_config.get("easy_apply_only", True)

    jobs = []

    async with async_playwright() as p:
        # Use persistent context so you're already logged in
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=li_config.get("browser_profile_path", "./browser_profile"),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            no_viewport=True,
        )

        page = await browser.new_page()

        # Build search URL
        params = {
            "keywords": keywords,
            "location": location,
            "f_LF": "f_AL" if easy_apply_only else "",  # Easy Apply filter
        }

        exp_level = search_config.get("experience_level")
        if exp_level:
            level_map = {
                "internship": "1", "entry": "2", "associate": "3",
                "mid": "4", "director": "5", "executive": "6"
            }
            if exp_level in level_map:
                params["f_E"] = level_map[exp_level]

        query_string = "&".join(f"{k}={v}" for k, v in params.items() if v)
        url = f"{LINKEDIN_JOBS_URL}?{query_string}"

        await page.goto(url)
        await human_delay(2000, 3500)

        # Check for CAPTCHA or login wall
        if "checkpoint" in page.url or "login" in page.url:
            print("\n  ⚠️  LinkedIn is asking you to log in or complete a CAPTCHA.")
            print("  Please complete it in the browser window, then press Enter here...")
            input()

        # Scroll and collect job cards
        collected = 0
        while collected < max_jobs:
            # Get all job cards on the page
            job_cards = await page.query_selector_all(".job-search-card, .jobs-search-results__list-item")

            for card in job_cards:
                if collected >= max_jobs:
                    break
                try:
                    title_el = await card.query_selector(".job-search-card__title, .job-card-list__title")
                    company_el = await card.query_selector(".job-search-card__company-name, .job-card-container__company-name")
                    location_el = await card.query_selector(".job-search-card__location, .job-card-container__metadata-item")
                    link_el = await card.query_selector("a.job-search-card__title-link, a.job-card-list__title")
                    easy_apply_el = await card.query_selector(".job-search-card__easy-apply-label, .job-card-container__apply-method")

                    if not title_el or not link_el:
                        continue

                    title = (await title_el.inner_text()).strip()
                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                    location = (await location_el.inner_text()).strip() if location_el else "Unknown"
                    url = await link_el.get_attribute("href")
                    easy_apply = easy_apply_el is not None

                    if url and not url.startswith("http"):
                        url = "https://www.linkedin.com" + url

                    # Filter by excluded companies/keywords
                    excluded = config.get("filters", {}).get("exclude_companies", [])
                    if any(exc.lower() in company.lower() for exc in excluded):
                        continue

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url.split("?")[0],  # clean URL
                        "easy_apply": easy_apply,
                        "source": "linkedin",
                    })
                    collected += 1

                except Exception:
                    continue

            # Try to go to next page
            next_btn = await page.query_selector("button[aria-label='View next page']")
            if not next_btn or collected >= max_jobs:
                break

            await next_btn.click()
            await human_delay(2000, 4000)

        await browser.close()

    return jobs
