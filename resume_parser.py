"""
Resume Parser
-------------
Reads resume.pdf and uses Claude to extract structured profile data.
Result is cached in profile.json so you only pay for this once.
"""

import json
import pdfplumber
import anthropic
from pathlib import Path


SYSTEM_PROMPT = """You are a resume parser. Extract structured data from the resume text.
Return ONLY a JSON object with no markdown or explanation. Use this exact schema:

{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "555-555-5555",
  "location": "City, State",
  "linkedin_url": "https://linkedin.com/in/...",
  "portfolio_url": "https://...",
  "summary": "One paragraph professional summary",
  "years_experience": 5,
  "current_title": "Software Engineer",
  "skills": ["Python", "React", "AWS"],
  "work_experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "start_date": "Jan 2022",
      "end_date": "Present",
      "description": "Key responsibilities and achievements"
    }
  ],
  "education": [
    {
      "degree": "B.S. Computer Science",
      "school": "University Name",
      "year": "2019"
    }
  ],
  "certifications": ["AWS Certified Developer"],
  "languages": ["English", "Spanish"]
}

If a field isn't present in the resume, use null for strings and [] for arrays.
"""


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def parse_resume(pdf_path: Path) -> dict:
    """Parse resume PDF into a structured profile dict using Claude."""
    # Extract text
    resume_text = extract_text_from_pdf(pdf_path)
    if not resume_text:
        raise ValueError("Could not extract text from resume.pdf — is it a scanned image?")

    # Call Claude
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Parse this resume:\n\n{resume_text}"}
        ]
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    profile = json.loads(raw)
    return profile
