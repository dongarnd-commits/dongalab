import { test as base, expect, type Page } from "@playwright/test";
import { spawn } from "node:child_process";
import { request as httpRequest } from "node:http";
import { mkdirSync, writeFileSync, appendFileSync } from "node:fs";
import { resolve } from "node:path";

type Account={port:number;admin:string;operator:string;password:string;capabilities:Record<string,{capability_id:string;version_id:string;ordinal:number}>;notices:Record<string,{notice_id:string;requirement_version_id:string}>};
type Scenario={account:Account;base:string;runtime:string};
const test=base.extend<{scenario:Scenario}>({
 scenario:async({page,request},provide,testInfo)=>{
  const runtime=resolve("../../storage/private/runtime/capability-scenarios/browser",String(testInfo.line));mkdirSync(runtime,{recursive:true});
  const child=spawn(resolve("../api/.venv/Scripts/python.exe"),["tests/capability_scenario_browser_server.py",runtime],{cwd:resolve("../api"),env:{...process.env,PYTHONPATH:".",PYTHONIOENCODING:"utf-8"},windowsHide:true});
  let buffer="",rolledBack=false,origin="";
  child.stderr.on("data",chunk=>appendFileSync(resolve(runtime,"launch-error.log"),String(chunk)));
  child.stdout.on("data",d=>{buffer+=String(d);if(String(d).includes("ISOLATED_SCENARIO_SCHEMA_ROLLED_BACK"))rolledBack=true;});
  const exited=new Promise<void>(done=>child.once("exit",()=>done()));
  const ready=new Promise<Account>((done,reject)=>{child.stdout.on("data",()=>{const line=buffer.split(/\r?\n/).find(l=>l.startsWith("{"));if(line)done(JSON.parse(line));});child.on("error",reject);child.on("exit",code=>{if(!buffer.includes('"port"'))reject(new Error("Scenario API startup failed: "+code));});});
  try{
   const account=await ready;origin="http://127.0.0.1:"+account.port;
   await expect.poll(async()=>{try{return(await request.get(origin+"/health")).status();}catch{return 0;}},{timeout:15000}).toBe(200);
   for(const pattern of ["**/api/capability**","**/api/notice/session","**/api/workspace"]){
    await page.route(pattern,async route=>{const req=route.request(),u=new URL(req.url());const response=await request.fetch(origin+u.pathname.replace("/api/","/")+u.search,{method:req.method(),data:req.postData()??undefined,headers:{"Content-Type":"application/json",Origin:process.env.WEB_ORIGIN!,Cookie:req.headers()["cookie"]??""}});await route.fulfill({status:response.status(),headers:response.headers(),body:await response.body()});});
   }
   await provide({account,base:origin,runtime});
  }finally{
   await page.unrouteAll({behavior:"wait"});
   if(origin){
    try{await new Promise<void>((done,reject)=>{const stop=httpRequest(origin+"/__test/stop",{method:"POST"},r=>{r.resume();r.on("end",done);});stop.on("error",reject);stop.setTimeout(5000,()=>stop.destroy(new Error("Stop timeout")));stop.end();});await exited;}
    catch{child.kill();}
    await expect.poll(()=>rolledBack,{timeout:20000}).toBeTruthy();
   }else child.kill();
  }
 }
});
async function login(page:Page,scenario:Scenario,role:"admin"|"operator"){
 await page.goto("/capability?view=catalog");
 const form=page.locator("details").filter({has:page.getByText("계정 로그인",{exact:true})}).first();
 if(!(await form.evaluate(e=>(e as HTMLDetailsElement).open)))await page.getByText("계정 로그인",{exact:true}).click();
 await page.getByLabel("아이디",{exact:true}).fill(scenario.account[role]);await page.getByLabel("비밀번호",{exact:true}).fill(scenario.account.password);await page.getByRole("button",{name:"로그인",exact:true}).click();await expect(page.getByText(role==="admin"?"DATCO_ADMIN":"DATCO_OPERATOR",{exact:true})).toBeVisible();
}
function evidence(scenario:Scenario,name:string,data:unknown){writeFileSync(resolve(scenario.runtime,name+".json"),JSON.stringify(data,null,2));}

