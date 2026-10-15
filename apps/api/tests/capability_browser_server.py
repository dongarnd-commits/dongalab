"""Private rollback-only browser harness; never registers routes in normal runtime."""
import asyncio,json,secrets,socket,sys
from pathlib import Path
from uuid import uuid4
import uvicorn
from sqlalchemy.orm import sessionmaker
from starlette.responses import Response
from app.infrastructure.database import Base,get_engine,get_session
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.local_auth import hash_password
from app.capability.application import CapabilityApplication
from app.notice.domain import Denied
from app.core.config import ROOT
from app.main import app
import app.api.capability as api
import app.api.notice as notice_api
from app.demo import load_input
from app.notice.application import NoticeApplication
from app.notice.domain import Actor
from app.worker import process_one

async def main():
    from isolation import require_test_database
    require_test_database()
    schema='test_cap_browser_'+uuid4().hex
    connection=get_engine().connect().execution_options(schema_translate_map={None:schema})
    outer=connection.begin(); connection.exec_driver_sql('CREATE SCHEMA '+schema); Base.metadata.create_all(connection)
    factory=sessionmaker(bind=connection,join_transaction_mode='create_savepoint')
    from lineage_test_support import install_test_lineage
    install_test_lineage(connection,schema,factory)
    files=LocalPrivateFiles(Path(sys.argv[1])/'sources'); password=secrets.token_urlsafe(24)
    try:
        with factory.begin() as session:
            store=SqlNoticeStore(session)
            admin=store.add('actors',username='test-admin-'+uuid4().hex,role='DATCO_ADMIN',password_hash=hash_password(password))
            company=store.add('actors',username='test-company-'+uuid4().hex,role='COMPANY_EDITOR',password_hash=hash_password(password))
            operator=store.add('actors',username='test-operator-'+uuid4().hex,role='DATCO_OPERATOR',password_hash=hash_password(password))
            CapabilityApplication(session,files).import_inventory((ROOT/'_local_inputs/dmp_features_649.json').read_bytes(),Actor(admin['id'],admin['role']))
            notice=load_input(store,files,'normal',external_key='TEST_BROWSER_NOTICE')
            nv=store.rows('versions',notice_id=notice['id'])[0]
            NoticeApplication(store,files).request(Actor(operator['id'],operator['role']),nv['id'],'browser-notice')
        process_one(factory,files)
        with factory.begin() as session:
            store=SqlNoticeStore(session); na=NoticeApplication(store,files); who=Actor(operator['id'],operator['role'])
            run=store.rows('runs',version_id=nv['id'])[0]
            candidate=next(c for c in store.rows('candidates',run_id=run['id']) if c['kind']=='ELIGIBILITY_REQUIREMENT')
            rv=na.confirm(who,nv['id'],candidate['id'],True,'TEST source review','TEST reviewed scope','')
        class Inputs:
            def read(self,actor,version_id):
                if actor.id!=operator['id'] or version_id!='TEST_IMPROVEMENT_A': raise Denied('OBJECT_NOT_FOUND',404)
                return {'company_id':'TEST_COMPANY_A','site_id':'TEST_SITE_A','improvement_version_id':version_id,
                    'original_text':'재고가 맞지 않고 입출고를 수기로 관리합니다.','confirmed':True,'current_valid':True,
                    'fact_version_ids':[],'evidence_refs':[],'demo':True}
        def sessions():
            with factory() as session: yield session
        app.dependency_overrides[get_session]=sessions
        api.application=lambda session:CapabilityApplication(session,files,Inputs())
        notice_api.application=lambda session:NoticeApplication(SqlNoticeStore(session),files)
        lock=asyncio.Lock()
        @app.middleware('http')
        async def serialized(request,call_next):
            async with lock:
                response=await call_next(request)
                body=b''.join([chunk async for chunk in response.body_iterator])
                return Response(body,status_code=response.status_code,headers=dict(response.headers))
        sock=socket.socket(); sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'))
        @app.post('/__test/stop')
        def stop(): server.should_exit=True; return {'stopping':True}
        print(json.dumps({'port':port,'admin':admin['username'],'operator':operator['username'],'company':company['username'],'password':password,
            'notice_id':notice['id'],'requirement_version_id':rv['id']}),flush=True)
        await server.serve(sockets=[sock])
    finally:
        app.dependency_overrides.clear(); outer.rollback(); connection.close()
        print('ISOLATED_CAPABILITY_SCHEMA_ROLLED_BACK',flush=True)
if __name__=='__main__': asyncio.run(main())
