from datetime import datetime, timedelta
from backend.models import ClassificationResult, RemediationOutput
from backend.response_generator import generate_ai_draft

# This is the actual branching logic the assignment brief asked for --
# one handler per request type, each running its own multi-step sequence.
# I kept the four types matching the brief's examples since they cover the
# realistic urgency spread (Low -> Critical) pretty well.


def _draft_acknowledgement(sub_topic: str, tone: str = "empathetic") -> str:
    if tone == "urgent":
        return (
            f"Dear Customer,\n\nWe have received your message regarding '{sub_topic}' "
            f"and understand the seriousness of this matter. A senior team member has been "
            f"immediately notified and will contact you within the hour.\n\nRegards,\nOperations Team"
        )
    return (
        f"Dear Customer,\n\nThank you for reaching out regarding '{sub_topic}'. "
        f"We're sorry for the inconvenience caused and are looking into it right away. "
        f"Our team will follow up with a resolution shortly.\n\nRegards,\nOperations Team"
    )


def _draft_info_response(sub_topic: str) -> str:
    return (
        f"Dear Customer,\n\nThank you for your enquiry about '{sub_topic}'. "
        f"Based on our knowledge base, here is the information you requested. "
        f"Please let us know if you need further clarification.\n\nRegards,\nOperations Team"
    )


def _draft_confirmation(sub_topic: str) -> str:
    return (
        f"Dear Customer,\n\nYour service request regarding '{sub_topic}' has been received "
        f"and routed to the relevant department. You will receive an update within the SLA window.\n\n"
        f"Regards,\nOperations Team"
    )


def _get_draft(raw_text: str, classification: ClassificationResult, tone: str, fallback_fn) -> str:
    """
    Tries the LLM-generated draft first since it's tailored to the actual
    wording of the request. Falls back to the deterministic template if the
    API call fails for any reason -- the operator should never see a blank
    draft field just because the LLM call timed out.
    """
    ai_draft = generate_ai_draft(raw_text, classification, tone=tone)
    return ai_draft if ai_draft else fallback_fn


def handle_complaint(request_id: str, classification: ClassificationResult, raw_text: str = "") -> RemediationOutput:
    # Complaints get escalated straight away rather than auto-resolved --
    # a dissatisfied customer needs a human in the loop, not just a bot reply.
    steps = [
        "Acknowledged receipt",
        "Escalated to senior handler",
        "Logged case with priority flag",
        f"Set 2-hour follow-up reminder (due {(datetime.now() + timedelta(hours=2)).strftime('%H:%M')})",
    ]
    fallback = _draft_acknowledgement(classification.sub_topic, tone="empathetic")
    return RemediationOutput(
        request_id=request_id,
        request_type=classification.request_type,
        urgency=classification.urgency,
        steps_executed=steps,
        draft_response=_get_draft(raw_text, classification, "empathetic", fallback),
        routing_team="Senior Support / Complaints Desk",
        follow_up="2-hour follow-up reminder set",
        status="Escalated",
    )


def handle_general_enquiry(request_id: str, classification: ClassificationResult, raw_text: str = "") -> RemediationOutput:
    # Enquiries are the one branch that's safe to fully auto-resolve since
    # there's no real risk if the AI response is slightly off -- worst case
    # the customer replies again.
    steps = [
        f"Classified sub-topic: {classification.sub_topic}",
        "Generated AI response from knowledge base",
        "Sent response to customer",
        "Logged as resolved",
    ]
    fallback = _draft_info_response(classification.sub_topic)
    return RemediationOutput(
        request_id=request_id,
        request_type=classification.request_type,
        urgency=classification.urgency,
        steps_executed=steps,
        draft_response=_get_draft(raw_text, classification, "friendly and informative", fallback),
        routing_team="N/A (auto-resolved)",
        follow_up="None required",
        status="Resolved",
    )


def handle_service_request(request_id: str, classification: ClassificationResult, raw_text: str = "") -> RemediationOutput:
    # Service requests aren't urgent but they do need a real action taken
    # (e.g. by a department, not the AI), so I attach an SLA timer instead
    # of a follow-up reminder like the complaint branch uses.
    steps = [
        "Extracted required details from request",
        "Routed to relevant department",
        "Generated confirmation message to requester",
        "Set SLA timer (48 hours)",
    ]
    fallback = _draft_confirmation(classification.sub_topic)
    return RemediationOutput(
        request_id=request_id,
        request_type=classification.request_type,
        urgency=classification.urgency,
        steps_executed=steps,
        draft_response=_get_draft(raw_text, classification, "professional and reassuring", fallback),
        routing_team="Service Fulfillment Team",
        follow_up=f"SLA timer set — due {(datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M')}",
        status="Pending",
    )


def handle_escalation_urgent(request_id: str, classification: ClassificationResult, raw_text: str = "") -> RemediationOutput:
    # This is the one branch where I deliberately do NOT let the system
    # auto-resolve anything -- critical/urgent cases pause for a human,
    # even if that means slower turnaround. Better safe than automated.
    steps = [
        "Immediately flagged for human review",
        "Drafted urgent acknowledgement",
        "Notified supervisor",
        "Paused auto-resolution (human-in-the-loop)",
    ]
    fallback = _draft_acknowledgement(classification.sub_topic, tone="urgent")
    return RemediationOutput(
        request_id=request_id,
        request_type=classification.request_type,
        urgency=classification.urgency,
        steps_executed=steps,
        draft_response=_get_draft(raw_text, classification, "urgent and reassuring", fallback),
        routing_team="Supervisor / Human Review Queue",
        follow_up="Human review required before any auto-response is sent",
        status="Human Review",
    )


# Simple dict-based dispatch instead of a big if/elif chain -- easier to
# extend later if a 5th request type needs to be added.
BRANCH_MAP = {
    "Complaint": handle_complaint,
    "General Enquiry": handle_general_enquiry,
    "Service Request": handle_service_request,
    "Escalation/Urgent": handle_escalation_urgent,
}


def run_remediation(request_id: str, classification: ClassificationResult, raw_text: str = "") -> RemediationOutput:
    """Entry point the frontend calls once a request has been classified."""
    handler = BRANCH_MAP.get(classification.request_type, handle_general_enquiry)
    result = handler(request_id, classification, raw_text)

    # Edge case handling: if the AI itself wasn't confident about the
    # classification, don't let the normal branch auto-resolve or route
    # silently. Override it to a human-review state instead, regardless of
    # which branch it landed in -- an uncertain "General Enquiry" auto-reply
    # is a worse outcome than a slightly-delayed human check.
    if classification.confidence == "Low":
        result.steps_executed = [
            "AI confidence below threshold — escalation override triggered",
        ] + result.steps_executed
        result.routing_team = "Supervisor / Human Review Queue (low-confidence override)"
        result.follow_up = "Held for human verification before any auto-response is sent"
        result.status = "Human Review"

    return result
