import os
import json
from groq import Groq
from dotenv import load_dotenv
from backend.models import ClassificationResult

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

VALID_TYPES = ["Complaint", "General Enquiry", "Service Request", "Escalation/Urgent"]
VALID_URGENCY = ["Low", "Medium", "High", "Critical"]

SYSTEM_PROMPT = """You are an AI classifier for a customer operations team.
Classify the incoming request into exactly one of these types:
- Complaint (customer dissatisfied with product/service, wants resolution)
- General Enquiry (asking for information, no issue to resolve)
- Service Request (asking for an action to be taken, e.g. change, install, update)
- Escalation/Urgent (severe dissatisfaction, threat to leave, legal mention, repeated unresolved issue, safety concern)

Also assign urgency:
- Low, Medium, High, or Critical

Respond ONLY with valid JSON, no other text, in this exact format:
{
  "request_type": "<one of the 4 types above>",
  "urgency": "<one of Low/Medium/High/Critical>",
  "sub_topic": "<short 2-5 word topic, e.g. 'billing dispute', 'product info'>",
  "confidence": "<High/Medium/Low - your confidence in this classification>",
  "reasoning": "<one sentence explaining why>"
}
"""


def classify_request(raw_text: str) -> ClassificationResult:
    """Sends the request text to Groq LLM and returns a structured classification."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Classify this request:\n\n{raw_text}"}
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Safety fallback in case model returns something unexpected
        req_type = data.get("request_type", "General Enquiry")
        if req_type not in VALID_TYPES:
            req_type = "General Enquiry"

        urgency = data.get("urgency", "Low")
        if urgency not in VALID_URGENCY:
            urgency = "Low"

        return ClassificationResult(
            request_type=req_type,
            urgency=urgency,
            sub_topic=data.get("sub_topic", "general"),
            confidence=data.get("confidence", "Medium"),
            reasoning=data.get("reasoning", "No reasoning provided."),
        )

    except Exception as e:
        # Fallback: if API fails, mark for human review instead of crashing
        return ClassificationResult(
            request_type="Escalation/Urgent",
            urgency="Critical",
            sub_topic="classification_error",
            confidence="Low",
            reasoning=f"AI classification failed ({str(e)}) — routed to human review as safety fallback.",
        )