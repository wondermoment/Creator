"""Public-site reference archive, kept outside every client's factual knowledge."""
import hashlib
import json
import re
import time
import urllib.request
from collections import deque
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin,urlparse,urldefrag
from bs4 import BeautifulSoup

ROOT=Path(__file__).parent/'research/hqhf-20261002'
ROOT.mkdir(parents=True,exist_ok=True)
queue=deque(['https://www.hqhf.com/']);seen=set();records=[];errors=[]
while queue and len(seen)<2000:
    url=queue.popleft()
    if url in seen:continue
    seen.add(url); name=urlparse(url).path.strip('/') or 'index.html'
    try:
        target=ROOT/'html'/name;target.parent.mkdir(exist_ok=True)
        if target.exists():raw=target.read_bytes()
        else:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (public article research)'}),timeout=20) as r:
                if urlparse(r.url).hostname!='www.hqhf.com':raise ValueError('out-of-scope redirect')
                raw=r.read(3000000)
            target.write_bytes(raw);time.sleep(.1)
        doc=BeautifulSoup(raw.decode('utf-8-sig','replace'),'html.parser')
        for a in doc.find_all('a',href=True):
            link=urldefrag(urljoin(url,a['href']))[0];p=urlparse(link)
            if p.hostname=='www.hqhf.com' and p.scheme in ('http','https') and not p.query and re.fullmatch(r'/(?:info_\d+(?:_\d+)?|display_\d+)\.html',p.path):
                link='https://www.hqhf.com'+p.path
                if link not in seen and link not in queue:queue.append(link)
        title=doc.title.get_text(' ',strip=True) if doc.title else name
        for tag in doc(['script','style','nav','footer']):tag.decompose()
        text=doc.get_text('\n',strip=True)
        out=ROOT/'text'/Path(name).with_suffix('.txt');out.parent.mkdir(exist_ok=True);out.write_text(text,encoding='utf-8')
        records.append({'url':url,'title':title,'file':str(out.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'type':'detail' if name.startswith('display_') else 'index','characters':len(text)})
        if len(records)%25==0:print('Archived',len(records),'remaining',len(queue),flush=True)
    except Exception as e:errors.append({'url':url,'error':str(e)})
    manifest={'captured_at':datetime.now(timezone.utc).isoformat(),'scope':'公开站内可发现 HTML 及详情页；不含图片、登录区、未链接页面；参考写作，不作为和拓事实','records':records,'errors':errors,'remaining':list(queue),'robots':'robots.txt 与 sitemap.xml 均返回404；只跟随实际链接'}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':len(records),'details':sum(r['type']=='detail' for r in records),'errors':len(errors),'remaining':len(queue)},ensure_ascii=False))
