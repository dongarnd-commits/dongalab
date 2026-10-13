"""Browser test server: rollback-only PostgreSQL schema, copies of stored public input.
No route/tool is added to the product API. No public-schema analysis or confirmation.
"""
import asyncio
import json
import secrets
import sys
from pathlib import Path
from uuid import uuid4
import uvicorn
from starlette.responses import Response
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database import Base,get_engine,get_session
from app.infrastructure.notice_store import SqlNoticeStore
from app.infrastructure.notice_documents import LocalPrivateFiles
from app.infrastructure.local_auth import hash_password
from app.notice.application import NoticeApplication
from app.worker import process_one
from app.main import app
import app.api.notice as notice_api
from test_notice_korean import stored_inputs


def main():
    inputs=stored_inputs()
    connection=get_engine().connect().execution_options(schema_translate_map={None:'test_ko_browser_'+uuid4().hex})
    transaction=connection.begin()
    schema_name=connection.get_execution_options()['schema_translate_map'][None]
    connection.exec_driver_sql('CREATE SCHEMA '+schema_name)
    Base.metadata.create_all(connection)
    factory=sessionmaker(bind=connection,join_transaction_mode='create_savepoint')
    files=LocalPrivateFiles(Path(sys.argv[1])/'sources')
    username='ko-browser-'+uuid4().hex; password=secrets.token_urlsafe(24)
    with factory.begin() as s:
        st=SqlNoticeStore(s)
        st.add('actors',username=username,role='DATCO_OPERATOR',password_hash=hash_password(password))
        for original,version,source_inputs in inputs:
            n=st.add('notices',external_key='ISOLATED_'+uuid4().hex,title='격리 검증 사본 / '+original['title'],current_ordinal=1)
            v=st.add('versions',notice_id=n['id'],ordinal=1,mode='LIVE',metadata=version['metadata'])
            for source,data in source_inputs:
                key,digest=files.put(data) if data else (None,None)
                st.add('sources',version_id=v['id'],name=source['name'],media_type=source['media_type'],provenance='ISOLATED COPY OF STORED PUBLIC LIVE DOCUMENT; TEST ONLY',storage_key=key,digest=digest)
    def test_session():
        with factory() as session:
            yield session
    app.dependency_overrides[get_session]=test_session
    notice_api.application=lambda session: NoticeApplication(SqlNoticeStore(session),files)
    config=uvicorn.Config(app,host='127.0.0.1',port=0,log_level='error')
    server=uvicorn.Server(config)
    import socket
    sock=socket.socket(); sock.bind(('127.0.0.1',0))
    port=sock.getsockname()[1]
    lock=asyncio.Lock()
    @app.middleware('http')
    async def serialized_requests(request,call_next):
        async with lock:
            response=await call_next(request)
            # Finish dependency/session cleanup before another request uses the shared connection.
            body=b''.join([chunk async for chunk in response.body_iterator])
            if request.url.path=='/notice/analysis' and response.status_code==200:
                # Actual same-code Job/Attempt claim -> extractor -> provider -> persistence.
                await asyncio.to_thread(process_one,factory,files)
            return Response(body,status_code=response.status_code,headers=dict(response.headers))
    @app.post('/__test/stop')
    def stop():
        server.should_exit=True
        return {'stopping':True}
    print(json.dumps({'port':port,'username':username,'password':password}),flush=True)
    try:
        server.run(sockets=[sock])
    finally:
        transaction.rollback()
        connection.close()
        sock.close()
        print('ISOLATED_SCHEMA_ROLLED_BACK',flush=True)

if __name__=='__main__':
    main()
