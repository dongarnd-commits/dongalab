import json,re,unicodedata
from datetime import date
from hashlib import sha256
from sqlalchemy import select,insert,update,func,or_,text,false
from app.notice.domain import Denied
from app.infrastructure import capability_schema as S
from app.infrastructure.notice_schema import identity
from app.infrastructure.dmp_inventory import parse_inventory
from app.infrastructure.confirmed_notice_reader import ConfirmedNoticeReader
from app.infrastructure.notice_store import SqlNoticeStore
from app.capability.input import UnavailableImprovement
from app.capability.search import search_reasons
from app.capability.lineage import AnalysisLineage
from app.infrastructure import analysis_schema as A
from app.capability.comparison import compare, read_comparison_inputs, input_snapshot

def fingerprint(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def frozen_json(value):
    def encode(v):
        if isinstance(v,date): return v.isoformat()
        raise TypeError("Unsupported snapshot value")
    return json.loads(json.dumps(value,default=encode,ensure_ascii=False))

def terms(query):
    value=unicodedata.normalize('NFKC',query).lower()
    result=re.findall(r'[가-힣a-z0-9]{2,}',value)
    if '입출고' in value: result+=['입고','출고']
    for word in ('재고','입고','출고','불량','품질','생산','문서','결재'):
        if word in value: result.append(word)
    return list(dict.fromkeys(result))[:30]

class CapabilityApplication:
    def __init__(self,session,files=None,inputs=None):
        self.session=session; self.files=files; self.inputs=inputs or UnavailableImprovement()
    def authorize(self,actor,manage=False):
        if actor.role not in (('DATCO_ADMIN',) if manage else ('DATCO_ADMIN','DATCO_OPERATOR')):
            raise Denied('ACTION_NOT_AUTHORIZED',403)
    def operator(self,actor):
        if actor.role!='DATCO_OPERATOR': raise Denied('ACTION_NOT_AUTHORIZED',403)
    def get(self,table,key,lock=False):
        q=select(table).where(table.c.id==key)
        row=self.session.execute(q.with_for_update() if lock else q).mappings().first()
        if not row: raise Denied('OBJECT_NOT_FOUND',404)
        return dict(row)
    def add(self,table,**values):
        values.setdefault('id',identity())
        return dict(self.session.execute(insert(table).values(**values).returning(table)).mappings().one())
    def rows(self,table,**filters):
        return [dict(r) for r in self.session.execute(select(table).where(*[table.c[k]==v for k,v in filters.items()])).mappings()]
    def record(self,actor,action,**targets): return self.add(S.audit,actor_id=actor.id if actor else None,action=action,targets=targets)
    def command(self,actor,key,payload,execute):
        token=int.from_bytes(sha256((actor.id+key).encode()).digest()[:8],'big',signed=True)
        self.session.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':token})
        fp=fingerprint(payload); old=self.rows(S.receipts,actor_id=actor.id,key=key)
        if old:
            if old[0]['fingerprint']!=fp: raise Denied('IDEMPOTENCY_TARGET_MISMATCH')
            return old[0]['result']
        result=execute(); self.add(S.receipts,actor_id=actor.id,key=key,fingerprint=fp,result=result)
        return result
    def import_inventory(self,raw,actor=None):
        if actor: self.authorize(actor,True)
        inventory=parse_inventory(raw); digest=sha256(raw).hexdigest()
        lock=int.from_bytes(sha256(b'DATCO_DMP_INVENTORY').digest()[:8],'big',signed=True)
        self.session.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':lock})
        old=self.rows(S.imports,digest=digest)
        if old: return {'id':old[0]['id'],'feature_count':649,'replay':True}
        imported=self.add(S.imports,digest=digest,metadata=inventory.metadata.model_dump())
        roots={r['external_id']:r for r in self.rows(S.features)}
        existing=self.rows(S.revisions); revisions={(r['feature_id'],r['digest']):r for r in existing}
        ordinals={}
        for r in existing: ordinals[r['feature_id']]=max(ordinals.get(r['feature_id'],0),r['ordinal'])
        new_roots=[]; new_revisions=[]; new_members=[]
        for f in inventory.features:
            root=roots.get(f.feature_id)
            if root is None:
                root={'id':identity(),'external_id':f.feature_id}; roots[f.feature_id]=root; new_roots.append(root)
            data=f.model_dump(); fp=fingerprint(data); revision=revisions.get((root['id'],fp))
            if revision is None:
                ordinal=ordinals.get(root['id'],0)+1; ordinals[root['id']]=ordinal
                revision={'id':identity(),'feature_id':root['id'],'ordinal':ordinal,'digest':fp,'data':data}
                revisions[(root['id'],fp)]=revision; new_revisions.append(revision)
            new_members.append({'id':identity(),'import_id':imported['id'],'feature_id':root['id'],'revision_id':revision['id']})
        # Batch insertion stays in this single caller-owned transaction/advisory lock.
        if new_roots: self.session.execute(insert(S.features),new_roots)
        if new_revisions: self.session.execute(insert(S.revisions),new_revisions)
        self.session.execute(insert(S.members),new_members)
        self.record(actor,'IMPORT_DMP_FEATURES',import_id=imported['id'],digest=digest)
        return {'id':imported['id'],'feature_count':len(inventory.features),'replay':False}
    def inventory(self,actor,query='',system='',group='',page=1,limit=25,import_id=None):
        self.authorize(actor)
        if import_id: imported=self.get(S.imports,import_id)
        else:
            imported=self.session.execute(select(S.imports).order_by(S.imports.c.created_at.desc(),S.imports.c.id.desc()).limit(1)).mappings().first()
        if not imported: return {'items':[],'total':0,'page':page,'limit':limit,'import':None,'systems':[],'groups':[]}
        data=S.revisions.c.data; base=S.members.join(S.revisions,S.members.c.revision_id==S.revisions.c.id)
        filters=[S.members.c.import_id==imported['id']]
        if system: filters.append(data['system'].astext==system)
        if group: filters.append(data['feature_group'].astext==group)
        search=terms(query)
        if query.strip() and not search: filters.append(false())
        if search:
            filters.append(or_(*[or_(data['name'].astext.ilike('%'+t+'%'),data['description'].astext.ilike('%'+t+'%')) for t in search]))
        total=self.session.scalar(select(func.count()).select_from(base).where(*filters))
        rows=self.session.execute(select(S.revisions).select_from(base).where(*filters).order_by(data['system'].astext,data['feature_group'].astext,data['name'].astext,S.revisions.c.id).offset((page-1)*limit).limit(limit)).mappings()
        all_data=self.session.execute(select(data).select_from(base).where(S.members.c.import_id==imported['id'])).scalars().all()
        return {'items':[dict(r) for r in rows],'total':total,'page':page,'limit':limit,'import':dict(imported),
            'systems':sorted({d['system'] for d in all_data}),'groups':sorted({d['feature_group'] for d in all_data if not system or d['system']==system})}
    def feature(self,actor,key):
        self.authorize(actor); root=self.session.execute(select(S.features).where(S.features.c.external_id==key)).mappings().first()
        if not root: raise Denied('OBJECT_NOT_FOUND',404)
        return {'root':dict(root),'revisions':sorted(self.rows(S.revisions,feature_id=root['id']),key=lambda r:r['ordinal'])}
    def validate_capability(self,data):
        if not data['service'].strip() or not data['scope'].strip() or not data['evidence_note'].strip() or not data['problems'] or any(not p.strip() for p in data['problems']) or not data['functions']: raise Denied('REQUIRED_DATA_MISSING')
        ids=[f['revision_id'] for f in data['functions']]
        if len(set(ids))!=len(ids): raise Denied('DUPLICATE_FEATURE_REFERENCE')
        for f in data['functions']:
            self.get(S.revisions,f['revision_id'])
            if not f['role'].strip(): raise Denied('REQUIRED_DATA_MISSING')
    def save_capability(self,actor,data,key,capability_id=None,expected_revision=None):
        self.authorize(actor,True); self.validate_capability(data)
        def execute():
            if capability_id:
                root=self.get(S.capabilities,capability_id,True)
                if root['draft_revision']!=expected_revision: raise Denied('STALE_INPUT_VERSION')
                self.session.execute(update(S.capabilities).where(S.capabilities.c.id==capability_id).values(draft=data,draft_revision=root['draft_revision']+1))
                result={'id':capability_id,'draft_revision':root['draft_revision']+1}
            else:
                root=self.add(S.capabilities,draft=data,draft_revision=1,current_ordinal=0)
                result={'id':root['id'],'draft_revision':1}
            self.record(actor,'SAVE_CAPABILITY_DRAFT',**result); return result
        return self.command(actor,key,[capability_id,expected_revision,data],execute)
    def publish(self,actor,capability_id,expected_revision,key):
        self.authorize(actor,True)
        def execute():
            root=self.get(S.capabilities,capability_id,True)
            if root['draft_revision']!=expected_revision: raise Denied('STALE_INPUT_VERSION')
            data=root['draft']; self.validate_capability(data)
            existing=self.rows(S.versions,capability_id=capability_id)
            if existing:
                latest=max(existing,key=lambda v:v['ordinal'])
                if fingerprint(latest['data'])==fingerprint(data):
                    return {'id':latest['id'],'capability_id':capability_id,'ordinal':latest['ordinal']}
            # Every connected feature is exact immutable source evidence; extra assertions remain review notes.
            version=self.add(S.versions,capability_id=capability_id,ordinal=root['current_ordinal']+1,data=data,actor_id=actor.id)
            for f in data['functions']: self.add(S.links,version_id=version['id'],revision_id=f['revision_id'],role=f['role'])
            self.session.execute(update(S.capabilities).where(S.capabilities.c.id==capability_id).values(current_ordinal=version['ordinal']))
            self.record(actor,'PUBLISH_CAPABILITY_VERSION',version_id=version['id']); return {'id':version['id'],'capability_id':capability_id,'ordinal':version['ordinal']}
        return self.command(actor,key,[capability_id,expected_revision,'publish'],execute)
    def catalog(self,actor,query=''):
        self.authorize(actor); result=[]
        for root in self.rows(S.capabilities):
            versions=sorted(self.rows(S.versions,capability_id=root['id']),key=lambda v:v['ordinal'])
            visible=versions[-1]['data'] if versions else (root['draft'] if actor.role=='DATCO_ADMIN' else None)
            if visible is None: continue
            linked=[self.get(S.revisions,f['revision_id'])['data'] for f in visible['functions']]
            reasons=search_reasons(query,visible,linked)
            if query.strip() and not reasons: continue
            result.append({'id':root['id'],'current_ordinal':root['current_ordinal'],'data':visible,'version_id':versions[-1]['id'] if versions else None,'search_reasons':reasons})
        return result
    def capability(self,actor,key):
        self.authorize(actor); root=self.get(S.capabilities,key)
        if actor.role!='DATCO_ADMIN': root={k:v for k,v in root.items() if k not in ('draft','draft_revision')}
        versions=sorted(self.rows(S.versions,capability_id=key),key=lambda v:v['ordinal'])
        if not versions and actor.role!='DATCO_ADMIN': raise Denied('OBJECT_NOT_FOUND',404)
        return {'root':root,'versions':versions}
    def require_input_provider(self,actor):
        self.operator(actor)
        if isinstance(self.inputs,UnavailableImprovement):
            raise Denied('IMPROVEMENT_PROVIDER_NOT_CONNECTED',503)
    def context(self,actor,version_id,require_current=True):
        self.operator(actor); context=self.inputs.read(actor,version_id)
        if context.get('improvement_version_id')!=version_id or not context.get('company_id') or not context.get('confirmed'):
            raise Denied('REQUIRED_DATA_MISSING')
        if require_current and context.get('current_valid') is not True: raise Denied('STALE_INPUT_VERSION')
        return context
    def candidates(self,actor,version_id):
        context=self.context(actor,version_id)
        return {'context':context,'candidates':self.catalog(actor,context['original_text']) if context['original_text'].strip() else []}
    def save_composition(self,actor,data,key,composition_id=None,expected_version=None):
        context=self.context(actor,data['improvement_version_id'],require_current=False)
        ids=data['capability_version_ids']
        if len(ids)!=len(set(ids)) or not ids or not data['name'].strip() or not data['coverage']: raise Denied('REQUIRED_DATA_MISSING')
        selected=[self.get(S.versions,v) for v in ids]; roots={}
        for v in selected:
            root=self.get(S.capabilities,v['capability_id'])
            for link in self.rows(S.links,version_id=v['id']):
                feature=self.get(S.revisions,link['revision_id']); fid=feature['feature_id']
                if fid in roots and roots[fid]!=feature['id']: raise Denied('FEATURE_REVISION_CONFLICT')
                roots[fid]=feature['id']
        selected_features=set(roots.values())
        excluded=set(data.get('excluded_feature_revision_ids',[]))
        if not excluded<=selected_features: raise Denied('TARGET_VERSION_MISMATCH')
        active=selected_features-excluded
        for coverage in data['coverage']:
            if not isinstance(coverage.get('requirement'),str) or not coverage['requirement'].strip() or not isinstance(coverage.get('role'),str) or not coverage['role'].strip():
                raise Denied('REQUIRED_DATA_MISSING')
            cap_features={l['revision_id'] for l in self.rows(S.links,version_id=coverage['capability_version_id'])}
            if coverage['capability_version_id'] not in ids or not set(coverage['feature_revision_ids'])<=(active & cap_features):
                raise Denied('TARGET_VERSION_MISMATCH')
        if composition_id and self.get(S.compositions,composition_id)['company_id']!=context['company_id']: raise Denied('OBJECT_NOT_FOUND',404)
        def execute():
            # Shared order with prepare_match: Composition root, then sorted Capability roots.
            if composition_id: self.get(S.compositions,composition_id,True)
            self.context(actor,data['improvement_version_id'])
            for capability_id in sorted({v['capability_id'] for v in selected}):
                self.get(S.capabilities,capability_id,True)
            for selected_version in selected:
                if self.get(S.capabilities,selected_version['capability_id'])['current_ordinal']!=selected_version['ordinal']: raise Denied('STALE_INPUT_VERSION')
            if composition_id:
                root=self.get(S.compositions,composition_id,True)
                if root['company_id']!=context['company_id']: raise Denied('OBJECT_NOT_FOUND',404)
                previous=self.get(S.composition_versions,expected_version)
                if previous['composition_id']!=root['id'] or previous['ordinal']!=root['current_ordinal']: raise Denied('STALE_INPUT_VERSION')
                self.session.execute(update(S.compositions).where(S.compositions.c.id==root['id']).values(current_ordinal=root['current_ordinal']+1))
                ordinal=root['current_ordinal']+1
            else:
                root=self.add(S.compositions,company_id=context['company_id'],current_ordinal=1); ordinal=1
            version=self.add(S.composition_versions,composition_id=root['id'],ordinal=ordinal,improvement_version_id=context['improvement_version_id'],context=context,data=data,actor_id=actor.id)
            for v in selected:
                assessment=self.new_assessment(actor,context,v['id'],version['id'])
                self.add(S.composition_links,version_id=version['id'],capability_version_id=v['id'],assessment_id=assessment['id'])
            self.record(actor,'SAVE_SERVICE_COMPOSITION',version_id=version['id'])
            return {'id':root['id'],'version_id':version['id'],'ordinal':ordinal}
        return self.command(actor,key,[composition_id,expected_version,data],execute)
    def composition(self,actor,key,version_id=None):
        self.require_input_provider(actor); root=self.get(S.compositions,key)
        versions=sorted(self.rows(S.composition_versions,composition_id=key),key=lambda v:v['ordinal'])
        current=versions[-1]; context=self.context(actor,current['improvement_version_id'],require_current=False)
        if context['company_id']!=root['company_id']: raise Denied('OBJECT_NOT_FOUND',404)
        if version_id and not any(v['id']==version_id for v in versions): raise Denied('OBJECT_NOT_FOUND',404)
        return {'root':root,'versions':versions,'capability_versions':list({l['capability_version_id']:self.get(S.versions,l['capability_version_id']) for v in versions for l in self.rows(S.composition_links,version_id=v['id'])}.values()),'assessments':[self.get(S.assessments,l['assessment_id']) for v in versions for l in self.rows(S.composition_links,version_id=v['id']) if l['assessment_id']]}
    def new_assessment(self,actor,context,capability_version_id,composition_version_id=None,previous_assessment_id=None):
        version=self.get(S.versions,capability_version_id)
        if self.get(S.capabilities,version['capability_id'])['current_ordinal']!=version['ordinal']:raise Denied('STALE_INPUT_VERSION')
        run=AnalysisLineage(self).run(actor,'CAPABILITY_ASSESSMENT',['TASK_APPLICABILITY_REVIEW_REQUIRED'],[])
        assessment=self.add(S.assessments,company_id=context['company_id'],improvement_version_id=context['improvement_version_id'],
            capability_version_id=capability_version_id,state='REVIEW_REQUIRED',fit='NEED_MORE_INFO',
            reason='Selected source functions require task applicability review.',analysis_run_id=run['id'],legacy_lineage=False,
            input={'context':frozen_json(context),'capability_version_id':capability_version_id,
                'feature_revision_ids':[l['revision_id'] for l in self.rows(S.links,version_id=capability_version_id)]})
        AnalysisLineage(self).assessment(actor,assessment,run,composition_version_id,previous_assessment_id)
        return assessment
    def request_assessment(self,actor,improvement_version_id,capability_version_id,key,previous_assessment_id=None):
        context=self.context(actor,improvement_version_id)
        if previous_assessment_id:
            previous=self.assessment(actor,previous_assessment_id)
            if previous['company_id']!=context['company_id']:raise Denied('OBJECT_NOT_FOUND',404)
            if previous['state'] not in ('CONFIRMED','REVISION_REQUIRED'):raise Denied('TRANSITION_NOT_ALLOWED')
        def execute():
            latest=self.context(actor,improvement_version_id)
            result=self.new_assessment(actor,latest,capability_version_id,previous_assessment_id=previous_assessment_id)
            self.record(actor,'REASSESS_CAPABILITY' if previous_assessment_id else 'REQUEST_CAPABILITY_ASSESSMENT',assessment_id=result['id'],previous_assessment_id=previous_assessment_id,run_id=result['analysis_run_id'])
            return {'id':result['id'],'state':result['state'],'fit':result['fit'],'analysis_run_id':result['analysis_run_id']}
        return self.command(actor,key,[improvement_version_id,capability_version_id,previous_assessment_id],execute)
    def assessment(self,actor,key):
        self.require_input_provider(actor); assessment=self.get(S.assessments,key)
        context=self.context(actor,assessment['improvement_version_id'],require_current=False)
        if context['company_id']!=assessment['company_id']: raise Denied('OBJECT_NOT_FOUND',404)
        version=self.get(S.versions,assessment['capability_version_id'])
        valid=context.get('current_valid') is True and self.get(S.capabilities,version['capability_id'])['current_ordinal']==version['ordinal']
        return dict(assessment,current_valid=valid,lineage=AnalysisLineage(self).detail(assessment),reviews=self.rows(A.assessment_reviews,assessment_id=key))
    def review_assessment(self,actor,key,decision,note,command_key):
        assessment=self.assessment(actor,key); version=self.get(S.versions,assessment['capability_version_id'])
        if decision not in ('CONFIRMED','REVISION_REQUIRED') or not note.strip(): raise Denied('REQUIRED_DATA_MISSING')
        def execute():
            if not self.assessment(actor,key)['current_valid']: raise Denied('STALE_INPUT_VERSION')
            current=self.get(S.assessments,key,True)
            if current['state']!='REVIEW_REQUIRED': raise Denied('TRANSITION_NOT_ALLOWED')
            self.session.execute(update(S.assessments).where(S.assessments.c.id==key).values(state=decision))
            common=AnalysisLineage(self).common_review(actor,current,note)
            audit=self.record(actor,'REVIEW_CAPABILITY_ASSESSMENT',assessment_id=key,decision=decision,note=note,fit=current['fit'],analysis_review_id=common['id'])
            actual=self.add(A.assessment_reviews,assessment_id=key,actor_id=actor.id,analysis_review_id=common['id'],decision=decision,note=note,audit_id=audit['id'],created_at=common['created_at'])
            self.add(A.review_contexts,review_id=common['id'],assessment_review_id=actual['id'],match_review_id=None)
            return {'id':key,'state':decision,'fit':current['fit']}
        return self.command(actor,command_key,[key,decision,note],execute)
    def prepare_match(self,actor,composition_version_id,notice_id,requirement_version_id,key):
        self.require_input_provider(actor); cv=self.get(S.composition_versions,composition_version_id)
        self.composition(actor,cv['composition_id'])
        def execute():
            # Do not reuse a root read before command's idempotency lock.
            root=self.get(S.compositions,cv['composition_id'],True)
            if root['current_ordinal']!=cv['ordinal']: raise Denied('STALE_INPUT_VERSION')
            context=self.context(actor,cv['improvement_version_id'])
            links=self.rows(S.composition_links,version_id=cv['id'])
            versions=[self.get(S.versions,link['capability_version_id']) for link in links]
            for capability_id in sorted({v['capability_id'] for v in versions}):
                self.get(S.capabilities,capability_id,True)
            for v in versions:
                if self.get(S.capabilities,v['capability_id'])['current_ordinal']!=v['ordinal']: raise Denied('STALE_INPUT_VERSION')
            # Notice confirmation/collection also lock this root before changing current input.
            from app.infrastructure.notice_schema import notices
            self.get(notices,notice_id,True)
            notice=frozen_json(ConfirmedNoticeReader(SqlNoticeStore(self.session),self.files).read(actor,notice_id,requirement_version_id))
            comparison_inputs=read_comparison_inputs(self.inputs,actor,context,notice)
            comparison=compare(comparison_inputs,context['company_id'],context.get('site_id'),notice)
            snapshot=self.add(S.match_snapshots,composition_version_id=cv['id'],requirement_version_id=requirement_version_id,input={'comparison':frozen_json(input_snapshot(comparison_inputs)),'company':context,'composition':cv['data'],'capability_assessment_ids':[l['assessment_id'] for l in self.rows(S.composition_links,version_id=cv['id'])],'capability_assessments':[frozen_json(self.get(S.assessments,l['assessment_id'])) for l in self.rows(S.composition_links,version_id=cv['id']) if l['assessment_id']],'notice':notice})
            data={'reason':'Confirmed sources are available; scope and eligibility require human review.',
                'dimensions':{'service':{'scope':cv['data']['coverage']},'support_scope':{'items':[i for i in notice['items'] if i['kind']=='SUPPORT_SCOPE']},'eligibility':{'items':[i for i in notice['items'] if i['kind'] in ('ELIGIBILITY_REQUIREMENT','CONDITIONAL_REQUIREMENT','APPLICATION_PERIOD')]}},
                'missing':['COMPANY_AND_SUPPLIER_ELIGIBILITY_REVIEW_REQUIRED','SERVICE_SCOPE_REVIEW_REQUIRED'], 'opposing_evidence':[], 'notice_limitations':notice['limitations']}
            data['dimensions']['eligibility']['comparisons']=comparison['conditions']
            data['opposing_evidence']=comparison['opposing_evidence']
            data['missing']=sorted(set(data['missing']+comparison['missing']))
            if comparison['fit']=='MISMATCH': data['reason']='Confirmed mandatory eligibility conflict; a candidate requiring human review.'
            run=AnalysisLineage(self).run(actor,'SUPPORT_MATCHING',data['missing'],data['opposing_evidence'])
            candidate=self.add(S.match_candidates,snapshot_id=snapshot['id'],fit=comparison['fit'],data=data,analysis_run_id=run['id'],legacy_lineage=False)
            AnalysisLineage(self).match(candidate,run)
            self.record(actor,'REQUEST_MATCH_ANALYSIS',snapshot_id=snapshot['id'],candidate_id=candidate['id'])
            return {'snapshot_id':snapshot['id'],'candidate_id':candidate['id'],'fit':candidate['fit'],'data':data,'analysis_run_id':candidate['analysis_run_id']}
        return self.command(actor,key,[composition_version_id,notice_id,requirement_version_id],execute)
    def match(self,actor,key):
        self.require_input_provider(actor); candidate=self.get(S.match_candidates,key); snapshot=self.get(S.match_snapshots,candidate['snapshot_id'])
        cv=self.get(S.composition_versions,snapshot['composition_version_id']); self.composition(actor,cv['composition_id'])
        current=self.get(S.compositions,cv['composition_id'])['current_ordinal']==cv['ordinal']
        context=self.context(actor,cv['improvement_version_id'],require_current=False)
        current=current and context.get('current_valid') is True
        # Re-read the same authority; changed Fact/condition inputs stale only this snapshot.
        if 'comparison' in snapshot['input']:
            latest=read_comparison_inputs(self.inputs,actor,context,snapshot['input']['notice'])
            current=current and fingerprint(input_snapshot(latest))==fingerprint(snapshot['input']['comparison'])
        for frozen in snapshot['input'].get('capability_assessments',[]):
            actual=self.get(S.assessments,frozen['id'])
            current=current and actual['state']==frozen['state'] and actual['fit']==frozen['fit']
        for link in self.rows(S.composition_links,version_id=cv['id']):
            v=self.get(S.versions,link['capability_version_id']); current=current and self.get(S.capabilities,v['capability_id'])['current_ordinal']==v['ordinal']
        try: ConfirmedNoticeReader(SqlNoticeStore(self.session),self.files).read(actor,snapshot['input']['notice']['notice_id'],snapshot['requirement_version_id'])
        except Denied: current=False
        return {'candidate':candidate,'snapshot':snapshot,'reviews':self.rows(S.match_reviews,candidate_id=key),'current_valid':current,'lineage':AnalysisLineage(self).detail(candidate,match=True)}
    def review_match(self,actor,candidate_id,outcome,note,key,completion_items=None):
        self.operator(actor); result=self.match(actor,candidate_id)
        if outcome=='PROPOSABLE' and completion_items is None: raise Denied('MISSING_REQUIRED_INFORMATION')
        if outcome not in ('PROPOSABLE','REQUEST_MORE_INFO','HOLD','EXCLUDE') or not note.strip(): raise Denied('REQUIRED_DATA_MISSING')
        def execute():
            result=self.match(actor,candidate_id)
            # Same input-root lock order as matching and Proposal creation.
            cv=self.get(S.composition_versions,result['snapshot']['composition_version_id'])
            self.get(S.compositions,cv['composition_id'],True)
            for cid in sorted({self.get(S.versions,l['capability_version_id'])['capability_id'] for l in self.rows(S.composition_links,version_id=cv['id'])}):self.get(S.capabilities,cid,True)
            from app.infrastructure.notice_schema import notices
            self.get(notices,result['snapshot']['input']['notice']['notice_id'],True)
            self.get(S.match_candidates,candidate_id,True)
            result=self.match(actor,candidate_id)
            if not result['current_valid']: raise Denied('STALE_INPUT_VERSION')
            if outcome=='PROPOSABLE':
                from app.proposal.policy import validate_completion
                validate_completion(self,actor,result,completion_items)
            common=AnalysisLineage(self).common_review(actor,result['candidate'],note,match=True)
            review=self.add(S.match_reviews,candidate_id=candidate_id,actor_id=actor.id,outcome=outcome,note=note,analysis_review_id=common['id'],legacy_lineage=False,created_at=common['created_at'])
            self.add(A.review_contexts,review_id=common['id'],assessment_review_id=None,match_review_id=review['id'])
            if outcome=='PROPOSABLE':
                from app.proposal.policy import attach
                attach(self,actor,result,review,completion_items)
            self.record(actor,'REVIEW_MATCH',review_id=review['id']); return {'id':review['id'],'outcome':outcome}
        return self.command(actor,key,[candidate_id,outcome,note,completion_items] if completion_items is not None else [candidate_id,outcome,note],execute)
