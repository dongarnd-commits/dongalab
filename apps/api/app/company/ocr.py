"""Local OCR port. PDFium runs in a child process, never concurrent API threads.
No source/OCR text is logged or sent to a remote service. No staging files.
"""
import json,os,subprocess,sys
from pathlib import Path
from app.company.documents import DocumentError, Location

def ocr_pdf(content: bytes) -> tuple[Location, ...]:
    env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    try:
        r=subprocess.run([sys.executable,'-m','app.company.ocr_worker'],input=content,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=50,env=env,cwd=Path(__file__).resolve().parents[2],creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if len(r.stdout)>3_000_000:raise DocumentError('OCR_TEXT_LIMIT')
        result=json.loads(r.stdout)
        if r.returncode or result.get('error'):raise DocumentError(result.get('error','OCR_FAILED'))
        return tuple(Location(**l) for l in result['locations'])
    except DocumentError:raise
    except subprocess.TimeoutExpired:raise DocumentError('OCR_TIMEOUT') from None
    except (OSError,ValueError,KeyError):raise DocumentError('OCR_UNAVAILABLE') from None
