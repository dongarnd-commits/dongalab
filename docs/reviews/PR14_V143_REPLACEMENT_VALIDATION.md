# PR14 v1.4.3 — 파일 교체와 작성 중 개선요구 첨부

시작 HEAD: `a989f77416b6f1961f211569511f19f745de4e4f`. 기존 `feat/datco-company-to-operator-real-e2e`와 Draft PR #14에서만 작업한다.

## 원인과 수정

C07은 새 File을 등록한 뒤 기존 `/company/files/{id}/lifecycle` API로 `REPLACED(old→new)` 이벤트만 생성했다. C06의 현재 ImprovementVersion JSON과 `company_improvement_evidence`는 이전 Evidence→File ID를 계속 참조했다. 따라서 새 File의 업무 미분류는 실제 관계 누락이며, 이전 File을 비활성화한 뒤 기존 SUBMIT Guard가 제출을 차단한 것은 정상이다.

기존 API의 URL·요청·응답 구조는 유지한다. `BusinessRecords.file_event`에서 회사 잠금을 유지한 채 단일 현재 DRAFT의 일반 MANUAL_REVIEW 첨부를 찾는다. 기존 File/Event/Evidence/Version을 수정하지 않고 새 File의 첨부 Evidence와 기존 `save_improvement` 절차의 다음 Version을 생성한다. As-Is·To-Be·원문·다른 첨부·Fact 참조를 그대로 복사하고 DRAFT를 유지한다. 새 Evidence/Version/pointer/Audit와 교체 이벤트를 같은 트랜잭션으로 저장한다.

현재 여러 개선요구, 재무·이력 분석, Fact 후보, 보완 요청·응답 등과 공유되거나 분석 근거를 재해석해야 하는 경우에는 일괄 승계하지 않고 409와 사유를 반환한다. 다른 Company와 Site를 검사한다. 현재 SUBMITTED 등 DRAFT가 아닌 Version은 교체로 새 초안을 만들거나 State를 바꾸지 않는다. 같은 Root의 과거 제출 Version은 보존하면서 이미 작성 중인 DRAFT에만 새 Version을 적용한다.

Frontend는 C07의 상시 저장정책 안내를 제거하고 보조 설명을 ‘등록한 자료를 확인하고 관리할 수 있습니다.’로 정리했다. 교체 확인창에서 작성 중 첨부 변경·제출 이력 보존을 알린다. 취소 확인창은 현재 자료함 제외와 원본 영구 삭제의 차이를 짧게 알린다. 저장하지 않은 C06 편집을 먼저 저장하도록 안내하며, 서버가 새 Version을 만든 후에는 저장된 이전 첨부 캐시를 갱신한다. 응답 유실은 정확한 old→new 이벤트를 재조회해 확인하며 중복 Version을 생성하지 않는다.

Schema/Migration/새 State·Role·Permission 변경: **없음**. 기존 취소·동일 PDF 재등록 증분은 유지한다. 새 API나 기존 Version 재연결·backfill은 없다. 기준은 `00_PROJECT_BASELINE.md`, `01_SYSTEM_ARCHITECTURE.md`, `PR14_V14_CONTRACT_APPROVAL.md`의 v1.4.3 절이며 `10_TEST_ACCEPTANCE.md`, `11_DECISION_LOG.md`에 동기화했다.

## 기존 격리 검수 데이터 복구

사용자 지정 `http://localhost:58936`의 `datco_test_f644bc4c1a25`만 대상으로 기존 교체 이벤트와 단일 DRAFT·일반 첨부·정확한 ordinal 3을 검증했다. 복구 전 전체 조회 스냅샷과 원본 해시를 Private runtime에 보존했다.

기존 테스트 Editor 계정의 인증된 Evidence/Improvement API로 새 첨부 Evidence와 Version 4를 추가했다. 기존 Version 1~3, File 3개, 취소·교체 이벤트, Evidence, 기업정보·Site·재무·이력·Fact·후보는 변경하지 않았다. 같은 Editor의 실제 브라우저 ‘DATCO에 제출’로 Version 4가 SUBMITTED가 되었고 F5 후 상태·새 PDF·C07 업무 분류를 확인했다. 과거 원본의 다운로드 해시도 복구 전과 같았다.

API는 소유 PID/포트/격리 identity를 확인해 같은 DB·Storage·포트에서 재시작했다. 기존 업무 DB와 구 사용자 검수 DB에는 Migration·초기화·업무 쓰기를 수행하지 않았다. 지정 검수 DB도 Migration 없이 승인된 테스트 건의 새 Version/제출 기록만 추가했다. 복구/제출은 반복 실행하지 않으며 완료된 상태는 SUBMITTED다.

