"""Public linked-page inventory. No guessed article IDs, login or browser sessions."""
import concurrent.futures, datetime, hashlib, json, re, time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlsplit, parse_qs
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
BASE = 'https://www.hqhf.com/'
MAX_PAGES = 2500

def canonical(url):
    p = urlsplit(urljoin(BASE, url))
    if p.hostname not in ('www.hqhf.com', 'hqhf.com'): return None
    path = p.path
    q = parse_qs(p.query)
    if path in ('', '/', '/index.html', '/index.php'): return BASE
    if path == '/info.php' and q.get('class_id'):
        path = '/info_' + q['class_id'][0] + ('_'+q['page'][0] if q.get('page') and q['page'][0]!='1' else '') + '.html'
    if path == '/display.php' and q.get('id'): path = '/display_'+q['id'][0]+'.html'
    if re.fullmatch(r'/(?:info_[0-9]+(?:_[0-9]+)?|display_[0-9]+)\.html', path): return BASE.rstrip('/')+path

def fetch(url):
    name = 'home' if url == BASE else urlsplit(url).path.strip('/').removesuffix('.html')
    cache = ROOT/'html'/f'{name}.html'
    try:
        if cache.exists(): html=cache.read_text(encoding='utf-8'); status=200
        else:
            time.sleep(.4)
            r=requests.get(url, timeout=30, headers={'User-Agent':'PublicArticleResearch/1.0 (low-rate content analysis)'})
            status=r.status_code
            if status!=200: return {'url':url,'status':status,'error':'HTTP '+str(status)}
            r.encoding='utf-8-sig'; html=r.text; cache.write_text(html,encoding='utf-8')
        s=BeautifulSoup(html,'html.parser')
        links=sorted({v for a in s.select('a[href]') if (v:=canonical(a['href']))})
        out={'url':url,'status':status,'title':s.title.get_text(' ',strip=True) if s.title else '', 'links':links}
        a=s.select_one('.article'); body=a.select_one('.bd') if a else None
        if a is not None and body is not None:
            for n in body.select('script,style'): n.decompose()
            title=a.select_one('h1'); meta=a.select_one('.titBar')
            out.update(kind='article',title=title.get_text(' ',strip=True) if title else out['title'],metadata=meta.get_text(' ',strip=True) if meta else '',text=body.get_text('\n',strip=True),images=[urljoin(url,x.get('src','')) for x in body.select('img[src]')],headings=[x.get_text(' ',strip=True) for x in body.select('h1,h2,h3,h4,strong,b')],content_sha256=hashlib.sha256(body.get_text(' ',strip=True).encode()).hexdigest())
            (ROOT/'articles'/f'{name}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        else:
            out.update(kind='catalog_or_page',text=s.get_text('\n',strip=True))
        return out
    except Exception as e: return {'url':url,'error':type(e).__name__+': '+str(e)}

def main():
    for d in ('html','articles'): (ROOT/d).mkdir(parents=True,exist_ok=True)
    pending={BASE}; seen=set(); rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        while pending and len(seen)<MAX_PAGES:
            batch=sorted(pending)[:40]; pending.difference_update(batch);seen.update(batch)
            for row in pool.map(fetch,batch):
                rows.append(row); pending.update(set(row.get('links',[]))-seen)
            summary={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'visited':len(rows),'articles':sum(x.get('kind')=='article' for x in rows),'errors':sum('error' in x for x in rows),'queued':len(pending),'limit':MAX_PAGES}
            (ROOT/'progress.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(summary),flush=True)
    (ROOT/'pages.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    inv=[{k:v for k,v in x.items() if k not in ('text','links','headings')} for x in rows]
    (ROOT/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2),encoding='utf-8')
    hashes=defaultdict(list)
    for x in rows:
        if x.get('kind')=='article': hashes[x['content_sha256']].append(x['url'])
    summary.update(linked_graph_exhausted=not pending,unvisited=sorted(pending),duplicate_text_groups=[v for k,v in hashes.items() if len(v)>1],robots={'url':BASE+'robots.txt','status':404},sitemap={'url':BASE+'sitemap.xml','status':404},coverage_limit='Public same-domain pages reachable via homepage navigation, catalog pagination and article previous/next links. No claim about orphan URLs, unlinked articles, private pages or image-only text. No OCR or attachment downloads.')
    (ROOT/'coverage.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
