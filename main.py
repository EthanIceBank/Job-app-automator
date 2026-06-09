"""
Job Application Automator
-------------------------
1. Parses your resume with AI → profile.json
2. Searches LinkedIn & Indeed
3. Opens matching jobs in browser, fills forms
4. Pauses for your review before submitting
5. Logs everything to tracker.csv
"""

import asyncio
import json
import csv
import os
import sys
from pathlib import Path
from datetime import datetime

import yaml
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from resume_parser import parse_resume
from scrapers.linkedin import search_linkedin
from scrapers.indeed import search_indeed
from form_filler import fill_linkedin_form, fill_indeed_form
from tracker import log_job

console = Console()

CONFIG_PATH = Path("config.yaml")
PROFILE_PATH = Path("profile.json")
RESUME_PATH = Path("resume.pdf")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        console.print("[red]config.yaml not found. Copy config.example.yaml and fill it in.[/red]")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_or_build_profile(config: dict) -> dict:
    """Parse resume once, cache the result."""
    if PROFILE_PATH.exists():
        console.print("[dim]Using cached profile.json (delete it to re-parse)[/dim]")
        with open(PROFILE_PATH) as f:
            return json.load(f)

    if not RESUME_PATH.exists():
        console.print("[red]resume.pdf not found in project root.[/red]")
        sys.exit(1)

    console.print("[cyan]Parsing resume with AI...[/cyan]")
    profile = parse_resume(RESUME_PATH)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)
    console.print(f"[green]Profile saved to profile.json[/green]")
    return profile


async def run(config: dict, profile: dict):
    jobs = []

    # --- Scrape jobs ---
    if config.get("linkedin", {}).get("enabled", True):
        console.print("\n[cyan]Searching LinkedIn...[/cyan]")
        linkedin_jobs = await search_linkedin(config)
        console.print(f"  Found {len(linkedin_jobs)} LinkedIn jobs")
        jobs.extend(linkedin_jobs)

    if config.get("indeed", {}).get("enabled", True):
        console.print("[cyan]Searching Indeed...[/cyan]")
        indeed_jobs = await search_indeed(config)
        console.print(f"  Found {len(indeed_jobs)} Indeed jobs")
        jobs.extend(indeed_jobs)

    if not jobs:
        console.print("[yellow]No jobs found. Try loosening your filters in config.yaml.[/yellow]")
        return

    # --- Display results ---
    console.print(f"\n[bold green]Found {len(jobs)} jobs total:[/bold green]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=4)
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Source", width=10)
    table.add_column("Easy Apply", width=11)

    for i, job in enumerate(jobs, 1):
        easy = "[green]Yes[/green]" if job.get("easy_apply") else "[dim]No[/dim]"
        table.add_row(str(i), job["title"], job["company"], job["location"], job["source"], easy)

    console.print(table)

    # --- Apply loop ---
    for job in jobs:
        if not job.get("easy_apply"):
            log_job(job, status="skipped_no_easy_apply")
            continue

        console.print(f"\n[bold]→ {job['title']} at {job['company']}[/bold]")
        console.print(f"  {job['url']}")

        if not Confirm.ask("  Open and fill this application?"):
            log_job(job, status="skipped_by_user")
            continue

        try:
            if job["source"] == "linkedin":
                result = await fill_linkedin_form(job, profile, config)
            else:
                result = await fill_indeed_form(job, profile, config)

            if result == "submitted":
                log_job(job, status="submitted")
                console.print("  [green]✓ Submitted[/green]")
            elif result == "filled":
                log_job(job, status="filled_needs_review")
                console.print("  [yellow]✓ Filled — waiting for your manual submit[/yellow]")
            else:
                log_job(job, status="error")
                console.print("  [red]✗ Something went wrong[/red]")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            log_job(job, status=f"error: {e}")

    console.print("\n[bold]Done! Check tracker.csv for a full log.[/bold]")


def main():
    console.print("[bold cyan]Job Application Automator[/bold cyan]\n")
    config = load_config()
    profile = load_or_build_profile(config)

    console.print(f"[dim]Applying as: {profile.get('name', '?')} | {profile.get('email', '?')}[/dim]")

    asyncio.run(run(config, profile))


if __name__ == "__main__":
    main()
