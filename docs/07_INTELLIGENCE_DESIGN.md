# DATCO 정부지원사업 운영체계 - Intelligence Design

## 1. 목적 / 기준 / 불변조건

확보된 Source/File/Domain Version을 구조화 Candidate로 분석하고 Reason/Evidence/Source Location → Human Review → Confirmed 업무정보로 연결하는 최소 구현계약이다. Notice/Form, Company Fact, Improvement, Capability, 3-way Matching, Change Impact의 6개 분석종류를 다룬다.

기준은 [AGENTS](../AGENTS.md) → [00 Baseline](00_PROJECT_BASELINE.md) → [01 Architecture](01_SYSTEM_ARCHITECTURE.md) → [02 E2E](02_E2E_SYSTEM_FLOW.md) → [03 Data](03_DATA_MODEL.md) → [04 State/Action](04_STATE_ACTION_MODEL.md) → [05 Permission](05_PERMISSION_UI_MATRIX.md) → [06 Collector](06_BIZINFO_COLLECTOR.md) → 실제 [1차](../tools/bizinfo-probe/ANALYSIS.md)/[2차 Probe](../tools/bizinfo-probe/PHASE2_ANALYSIS.md) → 이 문서다. 상위 Entity/State/Action을 변경하지 않는다.

- AI/Rule/OCR 결과는 Candidate다. Candidate ≠ Confirmed Fact ≠ Confirmed Requirement ≠ MatchReview ≠ Approval ≠ Proceed Decision이다.
- 중요한 후보는 정확한 Input Version, Source, Evidence, 가능한 Source Location과 업무 Reason을 연결한다. 근거 없는 값은 생성하지 않는다.
- UNKNOWN/NOT_FOUND/NEEDS_REVIEW는 미확인 의미다. Missing을 False/0/부적합으로 바꾸지 않는다. 실제 enum 이름은 구현에서 정한다.
- Confidence가 높아도 자동 Confirm하지 않는다. Confidence와 Fit도 서로 다른 개념이다.
- 입력 Version/분석 설정을 고정하고 새 입력 분석과 과거 분석을 구분한다. 오래된 결과를 현재 확정정보처럼 사용하지 않는다.
- 기업간 Source/File/Candidate를 섞지 않는다. 입력부터 결과·조회·근거 다운로드까지 Company Scope를 유지한다.

AI/OCR 코드, Provider/Model 제품, Vector DB/Embedding, Queue, Prompt 전문, Token/Temperature/비용·Timeout 수치, API Route/UI 상세, Fine-tuning, HWP/HWPX Library는 확정하지 않는다. 범용 Agent/Prompt/RAG Platform, Multi-Agent, 모든 Format/공고의 완전 자동해석, 하나의 거대한 LLM Prompt를 전제하지 않는다.

## 2. 공통 Pipeline / Module 경계

Source/File/Domain Version → Input Validation → Content Acquisition 확인 → Text/Structure Extraction → Normalization/Classification → AnalysisRun → Structured Candidate → Reason/Evidence/Source Location → Human Review → Domain Result가 공통 흐름이다. 실행 중 요청·추출·분석 단계와 각 실패범위를 추적하며 Run 입력/출력을 보존한다.

| 경계 | 책임 | 제외되는 책임 |
| --- | --- | --- |
| Collector | Raw, NoticeVersion, SourceReference, FileAsset, 확보상태/Metadata | 본문 의미판정/Requirement 확인 |
| Intelligence | 확보 Content 읽기, 추출/문서역할 분류, 구조화 후보·근거 생성 | API Pagination/Secret 관리, 업무 승인·추진 |
| Operations / Domain | 사람 검토/확정, Request 발송, Template/MatchReview/Impact 업무조치 | 분석성공을 자동 확정으로 취급 |

자료 확보 실패 시 없는 내용을 추정하지 않는다. File 확보 ≠ Extraction 성공 ≠ Candidate 생성 성공 ≠ Human Confirmed다. 기술적 AnalysisJob SUCCEEDED는 입력과 결과 처리의 성공이며 업무판정을 뜻하지 않는다.

03의 BackgroundJob/JobAttempt, AnalysisRun, AnalysisInputReference, AnalysisCandidate, AnalysisReview, EvidenceReference, SourceLocation을 공통 재사용한다. FactCandidate/FactReview, CapabilityAssessment, MatchInputSnapshot/MatchCandidate/MatchReview, ImpactAssessment/ImpactTarget 등 기존 Domain 객체로 typed 관계를 연결한다. 분석별 중복 Run/Job Entity 또는 unchecked generic target graph를 추가하지 않는다.

## 3. Analysis Type / Input Contract / 재현 근거

아래 Type은 논리 이름이며 최종 API enum이 아니다. 현재 Root 포인터만 받아 분석하지 않고 요청 시 정확한 Version/파일조합을 고정한다.

| Analysis Type | 정확한 입력 | 후보 / Human 결과 연결 |
| --- | --- | --- |
| NOTICE_REQUIREMENT_ANALYSIS | NoticeVersion, API Metadata/Raw 근거, 확보 HTML/FileAsset | AnalysisCandidate → AnalysisReview → NoticeRequirementVersion/Item |
| COMPANY_FACT_EXTRACTION | CompanyIntake/Company·Site, 실제 Company FileAsset, 비교용 기존 FactVersion | AnalysisCandidate → FactCandidate → FactReview → 새/기존 CompanyFactVersion 또는 Conflict |
| IMPROVEMENT_ANALYSIS | Submitted ImprovementVersion, 관련 Confirmed FactVersion, 첨부 FileAsset | AnalysisCandidate → AnalysisReview → 확인된 ImprovementVersion |
| CAPABILITY_ASSESSMENT | Confirmed ImprovementVersion + CapabilityVersion | CapabilityAssessment의 후보 의미/근거 → AnalysisReview |
| SUPPORT_MATCHING | Confirmed FactVersion(s)/ImprovementVersion, Reviewed CapabilityVersion/Assessment, Confirmed RequirementVersion | MatchInputSnapshot → MatchCandidate → MatchReview |
| CHANGE_IMPACT_ANALYSIS | 변경 전후 정확한 Version, 명시적 입력/결과 Lineage | 영향 Candidate → ImpactAssessment/ImpactTarget 검토·후속조치 |

