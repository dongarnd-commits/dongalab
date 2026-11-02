# 최종 사용자 통합 인수 절차

대상은 Draft PR의 integrate/datco-one-mvp-v1 코드다. 기존 공동 HTTPS(10.10.10.145:8443)는 기존 검수판을 그대로 유지하므로 새 MVP가 배포되었다고 해석하지 않는다. main Merge/실서비스 적용/공유 DB Migration은 사용자 인수 뒤 별도 승인한다.

## 인수 전 확인

1. Draft PR HEAD와 GitHub Checks, ACCEPTANCE의 실행 근거를 확인한다. 자동 검증과 사용자 인수를 구분한다.
2. 검수는 승인된 합성자료·작업 소유의 격리 DB/Private Files/별도 API·Worker·Frontend를 사용한다. 실제 기업 원본/계정을 복제하지 않는다.
3. 재현 자동 검증은 새 개발 Worktree에서 apps/api의 Python으로 tests/slice2_local.py e2e를 실행한다. 하네스가 별도 nonce DB/Role/포트를 검증하고 자기 프로세스/DB만 정리한다. 일반 .env DB로 fallback하지 않는다.
4. 수동 인수 환경·역할별 합성 계정·URL은 해당 격리 실행에서 확인한다. 이번 개발결과로 공유 HTTPS 서비스가 자동 갱신되지는 않는다.

## 한 기업으로 확인할 정상 업무

| 순서 | 역할 | 확인할 업무 |
|---|---|---|
| 1 | 기업 Editor | 기업/사업장, 재무/이력, 파일 및 직접 입력 자료를 저장하고 F5·재로그인 |
| 2 | 기업/Operator | 파일 추출 후보의 기업 ACK와 운영자 Fact 확인을 별도로 수행, 원본 digest 비교 |
| 3 | 기업 | 개선요구 As-Is/To-Be·첨부를 제출하고 Draft 추가가 기존 제출본을 바꾸지 않는지 확인 |
| 4 | Operator | 제출본 상세에서 Rule 자동 분석, 검토 범위/근거/불확실성·부족정보·충돌 확인 |
| 5 | Operator/기업 | 후보 선택·명시 검토→영속 요청 초안→최종 확인 전0건→기업 답변→검증답변 재분석 |
| 6 | Operator/기업 | 제출v1 Run·최신 Review 출처를 명시해 구조화v2 저장→기업 ACK v2→별도 OP CONFIRM |
| 7 | Admin/Operator | 실제 원천 기능에 연결해 발행한 상위 서비스 조회·근거 있는 단독/복합 후보 비교 |
| 8 | Operator | 서비스 선택, 각 역할·연계 데이터/업무·선행조건, 해결/일부/미해결 Coverage를 명시 저장 |
| 9 | Operator | 실제 저장 Notice 탐색, LIVE/합성 원천·기간·요건 Version을 구분하고 원문 기반 Human Review |
| 10 | Operator | 동일 회사/구조화/Composition/Requirement Version으로 Match 후 UNKNOWN·반대 근거 확인, 항목별 검토/PROPOSABLE |
| 11 | Operator | MVP_16 제안 초안 16개 항목 보완·새 Version 저장·정확 내용 Review |
| 12 | Operator/기업 | 같은 ProposalVersion DOCX/PDF 생성·한글/본문/Version 확인→지정 기업계정에 명시 전달→회사 조회·다운로드·수정요청 |
| 13 | Admin | 최소 실제 집계·Catalog·기존 사용자 회사접근권한 grant·연동 상태, Operator 업무 대행 불가 확인 |

최소 예외: 타기업 직접 URL/파일, 새 입력·Review 이후 stale 분석/매칭/제안 차단, 무근거 서비스/공고·자격 확정 금지, PDF 실패/부분 추출과 Retry, 전달 취소/Escape/배경 차단/포커스 복귀/이중클릭, 구버전 문서·승인·답변·첨부 이력 보존.

RULE만 사용 가능해야 한다. GPT/GEMINI/CLAUDE/GROK은 모두 NOT_CONFIGURED여야 하며 UI 선택·직접 API 실행이 차단돼야 한다. 외부 계정 로그인/API키/자료 전송 승인은 이번 인수의 선행조건이 아니다.

## 남는 사람의 결정

- 실제 발행할 DATCO 상위 서비스 이름/제공범위/선행조건과 원천 Feature 연결의 사업적 검토.
- 기업 제출자료 및 목표·원인 후보·지원사업 조건·통합 가능성·비용·일정의 실제 확인.
- 제안 내용 확정·지정 회사 전달·회사의 실제 의사결정.
- 조직 공식 제품 승인, 최종 main Merge, 공유 DB 백업/복원 검증과 Migration/HTTPS 적용 승인.
- 외부 AI 공급자별 자격/전송/비용/보존 정책과 실제 연동은 다음 별도 결정.

자동 테스트 통과는 실제 고객 자료의 완전성·신청자격·사업성과·회사 승인·사용자 인수의 자동 확정이 아니다.
