"""MVP provider availability. External adapters and credentials do not exist."""
from dataclasses import asdict, dataclass
from typing import Protocol
from app.company.improvement_rules import VERSION
from app.notice.domain import Denied

PROVIDERS = ('RULE', 'GPT', 'GEMINI', 'CLAUDE', 'GROK')

def provider_status():
    return dict(default='RULE', providers=[dict(
        id=name, label='Rule 기반 분석' if name=='RULE' else name,
        status='AVAILABLE' if name=='RULE' else 'NOT_CONFIGURED',
        version=VERSION if name=='RULE' else None,
        external=name!='RULE',
        reason='' if name=='RULE' else '연결 미설정 — 이번 MVP에서는 실행할 수 없습니다.',
    ) for name in PROVIDERS])

def ensure_provider(name):
    if name not in PROVIDERS:
        raise Denied('ANALYSIS_PROVIDER_UNSUPPORTED',422)
    if name!='RULE':
        raise Denied('ANALYSIS_PROVIDER_NOT_CONFIGURED',409)
    return name

@dataclass(frozen=True)
class AnalysisContext:
    company_id: str
    improvement_version_id: str
    input_digest: str

@dataclass(frozen=True)
class StructuredAnalysisResult:
    schema_version: str
    provider: str
    provider_version: str
    context: AnalysisContext
    structure: dict
    candidates: tuple
    diagnostics: tuple
    limitations: tuple

class ImprovementAnalysisProvider(Protocol):
    """Slice2 adapter contract; company.analysis remains the document-provider boundary."""
    def analyze(self, context: AnalysisContext, data: dict, spans: list,
                *, coverage=(), incomplete=False) -> StructuredAnalysisResult: ...

class RuleProvider:
    def __init__(self, analyzer=None):
        self.analyzer=analyzer

    def analyze(self, context, data, spans, *, coverage=(), incomplete=False):
        from app.company.improvement_rules import analyze
        candidates, diagnostics = (self.analyzer or analyze)(data, spans, coverage=coverage, incomplete=incomplete)
        def texts(*subjects):
            return [dict(text=c['content'], evidence=c['data']['evidence'],
                         uncertainty=c['data']['uncertainty']) for c in candidates
                    if c['category']=='STRUCTURE' and c['data']['subject'] in subjects]
        from app.company.improvement_language import classify_domains
        structure=dict(current_state=texts('as_is','현황'), problems=texts('problem','문제','업무요구 후보'),
            cause_candidates=texts('원인 후보'), goals=texts('goal','to_be','개선 목표'),
            required_functions=texts('required_functions','필요 기능'),
            scope_constraints=texts('constraints','적용 범위','제약사항'),
            missing_information=[dict(subject=c['data']['subject'],question=c['data'].get('question',''),
                uncertainty=c['data']['uncertainty']) for c in candidates if c['category']!='STRUCTURE'],
            domains=classify_domains(spans), review_status='UNREVIEWED_CANDIDATES')
        return StructuredAnalysisResult('improvement-result-v1','RULE',VERSION,context,structure,
            tuple(candidates),tuple(diagnostics),
            ('제한된 명시 표현·규칙 분석; 범용 AI 의미분석 아님',
             '원인·추천·정보부족은 사람 검토 후보이며 확정 사실이 아님'))

def execute_provider(name, context, data, spans, *, coverage=(), incomplete=False, rule_analyzer=None):
    ensure_provider(name)
    result=RuleProvider(rule_analyzer).analyze(context,data,spans,coverage=coverage,incomplete=incomplete)
    if result.context!=context or result.provider!='RULE':
        raise Denied('ANALYSIS_SOURCE_MISMATCH',409)
    return result

def public_result(result):
    return asdict(result)
