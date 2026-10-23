"""One-document PDFium process; bounded, pipe-only Tesseract adapter."""
import io,json,os,re,shutil,subprocess,sys,time
from uuid import uuid4
from app.company.documents import MAX_UPLOAD,DocumentError

# Selected after synthetic registration scans are compared; this is a render
# setting, never a claim that OCR text is accurate or human-confirmed.
TABLE=os.environ.get('DATCO_OCR_CATEGORY_TABLE')=='1'
DPI=180 if TABLE else 300
PSM=6 if TABLE else 4

def recognize(png):
    image=os.environ.get('DATCO_OCR_DOCKER_IMAGE','')
    name='datco-ocr-'+uuid4().hex
    docker=bool(image)
    if docker:
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._/:-]{0,150}',image):raise DocumentError('OCR_UNAVAILABLE')
        command=['docker','run','--rm','--name',name,'--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=512m','--cpus=2','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','-i',image]
    else:
        binary=shutil.which('tesseract')
        if not binary:raise DocumentError('OCR_UNAVAILABLE')
        watchdog=shutil.which('timeout') if os.name!='nt' else None
        if not watchdog:raise DocumentError('OCR_UNAVAILABLE')
        command=[watchdog,'--kill-after=2s','15s',binary]
    command+=['stdin','stdout','-l','kor+eng','--oem','1','--psm',str(PSM)]
    try:
        r=subprocess.run(command,input=png,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=12,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if r.returncode in (124,137):raise DocumentError('OCR_TIMEOUT')
        if r.returncode:raise DocumentError('OCR_UNAVAILABLE')
        if len(r.stdout)>200_000:raise DocumentError('OCR_TEXT_LIMIT')
        return r.stdout.decode('utf-8',errors='strict')
    except subprocess.TimeoutExpired:raise DocumentError('OCR_TIMEOUT') from None
    except (OSError,UnicodeError):raise DocumentError('OCR_FAILED') from None
    finally:
        if docker:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)

def run(raw):
    import pypdfium2 as pdfium
    if not raw or len(raw)>MAX_UPLOAD:raise DocumentError('UPLOAD_SIZE_INVALID')
    deadline=time.monotonic()+40
    result=[]
    with pdfium.PdfDocument(raw) as document:
        if len(document)>10:raise DocumentError('OCR_PAGE_LIMIT')
        for n in range(len(document)):
            if time.monotonic()>deadline:raise DocumentError('OCR_TIMEOUT')
            page=document[n]
            try:
                width,height=page.get_size()
                if width*height*(DPI/72)**2>20_000_000:raise DocumentError('OCR_PIXEL_LIMIT')
                bitmap=page.render(scale=DPI/72)
                try:
                    image=bitmap.to_pil();out=io.BytesIO();image.save(out,format='PNG');image.close()
                finally:bitmap.close()
                text=recognize(out.getvalue())
                if text.strip():result.append({'descriptor':f'PDF page {n+1} / local Tesseract kor+eng OCR / {DPI} dpi / psm {PSM}'+(' / category table' if TABLE else ''),'page':n+1,'text':text})
            finally:page.close()
    return {'locations':result}

if __name__=='__main__':
    try:result=run(sys.stdin.buffer.read(MAX_UPLOAD+1))
    except DocumentError as e:result={'error':str(e)}
    except Exception:result={'error':'OCR_FAILED'}
    sys.stdout.write(json.dumps(result,ensure_ascii=False))
