"""Bounded PR21 recovery preflight. No stop/start/deployment actions.

Only the explicitly proven synthetic clone accepts normal business writes.
The actual owner's path is never accepted by the compatibility probe.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

TARGET = '3057acc861eef27249bbc49c86f1888377e575c6'
PREVIOUS = '04dfea4ee9d2521ba632c430c2218463df5df63c'
CONTROL = '8c98d6469b18ca17c3dd6cffc6c1c2633d612988'
PROTECTED = {18445, 8443, 8444, 49355, 49356}


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def hash_file(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding='utf-8')


def git(root, *args):
    return subprocess.check_output(['git', '--no-optional-locks', *args],
        cwd=root, text=True, encoding='utf-8').strip()


def clone_manifest(root):
    from acceptance_handover_projection import project_manifest
    root = Path(root).resolve()
    require(root.name.startswith('dongalab-handover-clone-'), 'PR21_SYNTHETIC_CLONE_REQUIRED')
    candidates = list((root/'storage/private/runtime/manual-acceptance').glob('*/manifest.json'))
    require(len(candidates) == 1, 'PR21_SINGLE_CLONE_MANIFEST_REQUIRED')
    path = candidates[0]
    m, _ = project_manifest(path)
    require(m['nonce'] != '9ca49b473812'
        and not {m[k] for k in ('https_port','api_port','web_port','pg_port')} & PROTECTED,
        'PR21_PROTECTED_OWNER_REJECTED')
    require(Path(m['root']).resolve() == root, 'PR21_CLONE_ROOT_CHANGED')
    proof = read(path.parent/'clone-origin.json')
    require(proof.get('scope') == 'NON_SENSITIVE_VOLUME_COPY_ONLY'
        and proof.get('source_nonce') == '2002c1fabb87'
        and proof.get('actual_owner_read') is False, 'PR21_SYNTHETIC_PROVENANCE_REQUIRED')
    require(m['db'] == 'datco_test_'+m['nonce'] and m['role'] == 'datco_test_role_'+m['nonce'], 'PR21_CLONE_DATABASE_NAMES_CHANGED')
    require(m['container'] == 'datco-mvp-uat-'+m['nonce']
        and m['volume'] == 'datco-mvp-uat-pg-'+m['nonce'], 'PR21_CLONE_RESOURCE_NAMES_CHANGED')
    fmt = '{"running":{{json .State.Running}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},"ports":{{json .HostConfig.PortBindings}}}'
    r = subprocess.run(['docker','inspect','--format',fmt,m['container']],
        capture_output=True, text=True, encoding='utf-8')
    require(r.returncode == 0, 'PR21_EXISTING_CLONE_REQUIRED')
    d = json.loads(r.stdout)
    require(d['running'] is True and d['labels'].get('datco.manual_acceptance') == m['nonce'],
        'PR21_RUNNING_OWNED_CLONE_REQUIRED')
    require(any(v.get('Name') == m['volume'] and v.get('Destination') == '/var/lib/postgresql/data'
        for v in d['mounts']), 'PR21_CLONE_VOLUME_CHANGED')
    require(d['ports'].get('5432/tcp') == [dict(HostIp='127.0.0.1',HostPort=str(m['pg_port']))],
        'PR21_CLONE_DATABASE_BINDING_CHANGED')
    # Only the proven synthetic configuration is consumed; never emitted.
    raw = read(path)
    from sqlalchemy.engine import make_url
    u = make_url(raw['url'])
    require((u.drivername,u.host,u.port,u.database,u.username) ==
        ('postgresql+psycopg','127.0.0.1',m['pg_port'],m['db'],m['role']), 'PR21_CLONE_URL_CHANGED')
    return m, raw['url'], path.parent


def context(args, expected):
    source = Path(args.source).resolve()
    require(git(source,'rev-parse','HEAD') == expected
        and not git(source,'status','--porcelain'), 'PR21_EXACT_CLEAN_SOURCE_REQUIRED')
    require(not any((source/p).exists() for p in ('.env','apps/api/.env','apps/api/.env.local','apps/web/.env','apps/web/.env.local')), 'PR21_UNEXPECTED_SOURCE_ENV_FILE')
    # Must run in a fresh interpreter; do not splice old/new product modules.
    require(not any(n == 'app' or n.startswith('app.') for n in sys.modules),
        'PR21_MIXED_PRODUCT_IMPORTS_REJECTED')
    sys.path.insert(0, str(source/'apps/api'))
    sys.path.insert(1, str(source/'apps/api/tests'))
    m, url, data = clone_manifest(args.clone)
    for name in list(os.environ):
        if any(x in name.upper() for x in ('OPENAI','ANTHROPIC','GEMINI','AZURE_OPENAI','BIZINFO')):
            os.environ.pop(name)
    os.environ.update(DATABASE_URL=url, WEB_ORIGIN=m['origin'],
        DATCO_TEST_DATABASE=m['db'], DATCO_TEST_DB_ROLE=m['role'])
    from sqlalchemy import create_engine, text, select
    from sqlalchemy.orm import sessionmaker
    from isolation import require_test_database
    engine = create_engine(url)
    require_test_database(engine)
    with engine.connect() as c:
        require(c.execute(text('SELECT version_num FROM alembic_version')).scalars().all() == ['gh02a0012026'],
            'PR21_EXISTING_SCHEMA_REQUIRED_NO_MIGRATION')
        require(c.execute(text("SELECT count(*) FROM background_jobs WHERE state IN ('QUEUED','PROCESSING')")).scalar() == 0,
            'PR21_CLONE_UNFINISHED_JOBS')
    from app.company.application import CompanyApplication
    from app.infrastructure.notice_documents import LocalPrivateFiles
    from app.infrastructure.notice_schema import actors
    from app.notice.domain import Actor
    factory = sessionmaker(engine)
    with factory() as s:
        people = {}
        for role in ('COMPANY_EDITOR','COMPANY_APPROVER','DATCO_OPERATOR','DATCO_ADMIN'):
            rows = s.execute(select(actors.c.id,actors.c.username).where(actors.c.role == role)).mappings().all()
            require(len(rows) == 1, 'PR21_EXISTING_SYNTHETIC_ROLES_REQUIRED')
            people[role] = dict(rows[0])
    who = {role:Actor(p['id'],role) for role,p in people.items()}
    return factory, LocalPrivateFiles(data/'files'), who, people


def fingerprint(factory, cid):
    from sqlalchemy import text
    tables = ('companies','company_sites','company_input_versions','company_site_versions',
        'company_improvements','company_improvement_versions','company_improvement_reviews','company_audit')
    result = {}
    with factory() as s:
        s.execute(text('SET TRANSACTION READ ONLY'))
        for name in tables:
            # Fingerprint the same entire synthetic tables before/after each reader.
            q = "SELECT md5(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY id),'')) FROM "+name+" t"
            result[name] = s.execute(text(q)).scalar()
    return result


def writer(args):
    require(not (args.out/'fixture.json').exists(), 'PR21_EXISTING_PROOF_MUST_BE_PRESERVED')
    f, files, who, people = context(args, TARGET)
    from app.company.application import CompanyApplication
    from app.company.improvement_analysis import ImprovementAnalysis
    from app.company.improvement_worker import process_improvement_one
    from app.company.provider import CompanyProvider
    from registration_sources import number
    raw = read(Path(args.source)/'apps/api/tests/fixtures/requirements_text_only.json')
    editor, operator, admin = (who[k] for k in ('COMPANY_EDITOR','DATCO_OPERATOR','DATCO_ADMIN'))
    profile = dict(name='TEST PR21 recovery compatibility',business_number=number(),industry='manufacturing')
    with f.begin() as s:
        a = CompanyApplication(s, files)
        company = a.register(editor, profile);cid = company['id']
        for role in ('DATCO_OPERATOR','COMPANY_APPROVER'):
            a.grant(admin,cid,people[role]['username'])
        site = a.save_site(editor,cid,dict(name='TEST compatibility site',address='TEST synthetic address'))['site']
        values = dict(raw,title='TEST PR21 text source',original_text='\n'.join(raw.values()),
            problem='',goal='',site_id=site['id'])
        v = a.save_improvement(editor,cid,values)
        a.improvement_action(editor,v['id'],'SUBMIT','TEST synthetic submitted source')
    with f.begin() as s:
        a = CompanyApplication(s,files);analysis = ImprovementAnalysis(a)
        src = analysis.sources(operator,v['id'])
        job = analysis.request(operator,v['id'],str(uuid4()),src['selection_token'],{},
            'TEST bounded recovery compatibility probe',common=[])
    require(process_improvement_one(f,files), 'PR21_SYNTHETIC_WORKER_DID_NOT_RUN')
    with f.begin() as s:
        a = CompanyApplication(s,files);analysis = ImprovementAnalysis(a)
        run = analysis.listing(operator,v['id'])[-1]
        require(run['status'] == 'SUCCEEDED' and run['freshness']['usable'], 'PR21_FRESH_V8_RUN_REQUIRED')
        candidates = [c for c in run['candidates'] if c['category'] == 'STRUCTURE']
        reviews = [analysis.review(operator,c['id'],str(uuid4()),0,'USE_FOR_REQUEST',
            'TEST synthetic literal source checked','') for c in candidates]
        basis = dict(run_id=run['run']['id'],source_version_id=v['id'],review_ids=[r['id'] for r in reviews])
    def content(subject):
        return '\n'.join(c['content'] for c in candidates if c['data']['subject'] == subject)
    formal = dict(values,as_is=content('as_is'),problem=content('problem'),goal=content('goal'),
        to_be=content('to_be'),required_functions=content('required_functions'),
        analysis_basis=basis,evidence_ids=[],fact_version_ids=[],missing='')
    with f.begin() as s:
        a = CompanyApplication(s,files)
        target = a.save_improvement(operator,cid,formal,v['improvement_id'],1)
    with f.begin() as s:
        CompanyApplication(s,files).improvement_action(editor,target['id'],'ACKNOWLEDGE','TEST exact synthetic version checked')
    with f.begin() as s:
        CompanyApplication(s,files).improvement_action(operator,target['id'],'CONFIRM','TEST reviewed literal source and complete fields')
    with f() as s:
        require(CompanyProvider(CompanyApplication(s,files)).read(operator,target['id'])['current_valid'],
            'PR21_NEW_WRITER_CONTEXT_INVALID')
    fixture = dict(company_id=cid,source_version=v['id'],target_version=target['id'],
        run_id=run['run']['id'],basis=basis,profile=profile,
        persisted_data_sha256=sha256(json.dumps(target['data'],sort_keys=True,ensure_ascii=False).encode()).hexdigest())
    write(args.out/'fixture.json',fixture)
    return dict(phase='writer',head=TARGET,synthetic_only=True,normal_business_commands=True,
        schema_migration=False,fixture=fingerprint(f,cid))


def reader(args):
    expected = git(Path(args.source),'rev-parse','HEAD')
    require(expected in (TARGET,PREVIOUS,'9b8d0e0f9eb79aaaa2b973f7e3455df78b8a046e'), 'PR21_UNSUPPORTED_READER')
    f, files, who, _ = context(args, expected)
    from sqlalchemy import text, event
    from app.company.application import CompanyApplication
    from app.company.provider import CompanyProvider
    from app.company.contracts import Improvement
    from app.company.improvement_analysis import ImprovementAnalysis
    from app.infrastructure import company_schema as C
    fixture = read(args.out/'fixture.json')
    def no_dml(conn, cursor, statement, parameters, context, executemany):
        require(not (context.isinsert or context.isupdate or context.isdelete or context.isddl), 'PR21_READER_WRITE_REJECTED')
    event.listen(f.kw['bind'], 'before_cursor_execute', no_dml)
    before = fingerprint(f, fixture['company_id'])
    with f() as s:
        # Product GETs take row locks. Forbid DML and never commit; allow those locks.
        a = CompanyApplication(s,files);operator = who['DATCO_OPERATOR']
        v = a.get(C.improvement_versions,fixture['target_version'])
        parsed = Improvement.model_validate(v['data']).model_dump()
        same = sha256(json.dumps(parsed,sort_keys=True,ensure_ascii=False).encode()).hexdigest() == fixture['persisted_data_sha256']
        context_value = CompanyProvider(a).read(operator,v['id'])
        freshness = ImprovementAnalysis(a).freshness(operator,fixture['run_id'])
    after = fingerprint(f, fixture['company_id'])
    require(before == after, 'PR21_READER_MUTATED_SYNTHETIC_DATABASE')
    return dict(phase='reader',head=expected,typed_data_roundtrip=same,
        current_valid=context_value['current_valid'],analysis_usable=freshness['usable'],
        reasons=freshness['reasons'],database_unchanged=True)


def stale(args):
    f,files,who,_ = context(args,TARGET)
    from app.company.application import CompanyApplication
    fixture=read(args.out/'fixture.json')
    with f.begin() as s:
        a=CompanyApplication(s,files)
        a.save_profile(who['COMPANY_EDITOR'],fixture['company_id'],
            dict(fixture['profile'],overview='TEST normal profile revision after v8 confirmation'),1)
    return dict(phase='stale',head=TARGET,normal_business_command=True)


def assess(measurements):
    """Data and decision compatibility are separate; neither authorizes a stop."""
    fresh, stale = measurements['fresh'], measurements['stale']
    expected = {TARGET, PREVIOUS, '9b8d0e0f9eb79aaaa2b973f7e3455df78b8a046e'}
    require(len(fresh) == len(stale) == 3
        and {r['head'] for r in fresh} == {r['head'] for r in stale} == expected,
        'PR21_COMPLETE_EXACT_READER_PROOF_REQUIRED')
    require(all(type(r.get(k)) is bool for r in fresh+stale
        for k in ('typed_data_roundtrip','current_valid','analysis_usable','database_unchanged')),
        'PR21_TYPED_COMPATIBILITY_PROOF_REQUIRED')
    require(all(r['typed_data_roundtrip'] and r['database_unchanged'] for r in fresh+stale),
        'PR21_RECOVERY_READER_DATA_FAILURE')
    new_fresh = next(r for r in fresh if r['head'] == TARGET)
    new_stale = next(r for r in stale if r['head'] == TARGET)
    require(new_fresh['current_valid'] and new_fresh['analysis_usable']
        and not new_stale['current_valid'] and not new_stale['analysis_usable']
        and 'COMPANY_INPUT_CHANGED' in new_stale.get('reasons',[]),
        'PR21_VALID_NEW_WRITER_PROOF_REQUIRED')
    blocked = [r['head'] for r in stale if r['head'] != TARGET and r['current_valid']]
    return dict(result='BLOCKED' if blocked else 'DATA_COMPATIBILITY_PROBE_ONLY',
        reason='PR21_RECOVERY_STALE_BASIS_ACCEPTED' if blocked else 'TRANSITION_NOT_IMPLEMENTED_OR_APPROVED',
        incompatible_recovery_heads=blocked, typed_data_roundtrip=True,
        database_unchanged_by_readers=True, deployment_ready=False, actual_owner_changed=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('writer','reader','stale','assess'))
    p.add_argument('--source',type=Path)
    p.add_argument('--clone',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    require(a.out.is_dir(), 'PR21_PRIVATE_OUTPUT_REQUIRED')
    require(a.out.resolve().is_relative_to(Path(__file__).resolve().parents[3]/'storage/private/runtime'),
        'PR21_OWNED_PRIVATE_OUTPUT_REQUIRED')
    if a.phase == 'assess':
        value = assess(read(a.out/'measurements.json'))
        print(json.dumps(value,ensure_ascii=True))
        return 2 if value['result'] == 'BLOCKED' else 0
    require(a.source is not None and a.clone is not None, 'PR21_SOURCE_AND_CLONE_REQUIRED')
    value={'writer':writer,'reader':reader,'stale':stale}[a.phase](a)
    print(json.dumps(value,ensure_ascii=True))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        code=str(e) if isinstance(e,RuntimeError) and re.fullmatch('PR21_[A-Z0-9_]+',str(e)) else type(e).__name__
        print(json.dumps(dict(result='BLOCKED',reason=code)))
        sys.exit(1)
