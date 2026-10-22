# PR14 v1.4 계약 변경 승인 요청

Status: ACCEPTED — 2026-10-22. 사용자가 A~C 증분 구현과 D 별도 승인 모드 구현을 각각 명시적으로 승인했다. 승인 전에는 사용자 운영 모델 요구만으로 서버 권한 변경 승인을 간주하지 않았다. 기존 AGENTS 2절과 03/04/05 계약을 따른다. UI 정리는 독립 진행한다.

## A. 재무·이력 저장 증분

현재 Financial은 year/revenue/period/unit/currency만, History는 name/period/agency/role만 저장한다. 기존 회사 입력 JSON Version에 재무의 유동/비유동자산·자산총계, 유동/비유동부채·부채총계, 자본금·자본총계, 영업이익·당기순이익의 선택적 정확한 원 단위 정수 문자열 및 확인 결과를 추가한다. 누락은 null/확인 필요이며 0으로 만들지 않는다. 기존 매출·단위·기간 계약은 호환 보존한다. 계산은 Decimal로 하며 비율·증감률은 원본값/연도 기반 파생값, 분모0·누락·동일 연도 충돌은 확인 필요다. 자산=부채+자본 및 소계 검증은 경고·명시 확인 없이 자동보정하지 않는다. 자료만으로 Fact 확정/현재 대표자 덮어쓰기를 하지 않는다.

파일·페이지·표종류·계정코드·원문 금액과 사용자가 저장한 값을 구분한다. 기존 company_input_versions와 File/Evidence에 대한 typed 연결 테이블(company_business_sources)을 추가해 해당 불변 입력 Version의 재무 연도/이력 행과 같은 Company의 원본 Evidence를 연결한다. 기존 자료는 backfill/재작성하지 않는다. 기존 Profile API/Type은 선택 필드 증분으로 호환 유지하고 새 저장도 기존 낙관적 Version 검사 및 Scope를 따른다. 지원 문서 PDF만 C05에서 등록하며 기존 과거 파일은 삭제하지 않는다.

## B. 파일 교체·등록 취소 정책

원본 File/Storage/Evidence/과거 제출·제안서 참조는 모두 유지한다. 새 append-only file_event 테이블로 REPLACED(old→new File ID) 및 CANCELLED를 감사 기록한다. 같은 회사 Editor만, 정확한 현재 파일 상태를 검사한다. 교체는 검증된 새 원본 생성 후 관계 기록, 기업/재무/이력/개선요구를 자동 덮어쓰거나 기존 근거를 재연결하지 않는다. 이미 참조된 자료의 취소도 원본 영구삭제가 아니라 현재 자료함의 비활성 등록이며 관련 업무의 과거 원본 다운로드는 권한 범위에서 유지한다. 새 업무 연결/재분석에는 비활성 자료를 사용할 수 없게 한다. 취소 자료는 별도 조회 가능하며 오류/미반영을 성공으로 표시하지 않는다. 이벤트와 Audit를 같은 트랜잭션으로 저장한다. 새 Migration은 격리 테스트 DB에서 검증하며 업무 DB에는 승인 없는 Migration을 적용하지 않는다.

## C. 보완 요청 물리 구현

실제 InformationRequest/Response 저장은 현재 없다. 03/04에 이미 정의된 DRAFT→WAITING_RESPONSE→REVIEW_REQUIRED→VERIFIED 또는 REVISION_REQUESTED→REVIEW_REQUIRED만 사용한다. 새 물리 테이블은 Company 및 개선요구 Version/기업 입력 Version/파일 중 실제 대상 FK, 고정 요청 내용/요청자/기한·시각, 불변 응답 Version·첨부 Evidence·제출자, 불변 운영자 Review를 저장한다. 요청 발송은 Scoped Operator, 응답 초안·제출은 같은 Company Editor, 검증/재보완은 Scoped Operator만 가능하다. 새 응답 Version은 이전 제출본을 변경하지 않으며 서버 State/Version/Scope를 검사한다. 자료 수정은 기존 Profile/Improvement API를 사용하고 원본 요청/과거 입력을 보존한다. 목록·정보조회·응답/검토 API 및 최소 운영자 요청/검토 UI가 필요하다. 관리자 자동 운영권한·자동 Membership은 추가하지 않는다.

