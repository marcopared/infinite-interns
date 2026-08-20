"""Strict immutable contracts for product input and versioned specifications."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from infinite_interns.domain.enums import RiskClass


class SpecificationModel(BaseModel):
    """Base model for immutable planning artifacts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class RequirementKind(StrEnum):
    FUNCTIONAL = "functional"
    NFR = "nfr"
    CONSTRAINT = "constraint"


class AssumptionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AssumptionDisposition(StrEnum):
    AUTO_ACCEPTED = "auto_accepted"
    REVERSIBLE_DEFAULT = "reversible_default"
    NEEDS_OPERATOR = "needs_operator"
    SAFE_ALTERNATIVE = "safe_alternative"


class ProductInput(SpecificationModel):
    input_id: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("created_at")
    @classmethod
    def require_aware_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class Assumption(SpecificationModel):
    assumption_id: str = Field(min_length=1)
    risk: AssumptionRisk
    statement: str = Field(min_length=1)
    chosen_default: str = Field(min_length=1)
    reversible: bool
    disposition: AssumptionDisposition

    @model_validator(mode="after")
    def enforce_risk_policy(self) -> "Assumption":
        if self.risk is AssumptionRisk.HIGH:
            if self.disposition not in {
                AssumptionDisposition.NEEDS_OPERATOR,
                AssumptionDisposition.SAFE_ALTERNATIVE,
            }:
                raise ValueError(
                    "high-risk assumptions require operator input or an explicit safe alternative"
                )
            if (
                self.disposition is AssumptionDisposition.SAFE_ALTERNATIVE
                and not self.reversible
            ):
                raise ValueError("high-risk safe alternatives must be reversible")

        if self.risk is AssumptionRisk.MEDIUM:
            if self.disposition is AssumptionDisposition.AUTO_ACCEPTED:
                raise ValueError("medium-risk assumptions may not be silently auto-accepted")
            if (
                self.disposition is AssumptionDisposition.REVERSIBLE_DEFAULT
                and not self.reversible
            ):
                raise ValueError("medium-risk defaults must be reversible")
        return self


class Requirement(SpecificationModel):
    requirement_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    kind: RequirementKind
    criticality: RiskClass
    acceptance_criteria: tuple[str, ...] = ()
    source_input_id: str = Field(min_length=1)
    supersedes: str | None = None
    required: bool = True

    @field_validator("acceptance_criteria")
    @classmethod
    def validate_criteria(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not criterion.strip() for criterion in value):
            raise ValueError("acceptance criteria must be non-empty")
        return value

    @model_validator(mode="after")
    def validate_requirement(self) -> "Requirement":
        if self.required and self.kind is RequirementKind.FUNCTIONAL and not self.acceptance_criteria:
            raise ValueError("required functional requirements need acceptance criteria")
        if self.supersedes == self.requirement_id:
            raise ValueError("a requirement cannot supersede itself")
        return self


class UserJourney(SpecificationModel):
    journey_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    steps: tuple[str, ...] = Field(min_length=1)
    requirement_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("steps", "requirement_ids")
    @classmethod
    def reject_empty_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("journey values must be non-empty")
        return value


class SpecStatement(SpecificationModel):
    statement_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_input_id: str = Field(min_length=1)


class GlossaryEntry(SpecificationModel):
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)


class ProductSpec(SpecificationModel):
    version_id: str = Field(min_length=1)
    parent_version_id: str | None = None
    product_input_id: str = Field(min_length=1)
    requirements: tuple[Requirement, ...]
    journeys: tuple[UserJourney, ...] = ()
    invariants: tuple[SpecStatement, ...] = ()
    nfrs: tuple[SpecStatement, ...] = ()
    constraints: tuple[SpecStatement, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    glossary: tuple[GlossaryEntry, ...] = ()

    @model_validator(mode="after")
    def validate_unique_ids_and_sources(self) -> "ProductSpec":
        requirement_ids = [item.requirement_id for item in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("requirement IDs must be unique within a specification")

        journey_ids = [item.journey_id for item in self.journeys]
        if len(journey_ids) != len(set(journey_ids)):
            raise ValueError("journey IDs must be unique within a specification")

        known_requirements = set(requirement_ids)
        for journey in self.journeys:
            unknown = set(journey.requirement_ids) - known_requirements
            if unknown:
                raise ValueError(
                    "journey references unknown requirements: " + ", ".join(sorted(unknown))
                )

        for requirement in self.requirements:
            if requirement.source_input_id != self.product_input_id:
                raise ValueError("requirement source input must match specification product input")
        return self
