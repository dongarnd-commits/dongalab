"""Bounded technical projection: unknown values are scanned, never retained."""
import codecs
import hashlib
import os
import re


class ProjectionRejected(ValueError):
    pass


def project_manifest(path):
    strings=set('nonce head root host db role container volume origin caddy'.split())
    ports=set('https_port api_port web_port pg_port'.split());allowed=strings|ports|{'preparation'};result={}
    decoder=codecs.getincrementaldecoder('utf-8')('strict');digest=hashlib.sha256();c=None;total=0
    def bad():raise ProjectionRejected('MANIFEST_PROJECTION_REJECTED')
    def advance():
        nonlocal c,total
        while True:
            raw=source.read(1)
            if type(raw) is not bytes or len(raw)>1:bad()
            total+=len(raw)
            if total>65536:bad()
            digest.update(raw);text=decoder.decode(raw,final=not raw)
            if text or not raw:
                if len(text)>1:bad()
                c=text or None;return
    def take():
        if c is None:bad()
        item=c;advance();return item
    def expect(item):
        if c!=item:bad()
        take()
    def whitespace():
        while c is not None and c in ' \t\r\n':take()
    def hex4():
        item=''.join(take() for _ in range(4))
        if not re.fullmatch(r'[0-9a-fA-F]{4}',item):bad()
        return int(item,16)
    def string(mode=None):
        expect('"');parts=[] if mode else None;length=0;key_hash=hashlib.sha256()
        escapes={'"':'"','\\':'\\','/':'/','b':'\b','f':'\f','n':'\n','r':'\r','t':'\t'}
        while c!='"':
            item=take()
            if ord(item)<32:bad()
            if item=='\\':
                escape=take()
                if escape=='u':
                    number=hex4()
                    if 0xD800<=number<=0xDBFF:
                        expect('\\');expect('u');low=hex4()
                        if not 0xDC00<=low<=0xDFFF:bad()
                        number=0x10000+((number-0xD800)<<10)+low-0xDC00
                    elif 0xDC00<=number<=0xDFFF:bad()
                    item=chr(number)
                elif escape in escapes:item=escapes[escape]
                else:bad()
            length+=1
            if mode=='key':
                if length>512:bad()
                key_hash.update(item.encode('utf-8'))
                if length>32:parts=None
            if mode=='value' and length>2048:bad()
            if parts is not None:parts.append(item)
        expect('"');item=''.join(parts) if parts is not None else None
        return (item,key_hash.digest()) if mode=='key' else item
    def number(keep):
        parts=[]
        def emit():
            item=take()
            if keep:
                parts.append(item)
                if len(parts)>16:bad()
        def digit():return c is not None and c in '0123456789'
        if c=='-':emit()
        if c=='0':emit()
        elif c is not None and c in '123456789':
            while digit():emit()
        else:bad()
        if c=='.':
            emit()
            if not digit():bad()
            while digit():emit()
        if c in ('e','E'):
            emit()
            if c in ('+','-'):emit()
            if not digit():bad()
            while digit():emit()
        if not keep:return None
        item=''.join(parts)
        if not re.fullmatch(r'0|[1-9][0-9]{0,4}',item):bad()
        return int(item)
    def value(keep,depth):
        if depth>16:bad()
        whitespace()
        if c=='"':return string('value' if keep else None)
        if c in ('{','['):
            if keep:bad()
            if c=='{':object_value(depth);return None
            expect('[');whitespace()
            if c!=']':
                while True:
                    value(False,depth+1);whitespace()
                    if c!=',':break
                    expect(',');whitespace()
            expect(']');return None
        for literal,scalar in (('true',True),('false',False),('null',None)):
            if c==literal[0]:
                for char in literal:expect(char)
                return scalar if keep else None
        if c=='-' or (c is not None and c in '0123456789'):return number(keep)
        bad()
    def object_value(depth):
        expect('{');whitespace();seen=set()
        if c!='}':
            while True:
                key,fingerprint=string('key')
                if fingerprint in seen or len(seen)>=512:bad()
                seen.add(fingerprint);whitespace();expect(':');keep=depth==0 and key in allowed
                scalar=value(keep,depth+1)
                if keep:result[key]=scalar
                whitespace()
                if c!=',':break
                expect(',');whitespace()
        expect('}')
    try:
        with path.open('rb') as source:
            before=os.fstat(source.fileno());advance()
            if c=='\ufeff':advance()
            whitespace()
            if c!='{':bad()
            object_value(0);whitespace();after=os.fstat(source.fileno())
            if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):bad()
            if c is not None or not (strings|ports)<=result.keys():bad()
            if any(type(result[k]) is not str or not result[k] or any(ord(x)<32 or ord(x)==127 for x in result[k]) for k in strings):bad()
            if any(type(result[k]) is not int or not 1024<=result[k]<=65535 for k in ports):bad()
            if 'preparation' in result and type(result['preparation']) is not bool:bad()
            if not re.fullmatch(r'[a-f0-9]{12}',result['nonce']) or not re.fullmatch(r'[a-f0-9]{40}',result['head']):bad()
            if not re.fullmatch(r'[A-Za-z0-9.-]{1,253}',result['host']):bad()
            if result['origin']!=f'https://{result["host"]}:{result["https_port"]}':bad()
            return result,digest.hexdigest()
    except Exception:
        result.clear();raise ProjectionRejected('MANIFEST_PROJECTION_REJECTED') from None