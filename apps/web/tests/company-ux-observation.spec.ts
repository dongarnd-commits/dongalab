import {test,expect} from '@playwright/test';
import {company,goto,detail,financial,history,optionalDetails,profileResponse} from './company-ux-fixture';
test.setTimeout(180000);
test('observe the same synthetic workflow before and after company UX changes',async({page},info)=>{
 const {cid,profile}=await company(page,'observation',{financials:[financial(2023,'3000'),financial(2024,'4000')],history:[history]});
 const metrics:Record<string,unknown>={label:process.env.COMPANY_UX_OBSERVATION_LABEL,synthetic:true};
 await expect(page.getByLabel('실제 기업 현황')).toContainText('미완료 보완 요청 0건 · 받은 제안서 0건');metrics.homeCompanyName=await page.getByRole('heading',{name:profile.name,exact:true}).count();
 metrics.homeFiveStepCount=await page.getByLabel('5단계 업무 진행').count();
 await page.screenshot({path:info.outputPath('01-home.png'),fullPage:true});
 await goto(page,cid,'company');await expect(page.getByLabel('기업명',{exact:true})).toHaveValue(profile.name);
 metrics.legacyIndustryInitiallyVisible=await page.getByLabel('기존 업종',{exact:true}).isVisible();
 await page.screenshot({path:info.outputPath('02-company-site.png'),fullPage:true});
 await goto(page,cid,'finance');await page.getByRole('button',{name:'재무정보 직접 입력',exact:true}).click();
 const editor=page.getByRole('dialog');metrics.singleEntryScope=await editor.getByTestId('finance-save-scope').count();metrics.singleEntryRowSelector=await editor.getByLabel('작성할 내역',{exact:true}).count();
 await editor.getByLabel('재무연도',{exact:true}).fill('2025');await editor.getByLabel('기준기간',{exact:true}).fill('2025');await editor.getByLabel(/^매출액/).fill('5000');
 await optionalDetails(page);await editor.getByLabel(/^자산총계/).fill('123');await editor.getByLabel(/^자산총계/).fill('');
 await page.screenshot({path:info.outputPath('03-finance-single.png'),fullPage:true});
 const save=profileResponse(page);await editor.getByRole('button',{name:'재무정보 저장',exact:true}).click();metrics.emptyOptionalAmountSaveStatus=(await save).status();
 const after=await detail(page,cid);metrics.profileVersions=after.inputs.length;metrics.historyCount=after.inputs.at(-1).data.history.length;metrics.financialYears=after.inputs.at(-1).data.financials.map((r:{year:number})=>r.year);
 if(await page.getByRole('dialog').count())await page.getByRole('button',{name:'편집창 닫기',exact:true}).click();
 await page.getByRole('button',{name:'수행이력 직접 입력',exact:true}).click();await page.screenshot({path:info.outputPath('04-history.png'),fullPage:true});await page.getByRole('button',{name:'편집창 닫기',exact:true}).click();
 await goto(page,cid,'needs');await page.getByRole('button',{name:'새 개선요구 작성',exact:true}).click();
 metrics.duplicateNewNeed=await page.getByRole('button',{name:'새 개선요구 작성',exact:true}).count();metrics.detachNoticeWithoutAttachment=await page.getByText('첨부 해제는 저장 후 반영되며 이전 제출 이력과 원본은 변경하지 않습니다.',{exact:true}).count();
 await page.screenshot({path:info.outputPath('05-need-draft.png'),fullPage:true});
 for(const [screen,file]of [['files','06-files.png'],['requests','07-requests-empty.png'],['proposals','08-proposals-empty.png']]){await goto(page,cid,screen);await page.screenshot({path:info.outputPath(file),fullPage:true});}
 await info.attach('observed-behavior',{body:JSON.stringify(metrics,null,2),contentType:'application/json'});console.log('COMPANY_UX_OBSERVATION '+JSON.stringify(metrics));
});