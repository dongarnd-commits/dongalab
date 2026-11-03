import {NextRequest} from 'next/server';

export async function POST(request:NextRequest){
 const limit=20*1024*1024;
 const size=Number(request.headers.get('content-length')??0);
 if(size>limit)return Response.json({reason:'UPLOAD_SIZE_INVALID'},{status:413});
 const parts:Uint8Array[]=[];let length=0;
 try{
  const reader=request.body?.getReader();
  if(!reader)return Response.json({reason:'UPLOAD_SIZE_INVALID'},{status:413});
  while(true){const {value,done}=await reader.read();if(done)break;length+=value.length;if(length>limit){await reader.cancel();return Response.json({reason:'UPLOAD_SIZE_INVALID'},{status:413});}parts.push(value);}
  const body=new Uint8Array(length);let offset=0;for(const part of parts){body.set(part,offset);offset+=part.length;}
  const target=new URL('/capability/asset-imports/preview',process.env.CAPABILITY_API_ORIGIN??process.env.API_ORIGIN??'http://127.0.0.1:8000');
  const response=await fetch(target,{method:'POST',headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','X-Upload-Name':request.headers.get('x-upload-name')??'','Cookie':request.headers.get('cookie')??'','Origin':request.headers.get('origin')??''},body,cache:'no-store',signal:AbortSignal.timeout(30000)});
  return new Response(await response.arrayBuffer(),{status:response.status,headers:{'Content-Type':response.headers.get('content-type')??'application/json','Cache-Control':'no-store'}});
 }catch{return Response.json({reason:'API_UNAVAILABLE'},{status:502});}
}
