from pydantic import ValidationError
import pytest

from infinite_interns.specification.models import (
    Assumption,
    AssumptionDisposition,
    AssumptionRisk,
    ProductInput,
    Requirement,
    RequirementKind,
)


def test_product_input_is_frozen() -> None:
    item = ProductInput(input_id="input-1", raw_text="Build a job tracker", source_ref="cli")

    with pytest.raises(ValidationError):
        item.raw_text = "simpler request"


def test_high_risk_assumption_cannot_be_auto_accepted() -> None:
    with pytest.raises(ValidationError):
        Assumption(
            assumption_id="A-1",
            risk=AssumptionRisk.HIGH,
            statement="Delete production data during migration",
            chosen_default="delete it",
            reversible=False,
            disposition=AssumptionDisposition.AUTO_ACCEPTED,
        )


def test_high_risk_assumption_may_choose_explicit_safe_alternative() -> None:
    item = Assumption(
        assumption_id="A-2",
        risk=AssumptionRisk.HIGH,
        statement="Production migration strategy is unspecified",
        chosen_default="use a reversible shadow migration in staging",
        reversible=True,
        disposition=AssumptionDisposition.SAFE_ALTERNATIVE,
    )

    assert item.disposition is AssumptionDisposition.SAFE_ALTERNATIVE


def test_medium_risk_automatic_default_must_be_reversible() -> None:
    with pytest.raises(ValidationError):
        Assumption(
            assumption_id="A-3",
            risk=AssumptionRisk.MEDIUM,
            statement="Choose a datastore index layout",
            chosen_default="irreversible vendor-specific layout",
            reversible=False,
            disposition=AssumptionDisposition.REVERSIBLE_DEFAULT,
        )


def test_required_functional_requirement_needs_acceptance_criteria() -> None:
    with pytest.raises(ValidationError):
        Requirement(
            requirement_id="REQ-JOBS-001",
            text="Users can save a job",
            kind=RequirementKind.FUNCTIONAL,
            criticality="high",
            acceptance_criteria=(),
            source_input_id="input-1",
        )


def test_nonfunctional_requirement_may_use_downstream_oracle_criteria() -> None:
    requirement = Requirement(
        requirement_id="REQ-PERF-001",
        text="Search remains responsive under the defined load envelope",
        kind=RequirementKind.NFR,
        criticality="medium",
        acceptance_criteria=(),
        source_input_id="input-1",
    )

    assert requirement.kind is RequirementKind.NFR
