import {expect,type Page} from '@playwright/test';

/** A work menu keeps its exact company/Version; the back action opens its list. */
export async function openGlobalRequestList(page:Page,cid:string,vid:string){
 const target=page.getByTestId('operator-business-context');
 // A send POST resolves before refreshDraft and its return-to-list callback.
 // Both callers sent an analysis draft: finish that view before opening another list.
 await expect(page.getByTestId('improvement-analysis')).toHaveCount(0);
 await page.locator('aside').getByRole('button',{name:'보완자료 요청',exact:true}).click();
 const selected=await target.getAttribute('data-company-id');
 if(selected){
  await expect(target).toHaveAttribute('data-company-id',cid);
  await expect(target).toHaveAttribute('data-version-id',vid);
  await page.getByRole('button',{name:'검토 목록으로 돌아가기',exact:true}).click();
  await page.locator('aside').getByRole('button',{name:'보완자료 요청',exact:true}).click();
 }else{
  // A completed send can already have returned to its originating global list.
  await expect(target).toHaveAttribute('data-company-id','');
  await expect(target).toHaveAttribute('data-version-id','');
 }
 await expect(target).toHaveAttribute('data-company-id','');
 await expect(target).toHaveAttribute('data-version-id','');
 await expect(page.locator('aside').getByRole('button',{name:'보완자료 요청',exact:true})).toHaveAttribute('aria-current','page');
 await expect(page).toHaveURL(url=>url.searchParams.get('screen')==='requests'&&!url.searchParams.has('company')&&!url.searchParams.has('version'));
 // The company replied in a different browser; explicitly reload the read view.
 await page.reload();
 await expect(target).toHaveAttribute('data-company-id','');
 await expect(target).toHaveAttribute('data-version-id','');
 await expect(page.getByLabel('요청 검색',{exact:true})).toBeVisible();
}
