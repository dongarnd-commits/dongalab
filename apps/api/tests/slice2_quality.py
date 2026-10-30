"""Local quality checks in a unique Next output directory; no service reuse."""
import json,os,subprocess,sys
from pathlib import Path
from uuid import uuid4
root=Path(__file__).resolve().parents[3];web=root/'apps/web';nonce=uuid4().hex[:12]
directory='.next/datco-e2e-'+nonce;config=web/('.next/datco-config-'+nonce)/'tsconfig.json';config.parent.mkdir(parents=True,exist_ok=True)
config.write_text(json.dumps(dict(extends='../../tsconfig.json',compilerOptions={'paths':{'@/*':[str(web/'src/*')]}},include=[str(web/'next-env.d.ts'),str(web/'src/**/*.ts'),str(web/'src/**/*.tsx'),str(web/'tests/**/*.ts'),str(web/directory/'types/**/*.ts')],exclude=[str(web/'node_modules')])),encoding='utf-8')
env=dict(os.environ,DATCO_TEST_DIST_DIR=directory,NEXT_TELEMETRY_DISABLED='1')
out=root/'storage/private/runtime/slice2';out.mkdir(parents=True,exist_ok=True)
commands=[('lint',['npm','run','lint']),('typecheck',['npx','tsc','--noEmit']),('build',['npm','run','build','--','--webpack'])]
for label,command in commands:
    if os.name=='nt':command=['cmd.exe','/c',command[0]+'.cmd',*command[1:]]
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT)
    print(json.dumps(dict(step=label,exit=r.returncode,log=str(out/(label+'.log')))),flush=True)
    if r.returncode:sys.exit(r.returncode)
