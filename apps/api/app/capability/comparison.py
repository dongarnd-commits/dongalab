"""Consumer-side deterministic comparison. No text parser or eligibility policy.

These immutable values are internal adapter inputs, not a Company domain schema.
Only an authoritative reader may supply independently human-reviewed conditions.
"""
from dataclasses import dataclass, asdict
from datetime import date
from app.notice.domain import Denied

@dataclass(frozen=True)
class ConfirmedFact:
    version_id: str
    company_id: str
    site_id: str | None
    attribute: str
    value: str
    review_id: str
    evidence_refs: tuple[str, ...]
    confirmed: bool
    current_valid: bool
    valid_from: str
    valid_until: str | None = None

@dataclass(frozen=True)
class ReviewedCondition:
    requirement_version_id: str
    item_id: str
    attribute: str
    operator: str
    values: tuple[str, ...]
    review_id: str
    evidence_id: str
    reviewed: bool
    current_valid: bool
    as_of: str
    mandatory: bool = True

@dataclass(frozen=True)
class ComparisonInputs:
    facts: tuple[ConfirmedFact, ...] = ()
    conditions: tuple[ReviewedCondition, ...] = ()

def input_snapshot(inputs):
    return asdict(inputs)

def compare(inputs, company_id, site_id, notice):
    # Scope is a security failure, never an information deficit or match evidence.
    if any(f.company_id != company_id or (f.site_id and f.site_id != site_id) for f in inputs.facts):
        raise Denied('OBJECT_NOT_FOUND', 404)
    items = {i['id']: i for i in notice['items']}
    duplicate_ids = {c.item_id for c in inputs.conditions if sum(x.item_id == c.item_id for x in inputs.conditions) > 1}
    results = []
    for condition in inputs.conditions:
        c = condition
        item = items.get(c.item_id)
        result = dict(requirement_version_id=c.requirement_version_id, item_id=c.item_id,
            fact_version_ids=[], fact_evidence_refs=[], condition_review_id=c.review_id,
            operator=c.operator, values=list(c.values), as_of=c.as_of, mandatory=c.mandatory,
            status='UNKNOWN', reason='', missing=[], notice_evidence=item['evidence'] if item else None)
        def unknown(reason):
            result['reason'] = reason
            result['missing'] = [reason]
        if (notice.get('current_valid') is not True or c.requirement_version_id != notice['requirement_version_id']
            or not item or item['kind'] not in ('ELIGIBILITY_REQUIREMENT', 'CONDITIONAL_REQUIREMENT')
            or item['review']['outcome'] != 'CONFIRM' or item['review']['official_verified'] is not True
            or c.reviewed is not True or c.current_valid is not True or not c.review_id.strip()
            or c.evidence_id != item['evidence']['id'] or c.item_id in duplicate_ids):
            unknown('CONDITION_NOT_INDEPENDENTLY_VERIFIED')
        elif c.operator not in ('IN', 'NOT_IN') or not c.attribute or not c.values or any(not isinstance(v,str) or not v.strip() for v in c.values):
            unknown('UNSUPPORTED_COMPARISON_SEMANTICS')
        else:
            try:
                as_of = date.fromisoformat(c.as_of)
                facts = [f for f in inputs.facts if f.attribute == c.attribute and f.confirmed is True and f.current_valid is True
                    and f.version_id.strip() and f.review_id.strip() and f.evidence_refs
                    and all(isinstance(e,str) and e.strip() for e in f.evidence_refs)
                    and date.fromisoformat(f.valid_from) <= as_of
                    and (f.valid_until is None or as_of <= date.fromisoformat(f.valid_until))]
            except (ValueError, TypeError):
                facts = []
            result['fact_version_ids'] = sorted({f.version_id for f in facts})
            result['fact_evidence_refs'] = sorted({e for f in facts for e in f.evidence_refs})
            if not facts:
                unknown('CONFIRMED_FACT_REQUIRED:' + c.attribute)
            elif len({f.value for f in facts}) != 1 or any(not isinstance(f.value,str) or not f.value.strip() for f in facts):
                unknown('CONFLICTING_FACTS:' + c.attribute)
            else:
                inside = facts[0].value in c.values
                satisfied = inside if c.operator == 'IN' else not inside
                result['status'] = 'CONFIRMED_SATISFIED' if satisfied else 'CONFIRMED_CONFLICT'
                result['reason'] = 'Human-reviewed exact code membership at the specified reference date.'
        results.append(result)
    covered = {c.item_id for c in inputs.conditions}
    for item in notice['items']:
        if item['kind'] in ('ELIGIBILITY_REQUIREMENT', 'CONDITIONAL_REQUIREMENT', 'APPLICATION_PERIOD') and item['id'] not in covered:
            results.append(dict(requirement_version_id=notice['requirement_version_id'], item_id=item['id'],
                status='UNKNOWN', reason='STRUCTURED_CONDITION_REVIEW_REQUIRED', missing=['STRUCTURED_CONDITION_REVIEW_REQUIRED'],
                fact_version_ids=[], fact_evidence_refs=[], notice_evidence=item['evidence']))
    conflicts = [r for r in results if r['status'] == 'CONFIRMED_CONFLICT' and r.get('mandatory') is True]
    return dict(fit='MISMATCH' if conflicts else 'NEED_MORE_INFO', conditions=results,
        opposing_evidence=conflicts, missing=sorted({m for r in results for m in r.get('missing', [])}))

def read_comparison_inputs(provider, actor, context, notice):
    reader = getattr(provider, 'read_comparison_inputs', None)
    if reader is None:
        return ComparisonInputs()
    result = reader(actor, context, notice)
    if not isinstance(result, ComparisonInputs):
        raise Denied('REQUIRED_DATA_MISSING')
    return result