| 공통 입력 의미 | 최소 검증 |
| --- | --- |
| analysisType / 요청 Domain Object | 허용 Type과 대상 관계, 분석 범위 |
| companyScope 필요 여부 / Company·Site·Case 맥락 | 신뢰된 권한 Context와 모든 Private 입력의 동일 Company 관계 |
| exact Version / Snapshot | 실제 존재·허용관계·현재 적용 Version; 이전/현재 비교는 양쪽 ID 명시 |
| SourceReference / FileAsset | URL 참조와 실제 확보 자료 구분, 읽기권한/검증된 Content |
| SourceLocation 가능 여부 | 위치 기술과 실제 입력 Content 관계; 없으면 한계 표시 |
| requestedAt / requestedBy | Human 또는 승인된 System 요청, Audit/실행 맥락 |
| analysis configuration version | 추출/분류/Rule/Prompt/Provider 설정 참조 |
| 입력 확보상태 / 범위 | 사용한 자료, 실패·미지원·누락 자료 및 분석 목적별 충분성 |

AnalysisRun/AnalysisInputReference에 당시 입력 Version, Rule Version, 필요 시 Prompt/Instruction·Model/Provider·Extractor Version, 실행시각/Attempt/결과를 추적한다. 재현성은 당시 근거와 설정을 이해할 수 있다는 의미이며 같은 자연어 결과의 완전 재현 보장이 아니다. Provider가 실제 제공하지 않은 Model 식별을 만들어 기록하지 않는다. Prompt 전문/Secret/Private Data를 Audit에 무조건 복제하지 않는다. 실제 JSON Schema/저장방식은 Stack 결정 후 구현한다.

## 4. Document Processing / OCR / Source Location

FileAsset/확보 HTML Content → Format Detection → Text/Structure Extraction → Extraction Quality 확인 → 분석 입력으로 처리한다. 1차 우선 대상은 HTML과 PDF다. Probe는 HTML 접근과 PDF prefix만 확인했으며 전체본문/파일 텍스트 추출 성공을 증명하지 않는다.

| 입력 / 처리 의미 | 최소 처리 |
| --- | --- |
| HTML | 확보본의 제목/절/문맥을 추출, 공통 메뉴와 본문 구분; 실제 Selector 검증 필요 |
| Text-based PDF | 페이지·절·텍스트/표 구조 추출 및 누락·깨짐 검토 |
| Scan/Image PDF, 텍스트 부족 | OCR 후보로 분기; 미구현/실패면 Manual Review/추가자료 |
| Excel/이미지 기업자료 | E2E 확장경계 유지, 실제 필요 Fixture로 지원범위 확인 |
| HWP/HWPX/압축/암호화·손상 파일 | 지원 여부 명시; 미지원/추출불가를 빈 문서로 분석하지 않음 |

SUPPORTED/PARTIAL/UNSUPPORTED/NEEDS_MANUAL_REVIEW는 처리 의미 후보이고 04 Job State를 대체하지 않는다. 전체 자료를 지원한다고 약속하지 않는다. OCR Text는 파생 결과이며 Source File 자체가 아니다. Source File → OCR/추출결과 → Candidate의 입력관계를 유지한다. OCR Provider는 교체 가능 경계로 두고 제품을 선정하지 않는다.

Extraction Quality는 텍스트 유무, 읽기 가능성, 페이지/절 범위, 표·단위 연결, OCR 불확실성/누락으로 검토한다. 텍스트 길이만으로 충분성 또는 정확도를 선언하지 않는다. 직접 추출로 충분한 경우 불필요한 OCR/모델 호출을 하지 않는다.

SourceLocation은 HTML section/heading/element·문맥 후보, PDF page/section/text span 후보, 구조화 Source field/record path를 표현한다. 사용자가 해당 **불변 Content**의 원문을 다시 확인할 수 있어야 한다. 모든 자료에 Pixel/Bounding Box를 강제하지 않는다. 정밀위치가 없으면 File/Source와 확인 가능한 절·문맥 수준을 표시하고 실제 존재하지 않는 페이지/좌표를 생성하지 않는다.

## 5. Structured Candidate / Evidence / Quality / Validation

AI 자유문장을 바로 Domain Object로 저장하지 않는다. 종류별 Structured Candidate에 아래 의미를 담고 검증 후 저장한다. Provider raw output은 필요 시 비공개 실행근거로 남기며 검증된 후보/확정정보와 구분한다.

| 출력 의미 | 계약 |
| --- | --- |
| candidateType / value 또는 structuredMeaning | 허용된 종류, 숫자/날짜/단위/기간 타입, 문맥별 의미 |
| inputVersion / run | 실제 Run/AnalysisInputReference의 고정 입력과 일치 |
| reason | 업무상 이유 요약; 적용 Rule이 있으면 근거 참조 |
| evidence[] / sourceLocation[] | 실제 입력 Source/File/위치 참조와 근거 범위 |
| provenance / uncertainty | DIRECT_SOURCE/INFERRED/CONFLICTING/MISSING의 의미 구분 |
| confidence / quality | 필요 시 추출·분석 Confidence/근거 Quality, 산출방식·한계 |
| missing / conflict / opposingEvidence | 부족자료·상충값·반대근거를 함께 보존 |

근거 있는 주장에는 Evidence Source + 확인 가능한 Source Location + Reason을 연결한다. 예: 지원대상 후보와 공고 PDF 3페이지/지원대상 절. 자료 부재 후보는 없는 문장을 증거로 만들지 않고 검사한 Source 범위와 Missing 사유를 기록한다. 직접 근거 없는 추론은 INFERRED/NEEDS_REVIEW로 분리하고 중요한 확정값으로 승격하지 않는다. 사람이 새 근거를 보완하면 그 Source/Location/검토기록을 연결해야 한다.

Provider 출력 이후 Candidate 저장 전 required field, 허용 Candidate Type, Evidence 참조 유효성, Source Location 실제 존재/입력 범위, exact Version/Company Scope, 숫자·날짜·기간·단위 구조를 검증한다. 존재하는 페이지를 인용했다는 사실만으로 주장 내용이 맞다고 보장하지 않으며 원문 내용과의 일치도 검토한다. 비정상 출력/조작된 ID·타기업 참조는 격리하고 정상 후보로 저장하지 않는다. 부분적으로 유효한 항목을 보존할 경우 PARTIAL과 실패항목을 명시하고 Invalid 항목은 업무 사용에서 제외한다.

