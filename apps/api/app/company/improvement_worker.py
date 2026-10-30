"""Production worker for exact submitted inputs. All extraction is local."""
from dataclasses import replace
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from hashlib import sha256
from sqlalchemy import update
from app.company.application import CompanyApplication
from app.company.improvement_analysis import ImprovementAnalysis, KIND, digest
from app.company.documents import parse_document, DocumentError
from app.company.improvement_rules import validate, VERSION
from app.company.improvement_providers import AnalysisContext,ensure_provider,execute_provider,public_result
from app.infrastructure import company_business_schema as B
from app.infrastructure import company_schema as C, improvement_schema as S, notice_schema as N
from app.infrastructure.database import get_session_factory
from app.infrastructure.notice_queue import claim
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.core.config import ROOT
from app.notice.domain import Actor, Denied

@contextmanager
def publication(factory,job,attempt):
    try:
        with factory.begin() as session:yield session
    except Exception:
        # Roll back the complete candidate/parse/draft graph before recording failure.
        # Never log source text or exception messages.
        with factory.begin() as session:
            a=CompanyApplication(session,None);j=a.get(N.jobs,job['id'],True);t=a.get(N.attempts,attempt['id'],True)
            if j['state']=='PROCESSING' and t['state']=='PROCESSING' and t['owner']==attempt['owner']:
                session.execute(update(N.jobs).where(N.jobs.c.id==j['id']).values(state='FAILED',error='ANALYSIS_OUTPUT_OR_STORAGE_FAILED',lease_until=None))
                session.execute(update(N.attempts).where(N.attempts.c.id==t['id']).values(state='FAILED',error='ANALYSIS_OUTPUT_OR_STORAGE_FAILED'))

def extract(name,raw):
    p=parse_document(name,raw)
    if p.format=='pdf' and any('OCR/manual' in l for l in p.limitations):
        try:
            from app.company.ocr import ocr_pdf
            present={l.page for l in p.locations};extra=ocr_pdf(raw)
            missing=[l for l in p.limitations if 'OCR/manual' not in l or not any(str(e.page) in l.split(':')[0].split() for e in extra)]
            return replace(p,locations=p.locations+tuple(l for l in extra if l.page not in present),limitations=tuple(missing)+('Local OCR candidate; original and human review required',),parser_version='improvement-local-ocr-v1')
        except DocumentError as e:
            return replace(p,limitations=p.limitations+(str(e),))
    return p