Private 증거: `storage/private/runtime/ux-v143/`의 `validation-before.private.json`, `repair-before.private.json`, `repair-after.private.json`, `repair-result.json`, `existing-after-submit.private.json`, `existing-verification.json`, C06/C07 스크린샷 및 API 로그. 실제 원본·자격증명·Private 스냅샷은 Git에 포함하지 않는다.

## 검증

관련 Backend 19건, 전체 Backend 370 PASS / 0 FAIL / 1 SKIP, 단위 테스트 137 PASS가 통과했다. 전체 Backend에는 실제 PostgreSQL·Migration·권한·OCR·재무·이력·C09/C10 연계 회귀가 포함된다. 기존 SKIP 1건은 별도 저장된 한국어 Live 공고 문서를 요구하는 검사이며 테스트나 SKIP 조건을 변경하지 않았다.

실제 격리 Web/API/Worker/PostgreSQL의 신규 브라우저 시나리오는 공유 파일 차단, 연결 저장 실패 후 동일 File ID 재시도, 저장 성공 뒤 응답 유실 복구, A→B 관계·분류·다운로드·F5·재로그인·실제 SUBMIT·과거 근거 보존을 통과했다. 전체 Playwright 최종 재실행은 **46 PASS / 0 FAIL / 0 SKIP**이다.

전체 Playwright 최초 실행은 45 PASS / 1 FAIL이었다. 신규 시나리오의 첫 저장은 API 200과 Version 생성까지 성공했으나, 화면이 저장 후 Context 재조회 중일 때 기본 5초 완료 문구 대기가 만료됐다. 새 개선요구 버튼의 활성화(전체 저장·재조회 완료)를 최대 30초로 기다린 뒤 기존 완료 문구를 그대로 검증하도록 보완했다. 실제 관계·파일·제출 단언은 제거하거나 완화하지 않았고 전체 46건을 새 격리 환경에서 재실행했다. 최초 로그와 화면 문맥도 Private에 보존했다.

lint, API_TYPES_MATCH, production build(TypeScript 포함) PASS. Next.js 버전·보안 설정을 변경하지 않았다. 로컬 build의 기존 업그레이드 안내에 따른 동일 명령 재실행 외 별도 우회는 없다. Private 검증기의 Windows npm 실행기, 상대 URL, 상세 펼침·제출 이력의 링크 selector 문제는 수정해 재검증했고 제품·테스트 기대값을 완화하지 않았다. 기존 건의 UI 제출 후에는 중복 제출 없이 저장 결과를 재조회했다.

최종 HEAD/Commit/Push/새 HEAD GitHub CI·역할별 Preview와 최종 판정은 Draft PR #14 및 완료 보고에 기록한다. 과거 HEAD의 CI 성공을 새 HEAD 성공으로 사용하지 않는다.

## 변경 파일 (12개)

- Backend: `apps/api/app/company/business_records.py`, `apps/api/app/company/file_replacement.py`
- Frontend: `apps/web/src/company/client.ts`, `apps/web/src/portal/company-business.tsx`, `apps/web/src/portal/company-library.tsx`
- 테스트: `apps/api/tests/portal_handoff_setup.py`, `apps/api/tests/test_company_v14.py`, `apps/web/tests/business-ux.spec.ts`
- 기준·검증 문서: `docs/10_TEST_ACCEPTANCE.md`, `docs/11_DECISION_LOG.md`, `docs/reviews/PR14_V14_CONTRACT_APPROVAL.md`, 이 보고서

## 사용자 직접 검증

URL: `http://localhost:58936/login`. 기존 `storage/private/runtime/ux-v142/test-validation/f644bc4c1a25/credentials.private.json`의 Editor 계정을 사용한다. DB와 원본은 같은 환경에 유지한다.

1. C07에서 `TEST-replacement-v142.pdf`와 관련 업무 ‘개선요구’를 확인한다.
2. C06에서 제출 내용을 열어 새 PDF, As-Is/To-Be와 제출 상태를 확인하고 F5한다. 복구 건은 실제 제출 검증을 마쳤다.
3. 교체를 직접 다시 확인하려면 ‘제출 내용 수정’에서 수정본을 저장해 DRAFT로 만든다. 이 절차는 기존 제출 Version 4를 보존한다.
4. C07에서 다른 PDF(예: 원래의 `TEST-reregister.pdf`)로 교체한다. C06에서 수동 해제·재업로드 없이 새 PDF가 연결되는지 확인한다.
5. F5·재로그인·다운로드 후 C06 제출을 확인한다. 제출 이력의 기존 Version/PDF는 그대로여야 한다.

`PHYSICAL_DELETION_POLICY: POLICY_BLOCKED`. 원본 영구 삭제·백업 파기·업무 DB Migration·운영 배포·main Merge·Draft 해제는 하지 않는다. `USER_ACCEPTANCE: PENDING`, `SYSTEM_ACCEPTANCE: NOT_TESTED`를 유지하고 사용자 직접 검증을 기다린다.
