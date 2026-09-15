"""Predict -> Decide: the policy gate for autonomous operational actions.

Pure logic only — no direct DB access, matching every other etl/*.py
module's convention (network calls only; api/*.py owns all Postgres
writes). This decides *whether* an evaluated reading is significant
enough to warrant asking the decision engine's Act step
(etl/operations_client.py -> POST /operations/loading-points/reassign)
to look for a loading-point reassignment — that endpoint does the actual
DB work (lazy bay/slot seeding, capacity check, the reassignment itself),
since api/operations.py is the one place decisions get durably recorded.

docs/11-PRODUCT-CONTRACT.md's "Decide" step 1 in full: risk_level must
meet the policy threshold for the asset's equipment_type *and*
criticality. Real per-asset criticality arrives with the Asset registry
(Part C of the build plan); until then every reading is evaluated as if
CRITICAL — deliberately the strictest tier (see POLICY_THRESHOLDS below)
— so this never *under*-reacts in the meantime.

This module never reschedules a truck, actuates equipment, or writes to
Postgres itself — it only answers "should the Act step even be asked."
"""

# risk_level required to trigger a decision-engine evaluation, by
# criticality tier — order matters for the comparison in should_evaluate.
_RISK_ORDER = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

POLICY_THRESHOLDS = {
    "CRITICAL": "MEDIUM",
    "HIGH": "HIGH",
    "MEDIUM": "HIGH",
    "LOW": "CRITICAL",
}

DEFAULT_CRITICALITY = "CRITICAL"  # see module docstring


def should_evaluate(risk_level: str | None, criticality: str = DEFAULT_CRITICALITY) -> bool:
    """True if this reading's risk_level clears the policy threshold for
    the given criticality tier — i.e. worth asking the Act step to look
    for a loading-point reassignment."""
    if not risk_level:
        return False
    threshold = POLICY_THRESHOLDS.get(criticality.upper(), "CRITICAL")
    try:
        return _RISK_ORDER.index(risk_level.upper()) >= _RISK_ORDER.index(threshold)
    except ValueError:
        return False
