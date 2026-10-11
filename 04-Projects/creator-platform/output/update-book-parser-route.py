from pathlib import Path
p=Path(__file__).resolve().parents[1]/'backend/app/book_chat.py'
s=p.read_text('utf-8')
s=s.replace('import io\n','')
s=s.replace('from .commerce import local_only','from .commerce import local_only\nfrom .book_parser import parse_book_data, BookParseError')
start=s.index('    try:\n        if suffix ==')
end=s.index('    # Each request owns',start)
s=s[:start]+'''    try:
        chunks = await asyncio.to_thread(parse_book_data, data, suffix)
    except BookParseError as exc:
        raise HTTPException(exc.status, exc.detail)
'''+s[end:]
p.write_text(s,encoding='utf-8')
