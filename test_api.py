import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env into process env
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _strip_fenced_json(raw: str) -> str:
    """If the model returns ```json ... ``` fences, strip them safely."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()
    return raw


def ask_ai(
    company_name: str,
    industry: str,
    notes: str,
    sender_company: str = "Northeast co.",
    sender_service: str = "automation + AI tools",
    sender_tone: str = "professional, concise, helpful",
) -> str:
    prompt = f"""
Return ONLY raw JSON. Do not wrap in ```json. Do not include any extra text.

Target company (the prospect):
Company: {company_name}
Industry: {industry}
Notes / pain points: {notes}

Sender (the company reaching out to help):
Sender company: {sender_company}
What we offer: {sender_service}
Tone: {sender_tone}

Your job:
1) Classify the pain points into a short category.
2) Summarize the opportunity in 1–2 sentences.
3) Write a SALES OUTREACH email from the SENDER to the TARGET company.
   - The email must be written in first person plural ("we") as the sender.
   - Do NOT write as if you work at the target company.
   - Keep it specific to the notes.
   - Keep it short and realistic (no hype).

Return ONLY valid JSON with exactly these keys:
- category
- opportunity_summary
- email_subject
- email_body

Rules:
- email_body must be plain text with normal new lines.
- Do not return nested objects.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You return structured business analysis as valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    raw = response.choices[0].message.content
    raw = _strip_fenced_json(raw)

    # Validate JSON now so errors are obvious early
    data = json.loads(raw)

    # Ensure keys exist (basic contract check)
    required = ["category", "opportunity_summary", "email_subject", "email_body"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Model response missing keys: {missing}\nRaw:\n{raw}")

    # Return raw JSON string (your Streamlit app will json.loads it again)
    return json.dumps(data, ensure_ascii=False)
