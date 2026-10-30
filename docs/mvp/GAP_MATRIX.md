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