Confidence는 **결과 신뢰 수준**, Fit은 **기업/과제/공고 적합 의미**다. MISMATCH에 높은 Confidence도 가능하다. Evidence Quality/Extraction Confidence/Analysis Confidence를 필요 시 분리하고 Fit Score와 하나의 숫자로 합치지 않는다. Confidence는 검토 우선순위/저품질 표시/추가정보 요청 후보에 사용하며 자동 Confirm/승인/Proceed 기준이 아니다. 계산공식·Threshold는 미확정이다.

Source 없는 숫자/날짜/기관/조건 생성, Missing→False, Unknown→자동 부적합, 기업 주장→공식 공고조건 전환, 파일명→문서역할 확정은 금지한다. Explainability는 Reason Summary/Evidence/Location/Applied Rule/Conflict/Missing으로 구현하며 모델 내부 Chain-of-Thought 저장·노출을 설계하지 않는다.

## 6. Notice / Form Analysis

NoticeVersion + API Metadata + pblancUrl에서 확보한 HTML + 실제 Attachment FileAsset이 입력이다. API 제목/기관/기간/대상/분야/개요/신청방법을 하나의 Source로 사용하고 PDF에서 다시 추정하여 자동 덮어쓰지 않는다.

출력은 Eligibility Requirement, Support Scope, Application Period, Required Document, Form Field, Plan Section, Evaluation Criterion, Conditional Requirement의 후보다. 각각 구조화 의미/원문/Reason/Evidence/Location/불확실성을 표현한다. Metadata-only 실행도 확보 범위에서 가능하지만 개요만으로 전체 공고의 서류·평가기준을 완전 분석했다고 표시하지 않는다.

06 periodOriginal/startCandidate/endCandidate를 활용한다. API와 상세/PDF 기간이 다르면 양쪽 Source/값을 Conflict로 보존하고 공식 근거를 사람이 검토한다. 날짜/시간대를 새로 상상하지 않는다. Confirmed Application Period는 Notice Requirement Review 결과다.

필수·조건부 서류, 서식명/제출방식/Field/계획서 Section은 Document Classification → Content Inspection → Candidate → Human Review를 따른다. flpthNm/printFlpthNm Source 역할 후보를 보존하고 print 파일/파일명만으로 신청서식 또는 전체본문을 확정하지 않는다.

DATCO_OPERATOR는 04 CONFIRM_NOTICE_REQUIREMENT의 공식 Source/Evidence/Version/현재성 Guard로 NoticeRequirementVersion/Item과 AnalysisReview를 연결한다. 부족 자료는 REQUEST_MORE_SOURCE_REVIEW로 되돌린다. 기업응답이 공식 공고조건을 변경하지 않는다. 부분확정은 확인 항목/범위를 기록하며 누락 서류목록을 완전한 목록으로 취급하지 않는다.

확인된 Requirement와 검토된 서식 근거를 ApplicationTemplateVersion/Definition 작성 입력으로 전달한다. Field 의미/자료형/필수·조건부 항목/Plan Section과 Source를 연결하는 최소 작성·검토 흐름이며 AI 즉시 Template 확정은 금지한다. 04 CONFIRM_APPLICATION_TEMPLATE와 기존 Guard를 사용하고 Template 생성·화면 상세는 후속 구현에서 구체화한다.

## 7. Company Document / Fact Extraction

사업자등록증/재무제표/공장·기업 증빙/기타 Upload를 CompanyIntake/Company·Site 및 해당 FileAsset으로 고정한다. Classification → Extraction → FactCandidate/Evidence/Location → 기존 Fact 비교 → DATCO Human Review 순서다. 출력은 CompanyFactVersion이 아닌 후보이며 기존 Confirmed Fact/Master를 직접 Update하지 않는다.

Fact Meaning, Value, Period/As-of Date, Unit, Source/Location, Quality/Confidence, Candidate를 표현한다. 전체 Fact Taxonomy는 설계하지 않으며 첫 Slice에서 필요한 항목을 명시한다. 재무값은 금액+연도/기간+단위를 함께 검증한다. 연도/기간/단위/Company·Site가 다르면 같은 Fact의 충돌로 단정하거나 값만 합치지 않는다.

예: 기존 2025년 매출 50억, 새 문서 같은 맥락 53억이면 자동 덮어쓰기 없이 FactConflict/FactReview에 양쪽 Version/후보/근거를 보존한다. 동일값이면 CONFIRM_EXISTING_FACT_VALUE로 기존 Version 참조, 새 확인값은 CONFIRM_NEW_FACT_VALUE로 새 Version, 충돌은 RECORD_FACT_CONFLICT, 부족정보는 REQUEST_FACT_INFORMATION, 거절은 REJECT_FACT_CANDIDATE다. 04의 CONFIRM_NEW_VALUE/CONFIRM_EXISTING_VALUE/CONFLICT/REQUEST_MORE_INFORMATION/REJECT_CANDIDATE 의미를 재사용한다.

기업 EDITOR는 자기 자료/정보를 제공하고 OPERATOR가 검토·확정한다. 기업 제공이라는 이유만으로 공식성/정확성/Confirmed 상태를 부여하지 않는다. 공통 AnalysisCandidate에서 FactCandidate로 매핑한 관계도 보존한다.

## 8. Improvement / Missing Information / Capability

Improvement는 Submitted ImprovementVersion + 관련 Confirmed CompanyFactVersion + 첨부 FileAsset을 입력으로 Current State, Problem, Root/Impact, Improvement Goal, Support Task, Required Function, Missing Information을 구조화한다. 각 주장과 추론에 근거/불확실성을 연결한다. 기업의 개선요구와 DATCO 최종 수행범위를 자동 동일시하지 않는다.

REGISTER_IMPROVEMENT_CANDIDATE로 검토대상을 연결하고 OPERATOR가 CONFIRM_IMPROVEMENT 또는 REQUEST_IMPROVEMENT_REVISION 등 04 Action으로 판단한다. Confirmed 입력·AnalysisReview/결과 관계를 유지하고 변경된 내용은 새 Version으로 보존한다.

