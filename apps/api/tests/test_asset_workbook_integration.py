"""Isolated PostgreSQL/HTTP workbook checks with synthetic input only."""
from uuid import uuid4
import pytest
from app.capability.application import CapabilityApplication
from app.infrastructure import capability_schema as S
from app.notice.domain import Actor
from test_notice_slice import context
from test_asset_workbook_import import workbook, ROWS


@pytest.mark.integration
def test_workbook_postgres_api_permissions_replay_and_provenance(context,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app as api_app
    from app.infrastructure.database import get_session
    from app.infrastructure.notice_store import SqlNoticeStore
    import app.api.asset_imports as api
    factory,files,_=context
    with factory.begin() as session:
        row=SqlNoticeStore(session).add('actors',username='TEST_workbook_'+uuid4().hex,role='DATCO_ADMIN',password_hash='TEST not a login credential')
        admin=Actor(row['id'],row['role'])
    def db():
        with factory() as session:yield session
    api_app.dependency_overrides[get_session]=db
    api_app.dependency_overrides[api.actor]=lambda:admin
    monkeypatch.setattr(api,'capability_application',lambda session:CapabilityApplication(session,files))
    try:
        with TestClient(api_app) as client:
            raw=workbook(ROWS)
            assert client.post('/capability/asset-imports/preview',content=raw,headers={'X-Upload-Name':'TEST.xlsx'}).status_code==403
            from app.core.config import get_settings
            from urllib.parse import quote
            headers={'X-Upload-Name':quote('개발 자료.xlsx'),'Origin':get_settings().web_origin}
            response=client.post('/capability/asset-imports/preview',content=raw,headers=headers)
            assert response.status_code==200,response.text
            preview=response.json();body={key:preview[key] for key in ('file_sha256','parser_version','catalog_digest','preview_digest')}
            body.update(selections=[dict(row_key='0:2')],idempotency_key=str(uuid4()))
            result=client.post('/capability/asset-imports/apply',json=body,headers=headers)
            assert result.status_code==200,result.text
            assert result.json()['changed']==1
            stale={**body,'selections':[dict(row_key='0:3')],'idempotency_key':str(uuid4())}
            assert client.post('/capability/asset-imports/apply',json=stale,headers=headers).status_code==409
            assert client.post('/capability/asset-imports/apply',json=body,headers=headers).json()==result.json()
            download=client.get('/capability/asset-imports/'+preview['file_sha256']+'/original')
            assert download.status_code==200 and download.content==raw
            assert quote('개발 자료.xlsx') in download.headers['content-disposition']
            api_app.dependency_overrides[api.actor]=lambda:Actor(admin.id,'DATCO_OPERATOR')
            assert client.post('/capability/asset-imports/preview',content=raw,headers=headers).status_code==403
            assert client.post('/capability/asset-imports/apply',json=body,headers=headers).status_code==403
            assert client.get('/capability/asset-imports/'+preview['file_sha256']+'/original').status_code==403
            api_app.dependency_overrides[api.actor]=lambda:Actor('other-admin','DATCO_ADMIN')
            assert client.get('/capability/asset-imports/'+preview['file_sha256']+'/original').status_code==404
            api_app.dependency_overrides[api.actor]=lambda:admin
            with factory() as session:
                service=CapabilityApplication(session,files)
                assert len(service.rows(S.features))==len(service.rows(S.revisions))==1
                assert service.rows(S.imports)[0]['metadata']['workbook_provenance']['rows'][0]['cells']['name']['cell']=='C2'
    finally:
        api_app.dependency_overrides.clear()


@pytest.mark.integration
def test_workbook_postgres_current_catalog_keeps_untouched_and_explicit_import(context):
    from app.capability.workbook_import import WorkbookImportApplication
    from app.infrastructure.notice_store import SqlNoticeStore
    from test_asset_workbook_import import HEADER
    factory,files,_=context
    with factory.begin() as session:
        record=SqlNoticeStore(session).add('actors',username='TEST_inventory_'+uuid4().hex,role='DATCO_ADMIN',password_hash='TEST not a login credential')
        actor=Actor(record['id'],record['role'])
        service=CapabilityApplication(session,files);app=WorkbookImportApplication(service)
        first=app.preview(actor,'TEST.xlsx',workbook(ROWS))
        args=lambda p,keys,key:dict(file_sha256=p['file_sha256'],parser_version=p['parser_version'],catalog_digest=p['catalog_digest'],preview_digest=p['preview_digest'],selections=[dict(row_key=k) for k in keys],key=key)
        saved=app.apply(actor,**args(first,['0:2'],str(uuid4())))
        original=service.inventory(actor,import_id=saved['import_id'])
        assert original['scope']=='IMPORT' and original['total']==1
        second=app.preview(actor,'TEST.xlsx',workbook(ROWS));app.apply(actor,**args(second,['0:3'],str(uuid4())))
        current=service.inventory(actor);assert current['scope']=='CURRENT_CATALOG' and current['total']==2
        assert service.inventory(actor,import_id=saved['import_id'])['items']==original['items']
        assert service.inventory(actor,query='receipts')['total']==1
        assert len(service.inventory(actor,page=2,limit=1)['items'])==1
        before=service.rows(S.revisions)
        missing=app.preview(actor,'TEST missing.xlsx',workbook([HEADER,ROWS[1]]))
        result=app.apply(actor,**args(missing,['0:2'],str(uuid4())))
        assert result['changed']==0 and service.rows(S.revisions)==before
        assert service.inventory(actor)['total']==2
