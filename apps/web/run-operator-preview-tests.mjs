import {mkdir,cp,symlink,writeFile,open} from "node:fs/promises";
import {spawn,spawnSync} from "node:child_process";
import path from "node:path";
import net from "node:net";
import {randomUUID} from "node:crypto";
const web=import.meta.dirname,repo=path.resolve(web,"../.."),out=path.join(repo,"storage/private/runtime/operator-visual-preview",randomUUID().slice(0,12)),shadow=path.join(out,"web");
await mkdir(shadow,{recursive:true});
for(const name of ["src","tests","public","package.json","package-lock.json","tsconfig.json","next-env.d.ts","build-company-preview.mjs","build-operator-preview.mjs","playwright.operator-preview.config.ts"]){try{await cp(path.join(web,name),path.join(shadow,name),{recursive:true});}catch(e){if(e.code!=="ENOENT")throw e;}}
await symlink(path.join(web,"node_modules"),path.join(shadow,"node_modules"),process.platform==="win32"?"junction":"dir");
await writeFile(path.join(shadow,"next.config.mjs"),'export default '+JSON.stringify({turbopack:{root:repo},experimental:{turbopackFileSystemCacheForDev:false}})+';');
const env={...process.env,NEXT_TELEMETRY_DISABLED:"1",API_ORIGIN:"http://127.0.0.1:1",CAPABILITY_API_ORIGIN:"http://127.0.0.1:1"},children=[],steps=[];
async function port(){const s=net.createServer();await new Promise(r=>s.listen(0,"127.0.0.1",r));const p=s.address().port;await new Promise(r=>s.close(r));return p;}
async function start(name,args,cwd=shadow){const f=await open(path.join(out,name+".log"),"w");const p=spawn(process.execPath,args,{cwd,env,stdio:["ignore",f.fd,f.fd],detached:process.platform!=="win32",windowsHide:true});children.push(p);p.on("exit",()=>f.close());return p;}
async function stop(p){if(p.exitCode!==null||p.signalCode!==null)return;if(process.platform==="win32")spawnSync("taskkill",["/PID",String(p.pid),"/T","/F"],{stdio:"ignore",windowsHide:true});else process.kill(-p.pid,"SIGTERM");await new Promise(r=>p.once("exit",r));}
async function command(name,args,cwd=shadow){const p=await start(name,args,cwd);const code=await new Promise(r=>p.once("exit",r));steps.push({name,code});console.log(name,code);if(code!==0)throw Error(name+" failed");}
async function wait(url,status){for(let i=0;i<180;i++){try{const r=await fetch(url,{signal:AbortSignal.timeout(3000)});if(r.status===status)return;}catch{}await new Promise(r=>setTimeout(r,500));}throw Error("Server timeout");}
try{const p=await port();env.DATCO_UI_PREVIEW_ORIGIN="http://127.0.0.1:"+p;const dev=await start("dev",[path.join(web,"node_modules/next/dist/bin/next"),"dev","--hostname","127.0.0.1","--port",String(p)]);await wait(env.DATCO_UI_PREVIEW_ORIGIN+"/ui-preview/operator",200);
await command("playwright",[path.join(web,"node_modules/@playwright/test/cli.js"),"test","--config","playwright.operator-preview.config.ts","--output",path.join(out,"screenshots")]);await stop(dev);
await command("lint",[path.join(web,"node_modules/eslint/bin/eslint.js"),"."],web);await command("typecheck",[path.join(web,"node_modules/typescript/bin/tsc"),"--project",path.join(web,"tsconfig.json"),"--noEmit","--incremental","false"],web);await command("build",[path.join(web,"node_modules/next/dist/bin/next"),"build"]);
const prod=await start("production",[path.join(web,"node_modules/next/dist/bin/next"),"start","--hostname","127.0.0.1","--port",String(p)]);await wait(env.DATCO_UI_PREVIEW_ORIGIN+"/ui-preview/operator",404);await wait(env.DATCO_UI_PREVIEW_ORIGIN+"/ui-preview/company",404);steps.push({name:"production-previews-404",code:0});await stop(prod);
}finally{for(const p of children)await stop(p);await writeFile(path.join(out,"report.json"),JSON.stringify({steps,no_database_or_api_started:true},null,2));console.log("REPORT",out);}
