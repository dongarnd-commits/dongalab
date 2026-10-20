# Company → Operator 실제 업무 Handoff v1.1

## 범위와 계약

기준: Baseline, Architecture, Permission Matrix, Screen Action, Test Acceptance 및 기존 W1 Decision006. 기존 Profile/Site/CompanyDocument/Evidence/Candidate/ACK/ImprovementVersion API를 승인된 역할 포털 본문에서 재사용한다. DB Schema, Migration, Role, State, Guard, 공통 인증, FROZEN 문서는 변경하지 않는다.

| 화면 | 실제 연결 | 구분 |
|---|---|---|
| C-02 | Company 등록, 본인 Membership, 입력 Snapshot | 기존 POST /company |
| C-04 | Profile 저장, 복수 Site 생성/수정 | expected_ordinal, 과거 Version 보존 |
| C-05 | financials와 history 저장 | 기존 Profile 필드만 |
| C-07 | raw 파일 업로드/다운로드, 파서 실행, 원문 위치 | Private Storage, SHA-256, 20MiB |
| C-03/C-08 | Candidate/Evidence, 기업 ACK, 별도 수동 정정 Candidate | Fact 자동확정/원문 덮어쓰기 없음 |
| C-06 | 불변 개선요구 초안 Version, 정확한 Version SUBMIT | 제출≠최종 Confirm/AI 분석 |
| O-02~O-05 | 허용 기업/사업장/개선요구/파일/근거 조회 | 쓰기·최종 검토·배정 미연결 |

기업 정정은 원후보 ACK 불일치와 별도 수동 Evidence/Candidate/기업 ACK로 기록한다. 원본 File/파서 Evidence/원후보/Fact/Profile은 정정값으로 덮어쓰지 않는다. 여러 기존 명령이므로 중간 실패 시 부분 기록이 남을 수 있다. 성공 메시지는 전체 수행·재조회 이후에만 표시한다.

Company Scope와 Version Guard는 기존 서버가 검사한다. 과거 개선요구 조회 시 초안 저장·SUBMIT은 차단하며 현재 선택을 명시적으로 변경한다. 현재 계약상 SUBMIT은 확정 Fact를 필수로 하지 않는다. ACK를 Fact 확정으로 대체하는 새 정책은 만들지 않는다.

## 지원 계약 GAP / 의사결정 필요

- Profile에는 종업원 수 필드가 없다. 파서의 직원 수 후보와 Profile 저장은 구분한다.
- history는 수행사업 행만 저장한다. 없음/미확인 상태는 표현할 수 없어 저장했다고 표시하지 않는다.
- 파일 설명·분류·업무단계·교체 계보의 영구 저장 계약은 없다. 신규 원본 추가와 기존 원본 보존만 제공한다.
- Site 삭제 API가 없으므로 실제 삭제를 제공하지 않는다.
- 운영자 접근에는 기존 Company Membership이 필요하다. 관리자 Membership 부여는 Assignment가 아니며 신규 기업 자동 공개를 추가하지 않는다.
- Assignment, 최종 Fact/개선요구 확정, 외부 AI, 자동 매칭/제안서, 전주기 후속 작업은 미연결이다.

## 검증/실사용 데이터 분리

기존 ci_run.py가 임시 DB/Role/Private Storage 및 테스트 계정만 생성하고 실제 HTTP·브라우저로 Company 등록부터 운영자 조회를 검증한다. 자동 테스트는 TEST cohort이며 사용자 검수 환경과 다른 DB이다.

별도 사용자 검수 환경은 기존 Migration과 격리 API를 재사용하되 계정만 준비하고 Company/Site/File/Improvement는 생성하지 않는다. 사용자가 실제 입력한다. 검수 계정의 회사만 기존 관리자 API를 통해 지정 운영자에게 Membership을 부여한다. 사용자 입력 자료는 테스트 정리 대상에 넣지 않는다.

입력 충돌은 409로 표시하고 입력값을 유지한다. 서버 자료를 명시적으로 다시 불러온 후 저장한다. 동일 동작 중 중복 명령은 잠금으로 차단하고, 기업/계정 전환 시 이전 요청의 UI 반영과 후속 명령을 중단한다. 업로드 부분 성공과 실패를 구분하고 이미 등록된 원본은 보존한다.

## 완료 판단

실행별 결과·실제 ID/Version/해시·스크린샷·사용자 로그인 안내는 Git 제외 Private 검증 보고서에 기록한다. 통합 테스트 통과는 사용자 인수 승인을 의미하지 않는다. 미지원 계약 GAP은 PARTIAL로 보고하고 사용자 검수 전 Draft PR을 유지한다.
