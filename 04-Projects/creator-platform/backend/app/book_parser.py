"""Bounded text extraction in a disposable Python process, not an OS sandbox."""
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

MAX_INPUT = 10 * 1024 * 1024
MAX_TEXT = 2000000
PARSE_TIMEOUT = 45
WORKER_PATH = Path(__file__).resolve()
_parse_slot = threading.BoundedSemaphore(1)
ERRORS = {
    'input_limit': (413, '文件限 10 MB'),
    'text_limit': (413, '文本过长，请分册上传'),
    'format': (422, '支持文字版 PDF、UTF-8 TXT、Markdown'),
    'invalid': (422, '无法解析，请使用未加密文字版 PDF 或 UTF-8 文本'),
    'empty': (422, '没有提取到文字，扫描版需先 OCR'),
    'busy': (503, '正在解析另一份资料，本次未开始解析，请稍后重试'),
    'timeout': (422, '资料解析超时，本次未替换原文；请拆分文件或转为 UTF-8 文本后重试'),
    'worker': (503, '资料解析进程未正常完成，本次未替换原文，请稍后重试'),
}

class BookParseError(Exception):
    def __init__(self, code):
        self.code = code
        self.status, self.detail = ERRORS[code]
        super().__init__(self.detail)

def extract_chunks(data, suffix):
    if len(data) > MAX_INPUT:
        raise BookParseError('input_limit')
    if suffix == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted or len(reader.pages) > 800:
            raise BookParseError('invalid')
        pages = ((f'PDF 第 {i+1} 页', page.extract_text() or '') for i, page in enumerate(reader.pages))
    elif suffix in ('.txt', '.md'):
        pages = [('文本', data.decode('utf-8-sig'))]
    else:
        raise BookParseError('format')
    chunks, total = [], 0
    for label, text in pages:
        for start in range(0, len(text), 1200):
            part = text[start:start+1400].strip()
            if part:
                total += len(part)
                if total > MAX_TEXT:
                    raise BookParseError('text_limit')
                chunks.append({'ref': f'S{len(chunks)+1}', 'location': label+f' · 段 {start//1200+1}', 'text': part})
    if not chunks:
        raise BookParseError('empty')
    return chunks

def parse_book_data(data, suffix):
    if len(data) > MAX_INPUT:
        raise BookParseError('input_limit')
    if suffix not in ('.pdf', '.txt', '.md'):
        raise BookParseError('format')
    if not _parse_slot.acquire(blocking=False):
        raise BookParseError('busy')
    try:
        # Do not inherit API keys, login locations or Python import overrides.
        keep = {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATH'}
        env = {k:v for k,v in os.environ.items() if k.upper() in keep}
        args = [sys.executable, '-I', str(WORKER_PATH), suffix]
        if suffix == '.pdf':
            spec = importlib.util.find_spec('pypdf')
            if spec is None or not spec.origin:
                raise BookParseError('worker')
            # This installation uses a user-site dependency. Pass its installed
            # directory explicitly; do not enable user-site startup or .pth files.
            args.append(str(Path(spec.origin).resolve().parent.parent))
        try:
            result = subprocess.run(args,
                                    input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    env=env, timeout=PARSE_TIMEOUT,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired:
            # subprocess.run kills and waits for this direct child on timeout.
            raise BookParseError('timeout')
        except OSError:
            raise BookParseError('worker')
        if result.returncode or len(result.stdout) > 13 * 1024 * 1024:
            raise BookParseError('worker')
        try:
            payload = json.loads(result.stdout.decode('utf-8'))
            if not isinstance(payload, dict):
                raise ValueError()
            if payload.get('error') in ('input_limit', 'text_limit', 'format', 'invalid', 'empty'):
                raise BookParseError(payload['error'])
            chunks = payload['chunks']
            if not isinstance(chunks, list) or not chunks or len(chunks) > 2000000:
                raise ValueError()
            total = 0
            for i, chunk in enumerate(chunks):
                if not isinstance(chunk, dict) or chunk.get('ref') != f'S{i+1}':
                    raise ValueError()
                if not isinstance(chunk.get('location'), str) or not 0 < len(chunk['location']) <= 100:
                    raise ValueError()
                text = chunk.get('text')
                if not isinstance(text, str) or not text.strip() or len(text) > 1400:
                    raise ValueError()
                total += len(text)
            if total > MAX_TEXT:
                raise ValueError()
            return chunks
        except (ValueError, KeyError, TypeError):
            raise BookParseError('worker')
    finally:
        _parse_slot.release()

def main():
    try:
        if sys.argv[1] == '.pdf' and len(sys.argv) == 3:
            sys.path.append(sys.argv[2])
        chunks = extract_chunks(sys.stdin.buffer.read(MAX_INPUT+1), sys.argv[1])
        payload = {'chunks':chunks}
    except BookParseError as exc:
        payload = {'error':exc.code}
    except Exception:
        payload = {'error':'invalid'}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

if __name__ == '__main__':
    main()
