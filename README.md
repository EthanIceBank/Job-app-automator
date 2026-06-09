# Job Application Automator

Automatically finds jobs on LinkedIn & Indeed, fills in application forms using your resume, and pauses for your review before submitting.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Add your resume

Drop your resume as `resume.pdf` in this folder.

### 4. Configure your search

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your keywords, location, etc.
```

### 5. Log in to LinkedIn & Indeed

The script uses a persistent browser profile so you stay logged in. Run once manually to log in:

```bash
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch_persistent_context('./browser_profile_linkedin', headless=False)
    input('Log into LinkedIn, then press Enter...')
    b.close()
"
```

Do the same for Indeed, pointing to `./browser_profile_indeed`.

### 6. Run it

```bash
python main.py
```

---

## How it works

1. **Resume parsing** — Claude reads your PDF and extracts your profile into `profile.json` (cached, only runs once)
2. **Job search** — Scrapes LinkedIn and Indeed with your keywords and filters
3. **Review** — Shows you a table of all matched jobs
4. **Form filling** — For each job you approve, Playwright opens the application and fills in your details
5. **Your review** — Pauses before submit so you can check everything
6. **Tracking** — Logs every job to `tracker.csv` with status (submitted / skipped / error)

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, orchestrates everything |
| `resume_parser.py` | AI-powered PDF → profile.json |
| `scrapers/linkedin.py` | LinkedIn job search |
| `scrapers/indeed.py` | Indeed job search |
| `form_filler.py` | Playwright form automation |
| `tracker.py` | CSV logging |
| `config.yaml` | Your search preferences |
| `profile.json` | Cached parsed resume (auto-generated) |
| `tracker.csv` | Application log (auto-generated) |

---

## Tips

- **Edit `profile.json`** directly after first run to fix any parsing mistakes
- **Add a cover letter** in `config.yaml` under `linkedin.default_cover_letter`
- **Delete `profile.json`** to re-parse your resume after updating it
- The script never auto-submits — you always review first
- If LinkedIn shows a CAPTCHA, complete it in the browser window and press Enter in the terminal

---

## Limitations

- LinkedIn Easy Apply only (not external application links)
- Form fields vary by company — some may need manual filling
- Bot detection can interrupt sessions; if blocked, wait a few hours and try again
- Indeed's apply flow varies significantly by employer
