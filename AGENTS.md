# DATCO 정부지원사업 운영체계 - 개발 행동규칙

## 1. 기준문서와 작업 전 확인

AGENTS.md는 사람 개발자와 Codex가 공통으로 따르는 영구적인 개발 행동규칙이다.
작업 시작 전 실제 Project/Git Root, Current Branch, git status와 파일 존재 여부를 확인하고, 이 파일 → docs/00_PROJECT_BASELINE.md → docs/01_SYSTEM_ARCHITECTURE.md 및 관련 설계문서 순으로 읽는다.
기준문서는 일시적인 채팅 지시보다 우선한다. 사용자가 명시적으로 기준 변경을 승인하면 기준문서를 먼저 또는 함께 갱신한다.
없는 문서/구현은 있다고 가정하지 않는다. 필요한 기준이 없으면 `기준 미확정` 또는 `의사결정 필요`로 보고한다.
제품 목표와 기능은 Project Baseline, 구조와 Module 책임은 System Architecture, 상세 Flow/Data/State/Permission/Collector/Intelligence/UI/Demo/Test는 해당 후속 문서를 참조한다.

## 2. 충돌과 공통 변경 통제

요구사항, 문서, 코드가 충돌하거나 불명확하면 추측하여 구현하지 않는다. 코드만을 기준으로 판단하지 않고 충돌사항, 원인, 영향범위, 선택지를 먼저 보고한다.
시스템 경계, 핵심 Domain Entity, State Machine, Role/Permission, E2E Flow, 외부 역할, DMP Adapter 전략, Demo Acceptance, Source of Truth, API/Integration Contract는 PM의 명시적 결정 없이 바꾸지 않는다.
DB Schema, Common Types, Shared, Contracts, Auth, Workflow, Architecture 및 다른 Module의 구조 변경은 실행 전에 영향범위를 보고한다.
확인되지 않은 외부 시스템/API 구조와 미확정 Stack을 가정하여 계약 확정이나 대규모 초기화를 하지 않는다.

## 3. 제품 방향과 Module 경계 보호

기업마당 API Collector 개발과 운영관리 시스템 연동은 필수범위다. Collector → Notice/NoticeVersion → Intelligence → Operations Web 연결을 유지하고 같은 공고를 각 Module에서 중복수집하지 않는다.
실제 API 문서/응답을 구현 전에 확인하며 API 정보가 충분한 영역을 불필요하게 Crawling하지 않는다.
1차 Standalone E2E Web과 장기 DMP 전환 목표를 유지한다. Modular Monolith를 우선하고 Collector, Intelligence, Operations, Integration, Shared/Core의 논리적 경계를 지킨다.
Domain은 외부 API/특정 저장소에 직접 고착시키지 않는다. Local/Demo Provider는 향후 DMP Adapter로 교체 가능하게 하며 실제 DMP 계약 확인 전 가짜 Contract를 확정하지 않는다.
공식 정부포털을 재구현하지 않는다. 실제 제출은 DATCO 직원이 외부 포털에서 수행하고, 필수 공식증빙 없이 최종 신청완료 처리하지 않는다.
Collector 세부구성, Dynamic Application/Package, Matching, Case Life Cycle는 Baseline과 Architecture를 참조한다.

## 4. 범용성과 기업 하드코딩 금지

동아테크놀로지는 대표 Demo 기업이며 전용 시스템을 만들지 않는다. 확인되지 않은 정보는 DEMO/SEED로 표시한다.
기업명/ID/업종/Site/조건, Support Program, DATCO Service, Workflow, Permission, UI Logic을 특정 기업에 고정하지 않는다.
다른 제조기업/비제조기업도 같은 Domain Model과 Flow를 사용해야 한다. 범용성 검증 범위는 Baseline을 따른다.

## 5. 분석과 사람 검토

AI/LLM/OCR/Rule/Extraction 결과는 최종 사실이나 업무판정이 아니다. Input → Candidate → Reason/Evidence → Human Review → Confirm을 지킨다.
Company Fact, Notice Requirement, Eligibility, Match, Proposal, Approval, Proceed Decision을 사람 확인 없이 자동확정하지 않는다. 입력 Source/Version, 근거, 분석 결과/Version을 추적한다.
기업문서 추출값으로 Company Master/Confirmed Fact를 자동 덮어쓰지 않는다. 충돌값은 보존하고 사람이 판단한다. 자동매핑도 확인을 거친다.

## 6. 권한과 State Guard

