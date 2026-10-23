"""Synthetic Korean registration sources; never real business documents."""
from io import BytesIO
from pathlib import Path
import os,secrets
from PIL import Image,ImageDraw,ImageFont

def number(prefix=None):
    prefix=prefix or str(secrets.randbelow(900_000_000)+100_000_000)
    prefix=prefix[:9].zfill(9);d=list(map(int,prefix));weights=(1,3,7,1,3,7,1,3,5)
    total=sum(a*b for a,b in zip(d,weights))+d[8]*5//10
    return prefix+str((10-total%10)%10)

def scan(number_value=None,company='합성검증기업',certificate=False):
    candidates=[Path('C:/Windows/Fonts/malgun.ttf'),Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')]
    font=next((p for p in candidates if p.exists()),None)
    if not font:raise RuntimeError('KOREAN_TEST_FONT_REQUIRED')
    image=Image.new('RGB',(1654,2339),'white');draw=ImageDraw.Draw(image);f=ImageFont.truetype(str(font),44)
    title='사업자등록증명원' if certificate else '사업자등록증'
    lines=[title,'TEST 합성 문서 - 실제 사업자 아님','상호 : '+company,'사업자등록번호 : '+(number_value or number('123456789')),'대표자 : 홍길동','사업장 소재지 : 서울특별시 합성로 100','사업의 종류 : [업태] 제조업 [종목] 장비 제조 및 유지보수','개업일 : 2020년 01월 01일']
    for i,line in enumerate(lines):draw.text((100,120+i*160),line,font=f,fill='black')
    out=BytesIO();image.save(out,format='PDF',resolution=200);image.close();return out.getvalue()
