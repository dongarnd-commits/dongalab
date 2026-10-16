# Proposal 생성 선행 MatchReview 완료 기준 — 승인 완료

상태: APPROVED — 사용자가 시스템 선행 파악→항목별 확인→저장→단계 승인 및 문서의 항목별 Gate 구현을 명시 승인함. 기존 P-01~P-05 구현 승인을 철회하거나 재요청하는 문서가 아니다. 미확정인 PROPOSABLE 사람 검토 완료 기준만 확정한다.

## 시스템 파악과 사용자 확인의 선행 흐름

사용자 추가 설명: 기업이 제공하는 사업계획서·재무제표·자유입력 및 공고문·공고요건·필수서류를 시스템이 파악하고, 수요기업과 DATCO 사용자에게 확인 요청·저장·다음 단계 승인을 제공해야 한다.

시스템은 확인 후보·Evidence·누락·충돌을 먼저 제시한다. 수요기업은 자기 자료의 사실확인/보완, DATCO는 공고조건과 제공 서비스의 적용 판단을 담당한다. 자동 추출/자료 업로드 자체는 Fact Confirm 또는 PROPOSABLE이 아니다. Proposal 내용 Review와 기업 Approval은 별개다.

이번 P01-P05는 기존 Company/Fact/Improvement 분석·확인 결과를 소비한다. 해당 실제 Provider와 정보요청/보완 도메인의 미구현을 숨기지 않는다. 새 기업문서 추출기나 Phase2 자료보완 전체를 이번 PR에서 임의 구현하지 않는다. 사용자는 추가 승인 질문에서 이 흐름과 문서에 명시한 항목별 Gate 구현을 명시 승인했다.

## 제안하는 최소 규칙

1. DATCO_OPERATOR가 현재 Candidate/InputSnapshot에 대해 직접 REVIEW_MATCH를 수행한다. Candidate 분석값은 수정하지 않고 MatchReview를 새로 기록한다. 자동 PROPOSABLE은 없다.
2. 기업 자격, 공급자 자격, 서비스 범위의 3개 필수 검토를 각각 기록한다. 각 항목에는 검토 의견과 같은 Company/입력 Version의 실제 Evidence 참조가 필요하다. 서비스 범위는 선택된 CapabilityVersion/FeatureRevision/Coverage/제외사항을 정확히 참조한다.
3. 현재 확정 공고의 모든 자격·조건·신청기간 항목은 항목 ID별 사람 검토 기록과 원문 Evidence를 요구한다. 필수정보 누락 사유도 항목별로 해소 근거를 기록한다. 조건의 해당없음도 사유·근거가 필요하다. 단순 전체 체크박스나 코멘트 하나로 대체하지 않는다.
4. Evidence는 서버의 신뢰된 Provider와 기존 File/Evidence 경로에서 권한·Company/Version·확인 여부·현재성·실제 파일 digest를 검사한다. Browser가 제출한 회사/Role/확인완료 값은 권위가 아니다. 실제 Provider가 없으면 운영은 기존 503 차단을 유지한다.
5. 확인된 필수조건 충돌(MISMATCH/CONFIRMED_CONFLICT)은 사람 체크로 해제하지 않는다. 원천 Fact/조건의 정상 새 Version·재검토·재분석이 필요하다. stale/legacy/미확인 입력도 차단한다.
6. 기존 Comparator의 NEED_MORE_INFO 분석값은 유지한다. 위 사람 검토가 모든 누락/미확인 항목을 명시적으로 해소했을 때만 별도 MatchReview.PROPOSABLE을 허용한다. Candidate/과거 Review/Snapshot을 UPDATE하지 않는다. Proposal Guard는 이 정확한 현재 Review와 불변 해소 근거를 확인한다.
7. 근거/Fact/Notice/Capability/Composition이 바뀌면 새 Proposal 생성·승인요청은 차단하며 재검토한다. 과거 Proposal/Review/승인은 보존한다.
8. MatchReview와 Proposal 내용 Review 및 지정 기업 승인은 별개다. Proposal 생성 허용이 제안내용 확정이나 기업 승인을 의미하지 않는다.

## 영향 범위

기존 REVIEW_MATCH Action/PROPOSABLE Outcome/4개 Role은 유지한다. 검토 완료항목의 불변 저장, API 검토 입력, UI, Proposal Guard를 확장한다. 범용 R07 자동 판정/AST/금액·날짜 자동 엔진은 구현하지 않는다. 정책 승인 후 03/04/05/08/10/11에 필요한 증분만 동기화한다. 실제 Provider 계약은 소비 Interface와 격리 Fixture로 분리한다.

구현 후에도 모든 조건 검증을 통과한 명시적 사람 검토만 허용한다. 정상 Proposal E2E는 실제 검증 전까지 NOT_TESTED다.
