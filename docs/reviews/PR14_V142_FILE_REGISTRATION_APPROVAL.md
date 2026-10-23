# PR14 v1.4.2 파일 재등록 계약 증분 승인안

상태: 2026-10-23 사용자 제한 승인 A 반영. 이 문서는 영구 삭제·보존기간·업무 DB Migration을 승인하지 않는다.

## 확인한 원인

- `company-attachments.ts`는 활성 상태와 무관하게 회사 전체 파일 중 같은 digest의 첫 행을 재사용한다. 오류 복구도 같다.
- `CompanyApplication.upload`와 `company_files UNIQUE(company_id,digest)`가 새 등록을 금지한다. Storage는 SHA-256 주소의 공유 바이트다.
- `company_file_events`의 CANCELLED/REPLACED는 원본 불변·현재 등록 비활성 이벤트다. 기존 이벤트를 지워 재활성화하면 이전 이력 의미가 바뀐다.
- C06은 이미 연결된 비활성 Evidence를 과거 근거로 보존할 수 있지만 C07은 현재 File만 표시하므로, 새로 업로드했다고 생각한 작업이 실제 새 등록이 아니었다.

## 승인 요청 범위 A: 동일 바이트의 독립 재등록

1. 기존 취소/교체 File 및 이벤트·원본·Evidence·Version은 변경하지 않는다.
2. 동일 기업에 활성 File이 있으면 기존 중복 409·명시적 재사용 규칙을 유지한다. 활성 등록이 없고 과거 비활성 File만 있으면 새 File ID·등록시각·actor·Audit를 만든다. 동일 Storage digest 객체는 안전하게 재사용한다.
3. 기존 UNIQUE(company_id,digest)를 비고유 검색 Index와 '동일 Company/digest의 활성 등록 최대 1개' DB Guard로 대체하는 새 Migration 1개를 추가한다. 신규 Table/업무 State/Role은 추가하지 않는다. Company 행 lock과 DB trigger로 직접 SQL·동시 업로드도 검증한다.
4. Frontend의 정상 중복 재사용과 통신실패 복구도 활성 File만 선택한다. Site Scope는 기존대로 검사한다. 취소된 File을 정상 업로드로 가장하지 않는다.
5. C06에서 과거 비활성 첨부를 명확히 안내하고 새 Version에서 해제/유효 등록으로 교체한다. C07의 일반 목록은 활성 File만 표시하며 과거 원본의 업무별/감사 조회 계약은 유지한다.
6. 기존 API 경로·응답 필드·File/Evidence 불변성·다운로드 Role/Company Scope를 유지한다. 과거 데이터 backfill/파일 복사/삭제는 하지 않는다.
7. Migration은 격리 테스트 DB에서만 검증한다. 업무 DB/기존 사용자 검수 DB 적용은 별도 승인 없이는 하지 않는다. Downgrade는 새 다중 등록 이력이 있으면 데이터 삭제 없이 거부한다.
8. 정상 중복 409, 취소/교체 후 동일 바이트 재등록, DB/Storage 실패, 직접 SQL 및 동시성, 기존 회사/Notice/Proposal 회귀를 검증한다.

## 범위 B: 영구 삭제 정책은 별도 미확정

기존 v1.4 B는 원본 File/Storage/Evidence/과거 제출·제안 참조 유지와 논리 취소를 승인했다. 현재 영구 삭제 API·보존기간·백업 파기 범위가 확정되어 있지 않다. 따라서 미참조 자료라도 이번 증분으로 물리 삭제를 구현하지 않는다. USER UI에 등록 취소와 영구 삭제를 구분하고, 실제 원본이 남는다는 사실을 정확히 안내한다.

향후 별도 결정 항목: 파기 권한/대상과 참조 정의(초안/분석/확정/제출), 보존 근거·기산점·기간, 공유 Storage의 전역 참조 확인, 백업/복구본 처리, 실패 복구·감사 최소항목. 기간이나 무기한 보존을 개발자가 임의 확정하지 않는다.

## 실제 DDL 및 적용 제한

Migration `fd18e0012026` → parent `fc07d0012026`.
- `company_files_company_id_digest_key UNIQUE(company_id,digest)`를 제거하고 비고유 `ix_company_files_company_digest(company_id,digest)`를 생성한다.
- INSERT trigger `guard_company_active_file_registration`은 Company 행을 잠근 뒤 동일 Company/digest 중 취소·교체 이벤트 없는 등록이 있으면 SQLSTATE 23505로 거부한다.
- File 행/취소 이벤트/원본/Evidence/Version을 UPDATE·DELETE하거나 backfill하지 않는다. ID·Company FK·불변 trigger는 유지한다.
- Downgrade는 반복 Company/digest 이력이 있으면 `COMPANY_FILE_REGISTRATION_HISTORY_EXISTS`로 중단한다. 호환 데이터에만 원래 UNIQUE를 복원한다.
- 기존 업무 DB·기존 사용자 검수 DB에는 Migration하지 않는다. 물리 삭제는 POLICY_BLOCKED다.
