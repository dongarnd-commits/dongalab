# PR14 v1.4.2 승인안 A 구현·검증

2026-10-23. 승인 범위는 `PR14_V142_FILE_REGISTRATION_APPROVAL.md`, 제품·구조 기준은 `00_PROJECT_BASELINE.md`와 `01_SYSTEM_ARCHITECTURE.md`를 따른다. 물리 모델·검증·결정은 `03_DATA_MODEL.md`, `10_TEST_ACCEPTANCE.md`, `11_DECISION_LOG.md`에 동기화했다.

## 변경 및 데이터 영향

Migration `fd18e0012026`의 parent는 `fc07d0012026`이다. 실제 DDL은 `apps/api/alembic/versions/fd18e0012026_company_file_reregistration.py`에 있다.

```sql
ALTER TABLE company_files DROP CONSTRAINT company_files_company_id_digest_key;
CREATE INDEX ix_company_files_company_digest ON company_files (company_id,digest);
CREATE FUNCTION guard_company_active_file_registration() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM id FROM companies WHERE id=NEW.company_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM company_files f
   WHERE f.company_id=NEW.company_id AND f.digest=NEW.digest
   AND NOT EXISTS(SELECT 1 FROM company_file_events e WHERE e.file_id=f.id)) THEN
  RAISE EXCEPTION 'DUPLICATE_ACTIVE_COMPANY_FILE' USING ERRCODE='23505';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER guard_company_active_file_registration BEFORE INSERT ON company_files
FOR EACH ROW EXECUTE FUNCTION guard_company_active_file_registration();
```

전체 등록 이력에 적용되던 UNIQUE를 활성 등록 중복 방지 Guard로 교체한다. 기존 File/Event/Evidence/Version/Snapshot 행을 수정·삭제·재연결하거나 backfill하지 않는다. 기존 FK·불변성·Company/Role/State Guard는 유지한다. 새 State·Role·Permission은 없다.

Backend는 같은 Company/digest의 활성 등록이 있으면 기존 409를 유지한다. 과거 등록만 있으면 새 File ID·actor·등록시각·Audit을 생성한다. Private Storage의 SHA-256 객체는 재사용하며 취소 이벤트는 과거 File ID에만 남는다. Company 잠금과 INSERT trigger는 동시 요청 및 직접 SQL 중복 등록을 제한한다.

Downgrade는 동일 Company/digest에 복수 등록 이력이 있으면 DDL 변경 전에 `COMPANY_FILE_REGISTRATION_HISTORY_EXISTS`로 거부한다. 호환 데이터에서는 trigger/function/index를 제거하고 기존 UNIQUE를 복원한다. 이력 삭제를 통한 강제 Rollback은 구현하지 않았다.

기존 독립 보완 10개 파일을 보존했다. C06 첨부 해제는 새 Version으로 저장되고 과거 제출본은 유지된다. 비활성 첨부의 신규 SUBMIT은 기존 active-file Guard를 적용한다. C07은 활성 등록만 표시하고 중복 표시값만 합치며 분석·업무 이력은 유지한다. Frontend의 digest 재사용·실패 복구 검색도 활성 등록에 한정한다.

## 실제 검증

격리 DB에서 Migration 적용·모델 비교, 빈 데이터 및 기존 단일 등록 데이터의 Down/Up, 기존 행의 필드별 동일성, 이력 존재 시 안전한 Down 거부가 통과했다. HTTP/직접 SQL 동시 재등록은 활성 등록 1건을 유지했다. 취소 File ID의 이벤트와 원본 bytes·Evidence·Version을 유지하고 새 File ID만 활성화하며 타기업 다운로드를 404로 차단했다. 실제 PDF의 C06/C07 재등록·첨부 해제·F5·중복 표시 제거 브라우저 시나리오도 통과했다.

기존 업무 DB `datco_skeleton`은 revision `b730cf01a649`, 기존 검수 DB `datco_test_4c55593f248e`는 revision `fc07d0012026` 및 기존 UNIQUE를 유지한다. 읽기 전용으로 수집한 전후 테이블별 행 수·전체 행 해시와 스키마 revision 비교가 동일했다. Private 증거는 `storage/private/runtime/ux-v142/protected-before.json`, `protected-after.json`에 보관한다.

