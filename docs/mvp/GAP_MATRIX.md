# MVP Gap Matrix

2026-10-30 main10d3d8b 소스 조사. 기존 CI Backend128 PASS/1 SKIP, PG248 PASS/1 SKIP, Frontend PASS, E2E58 PASS. 신규 MVP 연결은 별도 검증 대상이다.

| 영역 | 기존 실제 수준 | 추가 필요 |
|---|---|---|
| 기업/사업장/자료/개선요구 | 구현·연결·기존 검증 | MVP 통합 회귀 |
| Slice2/요청/응답 | 구현·연결·기존 검증 | Provider 경계·Rule 품질·검토답변 재사용 |
| 외부 AI | 미연결 | 4개 NOT_CONFIGURED·실행 차단만 |
| 649 원천 | Import/Revision/검색·legacy UI | 실제 원천 count/hash 검증, 합성 Fixture와 분리 |
| Capability | Admin Draft/Publish·조건/제외/선행요건 | 기존 관리자포털 연결·상위 솔루션 |
| 추천 | Confirmed Improvement 후보검색 | 검토 분석·동의어/부정·카탈로그 근거 |
| Composition/Coverage | Backend·legacy UI | 요구별 해결수준·역할·연계·실제 포털 |
| Assessment | Run/Candidate/Review | 미확인 적용성 NEED_MORE_INFO 유지 |
| Collector/Notice | 실제 API/Job/NoticeVersion | 저장검색/필터/페이지·신규 UI·LIVE 별도 확인 |
| Matching | Backend·legacy UI·Snapshot/Review | 새 포털 연결·관련성/자격 분리 |
| 조건 비교 | IN/NOT_IN·UNKNOWN | 범용 R07 자동 자격 구현으로 표시하지 않음 |
| Proposal/Approval | Backend·legacy UI·항목별 Proof | 16절 표준·운영자 UI |
| DOCX/PDF | 실제 OOXML/한글 PDF/digest | 11/16 병행·내용·레이아웃·Version |
| 기업 전달/Inbox | 실제 연결 | 신규 템플릿·운영자 전달이력 |
| 운영자 후속6메뉴 | placeholder | 실제 업무 Panel·scoped 선택·정확한 CTA |
| Admin4영역 | 실제 Catalog 집계 일부 | 안전 Projection·기존 grant UI, 가짜 차트 제외 |

CompanyProvider는 공식 CONFIRM·현재 입력을, proposal_basis는 정확한 ACKNOWLEDGE·Fact Proof·Approver를 요구한다. Slice2 Review만으로 충족했다고 처리하지 않는다.

근거: company/provider.py, capability/application.py, capability/proposal.py, proposal/application.py, proposal/documents.py, portal/operator-intake.tsx, portal/admin.tsx, portal/company-proposals.tsx 및 대응 기존 pytest/Playwright. 감사 Agent2개 모두 소스 조사만 수행했으며 신규 실행 테스트는 아직 없다.

## 통합 후 결과

기능/fixture HEAD4bfdc2d 기준으로 위 Gap을 구현·연결하고 로컬 자동검증을 완료했다. Company/원본/Fact/ACK/개선요구/Slice2를 재사용했으며, 후속6메뉴·Admin4영역·상위서비스/복합구성·공고/매칭·16절문서/전달을 실제 Backend와 연결했다.
649원천 검증, Rule/추천 고정기대, 하나의 기업 전체 계보, 전체Unit246/PG292+기존SKIP1/브라우저63PASS와 타입/빌드를 확인했다.
외부4Provider 미설정은 정상 MVP 목표다. 전주기H01~H32/공식신청·정산·실DMP/실외부AI는 제외/미래 범위로 보존한다. 상세근거는 ACCEPTANCE/IMPLEMENTATION_REPORT와 최신 PR Checks다.

## 2026-11-03 기업포털 UX 증분 — 화면 A–G

이 절의 A–G는 사용자 점검의 **화면 구분**이며, 실자료 평가의 A(자료·분석·추천·구성) / B(공고·매칭·정식 문서·전달) 승인 범위와 다르다. 기준은 HEAD `725987f4a375d4f77028e35361e4fcdb05aac4ee`에서 분리한 `dongalab-company-ux-20261103`, Branch `fix/company-portal-ux-20261103`다. 현재 표의 보완은 새 개발 Worktree의 코드 변경이며 기존 인수환경에 적용하거나 실기업 인수를 완료한 결과가 아니다.

