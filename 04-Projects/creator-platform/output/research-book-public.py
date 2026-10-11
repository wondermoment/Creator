"""Keyless public book metadata and article lookup. Never imports login/API keys."""
import concurrent.futures, html, json, re, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BOOKS=json.loads((ROOT/'output/book-research-catalog.json').read_text('utf-8'))
QUERIES={
'zhang-running':('跑步治愈','张展晖'),'zhang-control':('掌控','张展晖'),
'new-longevity-singularity':('长寿奇点','张见一'),
'new-noma':('The Noma Guide to Fermentation','Rene Redzepi'),
'new-synthetic-biology':('合成生物','李诗渊'),
'new-singularity-nearer':('The Singularity Is Nearer','Ray Kurzweil'),
'new-microbiome-master-key':('The Whole-Body Microbiome','Brett Finlay'),
'new-what-is-health':('What Is Health','Peter Sterling'),
'new-super-agers':('Super Agers','Eric Topol'),
'new-we-are-as-gods':('吾辈如神','Peter Diamandis'),
'new-getting-older':('The Book About Getting Older','Lucy Pollock'),
'new-biomanufacturing':('生命造万物','方昕'),
'hou-1':('Sapiens','Yuval Noah Harari'),'hou-2':('Homo Deus','Yuval Noah Harari'),
'hou-3':('The Body','Bill Bryson'),'hou-4':('Life Time','Russell Foster'),
'hou-5':('生命 非常的世界',''),'hou-6':('Lifespan','David Sinclair'),
'hou-7':('Outlive','Peter Attia'),'hou-8':('Ageless','Andrew Steele'),
'hou-9':('The Great Age Reboot','Michael Roizen'),
'hou-10':('How Not to Age','Michael Greger'),'hou-11':('长寿的习惯',''),
'hou-12':('Biology of Aging','Roger McDonald'),
'hou-13':('The Gene','Siddhartha Mukherjee'),'hou-14':('The Epigenetics Revolution','Nessa Carey'),
'hou-15':('DNA The Secret of Life','James Watson'),'hou-16':('Junk DNA','Nessa Carey'),
'hou-17':('The Song of the Cell','Siddhartha Mukherjee'),'hou-18':('细胞简史','陈涛'),
'hou-19':('Power Sex Suicide','Nick Lane'),'hou-20':('The Telomere Effect','Elizabeth Blackburn'),
'hou-21':('Brain Energy','Christopher Palmer'),'hou-22':('分子营养',''),
'hou-23':('The Disease Delusion','Jeffrey Bland'),
'hou-24':('The Emperor of All Maladies','Siddhartha Mukherjee'),'hou-25':('癌症 防御',''),
'hou-26':('Williams Textbook of Endocrinology',''),
'hou-27':('Why We Get Sick','Benjamin Bikman'),
'hou-28':('Human Metabolism A Regulatory Perspective','Keith Frayn'),
'hou-29':('酶与诺贝尔奖',''),'hou-30':('酶学方法',''),
'hou-31':('Immune','Philipp Dettmer'),'hou-32':('A Silent Fire','Shilpa Ravella'),
'hou-33':('Eat to Treat','Maggie Berghoff'),'hou-34':('肠道菌群与衰老',''),
'hou-35':('肠道菌群与精准营养健康',''),'hou-36':('第二大脑',''),
'hou-37':('The Beauty of Dirty Skin','Whitney Bowe'),'hou-38':('中西医结合临床',''),
'hou-39':('Spark','John Ratey'),'hou-40':('情绪的毒 身体知道',''),
'hou-41':('Flourish','Martin Seligman'),'hou-42':('Meditating Day by Day','Christophe Andre'),
'hou-43':('The Power of Now','Eckhart Tolle'),'hou-44':('能量的真相','')}

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'AgelessIsland-public-research/1.0 (book-reference-check)'})
    with urllib.request.urlopen(req,timeout=18) as r:
        return json.loads(r.read().decode('utf-8'))

def research(book):
    bid=book['id'];title,author=QUERIES[bid]
    result={'id':bid,'requested_title':book['title'],'query':title+' '+author,'checked':'2026-10-06','sources':[],'errors':[]}
    params={'title':title,'limit':2,'fields':'key,title,author_name,first_publish_year,isbn'}
    if author:params['author']=author
    try:
        url='https://openlibrary.org/search.json?'+urllib.parse.urlencode(params)
        for doc in fetch(url).get('docs',[]):
            work=fetch('https://openlibrary.org'+doc['key']+'.json')
            desc=work.get('description','');desc=desc.get('value','') if isinstance(desc,dict) else desc
            result['sources'].append({'type':'library','url':'https://openlibrary.org'+doc['key'],
                'title':doc['title'],'authors':doc.get('author_name',[]),'year':doc.get('first_publish_year'),
                'description':desc,'subjects':work.get('subjects',[])[:15]})
    except Exception as e:result['errors'].append('OpenLibrary: '+str(e))
    # Query the English title and author; Chinese-only ambiguities stay explicitly unresolved.
    if re.search('[a-zA-Z]',title):
        try:
            url='https://en.wikipedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','list':'search','srsearch':title+' '+author,'srlimit':1,'format':'json'})
            matches=fetch(url).get('query',{}).get('search',[])
            if matches:
                page=matches[0]
                url='https://en.wikipedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','prop':'extracts','explaintext':1,'pageids':page['pageid'],'format':'json'})
                entry=next(iter(fetch(url)['query']['pages'].values()))
                result['sources'].append({'type':'encyclopedia_candidate','url':'https://en.wikipedia.org/wiki/'+urllib.parse.quote(entry['title'].replace(' ','_')),'title':entry['title'],'text':entry.get('extract','')[:18000]})
        except Exception as e:result['errors'].append('Wikipedia: '+str(e))
    return result

if __name__=='__main__':
    folder=ROOT/'output/book-public-research';folder.mkdir(exist_ok=True)
    pending=[b for b in BOOKS if not (folder/(b['id']+'.json')).exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(research,pending):
            (folder/(result['id']+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(result['id'],len(result['sources']),flush=True)