test("SC-A to D real browser persistence and Notice review; business accuracy is evaluated separately",async({page,scenario})=>{
 test.setTimeout(240000);await login(page,scenario,"operator");
 for(const [id,cap] of [["A","A"],["B","B"],["C","C"],["D","B"]]){
  await page.goto("/capability?view=composer");await expect(page.getByText("DATCO_OPERATOR",{exact:true})).toBeVisible();
  await openLookup(page,'ImprovementVersion');await page.getByLabel("ImprovementVersion",{exact:true}).fill("TEST_IMPROVEMENT_"+id);await page.getByRole("button",{name:"권한 있는 요구사항 조회",exact:true}).click();
  await page.getByRole("group",{name:"TEST CAP-"+cap,exact:true}).getByRole("button",{name:"조합에 추가",exact:true}).click();
  await page.getByLabel("조합명",{exact:true}).fill("TEST browser SC-"+id);await page.getByRole("button",{name:"해결범위 항목 추가",exact:true}).click();
  await page.getByLabel("기능 해결 역할",{exact:true}).fill("TEST 실제 원천 기능의 등록·조회 역할");
  await page.getByLabel("해결 가능한 범위",{exact:true}).fill(id==="D"?"품질검사 및 불량 발생 현황 기록":"TEST 선택한 원천 기능의 제공범위");
  await page.getByLabel("부분·미해결 범위",{exact:true}).fill(id==="D"?"모든 불량의 AI 자동 원인 규명은 원천에서 확인되지 않음":"기업 도입조건 및 사업자격 추가 확인 필요");
  await page.getByRole("button",{name:"서비스 조합 저장",exact:true}).click();await expect(page.getByText("서비스 조합 버전이 저장됐습니다.",{exact:true})).toBeVisible();
  const compositionId=await page.getByLabel("저장된 조합 ID",{exact:true}).inputValue();
  await page.reload();await expect(page.getByText("DATCO_OPERATOR",{exact:true})).toBeVisible();await openLookup(page,'저장된 조합 ID');await page.getByLabel("저장된 조합 ID",{exact:true}).fill(compositionId);await page.getByRole("button",{name:"조합 재조회",exact:true}).click();await expect(page.getByLabel("조합명",{exact:true})).toHaveValue("TEST browser SC-"+id);
  await page.screenshot({path:resolve(scenario.runtime,"isolated-SC-"+id+"-composer.png"),fullPage:true});
  await page.getByRole("button",{name:"정부지원사업 매칭",exact:true}).click();const n=scenario.account.notices.A;
  await openLookup(page,'Notice ID');await page.getByLabel("Notice ID",{exact:true}).fill(n.notice_id);await openLookup(page,'확정 RequirementVersion');await page.getByLabel("확정 RequirementVersion",{exact:true}).fill(n.requirement_version_id);
  await page.getByRole("button",{name:"확정 근거로 매칭 후보 준비",exact:true}).click();await expect(page.getByRole("heading",{name:"추가 확인 필요",exact:true})).toBeVisible();
  await page.getByLabel("담당자 검토").selectOption("HOLD");await page.getByLabel("검토 사유",{exact:true}).fill("TEST 서비스 범위와 사업 적격성을 구분하여 보류");await page.getByRole("button",{name:"검토 기록",exact:true}).click();await expect(page.getByText("검토 이력이 저장됐습니다.",{exact:true})).toBeVisible();
  evidence(scenario,"SC-"+id,{mode:"ISOLATED_TEST",compositionId,compositionVersion:await page.getByLabel("CompositionVersion",{exact:true}).inputValue(),capabilityVersion:scenario.account.capabilities[cap].version_id,notice:n,candidateId:await page.getByLabel("저장된 후보 ID",{exact:true}).inputValue(),fit:"NEED_MORE_INFO",review:"HOLD",refresh:true,businessAccuracy:"NOT_IMPLEMENTED"});
  await page.screenshot({path:resolve(scenario.runtime,"isolated-SC-"+id+"-matching.png"),fullPage:true});
 }
});

