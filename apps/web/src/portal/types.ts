export type PortalRole = 'COMPANY_EDITOR' | 'DATCO_OPERATOR' | 'DATCO_ADMIN';
export type PortalIdentity = {id:string; role:PortalRole; name:string};
import type {BusinessContext} from "./context";
export type PortalProps = {business?:BusinessContext;session?:PortalIdentity; onLogout?:()=>void};
export const roleLanding:Record<string,string> = {COMPANY_EDITOR:'/portal/company',DATCO_OPERATOR:'/portal/operator',DATCO_ADMIN:'/portal/admin',COMPANY_APPROVER:'/'};
