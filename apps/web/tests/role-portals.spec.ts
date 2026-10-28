import {test,expect,Page} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
const context=()=>JSON.parse(process.env.DATCO_COMPANY_CONTEXT??'null');
const origin=()=>process.env.DATCO_E2E_BASE_URL!;
const paths={editor:'/portal/company',operator:'/portal/operator',admin:'/portal/admin'};
async function login(page:Page,role:keyof typeof paths){
 const c=context();await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(new RegExp(paths[role]+'$'));await expect(page.getByRole('button',{name:'로그아웃',exact:true}).first()).toBeVisible();
}
for(const role of ['editor','operator','admin'] as const)test('Slice0a real login, refresh, UI and logout '+role,async({page})=>{
 test.setTimeout(120000);const writes:string[]=[];
 page.on('request',r=>{if(r.method()!=='GET'&&!r.url().includes('/api/notice/session'))writes.push(r.method()+' '+new URL(r.url()).pathname);});
 await login(page,role);await page.screenshot({path:test.info().outputPath('landing-'+role+'.png'),fullPage:true});const actor=await(await page.request.get('/api/notice/session')).json();
 expect(actor.role).toBe({editor:'COMPANY_EDITOR',operator:'DATCO_OPERATOR',admin:'DATCO_ADMIN'}[role]);
 const identity=JSON.parse((await page.locator('#portal-identity').textContent())!);expect(identity.name).toBe(context().accounts[role]);expect(identity.id).toBe(actor.id);expect(identity.role).toBe(actor.role);if(role==='editor'){await expect(page.getByText('기업 사용자',{exact:true}).first()).toBeVisible();await expect(page.getByText(context().accounts[role],{exact:true})).toHaveCount(0);}else await expect(page.getByText(context().accounts[role],{exact:true}).first()).toBeVisible();
 expect((await page.context().cookies()).find(c=>c.name==='datco_session')?.httpOnly).toBe(true);
 expect(await page.evaluate(()=>localStorage.length)).toBe(0);
 await page.reload();await expect(page.getByRole('button',{name:'로그아웃',exact:true}).first()).toBeVisible();
 const nav=page.locator('aside nav, aside').first();
 if(role==='editor'){
  for(const name of ['기업정보 등록 시작','기업 · 사업장 관리','재무 · 사업이력','개선요구 등록','첨부자료 관리','보완 요청함','받은 제안서','기업 홈']){
   await page.locator('aside').getByRole('button',{name,exact:true}).click();
   await expect(page.getByRole('heading').first()).toBeVisible();
   await expect(page.getByText('㈜한빛정밀',{exact:false})).toHaveCount(0);
   await expect(page.getByText('공정 운영자료 추가 요청',{exact:true})).toHaveCount(0);
  }
  await page.locator('aside').getByRole('button',{name:'기업 · 사업장 관리',exact:true}).click();
  const allowed=await(await page.request.get('/api/company')).json();if(allowed.length>1){const own=page.getByLabel('소속 기업',{exact:true});if(await own.isVisible())await own.selectOption(allowed[0].id);else await page.getByLabel('업무 기업 선택',{exact:true}).selectOption(allowed[0].id);}await expect(page.getByRole('button',{name:'기업정보 저장',exact:true})).toBeEnabled();
 }else{
  const menu=page.getByRole('navigation',{name:role==='operator'?'운영자 업무 메뉴':'관리자 메뉴'});
  const buttons=await menu.getByRole('button').all();expect(buttons.length).toBe(12);
  for(const button of buttons){await button.click();await expect(page.getByRole('heading').first()).toBeVisible();}
  await expect(page.getByText('예시 화면 보기 · 기업 1개',{exact:true})).toHaveCount(0);
 }
 await expect(nav).toBeVisible();await page.screenshot({path:test.info().outputPath('authenticated-'+role+'.png'),fullPage:true});
 expect(writes).toEqual([]);
 await page.getByRole('button',{name:'로그아웃',exact:true}).first().click();
 if(role==='operator')await page.getByRole('dialog',{name:'로그아웃 확인'}).getByRole('button',{name:'로그아웃',exact:true}).click();
 await expect(page).toHaveURL(/\/login$/);expect((await page.request.get('/api/notice/session')).status()).toBe(401);
 expect((await page.request.get(paths[role],{maxRedirects:0})).status()).toBe(303);
 await page.goBack();await expect(page).not.toHaveURL(new RegExp(paths[role]));await expect(page.getByText(context().accounts[role],{exact:true})).toHaveCount(0);
});
test('Slice0a server rejects unauthenticated, invalid cookies and all other roles',async({page})=>{
 test.setTimeout(120000);
 for(const path of Object.values(paths))expect((await page.request.get(path,{maxRedirects:0})).status()).toBe(303);
 await page.context().addCookies([{name:'datco_session',value:'TEST_INVALID_SESSION',url:origin()}]);
 expect((await page.request.get('/portal/admin',{maxRedirects:0})).status()).toBe(303);await page.context().clearCookies();
 for(const role of ['editor','operator','admin'] as const){
  await login(page,role);
  for(const other of ['editor','operator','admin'] as const)if(other!==role){const r=await page.request.get(paths[other],{maxRedirects:0});expect(r.status()).toBe(403);expect(await r.text()).toBe('Forbidden');}
  if(role==='admin')expect((await page.request.post('/api/capability/compositions',{headers:{Origin:origin()},data:{data:JSON.parse(process.env.DATCO_PROPOSAL_CONTEXT!).composition_data,idempotency_key:crypto.randomUUID()}})).status()).toBe(403);
 }
});
test('Slice0a account switch, multi-tab logout and revoked session clear portal',async({page})=>{
 test.setTimeout(120000);await login(page,'editor');const c=context();
 const second=await page.context().newPage();await login(second,'operator');await page.bringToFront();await expect(page).toHaveURL(/\/login$/);
 await expect(page.locator('aside').getByText(c.accounts.editor,{exact:true})).toHaveCount(0);await second.bringToFront();await expect(second.getByRole('button',{name:'로그아웃',exact:true}).first()).toBeVisible();
 await second.request.post('/api/notice/session/logout',{headers:{Origin:origin()}});await second.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(second).toHaveURL(/\/login$/);
 await page.request.post('/api/notice/session',{headers:{Origin:origin()},data:{username:c.accounts.editor,password:c.password}});
 await page.goto(paths.editor);await expect(page.locator('aside')).toBeVisible();
 const current=(await page.context().cookies()).find(c=>c.name==='datco_session')!.value;
 await page.request.post('/api/notice/session/logout',{headers:{Origin:origin()}});
 const revoked=await page.request.get('/portal/company',{headers:{Cookie:'datco_session='+current},maxRedirects:0});
 expect(revoked.status()).toBe(303);
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page).toHaveURL(/\/login$/);await second.close();
});
test('Slice0a approver keeps approval-only workspace and cannot enter editor portal',async({page})=>{
 const c=JSON.parse(process.env.DATCO_PROPOSAL_CONTEXT??'null');await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(c.approver);await page.getByLabel('비밀번호',{exact:true}).fill(c.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page).toHaveURL(/\/$/);
 for(const path of Object.values(paths))expect((await page.request.get(path,{maxRedirects:0})).status()).toBe(403);
 expect((await page.request.get('/api/company/read-context')).status()).not.toBe(200);
 await page.goto('/proposal');await expect(page.getByRole('button',{name:'현재 세션 확인',exact:true})).toBeVisible();
});

