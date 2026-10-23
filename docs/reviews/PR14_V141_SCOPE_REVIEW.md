# PR14 v1.4.1 기존 계약 및 변경 범위 검토

이 문서는 구현 전 기존 계약 확인 결과와 UI 보완 범위를 기록한다. 새로운 State·Role·Permission·Schema를 승인하거나 추가하지 않는다.

| 항목 | 기존 구현 | 필요한 수정 | 정책 변경 |
|---|---|---|---|
| 사업장 버튼·연결 | Company Site API·Version 저장, 최초등록 확인 주소→본사 생성, 단일 Site 자동선택 | 신규 등록/변경 저장 구분·사업장명 안내 | 없음 |
| 재무 편집창 | Profile 불변 입력 Version·상세 원금액 저장 | 해당 연도 전용 모달·취소/포커스/모바일 | 없음 |
| 재무 원본 비교 | 추출 원본·필드·페이지·계정 코드 및 사용자 수정값 별도 보존 | 정상 시 요약·불일치 항목 안내·PDF 링크, 기존 메모 내부 보존 | 없음 |
| 수행이력 편집창 | name/period/agency·원본 연결 | 별도 편집창·긴 사업명·시작/종료일 UI, 기존 period 문자열 호환 | 없음 |
| 개선요구 목록 | Root별 불변 Version·SUBMIT | 짧은 UI 식별명·상세 펼침/접기·새 작성 시 상세 숨김 | 없음 |
| 제출 후 수정·재제출 | 기존 E 새 Version 저장, 04 ACT-IMPROVE-05에 SUBMITTED/REVIEW_REQUIRED/CONFIRMED/REVISION_REQUIRED→DRAFT 명시 | 기존 API 연결·제출 이력 조회·재제출 표시 | 없음: 기존 승인 경로 재사용 |
| 파일 교체·등록 취소 | v1.4 승인 A/B 기반 append-only FileEvent·원본 및 기존 참조 보호 | 중복 개발 없이 실제 UI/API 회귀 유지 | 없음 |

## 제출 후 수정·재제출 근거

- `docs/04_STATE_ACTION_MODEL.md` 4절: 제출 후 중요변경은 새 Draft/Version 및 재분석/검토.
- 같은 문서 ACT-IMPROVE-05: 기존 REVISE_IMPROVEMENT가 위 네 State에서 새 DRAFT를 허용하고 과거 이력을 유지.
- `docs/05_PERMISSION_UI_MATRIX.md`: 자기 기업 Editor의 Improvement 입력과 Company Scope, 이전 확정/승인의 자동 상속 금지.
- `CompanyApplication.save_improvement`: Company Editor+Company Scope·현재 ordinal·동일 Root/Site·Fact/Evidence 현재성 검사 후 새 불변 Version 삽입. 제출 Version을 UPDATE하지 않음.
- `improvement_action(SUBMIT)`: 현재 Version이고 Root=DRAFT인 Editor만 제출. SUBMIT Review 및 Audit의 actor/time 보존. 이전 제출로 새 Version을 자동 제출하지 않음.
- 운영자는 기존 scoped Company 상세/API에서 최신 Root·Version과 전체 제출 Review를 확인. 기존 Proposal/Match Snapshot을 갱신하지 않으며 기존 Provider의 현재성 Guard를 유지. 새 알림·업무배정 정책을 추가하지 않음.

제출일과 제출자는 Version별 SUBMIT Review와 기존 Audit로 추적한다. 사용자 UI의 '제출 이력 확인'은 당시 입력과 파일을 보여준다. 제목 길이는 UI에서만 줄이고 저장된 원문을 일괄 변경하지 않는다.

## 금액·원본·파일 보호

모든 금액은 기존 정수 문자열 계약으로 저장하고 쉼표는 표시에서만 적용한다. 합계/부채비율/유동비율/증감률의 기존 BigInt·반올림 계산을 유지한다. 원본과 수정값 상세는 기존 Evidence에 남는다. 필수 합계 불일치 확인 Guard는 제거하지 않고 해당 경우에만 사용자 확인을 받으며 기존 내부 consistency_note를 유지한다.

기간·단위·통화는 문서연결 입력에서 읽기 전용, 직접 입력에서는 편집 가능하다. 이력 기간은 시작/종료일을 기존 period 문자열로 저장하고 기존 자유형 기간을 강제로 재해석하지 않는다.

파일 교체는 새 File ID와 기존 원본 간 이벤트만 생성한다. 현재 자료 목록 제외와 원본 삭제를 혼동하지 않는다. 기존 Evidence·재무/이력·제출본·Proposal 참조를 자동 재연결하거나 삭제하지 않는다. 후속 분석/새 연결은 active-file Guard를 따른다.

## 검증과 범위

기존 격리 Runner의 전체 Backend Integration·Playwright를 유지한다. 연도별 취소/수정·정확한 저장·모바일·이력 편집, 기존 사업장 수정, 제출 후 새 Version·재제출·이전 제출 불변성 및 HTTP 타기업/역할/stale 차단을 보강한다. 실제 고객 원본을 테스트 Fixture로 복사하거나 업무 DB를 수정하지 않는다. C09/C10·운영자·관리자 UI는 재설계하지 않는다.

사용자 직접 인수는 자동 테스트와 구분한다. PR14 Draft 유지, Merge·업무 DB Migration·운영배포를 수행하지 않는다.
