"""Own disposable PostgreSQL container; never normal .env or shared databases."""
import os,sys,secrets,subprocess,json,time
from uuid import uuid4
from pathlib import Path
from sqlalchemy.engine import URL
name='datco-slice2-test-'+uuid4().hex[:12];password=secrets.token_urlsafe(24)
api=Path(__file__).resolve().parents[1];out=api.parents[1]/'storage/private/runtime/slice2';out.mkdir(parents=True,exist_ok=True)
made=False
try:
    subprocess.run(['docker','run','-d','--name',name,'-e','POSTGRES_USER=ci_provisioner','-e','POSTGRES_DB=datco_ci_admin','-e','POSTGRES_PASSWORD='+password,'-p','127.0.0.1::5432','postgres:17'],check=True,stdout=subprocess.DEVNULL);made=True
    port=subprocess.check_output(['docker','port',name,'5432'],text=True).strip().rsplit(':',1)[1]
    for _ in range(60):
        if subprocess.run(['docker','exec',name,'pg_isready','-U','ci_provisioner','-d','datco_ci_admin'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
        time.sleep(.5)
    env=dict(os.environ,DATCO_CI_ADMIN_URL=URL.create('postgresql+psycopg',username='ci_provisioner',password=password,host='127.0.0.1',port=int(port),database='datco_ci_admin').render_as_string(hide_password=False),PYTHONIOENCODING='utf-8')
    if os.name=='nt':env['DATCO_OCR_DOCKER_IMAGE']=env.get('DATCO_OCR_DOCKER_IMAGE','datco-local-ocr:pr14-v1')
    phase=sys.argv[1] if len(sys.argv)>1 else 'integration'
    with (out/(phase+'.log')).open('w',encoding='utf-8') as log:result=subprocess.run([sys.executable,'tests/ci_run.py',phase],cwd=api,env=env,stdout=log,stderr=subprocess.STDOUT)
    print(json.dumps(dict(phase=phase,exit=result.returncode,log=str(out/(phase+'.log')))));sys.exit(result.returncode)
finally:
    if made:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