Backend/API에서 인증 주체의 Role/Permission, State, Company Scope와 필요한 Case Scope를 검증한다. UI 숨김만으로 보안을 구현하지 않는다.
다른 기업 URL/API/파일에 직접 접근해도 데이터를 볼 수 없어야 한다. 권한 없음은 Action 숨김, 권한 있음/조건 미충족은 Disabled와 불가 사유 표시를 적용한다.
중요 업무객체는 State/Transition을 사용한다. 실행 권한, 현재 상태, 필수 입력/승인/증빙을 검사하며 버튼 클릭이나 임의 Update로 Guard를 우회하지 않는다.
정확한 Role/Permission/상태 정의는 관련 기준문서에서 확정한다.

## 7. Version / Approval / Audit와 변경영향

중요 객체와 승인 대상은 Version/Snapshot으로 추적한다. 과거 데이터, 승인, 상태 이력을 덮어쓰거나 삭제하지 않는다.
승인 후 중요변경은 새 Version으로 만들고 필요 시 Re-review/Reapproval을 수행한다. 이전 승인이 새 Version을 자동 승인하지 않는다.
누가 언제 어떤 Version을 어떻게 변경/승인했는지 Audit 가능해야 한다. 공고/Fact/Capability/Proposal/사업비 등의 변경이 후속 업무에 미치는 영향을 확인한다.
상세 대상과 변경영향 관계는 Baseline과 Architecture를 따른다.

## 8. Secret / 개인정보와 파괴적 작업

API Key, Password, Token, 실제 .env, 기업 개인정보, 민감 원본문서, 운영 인증정보를 Git에 Commit하지 않는다. API Key를 Frontend/Source/Git에 노출하지 않는다.
.env.example에는 실제 Secret 없이 환경변수 이름만 기록한다. 실제 Private 자료와 Sanitized Demo 자산을 구분한다.
DB Drop, 대량 Delete, Migration Reset, 대량 File Delete, force push, Git History Rewrite, Production Data 변경은 사용자의 명시적 승인 없이 수행하지 않는다.

## 9. 구현과 재사용 절차

기준 확인 → 기존 구현 분석 → 영향범위 확인 → 작은 단위 구현 → 관련 Test → 검증 → 변경내용 보고 순서로 진행한다.
기존 구현은 그대로 재사용, Adapter 연결, 일부 수정 후 재사용, 신규 개발 중 적합한 방법을 먼저 판단한다. 분석 없이 전면 재작성하거나 불필요한 Refactor를 하지 않는다.
승인된 작업범위를 지키며 담당 Module 외 변경을 최소화한다. 없는 파일/문서는 승인된 범위에서만 생성한다.

## 10. 다중 연구원 Git 협업

기능개발은 특별한 지시가 없으면 Feature Branch를 기본으로 하고 main에서 장기간 직접 작업하지 않는다.
Merge Conflict를 무시하거나 다른 사람의 작업을 덮어쓰지 않는다. 공통 변경 통제는 2절을 따른다.
사용자가 명시적으로 요청하지 않으면 git add, git commit, git push, branch merge, force operation을 수행하지 않는다. 개발 절차는 Git 실행 권한을 의미하지 않는다.

## 11. 테스트와 대표 Demo 보호

변경 후 관련 Test를 실행하고 실패를 숨기거나 무시하지 않는다. 1차 완료판단은 기능 숫자가 아니라 실제 E2E Demo 성공이다.
영속성/새로고침, 권한/Scope, State Guard, Version/Approval/Evidence/Audit, 중복수집/변경감지, 오류/Retry와 정상·예외 E2E를 검증한다. 상세 시나리오는 Baseline 및 Demo/Test 문서를 따른다.
Live API를 실제 구현하면서 검증된 Sanitized Snapshot/Seed/Fixture로 장애 시에도 같은 Domain Logic을 통과하도록 한다. 화면만 연결한 Mock Demo로 대체하지 않는다.
새 기능이 대표 Demo를 깨뜨리면 완료로 판단하지 않는다.

## 12. 문서 동기화와 완료 보고

중요 구현결정과 Architecture/State/Permission 변경은 관련 기준문서와 함께 갱신하고 중요한 새 결정은 Decision Log에 기록한다. 코드와 문서의 장기 불일치를 허용하지 않는다.
완료 보고에는 변경 파일, 내용/이유, 관련 기준문서, 실행한 Test와 결과, 남은 Issue/Risk, 필요한 의사결정을 포함한다. 문서상 검토와 실제 실행 테스트를 구분한다.
