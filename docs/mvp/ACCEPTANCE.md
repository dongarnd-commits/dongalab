# MVP 전용 인수

M01~M18은 이번 MVP 범위다. H01~H32 전체 완료를 뜻하지 않는다. 현재 아래는 계획이며 실행 후 증거를 갱신한다.

| ID | 정상 흐름 | 핵심 예외 |
|---|---|---|
| M01 | 로그인·기업/사업장 등록 | Role/Scope·중복·F5 |
| M02 | 자료·원본/Evidence | 타기업·digest·추출 실패 |
| M03 | 개선요구·정확한 제출 | Draft≠Submitted·불변 |
| M04 | Rule·구조화·원인후보·검토 | 숫자/원인 날조 금지·Version |
| M05 | 부족정보·응답·검토 | 중복질문·미검사≠부재 |
| M06 | 발행 서비스·Revision | 비발행/가짜 서비스 금지 |
| M07 | 단독/복합 후보 | 동의어/부정·과다추천 |
| M08 | 역할·연계·Coverage | 전제/제외·미해결·근거 |
| M09 | 실제 저장공고 검색 | LIVE/SNAPSHOT 구분·없음 |
| M10 | 조건·자격 검토 | UNKNOWN≠충족 |
| M11 | 3자 매칭·사람 판단 | stale/타기업 차단 |
| M12 | 16절 표준초안 | PROPOSABLE 실제 Proof |
| M13 | 내용 검토·Version | 이전11절/승인·재승인 |
| M14 | 동일Version DOCX/PDF | 한글·절·내용·권한·실패Retry |
| M15 | 전달·회사 다운로드 | 자동발송없음·미전달/타기업차단 |
| M16 | 수정·과거이력·재로그인 | 과거 승인 새Version 자동적용금지 |
| M17 | Admin4영역 | Secret/권한상속없음·기존grant |
| M18 | Rule만실행·외부미설정 | UI/API/Worker 차단·외부호출0 |

제조/품질·물류·인사·회계·사무/협업 합성 평가별 기대 근거·질문·추천·금지 판정을 고정한다. Rule 수/PASS 수만으로 정확도를 주장하지 않는다. 실제 자료는 Fixture로 사용하지 않는다.

필수 구현/검증 모두 완료시 MVP_READY_FOR_USER_ACCEPTANCE. 미구현 PARTIAL, 필수 외부조건 미충족 BLOCKED, 중요 검증실패 FAILED. 사용자 인수/main Merge/HTTPS 배포는 별도다.
