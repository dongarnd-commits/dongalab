# Slice 0b — 실제 업무 Context 읽기 모델

## 기준·승인 범위

시작 main: `cb7c2ad230e498a06f345776a88cc0e7a0d07f60`. 병합 후 DATCO CI 4개 SUCCESS를 확인했다. 사용자 Slice 0b 명령 7.2에 따른 기존 읽기 권한 내 최소 Projection만 추가한다. FROZEN Role/Permission/State/Guard, DB Schema/Migration 및 Version/Evidence 저장 구조는 변경하지 않는다.

## 기존 조회 계약 조사

| 조회 | 실제 소스·DTO | Role / Scope | 식별자·정렬·오류·한계 |
| --- | --- | --- | --- |
| GET /workspace | app/api/workspace.py, actor/companies/sites/improvements 요약 dict | 기존 네 역할별 Projection | Company/Site Root ID, 최신 Improvement Version ID만 제공. 과거 Version 선택 불가. 관리자 Company 목록은 id/name만 허용 |
| GET /company?q= | app/api/company.py → CompanyApplication.listing | EDITOR/OPERATOR/APPROVER Membership, 관리자 403 | Root id/name, 기존 q 부분 검색, 전체 허용 목록·페이지네이션 없음. created_at/id 순서, 미인증 401 |
| GET /company/{id} | CompanyApplication.detail | Company Scope, APPROVER 별도 공개 Projection, 관리자 상세 차단 | Site/Improvement 전체 이력과 내부 업무 데이터도 포함하여 탐색 전용으로는 과다. 기존 응답은 수정하지 않음 |
| GET /company/improvements/{version_id}/context | CompanyApplication.read_context → CompanyProvider | EDITOR/OPERATOR + Company Scope | 정확한 Version의 Fact/Evidence/현재 유효성 소비 계약. 탐색에 불필요한 내부 근거·잠금까지 수행하므로 변경 없이 보존 |

## 추가한 최소 Read Projection

`GET /company/{company_id}/navigation` → `app/company/navigation.py::read_navigation`.

- 기존 CompanyApplication.role/scope/rows와 기존 저장 모델만 사용한다. 신규 Provider·Entity·권한·DB 쓰기 없음.
- EDITOR/OPERATOR만 허용한다. APPROVER/ADMIN은 Membership 유무와 관계없이 403이다.
- Company는 id/name/current_ordinal, Site는 id/name/current_ordinal 및 ordinal별 기존 name/address/industry/process, Improvement는 Root id/site_id/title/state/current_ordinal 및 Version id/ordinal/site_ordinal/기존 서술 필드만 반환한다.
- 파일·Storage Key·Fact·Evidence·내부 Review 메모·Audit·승인 상태를 반환하지 않는다.
- 선택 Query: site_id / site_ordinal / improvement_id / version_id. Root와 Version, Site와 Company 및 Improvement의 관계를 서버에서 모두 검사한다.
- 없는 객체·타기업·잘못된 부모 관계는 404, 실제 참조와 다른 사업장 Version은 409, 잘못된 ordinal 타입은 422, 미인증은 401이다.
- Version은 ordinal 순으로 반환한다. 페이지네이션은 추가하지 않는다. 회사 목록/검색은 기존 API를 재사용한다.
- SiteVersion은 기존 Improvement 참조 계약인 `site_ordinal`을 사용한다. Improvement Root UUID와 ImprovementVersion UUID는 별개로 유지한다.
- `is_latest_version`은 Root의 current_ordinal과 비교한 표시일 뿐 Fact 확인·현재 유효성·승인을 의미하지 않는다. Root 상태도 현재 상태로 명시한다.

## UI Context

새 /portal/company, /portal/operator에서 기존 Proxy /api/company를 통해 조회한다. 허용 기업 1개는 자동 선택하고 Dropdown을 숨긴다. 여러 기업은 이름으로 선택한다. 0개이면 실제 빈 상태를 표시한다. 사업장·개선과제·정확한 Version을 선택하고 기존 메뉴 전체에 같은 Context를 전달한다.

URL의 company/site/site_version/improvement/version은 실제 DB 참조만 저장한다. context_actor로 이전 계정의 URL 선택을 현재 계정에 자동 적용하지 않는다. URL은 권한 근거가 아니며 매 조회마다 서버 Role/Membership/부모 관계를 재검사한다. 비밀번호·토큰·기업 이름·원문을 로컬 저장소에 저장하지 않는다.

유효 선택은 URL에 고정하여 메뉴 이동/새로고침/직접 링크에서 유지한다. 기존 Version에 새 Version이 추가되어도 자동으로 최신으로 바꾸지 않는다. 사용자가 회사/사업장을 변경하면 이전 자식 참조를 제거하고 다시 검증한다. 재조회 중에는 이전 데이터를 비우고 AbortController/요청 순서로 늦은 응답을 폐기한다. 로그인 계정 변경·로그아웃·만료는 기존 Slice 0a가 처리한다.

기업 기본명/사업장 목록/기존 개선과제 원문은 읽기 전용이다. 저장·업로드·파싱·Fact 확인·Improvement 제출·추천·매칭·제안서 업무 Action은 연결하지 않는다. 미리보기 UI/Fixture는 보존하고 실제 포털의 데이터 원천으로 사용하지 않는다.

## 관리자·정책 경계

