import {NextRequest} from 'next/server';

export async function GET(request:NextRequest,context:{params:Promise<{path?:string[]}>}){
 const {path=[]}=await context.params;
 if(path.length!==1||!['overview','access','connections'].includes(path[0]))return Response.json({reason:'INVALID_PATH'},{status:400});
 const target=new URL('/admin/'+path[0],process.env.API_ORIGIN??'http://127.0.0.1:8000');
 try{
  const upstream=await fetch(target,{headers:{Cookie:request.headers.get('cookie')??''},cache:'no-store',signal:AbortSignal.timeout(10000)});
  return new Response(await upstream.arrayBuffer(),{status:upstream.status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
 }catch{return Response.json({reason:'API_UNAVAILABLE'},{status:502});}
}
