"""Common execution records and typed domain links in the caller-owned transaction."""
from app.infrastructure import notice_schema as N,analysis_schema as A
from app.notice.domain import Denied

class AnalysisLineage:
    def __init__(self,service):self.s=service
    def run(self,actor,kind,missing,conflicts):
        return self.s.add(N.runs,analysis_kind=kind,actor_id=actor.id,attempt_id=None,version_id=None,
            provider_version='capability-evidence-v1' if kind=='CAPABILITY_ASSESSMENT' else 'confirmed-code-membership-v1',
            extractor_version='not-applicable',missing=missing,conflicts=conflicts)
    def assessment(self,actor,assessment,run,composition_version_id=None,previous_assessment_id=None):
        self.s.add(A.capability_contexts,run_id=run['id'],assessment_id=assessment['id'],
            capability_version_id=assessment['capability_version_id'],composition_version_id=composition_version_id,
            improvement_version_id=assessment['improvement_version_id'],company_id=assessment['company_id'],
            previous_assessment_id=previous_assessment_id,input=assessment['input'])
        self.s.add(N.candidates,run_id=run['id'],analysis_kind='CAPABILITY_ASSESSMENT',kind='CAPABILITY_ASSESSMENT',
            assessment_id=assessment['id'],location_id=None,match_candidate_id=None,content=assessment['fit'],reason=assessment['reason'])
    def match(self,candidate,run):
        self.s.add(A.match_contexts,run_id=run['id'],snapshot_id=candidate['snapshot_id'],match_candidate_id=candidate['id'])
        self.s.add(N.candidates,run_id=run['id'],analysis_kind='SUPPORT_MATCHING',kind='SUPPORT_MATCHING',
            assessment_id=None,location_id=None,match_candidate_id=candidate['id'],content=candidate['fit'],reason=candidate['data']['reason'])
    def common_review(self,actor,domain,note,match=False):
        if not domain.get('analysis_run_id'):raise Denied('LEGACY_ANALYSIS_REQUIRES_REANALYSIS')
        candidates=self.s.rows(N.candidates,run_id=domain['analysis_run_id'])
        target='match_candidate_id' if match else 'assessment_id'
        candidate=next((c for c in candidates if c[target]==domain['id']),None)
        if candidate is None:raise Denied('REQUIRED_EVIDENCE_MISSING')
        return self.s.add(N.reviews,candidate_id=candidate['id'],actor_id=actor.id,
            analysis_kind='SUPPORT_MATCHING' if match else 'CAPABILITY_ASSESSMENT',outcome=None,official_verified=None,note=note)
    def detail(self,domain,match=False):
        context_table=A.match_contexts if match else A.capability_contexts
        target='match_candidate_id' if match else 'assessment_id'
        contexts=self.s.rows(context_table,**{target:domain['id']})
        runs=[]
        for context in contexts:
            run=self.s.get(N.runs,context['run_id'])
            candidates=self.s.rows(N.candidates,run_id=run['id'])
            reviews=[r for c in candidates for r in self.s.rows(N.reviews,candidate_id=c['id'])]
            runs.append(dict(run=run,context=context,candidates=candidates,reviews=reviews,
                review_contexts=[x for r in reviews for x in self.s.rows(A.review_contexts,review_id=r['id'])]))
        return {'legacy':domain.get('legacy_lineage',False),'runs':runs}
