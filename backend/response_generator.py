import os
from groq import Groq
from dotenv import load_dotenv
from backend.models import ClassificationResult

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Separate, lightweight prompt just for drafting -- kept apart from the
# classifier prompt since this one needs a bit more "voice" and the
# classifier needs to stay strictly structured/deterministic.
DRAFT_SYSTEM_PROMPT = """You are a customer operations agent writing a short draft
response to a customer. Write 3-5 sentences, professional and {tone} in tone.
Do not invent specific dates, refund amounts, or promises you can't verify --
keep it general (e.g. "a team member will follow up shortly") rather than
specific. Sign off as "Operations Team". Return ONLY the message body, no
subject line, no extra commentary."""


def generate_ai_draft(raw_text: str, classification: ClassificationResult, tone: str = "empathetic") -> str | None:
    """
    Asks the LLM to write a tailored draft response for this specific request,
    instead of filling a fixed template. Returns None on any failure so the
    caller can fall back to the deterministic template -- a broken draft
    should never block the rest of the workflow from completing.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": DRAFT_SYSTEM_PROMPT.format(tone=tone)},
                {
                    "role": "user",
                    "content": (
                        f"Customer request type: {classification.request_type}\n"
                        f"Sub-topic: {classification.sub_topic}\n"
                        f"Urgency: {classification.urgency}\n"
                        f"Original message: {raw_text}\n\n"
                        f"Write the draft response now."
                    ),
                },
            ],
            temperature=0.6,
            max_tokens=200,
        )
        draft = response.choices[0].message.content.strip()
        return draft if draft else None
    except Exception:
        # Silent fallback by design -- the remediation engine always has a
        # hardcoded template ready to use if this returns None.
        return None
