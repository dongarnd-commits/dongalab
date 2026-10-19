import { NextRequest } from "next/server";
async function proxy(request:NextRequest,context:{params:Promise<{path?:string[]}>}){
 const {path=[]}=await context.params;
 if(path.some(s=>!/^[a-zA-Z0-9_-]+$/.test(s)))return Response.json({reason:"INVALID_PATH"},{status:400});
 const url=new URL("/company"+(path.length?"/"+path.join("/"):""),process.env.API_ORIGIN??"http://127.0.0.1:8000");url.search=request.nextUrl.search;
 try{
  let body:Uint8Array|undefined;
  if(request.method==="POST"){
   const reader=request.body?.getReader();const chunks:Uint8Array[]=[];let size=0;
   if(reader)while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>20*1024*1024+128000){await reader.cancel();return Response.json({reason:"UPLOAD_SIZE_INVALID"},{status:413});}chunks.push(value);}
   body=new Uint8Array(size);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.length;}
  }
  const r=await fetch(url,{method:request.method,headers:{"Content-Type":request.headers.get("content-type")??"application/json","X-Upload-Name":request.headers.get("x-upload-name")??"","Cookie":request.headers.get("cookie")??"","Origin":request.headers.get("origin")??""},body:body as BodyInit|undefined,cache:"no-store",signal:AbortSignal.timeout(60000)});
  const headers=new Headers({"Cache-Control":"no-store"});for(const name of ["content-type","content-disposition","x-content-type-options","content-security-policy"]){const v=r.headers.get(name);if(v)headers.set(name,v);}
  return new Response(await r.arrayBuffer(),{status:r.status,headers});
 }catch{return Response.json({reason:"API_UNAVAILABLE"},{status:502});}
}
export const GET=proxy;export const POST=proxy;