Missing Information 후보는 필요한 항목/이유/검토한 Source/부족 범위와 후속업무 Blocking 여부의 근거를 표현한다. 매출연도/공정범위/설비수량/자격근거 미확인 등을 Request Draft 검토 입력으로 제공할 수 있다. 자동으로 기업 메시지/Information Request를 발송하지 않는다. DATCO 검토 → 요청 작성 → SEND_INFORMATION_REQUEST로 04/05의 Actor/항목/기한/Scope를 검사한다.

Capability Assessment는 Confirmed ImprovementVersion + CapabilityVersion의 과제별 평가다. Solvable Problem/Function/Applicable Condition/Exclusion/Prerequisite/Scope를 근거로 FIT/PARTIAL_FIT/NEED_MORE_INFO/MISMATCH 후보와 Reason/Evidence를 만든다. CapabilityAssessment/AnalysisReview에서 REVIEW_CAPABILITY_ASSESSMENT로 확인·보완한다. Catalog 내용/Version은 기업별 적합성 결과로 바꾸지 않으며 Catalog 관리는 ADMIN의 별도 PUBLISH_CAPABILITY_VERSION 책임이다.

## 9. 3-way Matching / Rule / 업무판정

Company FactVersion(s) + Confirmed ImprovementVersion + Reviewed CapabilityVersion/Assessment + Confirmed NoticeRequirementVersion을 **MatchInputSnapshot/MatchInputReference**로 고정한다. 기업·과제 × DATCO Capability × 정부지원사업의 관계이며 단순 MES/QMS Label이나 자연어 유사도로 확정하지 않는다. 각 입력은 당시 확인·검토·현재 사용가능 여부를 검사한다.

Candidate에는 Eligibility, Task Fit, Service Fit, Missing Information, Conflict/Opposing Evidence를 포함한다. 분석 의미 FIT/PARTIAL_FIT/NEED_MORE_INFO/MISMATCH와 사람 REVIEW_MATCH의 PROPOSABLE/REQUEST_MORE_INFO/HOLD/EXCLUDE는 별개다. FIT는 제안·Approval·Proceed·Case 자동 Gate가 아니다.

| 판단 요소 | 최소 원칙 |
| --- | --- |
| Hard Eligibility | 명시 공식조건과 해당 기간/기준일·단위의 확인된 Fact 비교. FAIL/PASS/UNKNOWN 의미 후보를 구분 |
| 숫자/날짜/포함·제외 | 명확히 구조화·확인된 조건은 작은 Deterministic Comparison으로 검증 |
| Semantic Task/Service Fit | 서술·문맥·서비스 범위는 모델 또는 규칙의 후보/근거로 제시 |
| 정보부족 | UNKNOWN을 FAIL로 바꾸지 않고 NEED_MORE_INFO/추가자료 후보 |
| 반대근거 | 제외조건/충돌 Fact/근거부족/Opposing Evidence를 적합근거와 함께 보존 |

예: 기준일의 업력 7년 이하가 필수이고 확인된 기업 업력이 10년이면 Hard Eligibility Conflict다. Semantic Fit이 높아도 해당 제약을 점수로 상쇄하지 않는다. 적용 기준일/예외·유예조건이 불명확하면 확정 FAIL 대신 검토 대상으로 남긴다. 첫 기본판정은 명시 Hard Conflict → MISMATCH 후보, 필수 근거 부족 → NEED_MORE_INFO 후보, 확인된 충족/적합 → FIT 또는 제한범위 PARTIAL_FIT 후보다. 상세 점수공식은 필수로 만들지 않는다.

범용 Rule DSL/Engine을 만들지 않고 확인된 조건의 명시 비교와 문맥 분석을 구분한다. Candidate 검증·사람 Review는 둘 다 필요하다. OPERATOR는 반대근거/미해결 Blocking 정보와 현재 Version/Impact를 확인하고 04 G-PROPOSABLE/G-NO-INFO 등 기존 Gate를 적용한다. 검증된 Hard Conflict를 AI 이유문장/유사도만으로 무시하지 않는다.

## 10. Change Impact / Human Review 계약

NoticeVersion/CompanyFactVersion/CapabilityVersion/ProposalVersion 중요변경 전후와 명시 Lineage를 따라 실제 사용한 Match/Proposal/Approval/Package/Case/Task를 영향 후보로 연결한다. NO_ACTION/REANALYSIS_REQUIRED/RE_REVIEW_REQUIRED/REAPPROVAL_REQUIRED/TASK_REQUIRED는 후보 조치 의미다. 새 업무 State/Role을 만들지 않는다.

Domain의 적용 Version 불일치/Blocking Guard는 모델 실행 여부와 별개로 검사한다. 최소 Lineage/현재성 보류는 초기 구현부터 지키고 고급 AI 영향분석은 후속 확장할 수 있다. 영향 없는 객체까지 모두 자동 무효화하거나 과거 결정/제출기록을 덮어쓰지 않는다.

OPERATOR가 04 CREATE_IMPACT_ASSESSMENT/RESOLVE_IMPACT_REVIEW로 대상별 근거·조치를 판단하고 실제 새 Run/Review/Approval/Task 완료를 REGISTER_IMPACT_FOLLOWUP으로 연결한다. 검토 RESOLVED ≠ 후속조치 완료다. 재분석/재검토 같은 복구 Action에는 해결하려는 Target 자체의 선행 완료를 요구하지 않지만 현재 후속조치 대상/입력과 다른 선행제약을 검사한다.

Human Review에 필요한 최소 정보는 Candidate 의미/입력 Version/Source/Location/Evidence/Reason, Quality/Confidence, Missing/Conflict/Opposing Evidence, 기존 Confirmed 값/Version과 현재성이다. 08은 이 정보를 화면으로 연결하고 여기서는 Layout을 정하지 않는다.

공통 AnalysisReview는 04의 CONFIRM/REQUEST_MORE_INFORMATION/REQUEST_REVISION/REJECT를 사용한다. FactReview/MatchReview/CapabilityAssessment는 각각 기존 Outcome/State를 따른다. 새로운 일괄 Review State를 만들지 않는다. Human은 확인할 수 있는 항목만 확정하고 부족·거절·보완을 기록한다. 대상 Version/Scope/State/공식근거가 맞는지 Backend에서 재검사하며 Human 확인도 Guard를 우회하지 않는다. Review Actor/시각/대상 후보·입력·결과/이유를 Audit 가능하게 보존한다.

## 11. Partial / Failure / Retry / Idempotency

