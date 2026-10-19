"""Provider boundary and untrusted-output validation, with no external AI adapter.

This is not a Company Provider or a persistence implementation. Authorization and
exact File/Company/Version lookup belong to the calling application. Valid output
remains unconfirmed and requires company acknowledgement and DATCO review.
"""
from dataclasses import dataclass
from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.company.documents import ParsedDocument


class AnalysisError(ValueError):
    pass


class Candidate(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    field: Literal['company_name', 'business_number', 'representative', 'address',
                   'industry', 'revenue', 'employees', 'assets', 'liabilities',
                   'support_history', 'as_is', 'problem', 'impact', 'to_be',
                   'required_function', 'constraint', 'missing_information']
    value: str = Field(min_length=1, max_length=10000)
    descriptor: str = Field(min_length=1, max_length=1000)
    quote: str = Field(min_length=1, max_length=10000)
    claim: Literal['EXTRACTED', 'INFERRED']
    reason: str = Field(min_length=1, max_length=5000)
    period: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=100)
    uncertainty: str = Field(min_length=1, max_length=2000)

    @model_validator(mode='after')
    def financial_context(self):
        if self.field in ('revenue', 'assets', 'liabilities') and (not self.period or not self.unit):
            raise ValueError('FINANCIAL_PERIOD_AND_UNIT_REQUIRED')
        return self


class ProviderOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    company_id: str = Field(min_length=1, max_length=100)
    source_version_id: str = Field(min_length=1, max_length=100)
    digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    provider: str = Field(min_length=1, max_length=100)
    model_version: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=100)
    mode: Literal['TEST_FIXTURE', 'REAL_AI']
    candidates: tuple[Candidate, ...] = Field(max_length=1000)


@dataclass(frozen=True)
class AnalysisInput:
    company_id: str
    source_version_id: str
    document: ParsedDocument


class AnalysisProvider(Protocol):
    # The adapter is configured by the server, not selected by source content.
    mode: Literal['TEST_FIXTURE', 'REAL_AI']
    def analyze(self, source: AnalysisInput) -> ProviderOutput: ...


class UnavailableAnalysis:
    def analyze(self, source: AnalysisInput) -> ProviderOutput:
        raise AnalysisError('AI_PROVIDER_NOT_CONNECTED')


def analyze(source: AnalysisInput, provider: AnalysisProvider | None = None,
            *, external_transfer_approved: bool = False) -> ProviderOutput:
    if provider is None or isinstance(provider, UnavailableAnalysis):
        raise AnalysisError('AI_PROVIDER_NOT_CONNECTED')
    if provider.mode not in ('TEST_FIXTURE', 'REAL_AI'):
        raise AnalysisError('AI_PROVIDER_MODE_INVALID')
    if provider.mode == 'REAL_AI' and not external_transfer_approved:
        raise AnalysisError('EXTERNAL_AI_TRANSFER_NOT_APPROVED')
    try:
        result = ProviderOutput.model_validate(provider.analyze(source))
    except Exception:
        # Provider errors may contain prompts/private text/credentials. Never expose them.
        raise AnalysisError('AI_EXECUTION_OR_OUTPUT_INVALID') from None
    if (result.company_id != source.company_id or
        result.source_version_id != source.source_version_id or
        result.digest != source.document.digest or result.mode != provider.mode):
        raise AnalysisError('ANALYSIS_SOURCE_MISMATCH')
    locations = {}
    for location in source.document.locations:
        locations.setdefault(location.descriptor, []).append(location.text)
    for candidate in result.candidates:
        if not any(candidate.quote in text for text in locations.get(candidate.descriptor, [])):
            raise AnalysisError('EVIDENCE_QUOTE_NOT_FOUND')
        # For an asserted extraction, the exact extracted value must occur in its quote.
        # Normalization/inference remains visibly INFERRED, never confirmed.
        if candidate.claim == 'EXTRACTED' and candidate.value not in candidate.quote:
            raise AnalysisError('EXTRACTED_VALUE_NOT_IN_EVIDENCE')
    return result
