# W1 Company 규칙 후보의 R-04 공통 계보 연결 — 승인 요청

상태: APPROVED. 사용자가 “문서에 명시한 공통 계보 증분 구현 승인”으로 명시 승인했다. 최초 자동 승인 검토 거절 이후 이 승인 범위에서 구현한다.

## 현재 구현과 남은 연결

Company 입력·파일·파싱 위치·Fact 후보·기업 사실확인·운영자 FactReview·Improvement·Provider는 W1 모듈에서 구현 중이다. 기존 문서 파서는 재사용한다. 직접 입력/수동 검토와 규칙 기반 후보는 구분하며 실제 AI 호출은 없다.
공통 analysis_runs/candidates/reviews의 기존 CHECK/typed context는 Notice/Capability/SupportMatching만 허용한다. Company 문서를 Notice 입력으로 위장하거나 기존 제약을 제거할 수 없다. 현재 Company의 파싱 기록은 로컬 파서 실행 기록이며 기존 공통 AnalysisRun에 연결됐다고 주장하지 않는다.

## 요청하는 정확한 증분

1. 기존 analysis_candidates에 nullable company_candidate_id FK를 추가한다. CompanyFactCandidate와 exact 공통 Candidate를 연결하며 다른 분석 종류에서는 반드시 NULL이다.
2. 기존 analysis_domain_review_contexts에 nullable company_review_id FK를 추가한다. 기존 Assessment/Match 연결과 합쳐 정확히 하나의 typed 업무 검토만 연결한다.
3. analysis_company_contexts를 추가하여 기존 AnalysisRun → exact Company/File/Parser 실행을 FK로 연결한다. 별도 중복 AnalysisRun 테이블이나 generic target_type JSON을 추가하지 않는다.
4. 기존 공통 CHECK의 Notice/Capability/SupportMatching 분기는 그대로 유지하고, 기준문서에 있는 COMPANY_FACT_EXTRACTION 분기만 추가한다. 이는 분석 종류이며 새로운 업무 State/Role이 아니다.
5. CompanyFactCandidate의 규칙 기반 결과는 exact 공통 Candidate와 양방향 FK로 연결한다. CompanyFactReview는 해당 공통 AnalysisReview와 연결한다. 직접 입력·사람 수동 후보는 자동 분석으로 위장하지 않는다.
6. Company/File/파싱 위치·값·Actor·검토가 맞지 않으면 deferred DB 제약으로 Transaction 전체를 거절한다. 공통 Run/Candidate/Review와 연결 Record의 불변성을 유지한다.
7. 이전 Migration은 수정하지 않는다. 새 Migration으로 적용하고, 데이터가 있는 Down은 거절한다. 적용은 전용 테스트 DB만 허용한다. Notice/Capability/Matching/Proposal/R04 회귀·Migration·API 타입·전체 UI/CI로 검증한다.

## 보호사항

- 기존 Role, FactReview Outcome, Improvement State, PROPOSABLE/Proposal Guard 유지.
- 실제 공용/업무 DB Migration 금지, Private 문서 외부 AI 전송 금지.
- 이전 Version/Review/Evidence/공통 계보 수정·삭제 금지.
- 기존 R04 Snapshot과 Notice 공식 근거 무결성 유지.
- 승인 후 필요한 03/07/10/11 증분을 함께 동기화한다.

## 선택의 영향

승인: 위 범위의 공통 typed 계보 확장·Migration·회귀 검증을 수행한다.
보류: Company 입력/수동 검토·Provider와 자체 원문/후보 근거는 계속 구현·검증하되, Company 자동 후보의 R04 공통 계보 연결은 미완료로 보고한다. 기존 공통 계보를 우회하거나 전체 정합성 PASS로 표시하지 않는다.


## 승인 후 구현·검증

위 typed Company 증분을 f974c0012026에 구현했다. 최종 전체 Backend 308 PASS/1 SKIP, Integration 192 PASS/1 SKIP, 전체 Playwright 23 PASS/1 SKIP, Migration check 및 lint/build/API 타입 비교 PASS. Notice·Capability·Matching·Proposal 회귀를 포함하며 공용 DB 변경 테이블은 0개다. AI 의미분석은 실행하지 않았다.
