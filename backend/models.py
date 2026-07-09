from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class IncomingRequest:
    """Represents a raw incoming request before processing."""
    request_id: str
    raw_text: str
    channel: str = "web_form"  # email, web_form, simulated_inbox
    received_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ClassificationResult:
    """Output of the LLM classification step."""
    request_type: str      # Complaint | General Enquiry | Service Request | Escalation/Urgent
    urgency: str            # Low | Medium | High | Critical
    sub_topic: str          # short descriptor, e.g. "billing", "product info"
    confidence: str         # High | Medium | Low  (AI's own confidence)
    reasoning: str           # short explanation from the LLM


@dataclass
class RemediationOutput:
    """Final output after branching logic executes."""
    request_id: str
    request_type: str
    urgency: str
    steps_executed: List[str]
    draft_response: str
    routing_team: str
    follow_up: str
    status: str              # Resolved | Pending | Escalated | Human Review
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())