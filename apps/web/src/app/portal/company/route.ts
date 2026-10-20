import {servePortal} from '../../../portal/server';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function GET(request:Request){return servePortal(request,'company');}
