import {expect,type Page} from '@playwright/test';

/** A work menu keeps its exact company/Version; the back action opens its list. */
export async function openGlobalRequestList(page:Page,cid:string,vid:string){
 const target=page.getByTestId('operator-business-context');
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
 // The company replied in a different browser; explicitly reload the read view.
 await page.reload();
 await expect(target).toHaveAttribute('data-company-id','');
 await expect(target).toHaveAttribute('data-version-id','');
 await expect(page.getByLabel('요청 검색',{exact:true})).toBeVisible();
}
