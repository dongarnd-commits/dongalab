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
NEGATIVE=r'제외|불필요|필요(?:가|는)?\s*없|도입하지\s*않|검토하지\s*않|대상(?:이)?\s*아(?:니|님)'

def active_match(text,pattern):
    for match in re.finditer(pattern,text):
        end=re.search(r'[,，;；\n。.!?]',text[match.end():])
        tail=text[match.end():match.end()+(end.start() if end else 35)][:35]
        head=re.split(r'[,，;；\n。.!?]',text[:match.start()])[-1][-12:]
        if not re.search(NEGATIVE,tail) and not re.search(r'(?:제외|불필요)\s*[:：]?\s*$',head):return match
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
 'R05':r'(?:현재|기존|현행)\s*(?:설비|시스템|ERP|MES)\s*(?:은|는|:|：)\s*\S+|(?:현재|기존).{0,12}(?:엑셀|스프레드시트|수기|SAP|ERP|MES)(?:로|를|을|\s)|기존\s*(?:시스템|설비)\s*(?:없음|미사용)|연계\s*대상\s*(?:은|는|:|：)\s*\S+',
 'R06':r'(?:예산|사업비|견적)\s*(?:은|는|:|：)?\s*(?:[0-9][0-9,.]*\s*(?:원|만원|억원|KRW|USD)|없음|미정|모름|추후\s*확인)',
 'R07':r'(?:일정|착수|완료|납기|기한|도입시기)\s*(?:은|는|:|：)?\s*(?:20\d{2}[^\n]{0,30}|\d+\s*(?:개월|주|월)|미정|모름|추후\s*확인)',
}

def answer_span(rule,spans,present):
    for source in spans:
        found=re.search(present,source['quote']) or re.search(ANSWERS.get(rule,r'(?!)'),source['quote'])
        if found:
            value=source['quote'][found.start():found.end()+12]
            return source,'DECLARED_UNKNOWN' if re.search(r'미정|모름|추후\s*확인',value) else 'FOUND'
    return None,None

UNITS={'초':('TIME',Decimal(1)),'분':('TIME',Decimal(60)),'시간':('TIME',Decimal(3600)),
       '원':('KRW',Decimal(1)),'만원':('KRW',Decimal(10000)),'억원':('KRW',Decimal(100000000)),
       '%':('PERCENT',Decimal(1)),'건':('COUNT',Decimal(1)),'명':('PERSON',Decimal(1))}

def scalar_observations(spans):
    groups={}
    for source in spans:
        for line in source['quote'].splitlines():
            match=re.fullmatch(r'\s*(불량률|처리시간|소요시간|재고오차|사업비|예산)\s*\(([^)]{1,100})\)\s*[:：]\s*([0-9]+(?:\.[0-9]+)?)\s*(억원|만원|시간|초|분|원|%|건|명)\s*',line)
            if not match or not re.search(r'20\d{2}|최근\s*\d+|분기|월|기간',match[2]):continue
            dimension,factor=UNITS[match[4]]
            key=(match[1],re.sub(r'\s+','',match[2]),dimension)
            groups.setdefault(key,{}).setdefault(Decimal(match[3])*factor,source)
    return groups
