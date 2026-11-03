import {NextRequest} from 'next/server';

/** Only this bounded workbook command accepts a larger JSON selection batch. */
export async function POST(request:NextRequest){
 const limit=1024*1024;
 if(Number(request.headers.get('content-length')??0)>limit)return Response.json({reason:'INVALID_WORKBOOK_SELECTION'},{status:413});
 try{
  const reader=request.body?.getReader();if(!reader)return Response.json({reason:'INVALID_REQUEST'},{status:422});
  const parts:Uint8Array[]=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();return Response.json({reason:'INVALID_WORKBOOK_SELECTION'},{status:413});}parts.push(value);}
  const body=new Uint8Array(size);let offset=0;for(const part of parts){body.set(part,offset);offset+=part.length;}
  const target=new URL('/capability/asset-imports/apply',process.env.CAPABILITY_API_ORIGIN??process.env.API_ORIGIN??'http://127.0.0.1:8000');
  const response=await fetch(target,{method:'POST',headers:{'Content-Type':'application/json','Cookie':request.headers.get('cookie')??'','Origin':request.headers.get('origin')??''},body,cache:'no-store',signal:AbortSignal.timeout(30000)});
  return new Response(await response.arrayBuffer(),{status:response.status,headers:{'Content-Type':response.headers.get('content-type')??'application/json','Cache-Control':'no-store'}});
 }catch{return Response.json({reason:'API_UNAVAILABLE'},{status:502});}
}