| 실행 | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Backend 단위 회귀 | 108 | 0 | 0 |
| CI 지정 PostgreSQL 회귀 | 208 | 0 | 1 |
| Backend 전체 361건 최초 실행 | 354 | 6 | 1 |
| 로컬 fixture의 Capability 전체 재검증 | 28 | 0 | 0 |
| 실제 Web/API/Worker/PostgreSQL Playwright 전체 | 45 | 0 | 0 |

전체 Backend 최초 실패 6건은 `DATCO_CI_SYNTHETIC=1`이 축약한 기능 목록과 실제 649개 기능을 전제로 한 `test_capability_scenarios.py`의 기대값 불일치였다. 실제 로컬 fixture를 사용하는 새 격리 DB에서 해당 파일 전체 28건을 재실행해 모두 통과했다. 최초 결과를 지우거나 제품·테스트 기대값을 수정하지 않았다. 테스트별 최종 결과는 360 PASS / 0 미해결 FAIL / 1 SKIP이며 단일 실행 360 PASS로 표기하지 않는다.

SKIP 1건은 저장된 한국어 Live 공고 문서를 명시적으로 제공해야 하는 `test_real_korean_sources_worker_content_and_review_in_isolated_schema`다. 합성 CI 환경에 실문서를 복사하거나 Live 수집을 실행하지 않았다.

lint, production build(TypeScript 포함), API_TYPES_MATCH 및 diff 검사는 PASS다. 로컬 OCR Adapter 환경변수를 빠뜨린 최초 단위 실행 2건은 기존 Docker OCR 설정을 지정한 재실행에서 통과했다. build 최초 실행은 Next.js 업그레이드 안내로 종료했고 안내된 동일 명령 재실행은 통과했다. Next.js 버전·보안 설정은 변경하지 않았다.

Private 실행 증거: `storage/private/runtime/ux-v142/`의 `unit-approved.xml`, `integration-full.log`, `backend-all-approved.log`, `backend-local-scenarios-approved.log`, `e2e-full.log`, `quality-final.json`, `lint-approved.log` 및 `api-types-approved/`. 전용 CI harness가 생성한 회귀 DB/역할은 실행 후 정리했고 사용자 재검증 환경은 유지한다.

Commit·Push 후 새 HEAD의 GitHub CI 결과는 Draft PR #14와 최종 보고에 별도로 기록한다. 기존 HEAD의 CI 성공을 새 HEAD의 성공으로 간주하지 않는다.

## 적용 제한 및 사용자 검증

기존 업무 DB와 기존 사용자 검수 DB에는 Migration을 실행하지 않는다. 운영 배포, 원본 영구 삭제, 백업 파기, 기존 Evidence/제출 이력 변경, Next.js 업그레이드, PR Merge/Draft 해제는 범위 밖이다. 물리 삭제는 **POLICY_BLOCKED**이며 파기 권한·참조 검사·보존기간·백업 처리 정책의 별도 승인이 필요하다.

새 격리 검증 환경은 `http://localhost:58936/login`이다. 기존 검수 환경과 별도 DB를 사용한다. 계정·비밀번호는 Git에 포함하지 않는 `storage/private/runtime/ux-v142/test-validation/f644bc4c1a25/credentials.private.json`을 사용한다. 같은 디렉터리의 `TEST-reregister.pdf`가 합성 검증 원본이다. 로컬 프로세스가 실행되는 동안 접속할 수 있다.

1. 기업 계정으로 로그인하고 C07에서 제공된 합성 PDF를 업로드한다.
2. 자료함 표시를 확인한 후 등록 취소하고 F5 후 제외 상태를 확인한다.
3. C06에서 같은 PDF를 첨부·저장하고 F5한다. C07에서 새 File ID의 활성 등록을 확인한다.
4. C06 첨부를 해제·저장하고 F5 후 해제 유지를 확인한다. 과거 제출 Version과 원본 다운로드는 유지되어야 한다.
5. 다른 기업 계정으로 기존·신규 파일 URL에 접근하면 차단되어야 한다.

USER_ACCEPTANCE: PENDING. 사용자 검증을 기다리며 SYSTEM_ACCEPTANCE나 기존 업무 환경 적용 완료를 주장하지 않는다.
