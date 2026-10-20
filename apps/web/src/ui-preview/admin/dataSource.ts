/** UI-only disconnected adapter. No network, permissions or business mutations. */
import type {Snapshot,Filter} from './types';
export function disconnectedSnapshot(filters:Filter):Snapshot {
 return {filters,source:{origin:'데이터 미연결 · UI 미리보기',asOf:null},viewer:{userId:'',name:'관리자 UI 미리보기',allowedActions:[],roleLabels:[]},totals:{distinctCompanies:null,requests:null,unassigned:null,assigned:null,inProgress:null,completed:null,reviewWaiting:null,overdue:null,activeOperators:null,technicalFailures:null,openIncidents:null},stages:[],stageReached:[],operatorLoads:[],throughput:[],heatmap:[],schedules:[],services:[],ai:null,portals:[],references:[],users:[],alerts:[],audits:[]};
}
