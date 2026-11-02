// Non-sensitive loopback UAT checks. Credentials/cookies stay in memory.
import {readFile,writeFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import {chromium,expect} from '@playwright/test';
async function main(){
const [out,phase]=process.argv.slice(2);
const m=JSON.parse(await readFile(path.join(out,'manifest.json'),'utf8'));
const accounts=JSON.parse(await readFile(path.join(out,'accounts.json'),'utf8'));
const root=path.resolve(import.meta.dirname,'../../..');
if(!m.preparation||m.host!=='127.0.0.1'||m.origin!=='https://127.0.0.1:'+m.https_port||!['initial','resumed'].includes(phase)
 ||!/^[a-f0-9]{12}$/.test(m.nonce)||path.resolve(out)!==path.join(root,'storage/private/runtime/manual-acceptance',m.nonce)
 ||path.resolve(m.root)!==root||m.head!==process.env.DATCO_ACCEPTANCE_HEAD||accounts.nonce!==m.nonce)throw Error('Owned loopback preparation required');
const browser=await chromium.launch();const results=[],privateValues=[accounts.password];
try{
 for(const [role,username] of Object.entries(accounts.accounts)){
  const context=await browser.newContext({baseURL:m.origin,ignoreHTTPSErrors:true});
  let external=0;
  await context.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin!==m.origin){external++;return route.abort();}return route.continue();});
  const page=await context.newPage();
  await page.goto('/login');await page.getByLabel('아이디',{exact:true}).fill(username);await page.getByLabel('비밀번호',{exact:true}).fill(accounts.password);
  await page.getByRole('button',{name:'로그인',exact:true}).click();
  const landing={approver:'/',editor:'/portal/company',operator:'/portal/operator',admin:'/portal/admin'}[role];
  await page.waitForURL(url=>url.pathname===landing);
  await page.reload();
  if((await page.request.get('/api/notice/session')).status()!==200)throw Error('Session persistence failed');
  const cookies=await context.cookies();
  privateValues.push(...cookies.map(c=>c.value));
  if(!cookies.some(c=>c.name==='datco_uat_'+m.nonce&&c.secure&&c.httpOnly)||cookies.some(c=>c.name==='datco_session'))throw Error('Cookie isolation failed');
  for(const name of ['admin','operator','company'])if((await page.request.get('/ui-preview/'+name)).status()!==404)throw Error('Production preview exposed');
  if((await page.request.get('/__test/identity')).status()!==404||external)throw Error('Unexpected surface or external request');
  await page.screenshot({path:path.join(out,'evidence','preflight-'+phase+'-'+role+'.png'),fullPage:true});
  await page.getByRole('button',{name:'로그아웃',exact:true}).click();
  if(role==='operator')await page.getByRole('dialog',{name:'로그아웃 확인'}).getByRole('button',{name:'로그아웃',exact:true}).click();
  await expect(page).toHaveURL(/\/login/);
  if((await page.request.get('/api/notice/session')).status()!==401)throw Error('Logout did not revoke session');
  results.push({role,login:true,refresh:true,namespaced_secure_httponly:true,production_preview_blocked:true,logout:true,external_requests:external});
  await context.close();
 }
 for(const name of (await readdir(out)).filter(name=>name.endsWith('.log'))){
  const log=await readFile(path.join(out,name));
  if(privateValues.some(value=>value&&log.includes(value)))throw Error('Private value in log');
 }
 await writeFile(path.join(out,'evidence','browser-'+phase+'.json'),JSON.stringify({head:m.head,nonce:m.nonce,roles:results,no_private_values_in_logs:true},null,2));
}finally{await browser.close();}
}
main().catch(()=>{process.stderr.write('OWN_BROWSER_PREFLIGHT_FAILED\n');process.exitCode=1;});
