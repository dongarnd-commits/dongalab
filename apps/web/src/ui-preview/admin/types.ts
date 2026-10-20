/** UI presentation shapes adapted from the supplied v0.2 reference.
 * Not an approved API, DB, permission or assignment contract.
 * The production preview uses only null metrics and empty collections.
 */
export type Screen = 'overview'|'intake'|'assignments'|'operators'|'journey'|'schedule'|'infrastructure'|'ai-quality'|'reference'|'users'|'portals'|'audit';
export type Period = '7d' | '30d' | '90d';
export type HealthState = 'UP'|'DEGRADED'|'DOWN'|'UNKNOWN';
export type Severity = 'info'|'warning'|'critical';
export type RunKind = 'REAL_AI_EXECUTION'|'RULE_BASED_EXTRACTION'|'MANUAL_REVIEW'|'NOT_SUPPORTED'|'BLOCKED_BY_POLICY';
export type WorkflowStage = 'intake'|'fact_review'|'improvement_review'|'capability_recommend'|'grant_matching'|'proposal'|'company_confirmation'|'other';
export interface Filter { period: Period; operatorId?: string; stage?: string }
export interface SourceInfo { origin: string; asOf: string | null; collectedAt?: string|null; note?: string|null }
/** 사용자 역할과 관리 Action은 Repository의 FROZEN/권한 계약에서 반드시 확인. */
export interface Viewer { userId: string; name: string; allowedActions: string[]; roleLabels: string[] }
export interface Totals {
  distinctCompanies: number|null; requests: number|null; unassigned: number|null;
  assigned: number|null; inProgress: number|null; completed: number|null;
  reviewWaiting: number|null; overdue: number|null; activeOperators: number|null;
  technicalFailures: number|null; openIncidents: number|null;
}
export interface StageCount { stage: WorkflowStage|string; label: string; count: number }
export interface OperatorLoad { operatorId: string; operatorName: string; assigned: number; inProgress: number; waiting: number; completed: number; overdue: number; capacity?: number|null; available?: boolean|null }
export interface DailyCount { date: string; received: number; completed: number; open: number }
export interface HeatCell { operatorId: string; operatorName: string; stage: string; label: string; count: number }
export interface TimelineWork { id: string; label: string; operator: string; startAt: string; dueAt: string; doneAt?: string|null; status: string; sourceId?: string }
export interface HealthMetric { at: string; value: number }
export interface ServiceHealth {
  id: string; name: string; kind: 'Web'|'API'|'DB'|'Storage'|'Worker'|'Integration'|string;
  health: HealthState; measuredAt: string|null; cpuPercent?:number|null; memoryPercent?:number|null;
  errorRatePercent?:number|null; latencyP95Ms?:number|null; storageUsedPercent?:number|null;
  history?:HealthMetric[]; note?:string|null;
}
export interface AIStats {
  totalRuns:number|null; successfulRuns:number|null; failedRuns:number|null;
  pendingRuns:number|null; avgLatencyMs:number|null; measuredPeriod?:string|null;
  runKindCounts?:{kind:RunKind;count:number}[];
  quality?:{
    evaluatedCases:number|null; correctCases:number|null; correctionReviewed:number|null;
    correctionCount:number|null; evidenceReviewed:number|null; evidenceWithReferences:number|null;
    evaluationMethod?:string|null; evaluationVersion?:string|null;
  }|null;
}
export interface PortalHealth { id:'company'|'operator'; name:string; health:HealthState; usersActive:number|null; failedActions:number|null; asOf:string|null }
export interface ServiceReference { id:string; domain:string; label:string; version?:string|null; dataStatus:string; verifiedAt?:string|null; source:string; note?:string|null }
export interface AdminUser { userId:string; name:string; roleLabels:string[]; accountStatus:string; companyScopes:number|null; assignedRequests:number|null; lastActiveAt?:string|null }
export interface AuditEvent { id:string; action:string; actor:string; subject:string; at:string; summary:string; source:string }
export interface ControlAlert { id:string; title:string; category:'assignment'|'workflow'|'ai'|'infrastructure'|'security'|'integration'|string; severity:Severity; detail:string; happenedAt:string; targetId?:string|null }
export interface Snapshot {
  filters:Filter; source:SourceInfo; viewer:Viewer;
  totals:Totals; stages:StageCount[]; stageReached:StageCount[]; operatorLoads:OperatorLoad[]; throughput:DailyCount[];
  heatmap:HeatCell[]; schedules:TimelineWork[]; services:ServiceHealth[];
  ai:AIStats|null; portals:PortalHealth[]; references:ServiceReference[]; users:AdminUser[];
  alerts:ControlAlert[]; audits:AuditEvent[];
}
export interface IntakeRequest { requestId:string; companyId:string; companyName:string; siteName?:string|null; title:string; receivedAt:string; stage:string; status:string; assignedOperatorId?:string|null; assignedOperatorName?:string|null; dueAt?:string|null; assignmentRevision?:string|null; lastUpdatedAt?:string|null }
export interface PageResult<T> { items:T[]; total:number|null; source:SourceInfo }
export interface AssignmentCandidate { operatorId:string; operatorName:string; reason:string; canAssign:boolean; blockers:string[]; currentLoad:number|null }
export interface AssignmentPreview { requestId:string; candidates:AssignmentCandidate[]; evaluatedAt:string|null; policyVersion?:string|null; blockers:string[] }