Metadata/HTML은 있지만 PDF 확보가 실패했다면 사용한 근거/미확정 항목/Missing Source를 표시한다. 목적에 충분한 일부 근거로 제한 후보는 만들 수 있으나 전체 분석·전체 Confirmed라고 표시하지 않는다. 파일 미지원·암호화·손상·빈 추출은 안전한 Failure/Partial 사유와 Manual Review/추가자료 경로로 분리한다.

| 실행 상황 | 처리 |
| --- | --- |
| 일부 자료/항목만 유효 | PARTIAL, 유효 후보범위와 실패·누락 명시; 부분 Review도 확인범위 제한 |
| 모든 필수 추출 실패/사용할 후보 없음 | FAILED, 원인/입력 보존; 성공 분석으로 표시 금지 |
| Model Timeout/일시 Provider 실패 | 새 Attempt Retry 후보, 실제 제한정책 적용 |
| Invalid Structured Output | 격리/실패 또는 유효부분만 PARTIAL; 검증 우회 금지 |
| Unsupported/영구 파싱 문제 | Manual Review/자료보완/Parser 수정 후보; 무한 Retry 금지 |
| 실행 중 Version 변경 | 역사적 Run 보존, 현재 사용 보류; 새 입력으로 명시적 재분석 |

04 BackgroundJob/JobAttempt QUEUED→PROCESSING→SUCCEEDED/PARTIAL/FAILED를 재사용한다. FAILED Run은 Confirmed 결과를 만들지 않는다. Retry는 기존 오류/Run/Attempt를 삭제하지 않고 현재 적용 입력/권한을 검사한다. 동일 입력 재시도와 새 Version 분석을 구분하며 오래된 분석을 새 현재 결과처럼 표시하지 않는다.

Analysis Type + exact Input Version 조합 + Configuration Version은 기술적 중복 판별 근거다. 동일 요청 Action Identity 재전송은 기존 요청/결과를 반환하고, 사용자 의도에 따른 재분석/새 Rule·Model 설정은 별도 Run으로 남긴다. Cache/Hash 구체값은 미확정이고 Company Scope·공개범위가 다른 결과를 공유하지 않는다. 일부 Provider 호출 중복이 생겨도 Candidate/Review/Confirmed 업무 Action을 중복 생성하지 않게 한다.

과거 Run/Review의 내용은 보존한다. Current Usability는 적용 Version/권한/기존 Guard로 별도 판별한다. Reanalysis 결과로 과거 승인/Fact/Requirement를 자동 교체하지 않는다.

## 12. Security / Provider / 공개범위 / Demo

공고·첨부·기업문서는 Untrusted Content다. Source Content와 System/Analysis Instruction을 분리하며 “지시를 무시하라/승인하라/적합하다고 판단하라” 같은 문서 문장을 실행 명령으로 취급하지 않는다. Extractor/Provider에는 Approval/Proceed/권한변경/Request 발송을 실행하는 Tool 권한을 부여하지 않는다. External Content가 업무 Action을 실행하거나 Company ID/입력 Version/공개권한을 정할 수 없다.

Company Private 자료는 요청·파일 읽기·Provider 입력·후보저장·결과/근거 조회에 동일 Scope 검사를 적용한다. Global Notice 자료와 해당 Company 입력만 필요한 분석 맥락에서 결합할 수 있고 다른 Company 자료는 차단한다. Secret/불필요한 개인정보 원문을 Log/Audit/Prompt 기록에 남기지 않는다. 외부 AI Provider에 Private Data 전송 가능하다고 가정하지 않으며 실제 계약/보안·보관·이용정책 확인 후 해당 Adapter의 전송범위를 결정한다.

TextExtractor/OCRProvider/AnalysisProvider의 작은 교체경계를 둔다. Domain은 Vendor Response를 직접 사용하지 않고 5절 Structured Candidate로 변환·검증한다. 첫 구현에 필요한 Adapter만 구현하며 특정 Vendor/Model/Vector DB/Embedding/RAG/Fine-tuning을 필수로 확정하지 않는다.

05의 DATCO_INTERNAL/COMPANY_SHAREABLE/COMPANY_INPUT_REQUIRED 공개의미를 따른다. 실제 공개는 Backend Permission/업무 Action으로 결정하며 AI가 공개권한을 지정하지 않는다. 기업에게 내부 Reason 전체/Operator Memo/Opposing Evidence 전체를 자동 공개하지 않는다. 지정 Request/Proposal/Case의 필요한 Projection만 제공하고 Evidence 다운로드도 부모/파일 Scope를 검사한다. Chain-of-Thought는 저장·노출 대상이 아니다.

Demo는 실제 구조·의미가 있는 Sanitized Notice/Company 자료를 Input Contract로 통과시킨다. 외부 Provider 장애 시 Fixture Adapter의 재현 후보출력을 공통 Validation/Run/Domain 검토 경로로 연결할 수 있지만 완성 Candidate/Confirmed 값을 DB에 직접 주입하는 별도 우회경로를 기본으로 하지 않는다. Fixture 사용 Mode/설정·입력/한계를 표시하고 사람 검토·Guard를 유지한다. 현재 Probe 마스킹 Sample은 구조검증용이고 의미분석/E2E Fixture 충분성을 증명하지 않는다.

## 13. Test Matrix A~Z

아래는 구현 후 실행할 기준이다. 이번 작업에서 AI API/OCR/기업마당 호출 또는 구현 Test를 수행한 뜻이 아니다. Unit/Fixture, Parser/Extraction, Structured Output Validation, Provider Adapter Integration, E2E Human Review를 분리한다. 모든 Test에서 외부 AI를 호출하거나 같은 자연어 출력문장을 요구하지 않는다. Schema/Evidence/Version/Guard/후보·확정 분리/실패처리를 검증한다.

