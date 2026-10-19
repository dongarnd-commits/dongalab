# PR #9 승인자 조회권한 P1 수정

기준: docs/05_PERMISSION_UI_MATRIX.md의 APPROVAL_ONLY, 지정 ApprovalRequest/ProposalVersion 및 File/Evidence 공개 범위. 새 Role/State/공개정책/Schema/승인 의미를 추가하지 않는다.

## 서버 변경
- Company 원본 File에는 승인 대상 공개 관계가 없다. 같은 기업 Membership은 원본 공개 허가가 아니므로 COMPANY_APPROVER 다운로드는 기본 차단한다. 타기업/미존재 파일은 기존 Scope/존재 검사를 유지한다. Editor/Operator의 허용된 원본 다운로드와 SHA256 검사는 유지한다.
- 승인자의 Company 목록/상세는 기업 ID·이름만 허용한다. 기존 상세 응답 배열 키는 유지하되 비공개 입력·Site 이력·File·Evidence·Candidate·Fact/Review·Improvement/Audit는 빈 배열이다. 중첩 자료를 읽기 전에 분기하므로 뒤늦은 UI 숨김/JSON 문자열 치환이 아니다.
- 기존 GET Improvement context는 Editor/Operator만 호출한다. 내부 CompanyProvider.read는 기존 Proposal 권한·현재성 검증에도 필요하므로 내부 계약을 바꾸지 않는다. 별도 Fact/Evidence GET API를 새로 만들지 않는다.
- 지정 ProposalVersion의 공개 내용·생성 DOCX/PDF는 기존 Proposal API와 동일 지정자/Version/Scope/Guard로 제공한다. Manifest의 참조 ID를 Company 원본 파일 공개 허가로 해석하지 않는다. 원본 공개 관계를 추가하려면 후속 명시 정책/계약 검토가 필요하다.
- Workspace는 기존 ProposalApplication.version 권한 검사를 통과한 요청에만 최소 Site/Improvement 식별 맥락을 제공한다. 공개 Proposal 제목을 표시하고 정확한 ImprovementVersion/SiteVersion을 연결한다. 이는 기존 승인 화면 URL/선택 동선을 보존하기 위한 Projection이며 비공개 Fact/Review나 다른 과제를 공개하지 않는다.

## 영향과 보호
기존 일반 dict 응답/Route를 유지하므로 OpenAPI 계약과 물리 DB/Migration 변경은 없다. 승인자에게 반환하던 비공개 값만 제한한다. 실제 UI/미리보기 코드·기존 Role/State·Membership·Fact/Improvement/Evidence 불변성·Matching 및 Proposal 승인 정책은 바꾸지 않는다. Editor 입력과 Operator 검토는 유지한다. README의 오래된 Provider 미구현 설명만 실제 구현과 동기화한다.

## 검증 대상
실제 격리 PostgreSQL·API·Private Storage에서 동일 기업 비공개 파일, 다른 기업 승인자, Evidence/Fact 식별자 변조, 직접 context, 중첩 내부 메모 차단을 검증한다. 기존 Projection 키와 기업 식별정보, Editor 저장/다운로드, Operator 검토를 확인한다. 동일 기업의 미지정 승인자에 대한 Proposal/파일/승인 차단과 지정 승인자의 정확한 Version 열람/생성 문서 다운로드/결정을 검증한다. 실제 W1 Provider·Membership·Fact·Improvement를 통한 정상 Proposal 생성/지정 승인 및 Workspace 최소 맥락도 HTTP로 확인한다. 합성 TEST 자료이며 실제 기업 적합성 판단이나 사용자 수용을 뜻하지 않는다.

## 검증 이력
최초 nonce 873ca1157153의 Backend는 314 PASS / 1 FAIL / 1 SKIP이었다. 새 테스트가 기존 Decision 응답에 없는 version_id를 읽은 것이 원인이며, 응답 계약을 바꾸지 않고 실제 결정 이력의 정확한 Version을 확인하도록 테스트를 수정했다. 이 실패를 PASS로 재분류하지 않는다. 같은 실행의 보완된 Integration은 200 PASS / 1 SKIP / 116 deselected, Migration check PASS이며 공용 변경 테이블 0·테스트 DB/Role 정리 완료다.

최종 소스의 nonce eb77af86aad0 전체 Backend는 316 PASS / 1 SKIP이다. 신규 보안 HTTP/정상 승인 5건이 포함된다. 실제 Company Provider 정상 승인 및 최소 Workspace 맥락, 원본 기본 차단과 내부 메모 비공개를 검증한다. 별도 관련 Playwright는 1798ae997cdd에서 10 PASS이며 공용 변경 테이블 0·테스트 DB/Role 정리 완료다. UI 미리보기는 9d3c9d59-557에서 5 PASS, lint/typecheck/build/production 404 PASS다. API 타입 비교는 API_TYPES_MATCH이며 생성 타입과 UI 소스 변경은 없다.

전체 Backend에 포함된 SKIP은 저장된 실제 한국어 공고의 선택 검사다. Live API/외부 AI를 호출하거나 실제 업무 DB를 Migration하지 않는다. 미리보기 및 실제 업무 체험 서버를 교체/재시작하지 않는다. Stash와 기존 외부 백업은 보존한다.

최종 eb77af86aad0의 별도 Integration도 200 PASS / 1 SKIP / 116 deselected, Migration upgrade/check PASS다. 공용 변경 테이블 0·테스트 DB/Role 정리를 확인했다. 실제 Proposal Evidence endpoint의 승인자 403/운영자 200을 추가로 명시하고 기존 격리 Runner의 authz 선택지로 보안 5건을 재검증했다: b2aee70582f3, 5 PASS / 44 deselected, Migration check PASS, 공용 변경 테이블 0·테스트 자원 정리 완료. 이 표적 실행은 전체 Backend 재실행으로 합산하지 않는다. 테스트 외 Product 소스는 동일하다.

공개 관계가 없는 원본 Company 파일의 향후 승인자별 공유는 별도 정책/계약 결정 사항이다. 현재 P1 수정에는 필요하지 않으며 기본 차단한다. 기존 지정 Proposal 공개 내용·생성 문서와 실제 승인 동작은 유지한다. main Merge/Draft 해제/업무 DB 적용은 수행하지 않는다.
