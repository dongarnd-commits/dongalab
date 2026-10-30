# 실행계획

기준 main10d3d8b. 통합 integrate/datco-one-mvp-v1 / dongalab-mvp-v1. 기존 Worktree·DB·HTTPS 보존.

| 단계 | 담당 | 작업/의존성 | 증거 |
|---|---|---|---|
| P0 | root+Agent2 | 실제 구현 조사 | GAP_MATRIX·기존 PR/CI |
| P1 | root | MVP overlay·공통 API/결과/보존 계약 | MASTER_DEVELOPMENT_CONTRACT·기준문서 |
| P2 | root | registry·Rulev3·검토답변·Evidence·분석UI | Unit 평가/PG/분석E2E |
| P3/P5 | solutions Agent | 추천·구성·Matching·16절 | 기존 Guard 회귀·문서 검증 |
| P4/P6 | portals Agent | 공고검색·Admin·후속6메뉴 | API/포털 E2E |
| P7 | root | 검증된 Feature 통합 | 전체 Unit/PG/Frontend/E2E·M01~M18 |
| 제출 | root | 증빙/통합 Draft PR | 사용자 인수 대기, main/배포 별도 승인 |

main.py·API 생성 타입·CI 하네스·Migration·기준문서는 root 소유. Agent는 지정 모듈/테스트만 수정하고 공유 변경은 메시지로 조정한다. 기존 테스트 삭제/완화 금지. 외부 Blocker로 독립 개발을 중단하지 않는다.
