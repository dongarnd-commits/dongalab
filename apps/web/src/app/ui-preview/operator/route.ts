import {execFile} from "node:child_process";
import {promisify} from "node:util";
import {readFile} from "node:fs/promises";
import path from "node:path";
export const runtime="nodejs";
export const dynamic="force-dynamic";
let compilation:Promise<string>|undefined;
export async function GET(){
  if(process.env.NODE_ENV!=="development")return new Response("Not Found",{status:404});
  compilation??=(async()=>{const out=path.join(process.cwd(),".next","operator-ui-preview-"+process.pid);await promisify(execFile)(process.execPath,[path.join(process.cwd(),"build-operator-preview.mjs"),out],{timeout:60000});return out;})().catch(e=>{compilation=undefined;throw e;});
  try{const out=await compilation;const [js,css]=await Promise.all([readFile(path.join(out,"preview.js"),"utf8"),readFile(path.join(out,"preview.css"),"utf8")]);
  return new Response(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DATCO ONE · 개발 전용 UI 미리보기</title><style>${css.replaceAll("</style","<\\/style")}</style></head><body><div class="operator-preview-disclaimer" role="status">개발 전용 UI 미리보기 · 기본 빈 상태 · 예시 모드는 가상 데이터 · 인증/DB/API/AI 미연결 · 실제 계정·민감자료 입력 금지</div><div id="root"></div><script>${js.replaceAll("</script","<\\/script")}</script></body></html>`,{headers:{"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store","Content-Security-Policy":"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'","X-Robots-Tag":"noindex, nofollow"}});
  }catch{return new Response("UI preview compilation unavailable",{status:503});}
}