| Test | 입력 / 유형 | 기대결과 |
| --- | --- | --- |
| A Notice Metadata만 | Fixture | Source 범위 제한 후보, 완전분석 표시 없음 |
| B Notice + HTML | Extraction Fixture | 실제 본문/절 위치와 후보 연결 |
| C Notice + PDF | Extraction Fixture | Page/Content 근거 연결 |
| D 첨부 실패 Partial | 실패 주입 | 누락 Source/미확정 항목/PARTIAL |
| E 기간 API/PDF 일치 | Fixture | 양쪽 근거 보존/일관 후보 |
| F 기간 Conflict | Fixture | 자동 덮어쓰기 없음/Review 필요 |
| G Required Document | 의미검증 Fixture | 조건부 여부/서식 근거/후보 분리 |
| H 근거 없는 후보 | 잘못된 출력 주입 | 격리/미확인, 확정 사용 차단 |
| I Fact 정상 추출 | Company Fixture | FactCandidate, Master 자동수정 없음 |
| J 기존 Fact 동일값 | 같은 기간/단위 Fixture | Review 후 기존 Version 연결 |
| K Fact Conflict | 상충값 Fixture | 양쪽 후보/근거 보존 |
| L 재무 연도/단위 | 다중기간·단위 Fixture | 값만 비교/합산 금지 |
| M Improvement | 제출 과제 Fixture | 문제/목표/기능과 근거 |
| N Missing Information | 부족자료 Fixture | Unknown 유지/Request 후보, 자동 발송 없음 |
| O Capability FIT | 조건충족 Fixture | 적합 후보, Catalog 변경 없음 |
| P Capability MISMATCH | 제외조건 Fixture | 불일치 근거 보존 |
| Q 3-way FIT | 확인된 입력 Fixture | 정확한 Snapshot, 자동 PROPOSABLE 없음 |
| R Hard Eligibility Conflict | 높은 Semantic Fit+명시 위반 | Hard 제약 상쇄 금지 |
| S NEED_MORE_INFO | 필수 Fact 부재 | Missing을 FAIL로 단정하지 않음 |
| T Opposing Evidence | 적합·반대근거 혼합 | 반대근거 삭제/누락 금지 |
| U Stale Input | 실행 중 새 Version | 과거 Run 유지/현재 결과 사용 차단 |
| V Failure / Retry | Timeout/Invalid output 주입 | 오류·Attempt 보존/확정 없음 |
| W Cross-company | 타기업 File/후보 ID | 입력·출력·조회 차단 |
| X Prompt Injection | 명령문 포함 자료 | 업무 Action/권한변경 실행 없음 |
| Y Human Confirm 없음 | Candidate 생성 성공 | Confirmed/Approval/Proceed 자동생성 없음 |
| Z Change Impact | 변경+Lineage Fixture | 후보→Human Review→실제 후속조치 연결 |

Provider Integration은 실제 계약·보안 범위에서 제한적으로 수행하고 Parser 정확도·표/Scan 처리·Reason의 Source 일치도는 의미검증 Fixture와 사람이 확인한다. 높은 Confidence나 Schema 통과만으로 정확도 통과를 선언하지 않는다.

## 14. 정합성 Validation A~Z / Model 영향

문서상 정합성 검토이며 실제 실행 검증은 13절 Test로 수행한다.

| 검증 | 문서 근거 | 결과 |
| --- | --- | --- |
| A Collector/Intelligence 경계 | 2절 Source 확보/추출 분리 | 충족 |
| B File 확보/추출 구분 | 4절 처리/Quality | 충족 |
| C Candidate/Confirmed 분리 | 1/10절 Human Gate | 충족 |
| D 정확한 Input Version | 3절/AnalysisInputReference | 충족 |
| E Evidence/Location 연결 | 5절 유효성/원문 검토 | 충족 |
| F Confidence 자동확정 아님 | 5절 검토 보조 의미 | 충족 |
| G Confidence/Fit 분리 | 5/9절 별도 의미 | 충족 |
| H API Metadata 활용 | 6절 Source 입력 | 충족 |
| I API/PDF Conflict 유지 | 6절 기간/원천 보존 | 충족 |
| J Requirement Human 확인 | CONFIRM_NOTICE_REQUIREMENT | 충족 |
| K 파일명만 역할 확정 금지 | 4/6절 Content 분류 | 충족 |
| L Fact 자동수정 금지 | 7절 후보/Review/Version | 충족 |
| M Fact Conflict 보존 | 7절 기존/신규 근거 | 충족 |
| N 재무 기간/단위 | 7절 비교 맥락 | 충족 |
| O Improvement 근거 | 8절 제출본/Fact/File | 충족 |
| P Missing→Request 후보 | DATCO 검토/발송 Action | 충족 |
| Q Catalog/Assessment 분리 | 8절 관리/과제평가 분리 | 충족 |
| R MatchInputSnapshot | 9절 고정 Version 조합 | 충족 |
| S FIT/PROPOSABLE 분리 | 분석 후보/REVIEW_MATCH | 충족 |
| T Hard Eligibility Conflict | 9절 구조조건/기준일 검사 | 충족 |
| U Opposing Evidence 보존 | 5/9절 반대근거 | 충족 |
| V Partial 완전분석 금지 | 11절 범위 표시 | 충족 |
| W Failed 확정 금지 | 11절 Job/Review 분리 | 충족 |
| X Cross-company 차단 | 3/12절 전체 처리 Scope | 충족 |
| Y Prompt Injection 실행 금지 | 12절 지시/Content/권한 분리 | 충족 |
| Z 실제 구현 전환 | 16절 첫 Slice/Stack 전환 | 가능 |

상위문서와 충돌은 발견하지 않았다. **Data Model Change Candidate: 없음.** 공통 Run/Candidate/Review와 기존 Domain typed 관계로 표현하며 처리 의미/논리 Contract 이름은 새로운 Entity/State 추가가 아니다.

## 15. Open Decision

| ID | 미확정 | 최소 출발점 / 후속 확인 |
| --- | --- | --- |
| OD-01 | AI Provider | 교체 Adapter, Private Data 계약/보안 확인 후 선택 |
| OD-02 | Model | 타입별 검증 가능한 출력/품질 기준으로 선정 |
| OD-03 | OCR Provider | Scan/텍스트부족 분기, 실제 필요 시 구현 |
| OD-04 | PDF Extraction Library | 첫 의미있는 PDF Fixture로 추출/위치 검증 |
| OD-05 | HWP/HWPX | 미지원/Manual Review 유지, 요구 확인 후 확장 |
| OD-06 | Image OCR | 기업자료 Fixture/필요범위로 검증 |
| OD-07 | Embedding/Vector Search 필요 | 현재 필수 아님, 실제 검색 필요 확인 |
| OD-08 | Prompt 전문 | 타입별 최소 Structured Output 계약부터 작성 |
| OD-09 | Confidence 계산법 | 검토보조만 사용, 자동확정 금지 |
| OD-10 | Model 비용/Timeout 수치 | 관측/실행제한 필요, 측정 후 설정 |
| OD-11 | Provider Retry 수치 | Failure 분류/Attempt 보존, 실제 정책 확인 |
| OD-12 | HTML Selector | 실제 확보본문 Fixture로 공통 UI/본문 분리 |
| OD-13 | 복잡한 Table Extraction | 누락/단위/기간 표시, 검증된 범위부터 |
| OD-14 | Company Fact Taxonomy 전체 | 첫 Slice 필수항목 명시, 전체 목록 확장 후속 |
| OD-15 | Advanced Matching Score | Hard 조건/누락/근거 우선, 고급공식 필수 아님 |

