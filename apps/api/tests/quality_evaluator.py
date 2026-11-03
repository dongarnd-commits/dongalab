"""Finite synthetic quality evaluation; failures/unsupported inputs stay in the denominator.

Gold assertions are authored separately from the bounded implementation. The raw
projection is retained alongside each assertion, including source locations.
This evaluator neither estimates real-company accuracy nor measures human time.
"""
from pathlib import Path
from hashlib import sha256
import argparse
import json
import subprocess

from app.company import improvement_rules as rules
from app.company.improvement_language import scalar_observations
from app.company.documents import parse_document, DocumentError
from app.capability import asset_solutions as assets
from app.capability import recommendations
from test_asset_solutions import catalog, context, feature

CORPUS = Path(__file__).parent / 'fixtures/analysis_quality_development_v1.json'
ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILES = ['apps/api/app/company/improvement_language.py',
    'apps/api/app/company/improvement_structure.py', 'apps/api/app/company/improvement_rules.py',
    'apps/api/app/company/documents.py', 'apps/api/app/company/registration.py',
    'apps/api/app/company/statement_documents.py', 'apps/api/app/company/ocr.py',
    'apps/api/app/capability/asset_solutions.py', 'apps/api/app/capability/recommendations.py',
    'apps/api/tests/test_asset_solutions.py']


def evaluate_case(case):
    payload, gold = case['input'], case['gold']
    checks = []
    def check(metric, actual, expected):
        checks.append(dict(metric=metric,actual=actual,expected=expected,passed=actual==expected))
    if case['kind']=='rules':
        spans=payload['spans']
        candidates, diagnostics=rules.analyze(payload.get('data',{}),spans,coverage=payload.get('coverage',()))
        output=dict(candidates=candidates,diagnostics=diagnostics)
        for c in candidates:
            rules.validate(c,spans)
        structures=[[c['data']['subject'],c['content']] for c in candidates if c['category']=='STRUCTURE']
        for wanted in gold.get('structures',[]):
            check('classification',wanted in structures,True)
        for rule,outcome in gold.get('diagnostic',{}).items():
            found=next((d['outcome'] for d in diagnostics if d['rule']==rule),None)
            check('repeated_question_or_answer_state',found,outcome)
        check('candidate_source_grounding',all(e in spans for c in candidates for e in c['data']['evidence']),True)
    elif case['kind']=='scalars':
        result=scalar_observations(payload['spans'])
        output=[dict(label=k[0],context=k[1],dimension=k[2],values=[str(v) for v in values],evidence=list(values.values())) for k,values in result.items()]
        check('number_unit_period_values',sorted({str(v) for vs in result.values() for v in vs}),sorted(gold['values']))
        check('number_unit_period_groups',len(result),gold['groups'])
    elif case['kind']=='assets':
        cat=payload.get('catalog') or catalog()
        if payload.get('catalog_profile')=='duplicate':
            cat['features']=[feature('A','생산실적','생산 실적 기록',module='SYNTHETIC_CORE'),feature('B','작업실적','작업실적 기록',module='SYNTHETIC_COPY')]
        output=assets.generate(context(payload['text']),cat,payload.get('reviewed',()))
        selected={c['name'] for c in output['candidates']}
        check('recommendation_missing',sorted(set(gold['names'])-selected),[])
        # Duplicate profile permits alternative equivalent source candidates;
        # the combined proposal must not grow only because their tokens differ.
        if payload.get('catalog_profile')!='duplicate':
            check('recommendation_unnecessary',sorted(selected-set(gold['names'])),[])
        modules=len(output['alternatives'][0]['modules']) if output['alternatives'] else 0
        check('unnecessary_composite_modules',modules<=gold.get('top_max_modules',modules),True)
        original={f['revision_id']:f for f in cat['features']}
        check('catalog_quote_grounding',all(e['quote'] in ([original[c['revision_id']][e['field']]] if isinstance(original[c['revision_id']][e['field']],str) else original[c['revision_id']][e['field']]) for c in output['candidates'] for e in c['evidence']),True)
        if 'reviewed_evidence' in gold:
            row=next((r for a in output['alternatives'] for r in a['coverage'] if r['demand_id']=='analysis:SYNTHETIC_CANDIDATE'),{})
            check('reviewed_corrected_source_used',gold['reviewed_evidence'] in row.get('evidence_refs',[]),True)
    elif case['kind']=='parser':
        try:
            parsed=parse_document(payload['filename'],payload['text'].encode())
            output=dict(parser=parsed.parser_version,locations=[dict(descriptor=l.descriptor,text=l.text,page=l.page) for l in parsed.locations],limitations=list(parsed.limitations))
        except DocumentError as exc:
            output=dict(error=str(exc))
        for key,wanted in gold.items():
            check('parser_'+key,len(output.get('locations',[])) if key=='locations' else output.get(key),wanted)
    else:
        raise ValueError('UNSUPPORTED_EVALUATOR_CASE')
    return dict(id=case['id'],kind=case['kind'],passed=all(c['passed'] for c in checks),checks=checks,output=output)


def evaluate(corpus=CORPUS):
    frozen=json.loads(Path(corpus).read_text(encoding='utf-8'))
    results=[]
    for case in frozen['cases']:
        try:
            results.append(evaluate_case(case))
        except Exception as exc:
            results.append(dict(id=case['id'],kind=case['kind'],passed=False,checks=[],processing_failure=type(exc).__name__+': '+str(exc)))
    checks=[c for r in results for c in r['checks']]
    by_metric={key:dict(total=sum(c['metric']==key for c in checks),failed=sum(c['metric']==key and not c['passed'] for c in checks)) for key in sorted({c['metric'] for c in checks})}
    return dict(schema='analysis-quality-evaluation-v1',scope='SYNTHETIC_DEVELOPMENT_ONLY',
        code_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        corpus_sha256=sha256(Path(corpus).read_bytes()).hexdigest(),
        versions=dict(improvement_rule=rules.VERSION,asset_rule=assets.VERSION,published_rule=recommendations.VERSION,generic_parser='company-local-parser-v1',registration_ocr='company-registration-local-ocr-v1.2',financial_ocr='nts-business-layout-ocr-v1'),
        source_sha256={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_FILES},
        summary=dict(cases=len(results),passed=sum(r['passed'] for r in results),failed=sum(not r['passed'] for r in results),processing_failures=sum('processing_failure' in r for r in results),unsupported_inputs=sum(isinstance(r.get('output'),dict) and r['output'].get('error')=='UNSUPPORTED_FORMAT' for r in results),rejected_inputs=sum(isinstance(r.get('output'),dict) and 'error' in r['output'] for r in results),content_cases=sum(not (isinstance(r.get('output'),dict) and 'error' in r['output']) for r in results),content_passed=sum(r['passed'] and not (isinstance(r.get('output'),dict) and 'error' in r['output']) for r in results)),
        metrics=by_metric,operator_correction_proxy=sum(not c['passed'] for c in checks),
        limitations=['Synthetic finite development corpus, not unseen holdout or real-company accuracy.','Gold mismatch counts are a correction proxy, not measured operator time or rewrite volume.','No OCR execution, real-company files, corrected Fact persistence or authenticated DB workflow is evaluated here; existing integration guards require separate regression.','Unsupported and damaged inputs are reported as such; expected rejection is not successful extraction.'],results=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--corpus',default=str(CORPUS))
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=evaluate(args.corpus)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(summary=result['summary'],metrics=result['metrics']),ensure_ascii=False))
