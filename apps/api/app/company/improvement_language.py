"""Versioned, bounded Korean business expressions. No language model or network."""
import re
from decimal import Decimal

DOMAINS=(
 ('PRODUCTION','생산·제조',r'생산|작업지시|공정|제조|가동|설비'),
 ('QUALITY','품질',r'품질|불량|검사|하자|추적성'),
 ('LOGISTICS','물류·재고',r'물류|재고|입출고|출하|배송|창고|운송'),
 ('HR','인사',r'인사|근태|휴가|급여|인력배치|출퇴근'),
 ('ACCOUNTING','회계',r'회계|전표|결산|세무|매입|매출|정산'),
 ('COLLABORATION','협업·사무',r'협업|결재|메신저|그룹웨어|문서공유|일반\s*사무'),
)
NEGATIVE=r'제외|불필요|필요(?:가|는)?\s*없|원하지\s*않|하지\s*않|대상(?:이)?\s*아(?:니|님)'
CLAUSE_BOUNDARY=r'[,，;；\n。.!?]|(?:하지만|반면|다만|그러나|하며|하고|하되|대신)\s+'

def active_match(text,pattern):
    for match in re.finditer(pattern,text):
        end=re.search(CLAUSE_BOUNDARY,text[match.end():])
        tail=text[match.end():match.end()+(end.start() if end else 35)][:35]
        head=re.split(CLAUSE_BOUNDARY,text[:match.start()])[-1][-12:]
        if not re.search(NEGATIVE,match.group(0)) and not re.search(NEGATIVE,tail) and not re.search(r'(?:제외(?:\s*(?:범위|대상))?|불필요)\s*[:：]?\s*$',head):return match
    return None

def classify_domains(spans):
    result=[]
    for identifier,label,pattern in DOMAINS:
        sources=[s for s in spans if s.get('kind')=='IMPROVEMENT' and active_match(s['quote'],pattern)]
        if sources:result.append(dict(id=identifier,label=label,evidence=sources,
            uncertainty='명시 업무 표현 분류 후보; 업종·솔루션 제공 가능성 확정 아님'))
    return result

ANSWERS={
 'R02':r'(?:현재|현행|평균|불량률|처리시간|소요시간).{0,35}?\d+(?:\.\d+)?\s*(?:%|분|초|시간|건)',
 'R03':r'(?:개선\s*목표|목표|희망\s*결과|개선\s*후)\s*(?:은|는|:|：)\s*\S+|(?:줄이|단축|향상|낮추|높이).{0,16}(?:싶|희망|목표|원합)',
 'R04':r'(?:적용\s*범위|대상\s*범위|대상|범위)\s*(?:은|는|:|：)\s*\S+|(?:공장|부서|물류센터|사업장).{0,20}(?:에만|만\s*대상)',
 'R05':r'(?:현재|기존|현행)\s*(?:회계\s*)?프로그램[^,，。.!?;；\n]{0,25}(?:유지|사용)|(?:현재|기존|현행)\s*(?:설비|시스템|ERP|MES)\s*(?:은|는|:|：)\s*\S+|(?:현재|기존).{0,12}(?:엑셀|스프레드시트|수기|SAP|ERP|MES)(?:로|를|을|\s)|기존\s*(?:시스템|설비)\s*(?:없음|미사용)|연계\s*대상\s*(?:은|는|:|：)\s*\S+',
 'R06':r'(?:예산|사업비|견적)\s*(?:은|는|도|:|：)?\s*(?:[0-9][0-9,.]*\s*(?:원|천원|만원|백만원|억원|KRW|USD)|없음|미정|미확정|미결정|모름|추후\s*확인)',
 'R07':r'(?:일정|착수|완료|납기|기한|도입\s*(?:시기|시점))\s*(?:은|는|도|:|：)?\s*(?:20\d{2}[^\n]{0,30}|\d+\s*(?:개월|주|월)|미정|미확정|미결정|모름|추후\s*확인)',
}

def unresolved_integration(spans):
    # An explicitly unanswered integration question is distinct from the known
    # current program. Never treat it as confirmed integration availability.
    pattern = r"(?:연계|연동|인터페이스)[^,，。.!?;；\n]{0,45}?(?:미정|미확정|추가\s*확인|재확인|확인(?:이|은|도)?\s*필요|검토(?:가|는|도)?\s*필요)"
    return next((source for source in spans if source.get('kind') in ('IMPROVEMENT', 'RESPONSE') and active_match(source['quote'], pattern)), None)