Provider/Library/수치 선택은 해당 실행 구현 전에 필요한 선택이다. Core 계약의 Blocker로 남겨 설계를 계속 확대하지 않는다. Evidence/Location/Version/Human Review/Scope/Missing·Conflict/Confidence·Fit 분리는 이미 확정된 최소 경계다.

## 16. Implementation Readiness / 개발 전환

아래 READY는 **해당 Intelligence 기능의 최소 구현설계가 준비됨**을 뜻하며, 지금 즉시 전체 애플리케이션 개발을 시작한다는 의미가 아니다. 기능 완성/정확도 검증/Provider 계약 승인/운영배포 완료도 아니다. 프로젝트 전체 개발 착수는 08~10 완료 후 최종 판단하며, Stack·Adapter·Library 선택과 실제 Fixture 검증은 그 이후 구현 과정에서 수행한다.

| 기능 | 판단 | 구현 출발점 / 남은 확인 |
| --- | --- | --- |
| Notice Intelligence | READY | HTML/PDF→근거있는 Requirement 후보→Human Review. Selector/Library/실제 추출 충분성 확인 |
| Company Fact Extraction | READY | Company Input/FactCandidate/Conflict/Review 계약. 첫 Fact 항목·자료/추출 품질 확인 |
| Improvement Analysis | READY | Submitted 입력/근거/부족정보/확정 경계. 타입별 Rule/Prompt 의미검증 |
| Capability Assessment | READY | Catalog와 과제평가 분리/조건·범위 근거. 실제 Catalog·과제 Fixture 확인 |
| 3-way Matching | READY | 고정 Snapshot/Hard 조건/정보부족/FIT와 Review 분리. 실제 필수 Fact·지원조건 비교 검증 |

첫 Vertical Slice는 Phase 1: Notice HTML/PDF Text Extraction → Requirement Candidate → Evidence/Source Location → DATCO Human Review → Confirmed Notice Requirement다. Phase 2에서 Company Fact 후보/Review와 Improvement, Phase 3에서 Capability Assessment/3-way Matching/MatchReview를 연결한다. 고급 Impact 분석·Format/OCR은 이후 확장하되 초기에도 Version 현재성/Lineage/Blocking Guard를 지킨다. 이는 개발 시 구현순서이며 08~10 문서를 건너뛰라는 의미가 아니다.

개발 전환 순서는 07_INTELLIGENCE_DESIGN 완료 → 08_SCREEN_ACTION_SPEC → 09_DEMO_SCENARIO → 10_TEST_ACCEPTANCE → 00~10 설계 Baseline 확정 → 기술 Stack 결정 → Repository / Application Skeleton → 첫 Vertical Slice 실제 구현 → 통합 Test / Demo다.

08~10은 기존 후속문서 책임을 구체화하여 개발범위를 닫는 실행계약이며 새로운 Architecture 재설계나 과도한 대형 문서로 확장하지 않는다. 08_SCREEN_ACTION_SPEC은 실제 화면/Screen Group·표시 데이터·Action/Button·Visibility/Disabled Reason·Backend Action 연결, 09_DEMO_SCENARIO는 1차 Standalone E2E 시연범위·Demo/Seed/Snapshot Fixture·정상/핵심 예외 시나리오, 10_TEST_ACCEPTANCE는 정상/예외/권한/Version/Evidence/Persistence의 실행 Test와 구현 완료 Acceptance 기준을 다룬다.

**현재 00~07 기준으로 08_SCREEN_ACTION_SPEC 설계 착수: READY.** Intelligence 각 기능은 최소 구현 착수 수준으로 설계되었으나, 프로젝트 전체 애플리케이션 개발 착수는 08_SCREEN_ACTION_SPEC, 09_DEMO_SCENARIO, 10_TEST_ACCEPTANCE 완료 후 최종 판단한다. 다음 작업은 **docs/08_SCREEN_ACTION_SPEC.md 신규 설계**다. 이 문서는 Stack 선택이나 구현을 실제 수행하지 않는다.

## Decision-004 실행 계보와 자동화 설계 경계

공통 Run/Candidate/Review를 CapabilityAssessment 및 SupportMatching에 실제 typed 관계로 연결한다. 동기 평가에는 Job/Notice SourceLocation을 강제하지 않으며 실제 입력/설정/실행 Actor·시각·후보/Evidence와 검토를 고정한다. Assessment는 ImprovementVersion × CapabilityVersion이고 실제 조합에 귀속할 때만 CompositionVersion을 연결한다. 재평가·새 매칭 실행은 새 Run/후보이며 기존 검토를 보존한다. 공통 Review 유형은 업무 outcome을 위장하거나 대체하지 않는다. Notice 분기의 기존 공식 Source/Evidence/Review/Version 조건은 유지한다.

Decision-004의 R-07 승인은 상세설계만이다. 기존 IN/NOT_IN Comparator와 Confirmed 입력/UNKNOWN/MISMATCH 후보·Human Review Guard는 유지한다. 자동 증빙 추출/범용 조건 정규화/AST/지역 계층/숫자·기간·예외 평가는 reviews/R07_REVIEWED_CONDITION_DESIGN.md의 제안이며 운영용 구현 완료로 보지 않는다. 자동 추출 후보는 Confirmed Fact/ReviewedConditionVersion이 아니다. 필수 공식 Human Review는 자동 정합성 검사로 제거하지 않는다. 연구원 Company/Fact/Improvement Provider 미연결 시 정상 503을 유지한다.


## W1 승인된 구현 증분 — 2026-10-19 / Decision-006

