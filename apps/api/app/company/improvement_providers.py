"""MVP provider availability. External adapters and credentials do not exist."""
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