test("R-01 edited but unsaved scope must not report successful publication of old content",async({page,request,scenario})=>{
 test.setTimeout(120000);await login(page,scenario,"admin");await page.getByRole("button",{name:"검색·조회",exact:true}).click();await page.getByRole("button",{name:"TEST CAP-A",exact:true}).click();
 await expect(page.getByLabel("제공범위",{exact:true})).not.toHaveValue("");
 const original=await page.getByLabel("제공범위",{exact:true}).inputValue(),edited="TEST UNSAVED scope requiring explicit save";
 let publicationRequests=0;page.on("request",r=>{if(r.url().endsWith("/publish"))publicationRequests++;});
 await page.getByLabel("제공범위",{exact:true}).fill(edited);
 const publish=page.getByRole("button",{name:"검토 후 버전 발행",exact:true});
 await expect(publish).toBeDisabled();await expect(page.getByText("저장되지 않은 변경이 있습니다. 작성본을 먼저 저장하세요.",{exact:true})).toBeVisible();expect(publicationRequests).toBe(0);
 const cookie=(await page.context().cookies()).map(c=>c.name+"="+c.value).join("; ");
 const before=await(await request.get(scenario.base+"/capability/catalog/"+scenario.account.capabilities.A.capability_id,{headers:{Cookie:cookie}})).json();
 expect(before.versions.at(-1).data.scope).toBe(original);expect(before.versions).toHaveLength(1);
 await page.getByRole("button",{name:"작성본 저장",exact:true}).click();await expect(page.getByText("작성본이 저장됐습니다.",{exact:true})).toBeVisible();
 await expect(publish).toBeEnabled();await publish.click();await expect(page.getByText("불변 버전이 발행됐습니다.",{exact:true})).toBeVisible();
 const response=await request.get(scenario.base+"/capability/catalog/"+scenario.account.capabilities.A.capability_id,{headers:{Cookie:cookie}});const result=await response.json();
 evidence(scenario,"R-01",{original,edited,persisted:result.versions.at(-1).data.scope,versionCount:result.versions.length,unsavedPublishBlocked:true,http:response.status()});await page.screenshot({path:resolve(scenario.runtime,"isolated-R-01.png"),fullPage:true});
 expect(result.versions.at(-1).data.scope).toBe(edited);expect(result.versions).toHaveLength(2);expect(result.versions[0].data.scope).toBe(original);

});

test("R-02 deselecting a Capability must not leave an invalid Coverage reference",async({page,scenario})=>{
 test.setTimeout(120000);await login(page,scenario,"operator");await page.getByRole("button",{name:"서비스 조합",exact:true}).click();await openLookup(page,'ImprovementVersion');await page.getByLabel("ImprovementVersion",{exact:true}).fill("TEST_IMPROVEMENT_A");await page.getByRole("button",{name:"권한 있는 요구사항 조회",exact:true}).click();
 await page.getByRole("group",{name:"TEST CAP-A",exact:true}).getByRole("button",{name:"조합에 추가",exact:true}).click();
 await page.getByLabel("조합명",{exact:true}).fill("TEST deselection scenario");await page.getByRole("button",{name:"해결범위 항목 추가",exact:true}).click();await page.getByLabel("기능 해결 역할",{exact:true}).fill("TEST 기능 역할");
 // Preserve a second Capability's independently written Coverage while removing A.
 await page.getByLabel("기능·서비스 검색").fill("생산");await page.getByRole("button",{name:"후보 검색",exact:true}).click();await page.getByRole("group",{name:"TEST CAP-B",exact:true}).getByRole("button",{name:"조합에 추가",exact:true}).click();
 await page.getByRole("button",{name:"해결범위 항목 추가",exact:true}).click();await page.getByLabel("적용 Capability").nth(1).selectOption(scenario.account.capabilities.B.version_id);
 await page.getByLabel("기능 해결 역할",{exact:true}).nth(1).fill("TEST preserve B role");await page.getByLabel("요구사항").nth(1).fill("TEST 생산 현황 확인");
 await page.locator(".feature-choice input").first().uncheck();
 await page.getByLabel("기능·서비스 검색").fill("재고");await page.getByRole("button",{name:"후보 검색",exact:true}).click();await page.getByRole("group",{name:"TEST CAP-A",exact:true}).getByRole("button",{name:"선택 해제",exact:true}).click();
 await expect(page.getByText("선택을 해제하고 해당 Capability의 해결범위 1개를 작성본에서 제거했습니다. 다른 해결범위와 저장된 버전은 유지됩니다.",{exact:true})).toBeVisible();
 await expect(page.getByLabel("기능 해결 역할",{exact:true})).toHaveCount(1);await expect(page.getByLabel("기능 해결 역할",{exact:true})).toHaveValue("TEST preserve B role");
 await page.getByRole("button",{name:"서비스 조합 저장",exact:true}).click();await expect(page.getByText("서비스 조합 버전이 저장됐습니다.",{exact:true})).toBeVisible();
 const id=await page.getByLabel("저장된 조합 ID",{exact:true}).inputValue();await page.reload();await openLookup(page,'저장된 조합 ID');await page.getByLabel("저장된 조합 ID",{exact:true}).fill(id);await page.getByRole("button",{name:"조합 재조회",exact:true}).click();await expect(page.getByLabel("기능 해결 역할",{exact:true})).toHaveValue("TEST preserve B role");
 evidence(scenario,"R-02",{compositionId:id,removedA:true,preservedB:true,refresh:true});await page.screenshot({path:resolve(scenario.runtime,"isolated-R-02.png"),fullPage:true});
 await expect(page.locator("p.catalog-error[role=alert]")).toHaveCount(0);

});

