"""Rules engine package (H2).

Pure, deterministic functions from a stream of `SignalFrame`s to severity,
verdict, state, tags and alert cards, per SPEC §3, §9.2–9.3. No I/O, no HTTP.
"""

from .alerts import AlertManager  # noqa: F401
from .classifier import ClassifierResult, classify  # noqa: F401
from .history import SignalHistory  # noqa: F401
from .severity import SeverityResult, score  # noqa: F401
from .state_machine import StateMachine, sev_of_state  # noqa: F401
from .tags import TagTracker, priority_order  # noqa: F401
