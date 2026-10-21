import type {CompanyWorkflow} from './workflow';
import type {CompanyData} from '../company/client';
export async function storeAttachment(w:CompanyWorkflow,file:File,site=''){
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer())),b=>b.toString(16).padStart(2,'0')).join('');
 const actual=await w.request<CompanyData>('/'+w.cid);const known=actual.files.find(f=>f.digest===digest);
 if(known){if(known.site_id&&known.site_id!==site)throw Error('이 파일은 다른 사업장에 등록되어 있습니다. 관련 사업장을 확인해 주세요.');return known;}
 try{return await w.upload(file,site,()=>{});}catch(e){const current=await w.request<CompanyData>('/'+w.cid);const recovered=current.files.find(f=>f.digest===digest&&(!f.site_id||f.site_id===site));if(recovered)return recovered;throw e;}
}
export function industryParts(value:string){const parts={type:'',items:'',legacy:''};let active:keyof typeof parts='legacy';for(const line of value.split('\n')){let text=line;if(line.startsWith('업태: ')){active='type';text=line.slice(4);}else if(line.startsWith('종목: ')){active='items';text=line.slice(4);}parts[active]+=(parts[active]?'\n':'')+text;}return parts;}
export const industryValue=(p:{type:string;items:string;legacy:string})=>[p.legacy,p.type&&'업태: '+p.type,p.items&&'종목: '+p.items].filter(Boolean).join('\n');
export const displayBusinessNumber=(n:string)=>/^[0-9]{10}$/.test(n)?n.slice(0,3)+'-'+n.slice(3,5)+'-'+n.slice(5):n;
