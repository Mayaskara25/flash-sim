"""Three-person 60-minute runbook from SPEC §10."""

from incident.contracts import Role


def phase_of(t: int) -> str:
    if t < 600:
        return "Detect"
    if t < 1200:
        return "Escalate"
    if t < 2400:
        return "Contain"
    if t < 3600:
        return "Stabilise"
    return "Close"


ROLE_FOCUS: dict[str, dict[Role, str]] = {
    "Detect": {"IC": "Acknowledge, classify and set initial severity.", "TL": "Check feed freshness, engine errors and latency.", "CS": "Review ticket themes; hold unverified public claims.", "system": "Start timer and record triggers."},
    "Escalate": {"IC": "Choose controls and page founders at SEV-1.", "TL": "Rule in or out engine and oracle faults.", "CS": "Approve the first customer notice and FAQ.", "system": "Surface actions and drafts."},
    "Contain": {"IC": "Track fund, exposure and collateral; decide top-up or ADL.", "TL": "Fix, roll back or shed load as needed.", "CS": "Update customers every 15–20 minutes and contact partners when needed.", "system": "Remind about updates and expiring controls."},
    "Stabilise": {"IC": "Confirm step-down and lift temporary controls.", "TL": "Verify recovery and preserve evidence.", "CS": "Prepare monitoring or resolution notice.", "system": "Show recovery trends and confirmation."},
    "Close": {"IC": "Sign off and open compensation review if needed.", "TL": "Write technical root cause.", "CS": "Send resolution notice and answer backlog.", "system": "Generate incident summary."},
}