A~C 승인 시 관련 03/04/08/10 및 Decision Log에 승인된 물리 증분과 범위를 기록하고 해당 Migration·API·UI·회귀를 구현한다. 신규 상태/Role나 외부 Provider/매칭엔진은 추가하지 않는다.

## D. 승인된 별도 내부 승인근거 기록 모드

현재 05는 Editor 승인 불가, 지정 Approver만 승인/수정요청을 허용한다. 실제 Proposal version()도 Editor를 차단하며 DB 결정 FK가 지정 Actor와 정확한 Version을 묶는다. 단순 Editor 버튼 활성화나 Approver Role 자동부여는 금지한다.

제안: 기존 지정 Approver 직접 승인 경로는 그대로 둔다. ApprovalRequest에 승인 모드(DIRECT_APPROVER 기본값 / COMPANY_RECORDED_AUTHORIZATION)를 추가하고 후자에만 운영자가 같은 회사의 정확한 Editor 기록자를 지정한다. 해당 Editor만 그 요청/Version의 내부 승인 근거를 기록해 승인/수정요청을 전송할 수 있다. 기존 intended_approver FK는 지정 시스템 행위자 관계로 유지하되 기록 승인 모드에서는 실제 승인권자 본인의 전자서명이 아님을 명시한다. 현재 Version/OPEN/최신 입력/기존 내용검토·승인 Guard를 유지한다.

새 불변 승인근거는 결정/요청/정확한 ProposalVersion, 로그인 기록자, 실제 승인권자 성명·직책, 구두/결재서류 방식, 실제 승인 일시, 방법·경위 또는 같은 회사의 결재 File/Evidence, 서버 전송 시각을 구분한다. APPROVE에는 필요한 근거와 최종 확인을 강제하고 두 사람을 같은 인물로 바꾸지 않는다. 이전 직접 승인/결정은 변경하지 않고 새 Version 재승인 원칙을 유지한다. 관리자/운영자가 기업 승인을 대신 생성할 수 없다. Role enum을 추가하지 않되 03/04/05 권한·Actor 의미와 DB Trigger/Provider/API/Proposal 회귀의 명시적 증분 변경이 필요하다.

승인 전 D는 POLICY_BLOCKED. Editor 공개 조회도 기존 공개 근거가 확인된 실제 발송 Version으로 제한하고 회사 공용 Membership으로 모든 Draft나 내부 Review/Manifest/Private 원문을 공개하지 않는다. 공개 관계를 확정할 수 없으면 해당 부분도 승인 전 차단한다.

## 보호 및 검증

기존 Company/Notice/Capability/Matching/Proposal Guard·P1 승인자 파일/메모 보안, 과거 Version/원본/승인, Stash/백업 보호. 새 물리 구조는 Alembic 정방향 Migration, 권한·Scope·FK/불변·상태전이·HTTP·실제 DB/File E2E와 기존 전체 CI로 검증한다. 민감 원본은 로컬 Private 검증에만 사용하며 공개 Git/CI에는 합성 문서만 사용한다.

## 승인 기록

2026-10-22 사용자 응답: “A~C 증분 구현 승인”, “D 별도 승인 모드 구현 승인”. 기존 지정 Approver 직접 승인·Version/Scope/Guard 유지와 별도 격리 환경 Migration 조건까지 포함한다. 실제 사용자 자료가 있는 기존 체험 DB/업무 DB의 Migration은 이 승인에 포함하지 않는다.

## 승인 범위 내 구현 확인

파일 비활성화는 원본·과거 업무 근거의 삭제가 아니다. 같은 업무에서 변경 없는 기존 근거를 이어 보존하되 신규 업무 연결·재분석·변경한 입력값의 새 근거에는 비활성 원본을 사용하지 않는다. 제안서 기록 모드의 Editor는 해당 요청의 승인근거 기록/승인 및 수정요청만 가능하며 기존 Approver의 REJECT 권한을 포괄 승계하지 않는다. 실제 승인 시각은 그 정확한 ProposalVersion 생성 이후이면서 서버 기록 이전이어야 한다. 직접 승인 모드의 기존 Idempotency 범위와 과거 결정은 보존한다.

검증용 DB에만 전방 Migration을 적용한다. 기존 사용자 체험 DB·원본·Version·Review에는 이번 승인으로 Migration을 적용하지 않는다. 실제 기업문서 검증 복사본과 합성 회귀 Fixture를 구분하며, 사용자 화면 승인과 전체 시스템 인수는 별도이다.
