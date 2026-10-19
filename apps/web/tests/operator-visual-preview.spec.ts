import {test,expect,Page} from "@playwright/test";
const names=["업무 대시보드","수요기업 목록","기업 통합 업무","기업자료·Fact 검토","개선요구 검토","DATCO 서비스 추천","서비스 조합 검토","정부지원사업 추천","매칭·자격 검토","보완자료 요청","맞춤형 제안서","전달·검토 이력"];
async function enter(page:Page){await page.goto("/ui-preview/operator");await page.getByRole("button",{name:"미리보기 진입",exact:true}).click();}
async function menu(page:Page,name:string){await page.getByRole("navigation",{name:"운영자 업무 메뉴"}).getByRole("button",{name,exact:true}).click();}
async function examples(page:Page){await page.getByRole("button",{name:"예시 화면 보기 · 여러 기업",exact:true}).click();}
test("empty default, explicit example counts, exit clears and refresh stays empty",async({page})=>{
 await enter(page);await expect(page.getByText("등록된 수요기업이 없습니다",{exact:true})).toBeVisible();await expect(page.locator(".op-company-mini")).toHaveCount(0);
 await menu(page,names[3]);await expect(page.locator(".op-fact-row")).toHaveCount(0);
 await page.getByRole("button",{name:"예시 화면 보기 · 기업 1개",exact:true}).click();await expect(page.locator(".op-company-mini")).toHaveCount(1);
 await examples(page);await expect(page.locator(".op-company-mini")).toHaveCount(3);
 await page.getByRole("button",{name:"예시 종료",exact:true}).click();await expect(page.locator(".op-company-mini")).toHaveCount(0);
 await page.reload();await page.getByRole("button",{name:"미리보기 진입"}).click();await expect(page.getByText("등록된 수요기업이 없습니다",{exact:true})).toBeVisible();
});
test("all 12 screens navigation screenshots and no business requests",async({page},info)=>{
 const errors:string[]=[],calls:string[]=[];page.on("pageerror",e=>errors.push(e.message));page.on("request",r=>{if(new URL(r.url()).pathname.startsWith("/api/"))calls.push(r.url());});
 await enter(page);await examples(page);
 for(let i=0;i<names.length;i++){await menu(page,names[i]);await expect(page.locator(".op-heading h1")).toBeVisible();await page.screenshot({path:info.outputPath(`O-${String(i+1).padStart(2,"0")}.png`),fullPage:true});}
 await menu(page,names[0]);await expect(page.locator(".op-heading h1")).toHaveText("업무 대시보드");expect(errors).toEqual([]);expect(calls).toEqual([]);
});
test("company site improvement context isolation and scoped request return",async({page})=>{
 await enter(page);await examples(page);await page.getByLabel("업무 대상 기업 변경").selectOption("COMP-001");await menu(page,names[4]);
 await page.getByLabel("To-Be 개선목표").fill("첫 기업 검토 초안");await page.getByRole("button",{name:"보완자료 요청으로 이동"}).click();await page.getByLabel("수요기업에 요청할 내용").fill("첫 기업 자료 보완");await page.getByRole("button",{name:"보완 요청 작성",exact:true}).click();await expect(page.locator(".op-request-list")).toContainText("첫 기업 자료 보완");
 await page.getByRole("button",{name:"검토하던 화면으로 돌아가기"}).click();await expect(page.getByLabel("To-Be 개선목표")).toHaveValue("첫 기업 검토 초안");
 await page.getByLabel("사업장 선택").selectOption("1");await expect(page.getByLabel("To-Be 개선목표")).not.toHaveValue("첫 기업 검토 초안");await menu(page,names[9]);await expect(page.locator(".op-request-list")).not.toContainText("첫 기업 자료 보완");
 await page.getByLabel("개선과제 선택").selectOption("1");await menu(page,names[4]);await expect(page.locator(".op-quote")).toContainText("가상 원문");
 await page.getByLabel("업무 대상 기업 변경").selectOption("COMP-002");await menu(page,names[4]);await expect(page.getByLabel("To-Be 개선목표")).not.toHaveValue("첫 기업 검토 초안");
 await page.getByLabel("업무 대상 기업 변경").selectOption("COMP-001");await menu(page,names[4]);await expect(page.getByLabel("To-Be 개선목표")).toHaveValue("첫 기업 검토 초안");
 await menu(page,names[1]);await page.getByPlaceholder("기업名, 업종, 개선과제 검색".replace("名","명")).fill("없는기업");await expect(page.getByText("검색 결과가 없습니다",{exact:true})).toBeVisible();
});
test("evidence fact review blockers and request back from matching",async({page})=>{
 await enter(page);await examples(page);await menu(page,names[3]);await page.locator(".op-doc-item").first().click();await expect(page.getByRole("dialog")).toContainText("Fixture");await page.getByRole("dialog").getByRole("button",{name:"확인",exact:true}).click();
 await page.locator(".op-fact-row").nth(1).getByRole("button",{name:"검토 확인",exact:true}).click();await expect(page.locator(".op-fact-row").nth(1)).toContainText("확인됨");
 await menu(page,names[8]);await expect(page.getByText("제안서 생성 차단",{exact:true})).toBeVisible();await page.getByRole("button",{name:"부족정보 보완"}).click();await page.getByRole("button",{name:"검토하던 화면으로 돌아가기"}).click();await expect(page.locator(".op-heading h1")).toHaveText("매칭 · 신청자격 검토");
 await menu(page,names[10]);await expect(page.getByRole("button",{name:"새 초안 생성"})).toBeDisabled();await page.getByLabel("업무 대상 기업 변경").selectOption("COMP-003");await menu(page,names[10]);await expect(page.getByRole("button",{name:"새 초안 생성"})).toBeDisabled();
});
test("normal composition match proposal new version review and local delivery",async({page},info)=>{
 await enter(page);await examples(page);await page.getByLabel("업무 대상 기업 변경").selectOption("COMP-002");await menu(page,names[5]);await page.getByRole("button",{name:"候補 선택".replace("候補","후보")}).click();await page.getByRole("button",{name:"서비스 조합 비교"}).click();await page.getByRole("button",{name:"이 조합 검토"}).click();await page.getByRole("button",{name:"정부지원사업 후보 검토"}).click();await page.getByRole("button",{name:"이 후보 검토"}).click();await page.getByRole("button",{name:"자격·매칭 검토"}).click();await expect(page.locator(".op-three-way")).toContainText("C안");await page.screenshot({path:info.outputPath("three-way.png"),fullPage:true});
 await page.getByRole("button",{name:"제안서로 이동"}).click();await page.getByLabel("제안 내용").fill("가상 제안서 수정본");await page.getByRole("button",{name:"새 버전 저장"}).click();await expect(page.locator(".op-heading")).toContainText("v3");await menu(page,names[11]);await expect(page.getByRole("button",{name:"화면상 전달 이력 기록"})).toBeDisabled();await menu(page,names[10]);await page.getByRole("button",{name:"현 버전 내용 검토 표시"}).click();await page.getByRole("button",{name:"전달·회신 이력 보기"}).click();await page.getByRole("button",{name:"화면상 전달 이력 기록"}).click();await expect(page.locator(".op-history")).toContainText("v3");await expect(page.locator(".op-toast")).toContainText("전송하지 않았습니다");
});
test("mobile navigation and logout are preview only",async({page},info)=>{
 await page.setViewportSize({width:390,height:844});await enter(page);await examples(page);await page.getByRole("button",{name:"메뉴 열기",exact:true}).click();await menu(page,names[3]);await expect(page.locator(".op-heading h1")).toBeVisible();await page.screenshot({path:info.outputPath("mobile.png"),fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.locator(".op-top-logout").click();await page.getByRole("dialog").getByRole("button",{name:"로그아웃",exact:true}).click();await expect(page.getByRole("button",{name:"미리보기 진입"})).toBeVisible();
});