기존 로컬 파서를 재사용해 PDF 페이지/DOCX 문단/XLSX 셀/TXT 줄의 원문을 보존한다. 명시된 기업명/업종/소재지/대표자/사업자번호 라벨에서만 RULE_BASED_EXTRACTION 후보를 생성한다. 재무 연도·수치·단위·기간 및 비정형 의미를 추정하지 않는다. 나머지는 실제 원문 근거에 사람이 후보를 작성하고 검토한다. 스캔·이미지는 원본 저장과 수동 전사 근거를 제공하며 OCR/이미지 의미분석 완료로 표시하지 않는다.

공통 COMPANY_FACT_EXTRACTION 계보 증분은 사용자 명시 승인 범위다. 승인 기록은 reviews/W1_COMMON_LINEAGE_APPROVAL_REQUEST.md. Company Provider는 현재 확정 FactVersion/Review/Evidence와 exact ImprovementVersion/Site ordinal을 읽는다. 기존 Capability/Matching/Proposal 소비에 연결하지만 Guard를 우회하지 않는다. 기간·단위가 필요한 재무/인원/이력은 기존 문자열 IN/NOT_IN 비교에 자동 전달하지 않는다. 범용 공고 조건 해석·추천 엔진은 미구현이며 조건 미확인은 UNKNOWN으로 남긴다. 외부 AI 전송 승인 없음: W1_AI_SEMANTIC_ANALYSIS=BLOCKED_BY_POLICY.


## PR14 최초 기업등록·로컬 한글 OCR 승인 증분 — 2026-10-21

사용자는 PR14의 C02/C03 서류 우선 최초 등록, 직접 입력, 실제 한글 OCR, 사용자 확인/수정, 사업자번호 정규화·체크디지트 및 기존 Company 등록/원본/Evidence 보존을 명시 지시했다. 과거 W1의 OCR 미승인 기록은 당시 범위로 보존하며, 이번 증분은 로컬 Tesseract/PDFium Adapter에 한정한다. 외부 OCR/AI 전송은 승인하지 않았다. 상세 영향은 reviews/PR14_INITIAL_REGISTRATION_OCR.md.

등록 전에는 기존 COMPANY_EDITOR 등록 권한으로 원문을 메모리 분석하며 Company/영속 File/공유 토큰을 만들지 않는다. 최종 사용자 확인 후 기존 Company/Membership Guard와 Private 파일/불변 Evidence를 재사용한다. 여러 서버 명령의 부분 실패는 회사 생성/문서 보존/추출 완료를 분리해 표시한다. 기업 ACK와 최종 Fact 확정은 계속 분리한다. DB Schema/Migration/Role/업무 State/Approval Guard/Assignment는 변경하지 않는다. 기존 저장 사업자번호나 과거 Version을 소급 수정하지 않는다. 실사용 인수는 PENDING이다.

PR14 사용자 검수 v1.2에서는 후보별 선택 UI를 단일 수정폼으로 바꾸고 기업정보 등록 클릭을 기업의 최종 입력 확인으로 기록한다. 기존 Fact 확정 권한은 유지한다. 업태/종목 라벨별 값을 기존 industry 문자열에 구분 보존하며, 표 보완 OCR은 동일 로컬 Adapter의 제한된 보조 읽기로 원문/근거를 추가한다. 원문과 불명확한 필드를 임의 확정하지 않는다. 세부 저장/실패/미지원 항목은 reviews/PR14_INITIAL_REGISTRATION_OCR.md의 v1.2 증분을 따른다.


## Slice 2 승인된 로컬 분석·영속 요청 초안 — 2026-10-28

규칙 기반 1차 분석 R01~R08은 명시된 입력·라벨·적용조건에만 동작한다. 숫자·원인·기간·업종별 필수사항을 만들지 않는다. 충돌은 같은 명시적 비교 맥락의 라벨 값으로 제한한다. 미추출·미지원·미검사 자료는 처리 한계이며 정보부족 확정이 아니다. 외부 AI Provider는 연결하지 않는다. File digest·정확한 Parse/Parser·원문 위치·검사 범위·Rule Version을 보존하고 기존 추출을 재사용한다.

PR #16 검토 보완: `improvement-rules-v2`는 Rule별 적용 근거와 발견 근거를 먼저 검증한다. 답변이 발견되면 미검사 파일과 무관하게 중복 질문을 만들지 않는다. 미확인 항목은 검사 범위·제외 사유를 동반한 부족정보 후보 또는 `PROCESSING_LIMITATION`의 `NEEDS_SOURCE_REVIEW` 분석 표시로 구분한다. 이는 업무 State 추가가 아니다. 관련성을 알 수 없는 미검사 자료는 보수적으로 불확실성에 남기며 파일명으로 주제를 추정하지 않는다. 운영자가 사유를 기록해 제외한 공통자료는 검사 범위 밖이며 일괄 차단·보완 질문 대상이 아니다. 직접 첨부자료는 제외해도 원문 미검사 불확실성을 유지한다.

과거 Parse는 성공 여부만으로 재사용하지 않는다. 범용 `company-local-parser-v1`만 재사용 후보로 삼고 동일 File/digest 원문을 로컬 native reader로 다시 읽어 모든 위치·텍스트·제한사항을 대조한다. 불일치·용도 전용 Parse·OCR 미처리 페이지는 승인된 로컬 추출로 다시 처리한다. OCR/특수 Parser는 현재 재사용 allowlist에 없다. 새 검사에는 실제 Parse/Parser/digest, 추출 목적, 재사용 검증 결과와 위치·한계를 보존한다. COMPLETE는 추출 가능한 텍스트 범위이며 문서의 의미·표·도면 전체를 검사했다는 뜻이 아니다.


## Slice 2 운영자 UX·제출본 검토 이력 — 2026-10-28

submitted-review-v1 입력 정책: 공통자료는 기본 NOT_SELECTED, 직접 근거는 포함, 명시 제외는 이유 검증. NOT_SELECTED와 EXCLUDED를 구분하며 과거 Manifest를 덮어쓰지 않는다. 실제 운영자의 상세 진입에서 보호된 ENSURE POST로 동일 입력 Job/Run을 재사용하고 실패는 명시적 retry로 처리한다. GET/SUBMIT 쓰기 및 외부 AI는 없다. Rule R01~R08 범위는 유지한다.

상세 계약·변경 영향·실행 검증 구분: [운영자 UX 구현 보고](reviews/SLICE2_OPERATOR_UX_REPORT.md).
