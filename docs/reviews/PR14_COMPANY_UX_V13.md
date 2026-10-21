# PR14 수요기업 UX v1.3 영향 및 재사용 계약

사용자 2026-10-21 지시에 따라 공통 로그인과 C01~C07의 업무동선을 정리한다. Auth/Role/State/Schema/Migration/Proposal Guard는 변경하지 않는다. 화면에서 숨긴 과거 데이터·API·버전은 삭제하지 않는다.

## 기존 저장 경로

- 재무: Profile.financials(year, revenue, period, unit, currency). 이력: Profile.history(name, period, agency, role). 각 저장은 전체 Profile의 expected_ordinal을 검사하고 새 CompanyInputVersion을 생성한다. 숨긴 contact/overview/기타 입력도 보존한다.
- 개선요구: 기존 Root/Version의 data.evidence_ids와 company_improvement_evidence가 file 참조를 가진 Evidence에 실제 연결된다. 파일 선택은 기존 Upload API와 수동 Evidence 등록을 사용한다. 기존 파일은 같은 Company/허용 Site 범위에서 재사용하고 매 저장 Version에 연결한다. Fact 선택은 기존 참조를 보존하며 자동 확정하지 않는다.
- 제목/원문: 신규 GUI의 As-Is/To-Be/선택 제약을 손실 없이 명시적 구획으로 original_text에 구성하고 As-Is 첫 줄을 짧은 식별명으로 사용한다. 이전 Version은 불변이다. 기존 원문과 숨긴 구조화 정보는 수정 시 보존한다. SUBMIT은 기존 상태·Version/Role 검사와 실제 서버 Action만 사용한다.
- 문서 분석: 기존 parse API에 선택적 purpose(finance/history)를 추가한다. 기존 로컬 파서와 스캔 PDF OCR을 재사용하며 명시된 라벨·연도·단위가 있는 값만 입력후보로 반환한다. 기존 Parse/Evidence/해당 공통 후보 계보는 보존한다. 사용자 Profile 저장 전 자동 Master/Fact 확정은 없다. API 확장은 기존 Editor/File Scope 내의 추가 읽기/분석 모드다.
- C07: 실제 파일 목록/등록일/원본 다운로드 및 저장된 ImprovementVersion→Evidence→File 관계를 조회한다. 문서 분석 목적은 분석 기록으로 표시하며 최초 업로드 업무 출처로 단정하지 않는다.

## 변경하지 않는 계약과 GAP

지원금액·자산/부채 전용 Profile 필드, 이력 없음/미확인 상태, Profile 행과 파일의 typed 연결, 최초 업로드 목적, 파일 교체 계보는 현재 계약에 없다. 표시 가능한 입력 저장 성공으로 위장하지 않는다. 재무·수행이력 원문은 File/Parse/Evidence로 보존하지만 해당 Profile 행과 원본의 정형 관계는 별도 결정 대상이다. 업태/종목은 기존 industry 문자열에 구분 보존하며 분리된 DB 컬럼으로 주장하지 않는다.

기존 수요기업의 일반 화면 기술정보만 제거한다. C08~C10·운영자·관리자 화면과 기존 Backend 검토 기능은 재설계/삭제하지 않는다. 공통 로그인 외 기존 Workspace 동작은 보존하며 로그인 화면에서만 구형 Shell을 노출하지 않는다.

## 검증 및 적용 경계

격리 DB/Private Storage에서 합성 재무 XLSX, 수행이력 DOCX, 한국어 스캔 PDF와 실제 HTTP/브라우저를 사용한다. 텍스트·표 라벨이 명확한 지원 필드만 자동 입력하고, 복잡한 표와 누락된 의미는 사람이 직접 입력한다. 범용 AI 정확도나 임의 문서 완전 분석을 완료로 선언하지 않는다.

C-06은 같은 Root 수정 시 새 Version, 별도 새 작성 시 새 Root를 만든다. 제출 시 최신 Version 및 기존 SUBMIT Guard를 적용한다. 첨부자료는 기존 Manual Evidence를 통해 실제 company_improvement_evidence에 저장되며, 이 Evidence는 파일 첨부 사실을 나타내고 문서 내용을 자동 분석했다는 의미가 아니다. 파일 원본 및 기존 Fact는 덮어쓰지 않는다.

C-07은 읽기·다운로드 전용이다. 파일의 분석 목적 및 실제 개선요구 연결만 표시하며, 원래 업로드 단계나 파일 교체 이력을 생성하지 않는다. 기업·재무·이력의 숨긴 기존 입력값은 전체 Profile 저장에서 보존하고 낙관적 Version 충돌을 차단한다.

기존 UI 제거로 바뀐 회귀는 명칭·정상 화면 경로를 갱신한다. Candidate ACK/정정·과거 Version 고정·일반 추출 API는 직접 HTTP 검증을 유지하며 Scope/Role/Proposal Guard 부정검사와 90초 유휴·포커스 복귀 검사를 삭제하거나 SKIP하지 않는다. DB Schema, Migration, State, Role, Provider/Architecture 및 FROZEN 문서 계약은 변경하지 않는다. 사용자 최종 승인은 별도다.