관리자 UI와 기존 Workspace 계정 요약은 유지한다. M-09는 기존 GET /workspace 관리자 Projection의 catalog.features(기능 Root 레코드 수)와 catalog.published(current_ordinal > 0인 Capability 수)만 실제 표시한다. 해당 값은 기업 접수/업무량 KPI가 아니며 상세 목록·버전·동기화 상태 연결로 해석하지 않는다. 조회 중/실패 시 0을 만들어 표시하지 않는다. 관리자 업무 상세/전체 접수 Projection·집계·Assignment는 추가하지 않는다. Membership을 담당 배정으로 표시하지 않는다. 관리자 전체 업무 조회가 불가능한 현재 상태는 후속 Slice 2a/2b/5의 관리 Projection 과제이며 운영자 권한 확대의 근거가 아니다.

현행 Membership에는 신규 권한 회수 Command가 없다. 회수 정책/쓰기 API를 만들지 않는다. 새 읽기 요청마다 현재 권한을 검사하며 격리 테스트에서 현재 Actor Role 변경 시 기존 세션의 조회가 즉시 거부되는지를 검증한다.

## 검증·데이터 구분

실제 HTTP/API/PostgreSQL 격리 테스트와 기존 CI Runner를 재사용한다. Context 테스트 계정은 기존 업무 E2E 계정과 분리해 기업 1개/여러 개/0개 조건을 보호한다. 테스트용 회사·사업장·개선과제는 Runner 소유 DB에 실제 기존 API로 생성하며 `TEST` 이름을 사용한다. 일반 서버나 공용·업무 DB에 Seed하지 않는다.

최종 실행 결과·스크린샷·CI는 완료보고에 기록한다. 정상 업무 데이터가 없어도 임의 생성하지 않는다. Slice 1 입력/저장, 관리자 Assignment/KPI, 실제 추천·매칭·새 UI Proposal 및 전주기 E2E는 이번 완료 범위가 아니다. 기존 HTTPS Secure Cookie 배포 보류도 그대로 유지한다.

## 사용자 UI 정리 v0.2

사용자 승인 범위에 따라 신규 포털의 구형 업무 화면 진입 링크·대형 미연결 배너·기술 ID 확인 패널을 제거한다. 호환 /company·/notice·/capability·/proposal 라우트와 기존 서버 계약은 삭제하지 않는다.

수요기업 홈에는 실제 기업명·사업장명·선택 개선요구 제목/상태와 업무 이동만 표시한다. 사업장 선택은 C-04, 개선요구 제목 선택과 필요 시 펼치는 수정 이력은 C-06 중심으로 제공한다. 수정 이력은 작성 제목으로 표시하고 UUID·ordinal을 업무 텍스트로 노출하지 않는다. 기존 선택 ID·Site ordinal·불변 ImprovementVersion은 내부 상태/URL/API와 자동화 단언에서 그대로 유지한다. 과거 기록을 최신으로 바꾸지 않는다.

미연결 쓰기 작업은 각 업무폼에서 안내하며 저장·제출 성공을 생성하지 않는다. 운영자는 기존 허용 기업·사업장·개선요구 선택을 유지하고 기술 Context 문구만 업무 표현으로 바꾼다. 관리자 기존 통합관제/상세관리와 승인자 정책은 수정하지 않는다. 이번 UI 정리는 DB/API/AI 및 Slice 1 입력 저장을 구현한 것이 아니다.

## 최종 UI·안정성 정리 v0.4

C-01~C-10 공통 부모의 업무 요약 카드 렌더링을 제거한다. C-04·C-06의 기존 업무 카드 안에만 각각 사업장/개선요구 선택을 두며 원문 읽기는 C-06 본문에 한정한다. 정상 상태에서 공통 상태 영역은 렌더링하지 않고, 초기 조회·빈 Scope·오류 안내만 필요한 경우 표시한다. 실제 식별자 검증은 사용자에게 보이는 패널이 아닌 내부 상태/URL/API 및 기존 화면 루트의 data 속성으로 유지한다.

실측상 기존 Context 15초 재조회 전 데이터 비우기와 Session의 focus/visibility 복귀 시 ready=false 처리가 빈 화면·포털 재마운트를 일으켰다. Session의 15초 보안 검사 및 서버 Role/Scope 검사는 유지한다. 중복 업무 타이머는 제거하고, 동일 사용자 검증 성공 이벤트로 Scope를 재조회한다. 정상 재조회에서는 기존 데이터를 유지하며 동일 응답은 이전 상태 객체를 재사용한다. 중복 focus/visibility 요청은 진행 중인 세션 검사로 합친다. 같은 URL에 history.replaceState를 반복 호출하지 않는다.

401·403/계정 불일치/로그아웃/세션 실패는 기존 포털을 차단한다. 업무 조회 403·404·통신 오류는 기존 Context를 비우고 오류를 표시한다. 회사·사업장 변경 또는 popstate 선택 변경은 이전 Context를 즉시 비우고 다시 서버 검증한다. pagehide/pageshow의 캐시 복원 보안 확인 및 BroadcastChannel 계정 변경 처리는 유지한다. 서버 인증 계약·권한·FROZEN State·DB/API는 변경하지 않는다.

실제 90초 대기, 탭 복귀 3회, 전체 10개 화면, 403 장애 주입, 실제 서버 세션 무효화 및 기존 실제 HTTP/PostgreSQL 권한 회귀로 검증한다. 테스트 시간 가속이나 신규 SKIP을 사용하지 않는다. Production 격리 빌드 안정성 비교와 상세 증거는 Private 완료보고에 기록한다. 사용자 인수와 main Merge는 별도 승인 대기다.