def answer_span(rule,spans,present):
    if rule == 'R05':
        unresolved = unresolved_integration(spans)
        if unresolved:
            return unresolved, 'DECLARED_UNKNOWN'
    desired={line.strip() for source in spans if source.get('field') in ('goal','to_be')
             for line in source['quote'].splitlines() if line.strip()}
    for source in spans:
        goal_section=source.get('field') in ('goal','to_be')
        lines=source['quote'].replace('\\n','\n').splitlines()
        if rule in ('R06','R07'):
            lines=[part for line in lines for part in re.split(r'(?<=이며)\s*|(?<=이고)\s*',line)]
        for line in lines:
            # Old composed original_text mirrors typed goals. A bare target
            # number on the next line must never become a current measurement.
            if rule=='R02':
                if source.get('field') in ('goal','to_be'):
                    continue
                if re.match(r'\s*(?:희망\s*개선목표|개선\s*목표|목표|To-Be)\s*(?:\([^)]*\))?\s*[:：]?',line,re.I):
                    goal_section=True
                elif re.match(r'\s*(?:현재\s*문제점|현재\s*업무|현황|현재\s*(?:처리|소요|불량|재고|평균|기준|값)|현재값|실측)',line):
                    goal_section=False
                if goal_section or line.strip() in desired:
                    continue
                baseline=bool(re.search(r'현재|실측|측정|기준|평균|발생',line))
                if not baseline and re.search(r'목표|희망|예상|추정',line):
                    continue
            explicit_scope = rule=='R04' and re.search(r'(?:[1-9]\d*\s*(?:개|곳)\s*(?:사업장|창고|공정|라인|부서)|(?:사업장|창고|공정|라인|부서)\s*[1-9]\d*\s*(?:개|곳))',line)
            current_tool = rule=='R05' and source.get('field') in ('as_is','problem') and active_match(line,r'(?:엑셀|Excel|수기|스프레드시트|ERP|MES).{0,12}(?:관리|기록|사용)')
            if explicit_scope or current_tool:
                return source,'FOUND'
            subject={'R06':r'예산|사업비|견적','R07':r'일정|착수|기한|납기|도입\s*(?:시기|시점)'}.get(rule)
            combined=r'(?:예산|사업비|견적|일정|착수|기한|납기|도입\s*(?:시기|시점))'
            if subject and re.search(r'(?:'+subject+r')(?:\s*(?:과|와|및|·|/)\s*'+combined+r')*\s*(?:은|는|도)?\s*(?:아직|현재)?\s*(?:미정|미확정|미결정|모름)',line):
                return source,'DECLARED_UNKNOWN'
            if subject and re.search(r'(?:'+subject+r')[^,;.!?]{0,80}(?:현재|아직)\s*(?:미정|미확정|미결정|모름)',line):
                return source,'DECLARED_UNKNOWN'
            if subject and re.search(r'(?:'+subject+r').{0,35}(?:추후|별도|근거\s*확인\s*후).{0,12}(?:산정|확인|검토)',line):
                return source,'DECLARED_UNKNOWN'
            found=re.search(present,line) or re.search(ANSWERS.get(rule,r'(?!)'),line)
            if found:
                value=line[found.start():found.end()+12]
                return source,'DECLARED_UNKNOWN' if re.search(r'미정|미확정|미결정|모름|추(?:가|후)\s*확인',value) else 'FOUND'
    return None,None

UNITS={'초':('TIME',Decimal(1)),'분':('TIME',Decimal(60)),'시간':('TIME',Decimal(3600)),
       '원':('KRW',Decimal(1)),'천원':('KRW',Decimal(1000)),'백만원':('KRW',Decimal(1000000)),'만원':('KRW',Decimal(10000)),'억원':('KRW',Decimal(100000000)),
       '%':('PERCENT',Decimal(1)),'건':('COUNT',Decimal(1)),'명':('PERSON',Decimal(1))}

def scalar_observations(spans):
    groups={}
    for source in spans:
        for line in source['quote'].splitlines():
            match=re.fullmatch(r'\s*(불량률|처리시간|소요시간|재고오차|사업비|예산)\s*\(([^)]{1,100})\)\s*[:：]\s*((?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)\s*(억원|백만원|만원|천원|시간|초|분|원|%|건|명)\s*',line)
            if not match or not re.search(r'20\d{2}|최근\s*\d+\s*(?:일|주|개월|월|년)|[1-4]\s*분기|[1-9]\d?\s*월',match[2]):continue
            dimension,factor=UNITS[match[4]]
            key=(match[1],re.sub(r'\s+','',match[2]),dimension)
            groups.setdefault(key,{}).setdefault(Decimal(match[3].replace(',',''))*factor,source)
    return groups
