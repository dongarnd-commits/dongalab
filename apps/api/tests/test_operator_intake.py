"""Operator receipts use actual SUBMIT history, including a root with a newer draft."""
import pytest
from test_company_workflow import env, fresh, call, upload
pytestmark=pytest.mark.integration


def test_receipt_scope_drafts_exact_versions_and_file_download(env):
 e=env;c,site,p=fresh(e);cid=c['id'];path='/company/operator/intake'
 data=dict(title='TEST receipt original',original_text='TEST original',as_is='TEST As Is',to_be='TEST To Be',site_id=site['id'])
 v1=call(e,'editor','/company/'+cid+'/improvements',dict(data=data))
 assert not next(i for i in call(e,'operator',path)['companies'] if i['company']['id']==cid)['receipts']
 call(e,'editor',path,status=403);call(e,'admin',path,status=403);call(e,'approver',path,status=403)
 call(e,'editor','/company/improvements/'+v1['id']+'/actions',dict(action='SUBMIT',note='TEST receipt'))
 first=call(e,'operator',path+'/'+cid);assert first['selection']['version_id']==v1['id']
 call(e,'editor','/company/'+cid+'/sites',dict(site_id=site['id'],expected_ordinal=1,data=dict(name='TEST new site',address='TEST new address')))
 v2=call(e,'editor','/company/'+cid+'/improvements',dict(improvement_id=v1['improvement_id'],expected_ordinal=1,data=dict(data,title='TEST private newer draft',to_be='TEST changed draft')))
 received=call(e,'operator',path+'/'+cid+'?version_id='+v1['id'])
 assert received['selection']['version_id']==v1['id'] and received['submitted_site']['data']['name']=='TEST Plant'
 assert 'TEST private newer draft' not in str(received['improvements'])
 assert received['improvements'][0]['versions'][0]['data']['to_be']=='TEST To Be'
 call(e,'operator',path+'/'+cid+'?version_id='+v2['id'],status=404)
 call(e,'other',path+'/'+cid,status=403)
 # Same existing membership guard also blocks another operator's company.
 from registration_sources import number
 foreign=call(e,'editor','/company',dict(name='TEST no operator access',business_number=number()))
 call(e,'operator',path+'/'+foreign['id'],status=404)
 assert foreign['id'] not in [i['company']['id'] for i in call(e,'operator',path)['companies']]



def test_receipt_counts_are_real_roots_and_submissions(env):
 e=env;c,site,p=fresh(e);cid=c['id'];path='/company/operator/intake'
 data=dict(title='TEST repeated submission',original_text='TEST original',site_id=site['id'])
 v=call(e,'editor','/company/'+cid+'/improvements',dict(data=data))
 call(e,'editor','/company/improvements/'+v['id']+'/actions',dict(action='SUBMIT',note='TEST first'))
 v2=call(e,'editor','/company/'+cid+'/improvements',dict(data=data,improvement_id=v['improvement_id'],expected_ordinal=1))
 call(e,'editor','/company/improvements/'+v2['id']+'/actions',dict(action='SUBMIT',note='TEST second'))
 overview=call(e,'operator',path);rows=next(i['receipts'] for i in overview['companies'] if i['company']['id']==cid)
 assert len(rows)==2 and len({r['root_id'] for r in rows})==1
 assert call(e,'operator',path+'/'+cid)['selection']['version_id']==v2['id']
 assert overview['submitted_count']==sum(len(i['receipts']) for i in overview['companies'])
 assert overview['submitted_root_count']==sum(len({r['root_id'] for r in i['receipts']}) for i in overview['companies'])
 f,raw=upload(e,cid,site['id']);assert e['clients']['operator'].get('/company/files/'+f['id']+'/download').content==raw
 assert e['clients']['other'].get('/company/files/'+f['id']+'/download').status_code==404
