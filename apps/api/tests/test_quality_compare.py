"""Provenance and evidence-preservation checks for the synthetic comparison CLI."""
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
TESTS = Path(__file__).parent
CORPUS = TESTS / 'fixtures/analysis_quality_round2_v1.json'


def invoke(output, code='HEAD'):
    return subprocess.run([sys.executable,str(TESTS/'quality_compare.py'),
        '--code',code,'--corpus',str(CORPUS),'--output',str(output)],
        cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)


def test_exact_commit_sources_and_all_adverse_cases_remain_in_the_report(tmp_path):
    output=tmp_path/'new-comparison.json'
    process=invoke(output)
    assert process.returncode==0,process.stderr
    report=json.loads(output.read_text(encoding='utf-8'))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert report['code_head']==report['code_selection']['selected_commit']==commit
    assert report['case_ids']==['H'+str(n).zfill(2) for n in range(1,25)]
    assert report['summary']['cases']==len(report['results'])==24
    assert report['summary']['declared_unsupported_grammar_cases']==5
    assert [r['id'] for r in report['results'] if r.get('support_status')]==['H10','H11','H12','H13','H14']
    assert report['summary']['processing_failures']==0
    assert report['summary']['rejected_inputs']==3
    assert report['scope']=='EXPOSED_REGRESSION_NOT_UNSEEN_HOLDOUT'
    for module in report['code_selection']['variable_modules']:
        path='apps/api/'+module.replace('.','/')+'.py'
        exact=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
        assert report['source_sha256'][path]==sha256(exact).hexdigest()
        assert report['source_loading'][path]['execution']=='EXACT_SELECTED_BYTES_COMPILED_IN_MEMORY'
        assert report['source_loading'][path]['selected']['bytes']==len(exact)
    assert all(row['support_lf_equivalent'] for row in report['source_loading'].values()
               if row['execution']=='WORKTREE_PURE_SUPPORT_IMPORT')


def test_existing_evidence_output_is_never_overwritten(tmp_path):
    output=tmp_path/'retained-result.json'
    original=b'TEST preserved raw evidence\r\n'
    output.write_bytes(original)
    process=invoke(output)
    assert process.returncode!=0
    assert 'OUTPUT_ALREADY_EXISTS' in process.stderr
    assert output.read_bytes()==original


def test_round2_preserves_raw_inputs_and_declares_every_gold_correction():
    second=json.loads(CORPUS.read_text(encoding='utf-8'))
    original_path=ROOT/second['source_corpus']['path']
    raw=original_path.read_bytes()
    assert sha256(raw).hexdigest()==second['source_corpus']['sha256']=='e2d0d22e91515bc46d11e4daac2ab3c3934ded49621b5d5bca2a80a688933cab'
    original=json.loads(raw)
    assert [c['input'] for c in second['cases']]==[c['input'] for c in original['cases']]
    changed=[before['id'] for before,after in zip(original['cases'],second['cases'],strict=True) if before['gold']!=after['gold']]
    assert changed==[r['id'] for r in second['round2_corrections']]==['H07','H08','H09','H24']
    assert sum(len(row['original_gold'].get('diagnostic',{})) for row in second['round2_corrections'])==4
    for source in second['preserved_original_results']:
        assert sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256']
    assert [c['gold'] for c in second['cases'][9:14]]==[c['gold'] for c in original['cases'][9:14]]
    assert second['cases'][23]['gold']['texts']==original['cases'][23]['input']['text'].splitlines()
