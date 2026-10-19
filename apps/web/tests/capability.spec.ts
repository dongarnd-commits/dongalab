import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { request as httpRequest } from "node:http";
import { mkdirSync, appendFileSync } from "node:fs";
import { resolve } from "node:path";

test("real 649 inventory, Admin publishing, Operator composition versions and confirmed Notice matching", async ({page,request}) => {
 test.setTimeout(180000);
 const runtime=resolve("../../storage/private/runtime/capability-browser"); mkdirSync(runtime,{recursive:true});
 const child=spawn(resolve("../api/.venv/Scripts/python.exe"),["tests/capability_browser_server.py",runtime],{cwd:resolve("../api"),env:{...process.env,PYTHONPATH:".",PYTHONIOENCODING:"utf-8"},windowsHide:true});
 let buffer="",rolledBack=false;
 child.stderr.on("data",chunk=>appendFileSync(resolve(runtime,"launch-error.log"),String(chunk)));
 child.stdout.on("data",chunk=>{if(String(chunk).includes("ISOLATED_CAPABILITY_SCHEMA_ROLLED_BACK"))rolledBack=true;});
 const ready=new Promise<{port:number;admin:string;operator:string;company:string;password:string;notice_id:string;requirement_version_id:string}>((done,reject)=>{
  child.stdout.on("data",chunk=>{buffer+=String(chunk);const line=buffer.split(/\r?\n/).find(l=>l.startsWith("{"));if(line){try{done(JSON.parse(line));}catch{}}});
  child.on("error",reject);child.on("exit",code=>{if(!buffer.includes('"port"'))reject(new Error("Isolated Capability API could not start: "+code));});
 });
 let base="";
 try{
  const account=await ready;base="http://127.0.0.1:"+account.port;
  await page.route("**/api/capability**",async route=>{
   const req=route.request();const u=new URL(req.url());const response=await request.fetch(base+u.pathname.replace("/api/capability","/capability")+u.search,{method:req.method(),data:req.postData()??undefined,headers:{"Content-Type":"application/json","Origin":process.env.WEB_ORIGIN!,"Cookie":req.headers()["cookie"]??""}});
   await route.fulfill({status:response.status(),headers:response.headers(),body:await response.body()});
  });
  await page.route("**/api/notice/session",async route=>{
   const req=route.request();const response=await request.fetch(base+"/notice/session",{method:req.method(),data:req.postData()??undefined,headers:{"Content-Type":"application/json","Origin":process.env.WEB_ORIGIN!,"Cookie":req.headers()["cookie"]??""}});
   await route.fulfill({status:response.status(),headers:response.headers(),body:await response.body()});
  });
  await page.route("**/api/workspace",async route=>{const req=route.request();const response=await request.fetch(base+"/workspace",{headers:{Cookie:req.headers()["cookie"]??""}});await route.fulfill({status:response.status(),headers:response.headers(),body:await response.body()});});
  await page.goto('/capability');
  await page.getByLabel('아이디',{exact:true}).fill(account.admin);await page.getByLabel('비밀번호',{exact:true}).fill(account.password);await page.getByRole('button',{name:'로그인',exact:true}).click();
  await page.getByRole('button',{name:'검색·조회',exact:true}).click();await expect(page.getByText('검색 결과 649건',{exact:false})).toBeVisible();
  await page.getByLabel('기능·서비스 검색').fill('재고현황');await page.getByRole('button',{name:'Capability Catalog',exact:true}).click();await page.getByRole('button',{name:'검색·조회',exact:true}).click();
  await page.getByLabel('재고현황 연결',{exact:true}).check();await page.getByLabel('Capability명',{exact:true}).fill('TEST 재고 정보 서비스');await page.getByLabel('해결 대상 문제',{exact:true}).fill('재고 관리');await page.getByLabel('제공범위',{exact:true}).fill('재고현황 조회');await page.getByLabel('기능 원천 검토 근거',{exact:true}).fill('TEST 실제 원천 설명 확인');await page.getByRole('button',{name:'작성본 저장',exact:true}).click();
  await expect(page.getByText('작성본이 저장됐습니다.',{exact:true})).toBeVisible();await page.getByRole('button',{name:'검토 후 버전 발행',exact:true}).click();await expect(page.getByText('불변 버전이 발행됐습니다.',{exact:true})).toBeVisible();
  await page.screenshot({path:resolve('../../storage/private/runtime/capability-browser/catalog.png'),fullPage:true});
  await page.reload();await page.getByRole('button',{name:'검색·조회',exact:true}).click();await expect(page.getByRole('button',{name:'TEST 재고 정보 서비스',exact:true})).toBeVisible();
  await page.getByText('계정 로그인',{exact:true}).click();await page.getByLabel('아이디',{exact:true}).fill(account.operator);await page.getByLabel('비밀번호',{exact:true}).fill(account.password);await page.getByRole('button',{name:'로그인',exact:true}).click();await expect(page.getByText('DATCO_OPERATOR',{exact:true})).toBeVisible();await page.getByRole('button',{name:'서비스 조합',exact:true}).click();
  await openLookup(page,'ImprovementVersion');await page.getByLabel('ImprovementVersion',{exact:true}).fill('TEST_IMPROVEMENT_A');await page.getByRole('button',{name:'권한 있는 요구사항 조회',exact:true}).click();await expect(page.getByText('재고가 맞지 않고 입출고를 수기로 관리합니다.',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'조합에 추가',exact:true}).click();await page.getByLabel('조합명',{exact:true}).fill('TEST 재고 개선 조합');await page.getByRole('button',{name:'해결범위 항목 추가',exact:true}).click();await page.getByLabel('기능 해결 역할',{exact:true}).fill('재고 정보 조회');await page.getByLabel('해결 가능한 범위',{exact:true}).fill('재고현황 관리');await page.getByLabel('부분·미해결 범위',{exact:true}).fill('자동 불량 원인분석 제외');
  await page.getByRole('button',{name:'서비스 조합 저장',exact:true}).click();await expect(page.getByText('서비스 조합 버전이 저장됐습니다.',{exact:true})).toBeVisible();
  const composition=await page.getByLabel('저장된 조합 ID',{exact:true}).inputValue();expect(composition).toBeTruthy();
  await page.reload();await openLookup(page,'저장된 조합 ID');await page.getByLabel('저장된 조합 ID',{exact:true}).fill(composition);await page.getByRole('button',{name:'조합 재조회',exact:true}).click();await expect(page.getByLabel('조합명',{exact:true})).toHaveValue('TEST 재고 개선 조합');await page.getByLabel('조합명',{exact:true}).fill('TEST 재고 개선 조합 v2');await page.getByRole('button',{name:'새 버전 저장',exact:true}).click();await expect(page.getByText('Version 2',{exact:false})).toBeVisible();
  await page.screenshot({path:resolve('../../storage/private/runtime/capability-browser/composer.png'),fullPage:true});
  await page.getByRole('button',{name:'정부지원사업 매칭',exact:true}).click();await openLookup(page,'Notice ID');await page.getByLabel('Notice ID',{exact:true}).fill(account.notice_id);await openLookup(page,'확정 RequirementVersion');await page.getByLabel('확정 RequirementVersion',{exact:true}).fill(account.requirement_version_id);await page.getByRole('button',{name:'확정 근거로 매칭 후보 준비',exact:true}).click();await expect(page.getByRole('heading',{name:'추가 확인 필요',exact:true})).toBeVisible();
  await page.getByLabel('검토 사유',{exact:true}).fill('TEST 공급자격 추가정보 필요');await page.getByRole('button',{name:'검토 기록',exact:true}).click();await expect(page.getByText('검토 이력이 저장됐습니다.',{exact:true})).toBeVisible();
  await page.screenshot({path:resolve('../../storage/private/runtime/capability-browser/matching.png'),fullPage:true});
  await page.getByText('계정 로그인',{exact:true}).click();await page.getByLabel('아이디',{exact:true}).fill(account.company);await page.getByLabel('비밀번호',{exact:true}).fill(account.password);await page.getByRole('button',{name:'로그인',exact:true}).click();
  await expect(page.getByRole('heading',{name:'접근 권한 없음',exact:true})).toBeVisible();await expect(page.getByText('현재 역할에 허용되지 않은 업무입니다.',{exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'3자 매칭 검토',exact:true})).toHaveCount(0);
  const cookies=await page.context().cookies();const session=cookies.find(c=>c.name==='datco_session');expect(session).toBeTruthy();
  const denied=await request.get(base+'/capability/features',{headers:{Cookie:'datco_session='+session!.value}});expect(denied.status()).toBe(403);

 }finally{
  await page.unrouteAll({behavior:"wait"});
  if(base){
   try{await new Promise<void>((done,reject)=>{const stop=httpRequest(base+'/__test/stop',{method:'POST'},r=>{r.resume();r.on('end',done);});stop.on('error',reject);stop.setTimeout(5000,()=>stop.destroy(new Error('Isolated stop timeout')));stop.end();});}
   catch{child.kill();}
   await expect.poll(()=>rolledBack,{timeout:20000}).toBeTruthy();
  }
  else child.kill();
 }
});

async function openLookup(page:import("@playwright/test").Page,label:string){const summary=page.getByText('고급 식별자: '+label,{exact:true});await expect(summary).toBeVisible();if(!await summary.locator('..').evaluate(el=>(el as HTMLDetailsElement).open))await summary.click();}
