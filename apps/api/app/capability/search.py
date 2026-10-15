"""Explainable catalog retrieval, not suitability/eligibility scoring."""
import re,unicodedata

# These alone describe generic actions/provenance, not a customer's business domain.
GENERAL={'실제','자료','업무','관리','기능','기술','전문','시스템','정보','데이터','현황','등록','처리','검색','조회',
 '지원','원천','검토','조건','기업','회사','수량','수기','수기로','입력','기록','제공','필요','대상','모든','새로',
 '개발','하고','싶습니다','맞지','않고','어렵습니다','정확하게','체계적으로','많고','자동','test','dmp','capability'}
PARTICLES=('으로','에서','하고','합니다','하며','하고싶습니다','입니다','습니다','으로는','에는','은','는','을','를','과','와','가','의','로')
OPERATIONS=('처리','등록','현황','관리','조회','검색','지정','설정','기안','수불부')

def normalize(value):
 return re.sub(r'[^가-힣a-z0-9]+',' ',unicodedata.normalize('NFKC',value).lower()).strip()
def compact(value):return normalize(value).replace(' ','')

def query_terms(query):
 value=normalize(query);tokens=[]
 for token in value.split():
  stripped=token
  for suffix in PARTICLES:
   if stripped.endswith(suffix) and len(stripped)-len(suffix)>=2:
    stripped=stripped[:-len(suffix)];break
  tokens.extend([token,stripped])
  for suffix in OPERATIONS:
   if stripped.endswith(suffix) and len(stripped)-len(suffix)>=2:tokens.append(stripped[:-len(suffix)])
 joined=compact(query)
 # Bounded conventional business compounds; these are not fixture/company identifiers.
 for term in ('재고','입고','출고','작업실적','품질','불량','생산','문서','결재','파일'):
  if term in joined:tokens.append(term)
 if '입출고' in joined:tokens.extend(['입고','출고'])
 if '생산' in joined:tokens.extend(['작업실적','공정'])
 return list(dict.fromkeys(t for t in tokens if len(t)>=2 and t not in GENERAL))[:30]

def search_reasons(query,capability,features):
 if not query.strip():return []
 terms=query_terms(query);q=compact(query);reasons=[]
 # Deliberately omit IDs, origins, availability, prerequisites, exclusions and audit notes.
 fields=[('서비스명',capability['service']),('서비스 설명',capability.get('description',''))]
 fields.extend(('해결 문제',p) for p in capability['problems'])
 for feature in features:
  fields.extend([('기능명 '+feature['name'],feature['name']),('기능 설명 '+feature['name'],feature['description'])])
 fields.extend(('기능 역할',f['role']) for f in capability['functions'])
 for label,value in fields:
  text=compact(value)
  found=[t for t in terms if compact(t) in text]
  # A complete two-word business phrase remains searchable even when individual words are weak.
  words=normalize(value).split()
  phrase_match=label in ('서비스명','해결 문제') and len(words)>=2 and len(text)>=4 and text in q
  if found or phrase_match:
   reasons.append(label+': '+(', '.join(found) if found else value))
 return list(dict.fromkeys(reasons))[:30]
