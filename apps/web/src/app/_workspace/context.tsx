"use client";
import {createContext,useContext} from "react";
export type Company={id:string;name:string;sites?:{id:string;name:string}[];improvements?:{id:string;title:string;state:string;version_id:string;site_id:string}[];counts?:{files:number;candidates:number;facts:number;pending_facts:number;improvements:number}};
export type WorkspaceData={actor:{id:string;username:string;role:string};companies:Company[];compositions:{id:string;version_id:string;ordinal:number;company_id:string;improvement_version_id:string;name:string}[];matches:{id:string;company_id:string;improvement_version_id:string;composition_id:string;name:string;fit:string}[];proposals:{id:string;company_id:string;title:string;ordinal:number;improvement_version_id:string;pending:boolean}[];catalog:{features:number;published:number}|null};
export const WorkspaceContext=createContext<{data:WorkspaceData|null;identity:{id:string;role:string;username?:string}|null;company:Company|undefined;refresh:()=>void}>({data:null,identity:null,company:undefined,refresh:()=>{}});
export const useWorkspace=()=>useContext(WorkspaceContext);
export const roles:Record<string,string>={COMPANY_EDITOR:"수요기업 담당자",COMPANY_APPROVER:"수요기업 승인자",DATCO_OPERATOR:"DATCO 운영자",DATCO_ADMIN:"DATCO 관리자"};
