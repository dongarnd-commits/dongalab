# PR14 v1.4.2 파일관리 원인·정책 검토

## 확인 범위

기준 HEAD e4f8537c5538ea7cf00e90e061aad3bcf0d9041e. 기존 Feature Branch 유지. 사용자 검수환경은 로그인 후 GET만 사용하여 업무 쓰기 0건으로 확인했다. 현재 첨부가 비활성 파일에 연결된 사례 1건, 파일별 동일 메타정보 반복 그룹 4개가 있었다. 고객 파일/원문을 복사·삭제·교체하거나 기존 Version을 고치지 않았다.

## 원인 및 저장 관계

| 문제 | 원인과 코드 | 저장 관계 / 영향 |
|---|---|---|
| C06 수정 시 기존 첨부 없음 | company-improvements.tsx가 기존 Evidence로 draft.fileIds를 초기화하지만 새 선택 File만 렌더링 | 첨부 연결은 이미 개선요구 Version JSON 및 company_improvement_evidence에 존재. 표시·해제 UI 누락 |
| 취소 후 같은 PDF가 현재 자료가 되지 않음 | company-attachments.ts의 digest 검색/오류 복구가 lifecycle을 무시하고 가장 오래된 행을 반환 | 같은 취소 File ID를 재사용. 저장소 read는 가능하지만 현재 등록이 아님 |
| 새 File ID 발급 불가 | CompanyApplication.upload의 전체 digest 중복 검사 + company_files UNIQUE(company_id,digest) | UI만 바꿔서는 재등록 불가능. 검토 가능한 최소 DB 증분 승인안을 별도 작성 |
| C06/C07 불일치 | C06은 현재 ImprovementVersion의 과거 Evidence 참조를 읽고, C07은 FileEvent 없는 File을 현재 자료로 봄 | 이미 연결된 과거 근거 보존과 신규 활성 등록은 다른 의미. 비활성 첨부를 정상 자료로 표시하지 말아야 함 |
| 연도/이력 반복 | CompanyLibrary가 모든 business_extractions 실행의 entries를 펼쳐 같은 표시값을 반복 | 재분석 기록의 실제 중복 삭제 대상이 아님. 사용자 표시값만 중복 제거 |
| 취소/교체가 실제 삭제인가 | BusinessRecords.file_event가 CANCELLED/REPLACED를 append-only로 추가. LocalPrivateFiles는 SHA-256 객체 put/read만 제공 | 기존 등록·원본·Evidence·Version이 남는 논리 비활성화. unlink/delete 호출 없음 |

파일 Storage key/digest는 내용 기반 공유 바이트 주소이며 File ID는 기업·사업장·등록자·시각에 연결된다. 같은 바이트를 여러 업무/기업에서 사용할 수 있으므로 파일 한 행의 취소만으로 공유 객체를 지우면 안 된다. FileEvent는 현재 등록의 비활성화이고 ImprovementVersion/제출 Snapshot 변경이 아니다.

## 기존 계약으로 가능한 보완

- C06에서 기존 fileIds를 표시하고 첨부 해제 시 현재 초안의 selected fileIds만 제외. 저장 시 기존 새 Version API가 evidence_ids와 관계를 생성한다. 과거 제출/다른 Root의 관계는 변경하지 않는다.
- 취소/교체된 첨부는 경고하고 현재 수정폼에서 해제/유효 자료로 교체하도록 안내. 기존 업무/과거 원본 다운로드는 기존 Role·Company Scope 범위에서 보존.
- 기존 DRAFT + SUBMIT 이력이 있으면 '수정 중 · 재제출 대기', 제출 이력에는 '제출 완료', 현재 SUBMITTED는 '제출됨'으로 설명. 새 State 없음.
- 일반 C07은 활성 File만 표시. 과거 포함 체크박스는 제거하되 업무 이력/API를 삭제하지 않음. 같은 연도·같은 수행사업 표시만 합치고 내부 분석/근거는 유지.
- 재등록에 필요한 DB 증분은 [승인안](PR14_V142_FILE_REGISTRATION_APPROVAL.md) A를 따른다. 승인 전 DB 구조나 이벤트 종류를 임의 변경하지 않는다.

## 물리 삭제 정책: POLICY_BLOCKED

1. 현재 등록 취소는 Storage 원본을 삭제하지 않는다. 사용자에게 '영구 삭제 완료'를 표시하지 않는다.
2. 미참조 파일이라도 현재 승인된 v1.4 B는 원본 보존을 전제로 한다. 별도 삭제 API·안전한 파기 계약은 없으므로 이번 작업에서 물리 삭제를 구현하지 않는다.
3. 이미 제출된 원본은 당시 제출 내용/Review/Approval/Evidence를 재현하기 위한 기존 승인된 업무 근거다. 이는 개발자가 법적 보존의무나 무기한 보관을 새로 결정한 것이 아니다.
4. `11_DECISION_LOG.md`의 Backup 주기·보존기간/SLA는 미확정 사항이다. 파일별 보존기간·기산점·백업 파기 범위도 확정되어 있지 않다.
5. 추가 결정: 파기 책임자/권한, 필수 참조의 범위(초안/분석/제출/확정), 보존 근거·기산점·기간, 전역 공유 Storage 및 백업/복구본 참조 검사, 실패 복구·감사 최소항목. 승인 전 고객 원본을 정리하지 않는다.
6. 일반 자료함 제외와 업무 첨부 해제, 등록 취소, Storage 영구 삭제는 서로 다른 처리임을 UI/보고서에 명시한다.

DB 재등록 증분 승인과 물리 삭제 정책 승인은 별개다. 재등록을 승인하더라도 기존 파일의 물리 삭제·보존기간·업무 DB Migration을 승인한 것으로 해석하지 않는다.

2026-10-23 추가: 사용자 제한 승인 A에 따라 `fd18e0012026`과 활성 등록 Guard를 구현했다. 기존 취소 File 재사용과 Company/digest 전체 UNIQUE 원인을 함께 해소한다. 물리 삭제 및 기존 업무·사용자 검수 DB 적용은 계속 승인 제외다.