| 화면 | 새 Worktree에서 보완한 동작 | 보존한 계약·남은 Gap |
| --- | --- | --- |
| A 기업 홈 | 실제 선택 기업명과 저장본·사업장·개선요구 상태를 표시한다. 현재 Root 상태와 과거 어느 Version에서든 제출한 이력이 있는 건수를 구분하고 집계 기준을 설명한다. 회신 필요/운영자 검토 대기와 계정에 전달된 제안서 건수, 조회 중/실패/정상0건을 구분한다. 정적5단계를 실업무 진행률처럼 보이지 않게 하고 바로가기를 별도 표시한다. | 저장·제출을 검토/승인 완료로 승격하지 않는다. 첨부자료 관리를 별도 필수 완료 단계로 만들지 않는다. 미확인 조회를0건으로 간주하지 않는다. 보완 요청은 해당 기업 입력 담당자들의 공유 범위, 제안서는 지정 수신 계정 범위다. |
| B 기업·사업장 | 기존 필수/선택 구분과 읽기 전용 사업자번호를 안내한다. 업태·종목과 이전 `industry` 문자열을 보존하고 이전 업종은 상세에서 확인한다. 저장된 사업장명·최신 주소를 함께 표시하고 미저장 기업/사업장 편집의 재조회·선택 변경에 확인을 둔다. 다음 업무 이동 간격과 버튼을 정리한다. | 별도 업종 컬럼·본사 flag를 만들지 않는다. ‘본사’는 입력한 사업장명일 수 있으며 공식 본사 여부를 추정하지 않는다. `industry`는 기존 입력 Evidence/Candidate 및 사실확인 경로를 유지하며 자동 확정하지 않는다. 숨긴 Profile 값·다른 재무연도·이력은 기존 전체 Profile 저장과 expected ordinal 검사로 보존한다. |
| C 재무 | 단일/다중 PDF/기존수정 구분, 기본5항목 우선·선택금액 빈값과0 구분. 원/KRW 상세 계약과 기존 단위 보존. 실제 변경/선택의 닫기·전환 확인, 잘못된 새 PDF에서도 기존 선택 보존. | 기준 ordinal의 Profile에서 재무 collection만 반영하며 다른 연도·수행이력·이전 Version을 보존. 동시수정409 유지. |
| D 수행이력 | 정부지원사업 이력 제목·사업명/기관·수행기간 정리. 필수/날짜 역전·저장/재조회·재무 보존 확인. | 미등록과 수행없음 확인은 다르다. 없음 확정 계약이 없어 새 flag/가짜 이력을 만들지 않음. |
| F 첨부자료 | 선택 취소/등록 해제/명시 교체 적용 구분. 실제 저장된 업무 연결과 파싱 시도 구분. | 선택·취소는 무쓰기, 교체 실패/재시도/응답 유실·다른 Scope 차단과 원본/Evidence/과거 제출 보존을 검증. |
| E 개선요구 | 목록0건과 조회 실패/로딩을 분리한다. 현재 불편/개선목표의 필수, 제약·첨부의 선택 여부를 설명한다. 업로드 허용 형식/크기·개수와 자동 분석 가능 범위의 차이를 알린다. 새 작성 중 중복 작성 진입을 줄이고, 작성 닫기의 미저장 확인과 화면 이동 후 작성본 복원을 유지한다. 제출 불가 이유를 표시한다. | 초안 저장과 DATCO 제출·재제출을 구분한다. 첨부가 없다는 이유만으로 새 필수 정책을 추가하지 않는다. 기존 Root/새 Version·원문·Evidence·사업장·ACK/CONFIRM Guard, 과거 제출본과 파일 원본을 유지한다. 근거 부족을 해결 완료로 바꾸지 않는다. |
| G 보완 요청·받은 제안서 | 요청/제안서의 조회 중·오류·정상0건과 재조회를 구분한다. 회사 공유 요청과 지정 계정 제안서의 범위를 안내한다. 제출본·전달본·기업 검토 대기·과거 전달본을 업무 용어로 표시하고, 내부 승인근거 기록 방식의 지정된 현재 전달본에서만 해당 입력을 표시한다. | 회사 전체 제안서 공개나 승인자 권한 확대를 하지 않는다. 내부 승인근거 기록은 승인권자의 직접 전자서명이 아니다. 실제 승인권자·시각·방법·근거·의견과 정확한 Version 검사를 생략하지 않으며, 기존 직접 승인/담당자 기록·최종 전달 Guard를 유지한다. |

확인한 제품 근거는 `company-home-summary.tsx`, `company-business.tsx`, `company-improvements.tsx`, `company-requests.tsx`, `information-response.tsx`, `company-proposals.tsx`, `DATCOV02.tsx`다. API/Schema/Role/업무 State 변경으로 UI 문제를 우회하지 않는다.