def process_improvement_one(factory=None,files=None,extractor=extract,before_publish=None):
    factory=factory or get_session_factory();files=files or LocalPrivateFiles(ROOT/'storage/private/notice')
    with factory.begin() as session:claimed=claim(session,kind=KIND)
    if not claimed:return False
    job,attempt=claimed;prepared=[];error=None
    try:
        with factory() as session:
            a=CompanyApplication(session,files);actor=a.get(N.actors,job['actor_id']);who=Actor(actor['id'],actor['role']);svc=ImprovementAnalysis(a)
            m=a.rows(S.manifests,job_id=job['id'])[0];v,_,_=svc.target(who,m['version_id'])
            ensure_provider(m['data'].get('provider','RULE'))
            sources=a.rows(S.inputs,manifest_id=m['id'])
        for x in sources:
            if not x['file_id']:continue
            item=dict(input=x,parsed=None,error=None,evidence=[])
            if not x['data']['included']:
                item['error']='NOT_INSPECTED';prepared.append(item);continue
            with factory() as session:
                a=CompanyApplication(session,files);actor=a.get(N.actors,job['actor_id']);who=Actor(actor['id'],actor['role'])
                ImprovementAnalysis(a).target(who,m['version_id'])
                f=a.get(C.files,x['file_id'])
                if x['parse_id']:
                    p=a.get(C.parses,x['parse_id'])
                    ev=a.rows(C.evidence,parse_id=p['id'])
                else:p=None;ev=[]
            # Binary IO and bounded OCR run with no open DB session/transaction.
            raw=files.read(f['storage_key'],x['data']['digest'])
            if f['id']!=x['file_id'] or f['digest']!=x['data']['digest'] or sha256(raw).hexdigest()!=f['digest']:
                raise DocumentError('ANALYSIS_DIGEST_MISMATCH')
            # Historical parses have no purpose/scope/digest attestation. Revalidate
            # the native reader's exact range against the same immutable bytes.
            # This is deliberately separate from OCR and specialized field extraction.
            if p and p['file_id']==f['id'] and p['error'] is None and p['parser_version']=='company-local-parser-v1':
                try:
                    checked=parse_document(f['name'],raw)
                    expected=sorted((l.descriptor,l.page or 0,l.text) for l in checked.locations)
                    actual=sorted((e['descriptor'],e['page'] or 0,e['text']) for e in ev if e['file_id']==f['id'] and e['parse_id']==p['id'])
                    if expected and not any('OCR/manual' in l for l in checked.limitations) and len(actual)==len(ev) and actual==expected and list(checked.limitations)==p['limitations']:
                        item.update(reuse=p,evidence=ev,scope_verified=True)
                except DocumentError:pass
            if not item.get('reuse'):
                try:
                    item['parsed']=extractor(f['name'],raw)
                    if item['parsed'].digest!=f['digest']:raise DocumentError('ANALYSIS_PARSE_DIGEST_MISMATCH')
                except DocumentError as e:item.update(parsed=None,error=str(e))
            prepared.append(item)
    except Exception as exc:error=exc.reason if isinstance(exc,Denied) else 'ANALYSIS_INPUT_FAILED'
    if before_publish:before_publish(job,attempt)
    with publication(factory,job,attempt) as session:
        a=CompanyApplication(session,files)
        m=a.rows(S.manifests,job_id=job['id'])[0];actor=a.get(N.actors,job['actor_id']);who=Actor(actor['id'],actor['role'])
        # Same Company -> Job lock order as request/retry/send commands.
        try:ImprovementAnalysis(a).target(who,m['version_id'],True)
        except Denied as exc:error=exc.reason
        current=a.get(N.jobs,job['id'],True);t=a.get(N.attempts,attempt['id'],True)
        history=sorted(a.rows(N.attempts,job_id=job['id']),key=lambda row:row['ordinal'])
        if current['state']!='PROCESSING' or t['state']!='PROCESSING' or t['owner']!=attempt['owner'] or history[-1]['id']!=t['id'] or current['lease_until']<=datetime.now(timezone.utc):return True
        if error:
            for table,key in ((N.jobs,job['id']),(N.attempts,t['id'])):
                values=dict(state='FAILED',error=error)
                if table is N.jobs:values['lease_until']=None
                session.execute(update(table).where(table.c.id==key).values(**values))
            return True
        v=a.get(C.improvement_versions,m['version_id']);spans=[]
        for field in ('original_text','as_is','problem','impact','goal','to_be','required_functions','constraints','missing'):
            if v['data'].get(field,'').strip():spans.append(dict(kind='IMPROVEMENT',version_id=v['id'],field=field,quote=v['data'][field]))
        profile=a.get(C.inputs,m['input_version_id'])
        if profile['data'].get('overview','').strip():spans.append(dict(kind='COMPANY_INPUT',version_id=profile['id'],field='overview',quote=profile['data']['overview']))
        site=a.get(C.site_versions,m['site_version_id'])
        if site['data'].get('process','').strip():spans.append(dict(kind='SITE',version_id=site['id'],field='process',quote=site['data']['process']))
        for fact in m['data']['facts']:
            fv=a.get(C.fact_versions,fact['id']);f=a.get(C.facts,fv['fact_id'])
            spans.append(dict(kind='FACT',version_id=fv['id'],review_id=fact['review_id'],evidence_id=fact['evidence_id'],quote=fv['value'],field='fact:'+f['field']))
        for source in a.rows(S.inputs,manifest_id=m['id']):
            if source['evidence_id']:
                e=a.get(C.evidence,source['evidence_id'])
                if e['text'].strip():spans.append(dict(kind='EVIDENCE',evidence_id=e['id'],descriptor=e['descriptor'],quote=e['text'],mode=e['mode']))
        for source in m['data'].get('reviewed_answers',[]):
            reply=a.get(B.responses,source['response_id']);request=a.get(B.requests,source['request_id']);review=a.get(B.request_reviews,source['review_id'])
            if request['company_id']!=m['company_id'] or request['improvement_version_id'] not in (None,m['version_id']) or reply['request_id']!=request['id'] or review['request_id']!=request['id'] or review['response_id']!=reply['id'] or review['outcome']!='VERIFIED' or not reply['submitted'] or sha256(reply['message'].encode()).hexdigest()!=source['message_digest']:
                raise ValueError('REVIEWED_ANSWER_SCOPE_MISMATCH')
            if reply['message'].strip():spans.append(dict(kind='RESPONSE',request_id=request['id'],response_id=reply['id'],review_id=review['id'],quote=reply['message']))
        run=a.add(N.runs,analysis_kind=KIND,attempt_id=t['id'],actor_id=who.id,provider_version=VERSION,extractor_version='company-local-parser-v1/improvement-local-ocr-v1',missing=[],conflicts=[])
        incomplete=False;limits=[];coverage=[]
        for item in prepared:
            x=item['input'];p=item.get('reuse');ev=item['evidence'];parsed=item['parsed'];err=item['error'];limitations=[]
            if parsed:
                p=a.add(C.parses,file_id=x['file_id'],actor_id=who.id,parser_version=parsed.parser_version,error=None,limitations=list(parsed.limitations))
                ev=[a.add(C.evidence,actor_id=who.id,company_id=m['company_id'],site_id=a.get(C.files,x['file_id'])['site_id'],file_id=x['file_id'],parse_id=p['id'],descriptor=l.descriptor,page=l.page,text=l.text,mode='ANALYSIS_EXTRACTION') for l in parsed.locations]
            elif err and err!='NOT_INSPECTED':
                p=a.add(C.parses,file_id=x['file_id'],actor_id=who.id,parser_version='company-local-parser-v1',error=err,limitations=[])
            if p:limitations=p['limitations']
            status=('NOT_SELECTED' if x['data'].get('selection')=='NOT_SELECTED' else 'EXCLUDED' if x['data'].get('exclude_reason') else 'UNSUPPORTED' if not x['data'].get('supported',Path(x['data']['name']).suffix.lower() in ('.pdf','.docx','.xlsx','.txt')) else 'NOT_INSPECTED') if err=='NOT_INSPECTED' else 'FAILED' if err or not ev else 'PARTIAL' if limitations else 'COMPLETE'
            if status!='COMPLETE' and not (status in ('EXCLUDED','NOT_SELECTED') and x['origin']=='COMMON_REFERENCE'):incomplete=True
            data=dict(status=status,method='NOT_RUN' if err=='NOT_INSPECTED' else 'REUSED_TEXT' if item.get('reuse') else 'LOCAL_OCR' if parsed and 'ocr' in parsed.parser_version else 'LOCAL_TEXT',
                parser_version=p['parser_version'] if p else None,error_code=err,limitations=limitations,
                locations=[dict(descriptor=e['descriptor'],page=e['page']) for e in ev],scope_known=bool(parsed or item.get('scope_verified')),
                purpose='IMPROVEMENT_LABEL_SEARCH',scope_kind='EXTRACTABLE_TEXT_ONLY',reuse_verified=bool(item.get('scope_verified')),
                reuse_decision='VALIDATED_NATIVE_RANGE' if item.get('reuse') else 'NOT_INSPECTED' if err=='NOT_INSPECTED' else 'REEXTRACTED_OR_ATTEMPTED',
                file_id=x['file_id'],selected_parse_id=x['parse_id'],exclude_reason=x['data'].get('exclude_reason',''),
                digest=x['data']['digest'])
            inspection=a.add(S.inspections,run_id=run['id'],input_id=x['id'],parse_id=p['id'] if p else None,data=data)
            coverage.append(dict(data,inspection_id=inspection['id'],origin=x['origin']))
            for e in ev:spans.append(dict(kind='DOCUMENT',evidence_id=e['id'],inspection_id=inspection['id'],file_id=x['file_id'],descriptor=e['descriptor'],page=e['page'],quote=e['text']))
            if status!='COMPLETE' and not (status in ('EXCLUDED','NOT_SELECTED') and x['origin']=='COMMON_REFERENCE'):limits.append(dict(category='PROCESSING_LIMITATION',content=f"자료 {x['data']['name']}: {status}",reason='검사하지 못한 자료를 정보부족 증거로 사용하지 않음',data=dict(subject='document',rule_id='PROCESSING',rule_version=VERSION,claim_kind='PROCESSING_STATUS',evidence=[],inspection_id=inspection['id'],uncertainty='자료 내용 전체를 판단하지 못함',question='자료를 직접 확인하거나 읽을 수 있는 자료를 보완해 주세요.')))
        result=execute_provider(m['data'].get('provider','RULE'),AnalysisContext(m['company_id'],m['version_id'],m['digest']),v['data'],spans,coverage=coverage)
        output=list(result.candidates);diagnostics=list(result.diagnostics)
        for c in output+limits:
            c['data']['inspection_ids']=[x['id'] for x in a.rows(S.inspections,run_id=run['id'])]
            c['data']['searched_fields']=['original_text','as_is','problem','goal','to_be','required_functions','constraints','overview','process','confirmed_fact_values']
            validate(c,spans)
            candidate=a.add(N.candidates,run_id=run['id'],analysis_kind=KIND,kind=c['category'],content=c['content'],reason=c['reason'])
            a.add(S.details,candidate_id=candidate['id'],category=c['category'],data=c['data'])
        state='PARTIAL' if incomplete else 'SUCCEEDED'
        structured=public_result(result);structured.pop('candidates');structured.pop('diagnostics')
        a.add(S.contexts,run_id=run['id'],manifest_id=m['id'],status=state,diagnostics=dict(rules=diagnostics,structured_result=structured,candidate_count=len(output)+len(limits),execution_hash=digest([x['data'] for x in a.rows(S.inspections,run_id=run['id'])])))
        for table,key in ((N.jobs,job['id']),(N.attempts,t['id'])):
            values=dict(state=state,error=None)
            if table is N.jobs:values['lease_until']=None
            session.execute(update(table).where(table.c.id==key).values(**values))
        a.record(who,m['company_id'],'COMPLETE_IMPROVEMENT_ANALYSIS',improvement_version_id=m['version_id'])
    return True