for (const [caseId, heading, fit] of [["F1","확인된 조건 충돌","MISMATCH"],["F2","미확인 조건","NEED_MORE_INFO"],["F3","확인된 조건 충족","NEED_MORE_INFO"],["F4","미확인 조건","NEED_MORE_INFO"]]) {
 test("SC-"+caseId+" reviewed facts and conditions survive browser reload",async({page,scenario})=>{
  test.setTimeout(120000);await login(page,scenario,"operator");
  await page.goto("/capability?view=composer");
  await openLookup(page,'ImprovementVersion');await page.getByLabel("ImprovementVersion",{exact:true}).fill("TEST_IMPROVEMENT_"+caseId);
  await page.getByRole("button",{name:"권한 있는 요구사항 조회",exact:true}).click();
  await page.getByRole("group",{name:"TEST CAP-A",exact:true}).getByRole("button",{name:"조합에 추가",exact:true}).click();
  await page.getByLabel("조합명",{exact:true}).fill("TEST browser "+caseId);
  await page.getByRole("button",{name:"해결범위 항목 추가",exact:true}).click();
  await page.getByLabel("기능 해결 역할",{exact:true}).fill("TEST 재고 등록·조회");
  await page.getByRole("button",{name:"서비스 조합 저장",exact:true}).click();
  await expect(page.getByText("서비스 조합 버전이 저장됐습니다.",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"정부지원사업 매칭",exact:true}).click();
  const n=scenario.account.notices.B;
  await openLookup(page,'Notice ID');await page.getByLabel("Notice ID",{exact:true}).fill(n.notice_id);
  await openLookup(page,'확정 RequirementVersion');await page.getByLabel("확정 RequirementVersion",{exact:true}).fill(n.requirement_version_id);
  await page.getByRole("button",{name:"확정 근거로 매칭 후보 준비",exact:true}).click();
  await expect(page.locator(".condition-comparison").getByRole("heading",{name:heading,exact:true})).toBeVisible();
  const candidateId=await page.getByLabel("저장된 후보 ID",{exact:true}).inputValue();
  await page.getByLabel("검토 사유",{exact:true}).fill("TEST 조건별 근거 확인 후 보류");
  await page.getByLabel("담당자 검토").selectOption("HOLD");
  await page.getByRole("button",{name:"검토 기록",exact:true}).click();
  await expect(page.getByText("검토 이력이 저장됐습니다.",{exact:true})).toBeVisible();
  await page.reload();await openLookup(page,'저장된 후보 ID');await page.getByLabel("저장된 후보 ID",{exact:true}).fill(candidateId);
  await page.getByRole("button",{name:"매칭 결과 조회",exact:true}).click();
  await expect(page.locator(".condition-comparison").getByRole("heading",{name:heading,exact:true})).toBeVisible();
  await expect(page.getByText("HOLD: TEST 조건별 근거 확인 후 보류",{exact:true})).toBeVisible();
  await expect(page.getByRole("option",{name:"PROPOSABLE"})).toHaveCount(0);
  await page.getByText("분석 실행 및 검토 계보",{exact:true}).click();
  await expect(page.getByText("공통 분석 1회",{exact:true})).toBeVisible();
  await expect(page.getByText("연결된 공통 검토 1건",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"제안서 생성조건 확인",exact:true}).click();
  const proposal=page.getByRole("region",{name:"제안서 생성조건"});
  await expect(proposal).toContainText("제안서 생성이 차단되었습니다.");
  await expect(proposal).toContainText("현재 담당자 검토가 제안 가능으로 확정되지 않았습니다.");
  await expect(proposal.getByRole("link",{name:"제안서 작성·항목별 검토 화면",exact:true})).toHaveAttribute("href",/\/proposal\?candidate=/);
  await expect(proposal.getByRole("button",{name:"저장",exact:true})).toHaveCount(0);
  await page.getByText("정확한 입력 Version과 근거 Snapshot",{exact:true}).click();
  await expect(page.locator("pre")).toContainText('"comparison"');
  evidence(scenario,caseId,{candidateId,notice:n,fit,heading,refresh:true,mode:"SYNTHETIC_TEST_ONLY",normalProvider:"NOT_CONNECTED"});
  await page.screenshot({path:resolve(scenario.runtime,"isolated-"+caseId+"-comparison.png"),fullPage:true});
 });
}

async function openLookup(page:import("@playwright/test").Page,label:string){const summary=page.getByText('고급 식별자: '+label,{exact:true});await expect(summary).toBeVisible();if(!await summary.locator('..').evaluate(el=>(el as HTMLDetailsElement).open))await summary.click();}