test('Slice0a server-expired session returns to login and removes authenticated UI',async({page})=>{
 await login(page,'editor');const cookie=(await page.context().cookies()).find(c=>c.name==='datco_session')!;
 const python=process.env.DATCO_TEST_PYTHON??path.resolve('../api/.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
 // Only the runner-owned disposable DB can be modified; normal settings DB is rejected independently.
 execFileSync(python,['-c',"from isolation import require_test_database; require_test_database(); import sys; from hashlib import sha256; from datetime import datetime,timezone,timedelta; from app.infrastructure.database import get_session_factory; from app.infrastructure.notice_store import SqlNoticeStore; token=sys.stdin.read();\nwith get_session_factory().begin() as s:\n st=SqlNoticeStore(s); rows=st.rows('sessions',token_hash=sha256(token.encode()).hexdigest()); assert len(rows)==1; st.change('sessions',rows[0]['id'],expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))"],{input:cookie.value,stdio:['pipe','pipe','pipe']});
 expect((await page.request.get('/api/notice/session')).status()).toBe(401);
 expect((await page.request.get('/portal/company',{maxRedirects:0})).status()).toBe(303);
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(page).toHaveURL(/\/login$/);
 await expect(page.getByText(context().accounts.editor,{exact:true})).toHaveCount(0);
});

test('operator returnTo rejects malformed external wrong-account and wrong-role destinations',async({page})=>{
 test.setTimeout(120000);
 const c=JSON.parse(process.env.DATCO_PORTAL_CONTEXT!);
 async function signIn(role:string){
  await page.getByLabel('아이디',{exact:true}).fill(c.accounts[role]);
  await page.getByLabel('비밀번호',{exact:true}).fill(c.password);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/notice/session')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'로그인',exact:true}).click();
  expect((await response).status()).toBe(200);
 }
 await page.goto('/login');await signIn('operator');await expect(page).toHaveURL(/\/portal\/operator$/);
 const actor=await(await page.request.get('/api/notice/session')).json();
 const valid='/portal/operator?screen=improvement&company='+c.a.id+'&version='+c.av1.id+'&context_actor='+actor.id;
 const origin=process.env.DATCO_E2E_BASE_URL!;
 for(const target of ['http://[','https://untrusted.invalid/portal/operator?context_actor='+actor.id,'/portal/admin?context_actor='+actor.id,valid.replace(actor.id,'different-actor')]){
  expect((await page.request.post('/api/notice/session/logout',{headers:{Origin:origin}})).ok()).toBe(true);
  expect((await page.request.get('/api/notice/session')).status()).toBe(401);
  await page.goto('/login?returnTo='+encodeURIComponent(target));await signIn('operator');
  await expect(page).toHaveURL(/\/portal\/operator$/);
 }
 await page.request.post('/api/notice/session/logout',{headers:{Origin:origin}});
 await page.goto('/login?returnTo='+encodeURIComponent(valid));await signIn('blocked_operator');await expect(page).toHaveURL(/\/portal\/operator$/);
 expect((await page.request.get('/api/company/operator/intake/'+c.a.id+'?version_id='+c.av1.id)).status()).toBe(404);
 await page.request.post('/api/notice/session/logout',{headers:{Origin:origin}});
 await page.goto('/login?returnTo='+encodeURIComponent(valid));await signIn('editor');
 await expect(page).toHaveURL(u=>u.pathname==='/portal/company'&&u.searchParams.get('context_actor')!==actor.id);
 const editor=await(await page.request.get('/api/notice/session')).json();expect(editor.role).toBe('COMPANY_EDITOR');
 expect((await page.request.get('/api/company/operator/intake')).status()).toBe(403);
});
