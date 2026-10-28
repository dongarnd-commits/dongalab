# Slice 2 승인된 구현 계약

사용자 개발 지시(2026-10-28), 기준 main 3fe9216c1565741f6ff2ebd8b128e280fa7f8efd.

로컬 규칙 기반 1차 분석만 구현한다. SUBMIT Version, 해당 Site Version, 당시 현재 기업 입력과 확인 Fact, 직접 Evidence와 동일 기업/사업장 공통자료를 구분해 고정한다. 자료 선택은 처리 가능한 현행 자료를 기본 포함하며 제외를 허용한다. 외부 AI, Fact/Improvement 자동 확정, 자동 발송은 금지한다.

공통 Job/Attempt/Run/Candidate/Review를 재사용하고 개선요구 종류만 typed 관계로 확장한다. 후보 0건은 개선요구에만 허용한다. 기존 Capability/Matching/Company/Notice 제약은 유지한다. 검토는 요청 활용/제외/추가확인이며 Improvement Root 상태를 변경하지 않는다.

기존 company_information_requests 및 불변 Trigger는 변경하지 않는다. 별도 영속 초안 Root/Version/선택 Review 관계를 보존하고 최종 확인에서 기존 생성·발송을 한 트랜잭션으로 호출한다. 취소는 발송을 발생시키지 않는다.

입력 변경은 과거 결과를 삭제하지 않는다. 새 제출, 사용 기업 입력/Fact/근거/자료 변경은 현재 사용을 차단한다. 신규 공통자료는 재검토 안내이며 무조건 무효화하지 않는다. 미제출 Draft는 기존 제출본을 대체하지 않는다.

Migration 실행은 합성자료 격리 DB에만 허용한다. 서비스 Worktree, 실사용 검수 DB, HTTPS 배포, main Merge, Draft 해제는 범위 밖이다. 구현·실행 검증 결과는 별도 보고한다.
