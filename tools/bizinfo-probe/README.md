# 기업마당 독립 Probe

Collector 본코드가 아닌 최소 연결/구조 확인용 도구다. Node.js v24.19.0에서 추가 패키지 없이 실행했다.

Project Root의 `.env`에 로컬에서 `BIZINFO_API_KEY`를 준비한다. Key를 채팅/소스/로그에 넣지 않는다.

```powershell
node tools/bizinfo-probe/probe.cjs --check
node tools/bizinfo-probe/probe.cjs
```

`--check`는 변수 존재만 확인하며 API를 호출하지 않는다. 일반 실행은 공식 지원사업 GET Endpoint에 `searchCnt=2`, `pageUnit=1`, `pageIndex=1,2`로 최대 2회 호출한다. 매 실행은 외부 호출을 다시 수행하므로 불필요하게 반복하지 않는다. 자동 재시도/첨부 다운로드/상세 조회/잘못된 Key 테스트는 없다.
redirect를 따라가지 않고 요청별 30초 timeout, 응답 1MB 제한을 둔다. 원문 URL/에러/응답은 콘솔에 출력하지 않으며 실패는 고정 메시지만 출력한다.

`observations.json`은 HTTP 상태, Content-Type, 필드 이름/타입/값 존재, 공고 ID와 전체건수만 기록한다. 샘플은 실제 JSON 구조를 보존하되 자유텍스트/HTML/문의처/파일명/외부 URL을 보수적으로 마스킹한다. 기업마당 URL의 허용된 공고/파일 식별 파라미터만 남긴다. Key 포함 여부를 저장 전에 검사한다.
샘플은 구조 검증용이며 의미 있는 Notice/Form 분석이나 다운로드 성공을 증명하지 않는다. 재실행 시 샘플/관찰 파일을 갱신한다. 현재 샘플의 수정시각 값은 마스킹되어 있고 필드 존재는 observations에서 확인된다.

공식 정보: [기업마당 지원사업 API](https://www.bizinfo.go.kr/apiDetail.do?id=bizinfoApi). 관찰 결과와 미확정 사항은 [분석결과](./ANALYSIS.md)를 참조한다.

## 2차 최소 Probe

`node tools/bizinfo-probe/probe.cjs --phase2`로 실행한다. 기존 1차 실행과 산출물은 유지한다.
최대 6회: pageUnit=2/searchCnt=0으로 현재 건수, 마지막 후보, 다음 페이지를 조회한 뒤 기존 공고 1건의 상세와 API가 제공한 파일 URL 2개를 확인한다. 파일은 Range GET 요청 후 최대 64바이트만 검사하고 즉시 스트림을 취소한다. 서버가 Range를 무시할 수 있으므로 전체 파일 전송량을 64바이트로 보장하지는 않는다. 파일 원문/전체 HTML은 저장하지 않는다.
redirect는 기록만 하고 자동 추적하지 않으며 공식 기업마당 HTTPS Domain만 허용한다. 실행마다 호출하므로 반복 실행을 피한다. 결과는 `phase2-observations.json`, 해석은 `PHASE2_ANALYSIS.md`에 구분한다. 오류는 원문 대신 고정 메시지만 남긴다.
