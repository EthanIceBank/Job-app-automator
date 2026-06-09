"""
Form Filler
-----------
Opens job application pages and fills in form fields using your profile.
Pauses before final submit so you can review everything.
"""

import asyncio
import random
from playwright.async_api import async_playwright, Page


async def human_delay(min_ms=300, max_ms=900):
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def type_into_field(page: Page, selector: str, value: str):
    """Click a field and type into it humanistically."""
    try:
        el = await page.wait_for_selector(selector, timeout=4000)
        await el.click()
        await human_delay(200, 500)
        await el.fill("")  # clear first
        await el.type(str(value), delay=random.randint(40, 120))
        await human_delay(100, 300)
    except Exception:
        pass  # Field not found — skip silently


async def fill_linkedin_form(job: dict, profile: dict, config: dict) -> str:
    """
    Open a LinkedIn Easy Apply form and fill it in.
    Returns: "submitted" | "filled" | "error"
    """
    async with async_playwright() as p:
        li_config = config.get("linkedin", {})
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=li_config.get("browser_profile_path", "./browser_profile"),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            no_viewport=True,
        )

        page = await browser.new_page()
        await page.goto(job["url"])
        await human_delay(2000, 3500)

        # Click the Easy Apply button
        try:
            easy_apply_btn = await page.wait_for_selector(
                "button.jobs-apply-button, button[aria-label*='Easy Apply']", timeout=6000
            )
            await easy_apply_btn.click()
            await human_delay(1500, 2500)
        except Exception:
            print("  Could not find Easy Apply button.")
            await browser.close()
            return "error"

        # Fill standard fields across multi-step form
        filled_pages = 0
        max_pages = 10

        while filled_pages < max_pages:
            await fill_linkedin_form_page(page, profile, config)
            await human_delay(500, 1000)

            # Check if there's a "Next" or "Review" button
            next_btn = await page.query_selector("button[aria-label='Continue to next step']")
            review_btn = await page.query_selector("button[aria-label='Review your application']")
            submit_btn = await page.query_selector("button[aria-label='Submit application']")

            if submit_btn:
                print("\n  [Form filled] Review the application in the browser.")
                print("  Press Enter here after you've reviewed and are ready to submit,")
                print("  OR close the browser window to skip this application.")
                input("  > ")
                try:
                    await submit_btn.click()
                    await human_delay(2000, 3000)
                    await browser.close()
                    return "submitted"
                except Exception:
                    await browser.close()
                    return "error"

            elif review_btn:
                await review_btn.click()
                await human_delay(1500, 2000)

            elif next_btn:
                await next_btn.click()
                await human_delay(1500, 2000)
                filled_pages += 1

            else:
                # Nothing to click — pause for user
                print("  Couldn't auto-navigate form. Please complete it manually in the browser.")
                input("  Press Enter when done (or Ctrl+C to skip)...")
                await browser.close()
                return "filled"

        await browser.close()
        return "filled"


async def fill_linkedin_form_page(page: Page, profile: dict, config: dict):
    """Fill whichever fields are visible on the current LinkedIn form page."""

    # Phone number
    await type_into_field(page, "input[id*='phoneNumber'], input[name*='phone']", profile.get("phone", ""))

    # City / location
    await type_into_field(page, "input[id*='city'], input[name*='location']", profile.get("location", ""))

    # Years of experience (numeric inputs)
    experience_inputs = await page.query_selector_all("input[type='number']")
    for inp in experience_inputs:
        label = await page.evaluate("el => el.closest('div')?.querySelector('label')?.innerText || ''", inp)
        if "experience" in label.lower() or "years" in label.lower():
            await inp.fill(str(profile.get("years_experience", 0)))

    # Yes/No radio buttons — default to "Yes" for common questions
    radios = await page.query_selector_all("input[type='radio']")
    for radio in radios:
        label_text = await page.evaluate(
            "el => document.querySelector(`label[for='${el.id}']`)?.innerText || ''", radio
        )
        if "yes" in label_text.lower():
            await radio.check()
            await human_delay(100, 300)

    # Dropdowns — select first non-placeholder option
    selects = await page.query_selector_all("select")
    for sel in selects:
        options = await sel.query_selector_all("option")
        for opt in options[1:]:  # skip placeholder
            val = await opt.get_attribute("value")
            if val:
                await sel.select_option(val)
                break

    # Cover letter textarea (if present)
    cl_textarea = await page.query_selector("textarea[id*='coverLetter'], textarea[name*='cover']")
    if cl_textarea:
        cover_letter = config.get("linkedin", {}).get("default_cover_letter", "")
        if cover_letter:
            await cl_textarea.fill(cover_letter)


async def fill_indeed_form(job: dict, profile: dict, config: dict) -> str:
    """
    Open an Indeed job application and fill it in.
    Returns: "submitted" | "filled" | "error"
    """
    async with async_playwright() as p:
        indeed_config = config.get("indeed", {})
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=indeed_config.get("browser_profile_path", "./browser_profile_indeed"),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            no_viewport=True,
        )

        page = await browser.new_page()
        await page.goto(job["url"])
        await human_delay(2000, 3500)

        # Click Apply button
        try:
            apply_btn = await page.wait_for_selector(
                "button#indeedApplyButton, a[data-jk][href*='apply'], button[class*='apply']",
                timeout=6000
            )
            await apply_btn.click()
            await human_delay(2000, 3000)
        except Exception:
            print("  Could not find Apply button on Indeed listing.")
            await browser.close()
            return "error"

        # Fill fields on current page
        await fill_indeed_form_page(page, profile)
        await human_delay(500, 1000)

        print("\n  [Form filled] Review the Indeed application in the browser.")
        print("  Complete any remaining steps and submit manually.")
        print("  Press Enter here when done.")
        input("  > ")

        await browser.close()
        return "filled"


async def fill_indeed_form_page(page: Page, profile: dict):
    """Fill visible Indeed form fields."""

    field_map = {
        "input[name='name'], input[id*='name']": profile.get("name", ""),
        "input[name='email'], input[type='email']": profile.get("email", ""),
        "input[name='phone'], input[type='tel']": profile.get("phone", ""),
        "input[name='location'], input[id*='location']": profile.get("location", ""),
    }

    for selector, value in field_map.items():
        if value:
            await type_into_field(page, selector, value)

    # Dropdowns
    selects = await page.query_selector_all("select")
    for sel in selects:
        options = await sel.query_selector_all("option")
        for opt in options[1:]:
            val = await opt.get_attribute("value")
            if val:
                await sel.select_option(val)
                break
            await human_delay(100, 200)