### 검증 상태와 남은 정책

`tests/company-portal-ux.spec.ts`와 `company-ux-fixture.ts`에 새 격리 시험 사례가 작성돼 있다. 관련 사례는 실제 합성 기업의 저장 상태/과거 제출 이력과 현재 작성 상태 구분, 이전 업종 보존·재조회 취소/수락, 사업장 주소, 개선요구 미저장 복원·선택 첨부, 요청/제안서 정상0건·지연·503 표시다. 지연·503은 실패 표시만을 위한 명시적 응답 제어이며 정상 업무의 저장 성공을 Mock으로 대신하지 않는다. **최종 보완 제품 코드에서 로컬27개 사례를 확인했다(집중 회귀26 PASS와 지연 시험 순서 수정 후 해당1 PASS). 전체 단일 실행의 합격으로 합산하지 않으며 원격 전체 회귀는 새 PR 최신 HEAD Checks로 확인한다.** 최신 전체 시험·빌드·브라우저의 최종 실행 Commit·명령·결과·실패 증거는 통합 검증 기록에서 확정한다.

- 실자료 보호/자료 사용·접근자·보존·정리/백업 승인, 개인별 계정 발급·암호/회수·세션 정리 수단은 이 UX 변경으로 완료되지 않는다. 기존 A 전용/읽기 전용 Role 부재와 직접 승인자의 정확히1명 제약도 그대로다.
- 공식 공고·자격·제공/릴리스·필요 연계 근거가 없으면 실자료 평가 B와 정식 DOCX/PDF·기업 전달은 보류한다. 공고 없는 상담용 문서, 복수 승인, 독립 모듈 연계 면제 등의 정책은 새로 만들지 않았다.
- 수행이력0건을 ‘수행 없음 확인’으로 확정하거나 제공 근거 없는 기능을 VERIFIED로 바꾸지 않는다. 사용자 최종 인수·main 반영·PR 병합과 이번 UI 보완은 별도다.

### 격리 유지와 향후 단일 적용·복귀 결정

현재 작업은 새 Worktree의 소스/합성 자동시험·빌드에 한정한다. 기존 `dongalab-dmp-assets`와 `https://127.0.0.1:18445`의 소스·문서·build/deps·DB·볼륨·files·계정·세션·프로세스, 기존8443/8444·백업은 변경하거나 시험하지 않는다. 실제 기업자료·인수 자격 파일을 개발 Fixture나 Codex 도구 출력으로 사용하지 않는다.

향후 반영은 다음 준비를 마친 **하나의 검토 가능한 적용/복귀안**으로 결정한다. 이 문서는 실행 승인이 아니다.

1. 새 격리 환경에서 변경 영향에 맞는 검증을 마치고 최종 Commit·실패/성공 근거와 변경 목록을 고정한다. 기존 인수환경의 주소·DB/볼륨/files·회사/계정·권한·이력을 유지하며 Migration/seed/초기화·자료 재입력을 하지 않는 적용안을 만든다.
2. 기존 인수 Worktree에는 이미 보존 중인 미커밋 문서가 있고 preparation의 clean-source/HEAD 검사 때문에 START가 차단될 수 있다. 그 문서의 실제 diff/바이트를 보호 보존하고 불변 실행 코드 경로·식별/가드 정합화 방법을 먼저 정한다. 문서 삭제/덮어쓰기, guard 무력화, manifest/HEAD/상태 파일의 임의 변경으로 시작하지 않는다. 현재 런처가 새 코드 경로로 자동 전환/복귀를 지원한다고 가정하지 않는다.
3. 사용자에게 적용할 정확한 Commit·시각, 기존 URL/자료/계정·권한 유지, 필요한 최소 실행 전환, 중단 기준과 복귀 경로를 함께 제시한다. 단일 적용 결정 전에는 기존 인수환경을 정지·전환·재빌드하지 않는다. 새 네트워크·방화벽·개인 계정/권한·자료 사용은 승인 범위를 넘으면 해당 부분을 별도로 구분한다.
4. 복귀안은 이전 실행 Commit/산출물/설정과 보존 문서를 식별해 두고, 문제 시 UI 코드 실행만 이전 버전으로 돌리는 것을 우선한다. UX 반영 후 정상 저장된 업무 데이터를 과거 DB 백업으로 되감거나 계정/URL을 바꾸지 않는다. 기존 API·Schema 호환과 안전한 복귀 수단이 확인되지 않으면 적용을 보류하며, 임의 DB/파일 삭제·전체 Docker 초기화·공유 서비스 전환을 복귀로 부르지 않는다.
