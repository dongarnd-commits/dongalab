"""Loopback-only scenario harness. Credentials go only to the parent test pipe."""
import asyncio,json,socket,sys
from pathlib import Path
import uvicorn
from starlette.responses import Response
from capability_scenario_fixture import scenario_environment
from app.main import app

lock=asyncio.Lock()
@app.middleware('http')
async def serial_fixture_request(request,call_next):
 async with lock:
  response=await call_next(request)
  body=b''.join([chunk async for chunk in response.body_iterator])
  return Response(body,status_code=response.status_code,headers=dict(response.headers))

async def main():
 with scenario_environment(Path(sys.argv[1])) as env:
  from confirmed_comparison_fixture import register
  for case,value,confirmed,reviewed in [('F1','MANUFACTURING',True,True),('F2','MANUFACTURING',False,True),('F3','SERVICE',True,True),('F4','MANUFACTURING',True,False)]:
   key='TEST_IMPROVEMENT_'+case
   env.contexts[key]=dict(env.contexts['TEST_IMPROVEMENT_F'],improvement_version_id=key)
   register(env,key,'B',value,confirmed,reviewed)
  sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error'))
  @app.post('/__test/stop')
  def stop():server.should_exit=True;return {'stopping':True}
  print(json.dumps({'port':port,'admin':env.accounts['admin']['username'],'operator':env.accounts['operator']['username'],
   'password':env.password,'capabilities':env.report['capabilities'],'notices':env.notices}),flush=True)
  await server.serve(sockets=[sock])
 print('ISOLATED_SCENARIO_SCHEMA_ROLLED_BACK',flush=True)
if __name__=='__main__':asyncio.run(main())
