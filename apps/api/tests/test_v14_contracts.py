from datetime import datetime,timezone,timedelta
import pytest
from pydantic import ValidationError
from app.company.contracts import Financial
from app.proposal.recorded_authorization import Authorization

def financial(**kwargs):return Financial(year=2025,revenue='9007199254740993',period='2025',unit='원',currency='KRW',**kwargs)
def test_exact_financial_contract_and_manual_inconsistency_review():
 row=financial(assets='9007199254740993',liabilities='1',equity='9007199254740992')
 assert row.assets=='9007199254740993' and row.current_assets is None
 with pytest.raises(ValidationError):financial(assets='4',liabilities='1',equity='2')
 assert financial(assets='4',liabilities='1',equity='2',consistency_note='Source checked; unresolved mismatch').assets=='4'
 with pytest.raises(ValidationError):financial(assets='1.5')
 with pytest.raises(ValidationError):financial(source_parse_id='only-one-half')

def test_recorded_authorization_requires_actual_person_time_and_evidence():
 data=dict(actual_approver_name='TEST Director',actual_approver_title='CEO',approved_at=datetime.now(timezone.utc)-timedelta(minutes=5),method='ORAL',context='Confirmed exact proposal in meeting')
 assert Authorization(**data).actual_approver_name=='TEST Director'
 for change in [dict(actual_approver_name=' '),dict(approved_at=datetime.now()),dict(approved_at=datetime.now(timezone.utc)+timedelta(days=1)),dict(context=''),dict(method='DOCUMENT')]:
  with pytest.raises(ValidationError):Authorization(**(data|change))
 assert Authorization(**(data|dict(method='DOCUMENT',file_id='TEST-FILE'))).file_id=='TEST-FILE'
