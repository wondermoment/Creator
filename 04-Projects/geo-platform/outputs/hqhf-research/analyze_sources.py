"""Offline source coverage and rule-assisted outline inventory; no network calls."""
from pathlib import Path
import collections,csv,hashlib,json,re
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
NAMES={'103101':'华清新闻','103102':'行业动态','103103':'市场活动','103104':'信息公开','103105':'液冷百科','103106':'镁合金资讯','103107':'表面处理资讯'}
categories={}; article_categories=collections.defaultdict(set)
for cat,name in NAMES.items():
    files=[p for p in (ROOT/'html').glob('info_'+cat+'*.html') if re.fullmatch('info_'+cat+r'(?:_\d+)?',p.stem)]
    urls=set()
    for f in files:
        soup=BeautifulSoup(f.read_text(encoding='utf-8'),'html.parser')
        urls.update('https://www.hqhf.com/'+a['href'] for a in soup.select('.main a[href]') if re.fullmatch(r'display_\d+\.html',a['href']))
    for url in urls: article_categories[url].add(name)
    categories[name]={'catalog_pages_including_aliases':len(files),'distinct_listed_articles':len(urls),'urls':sorted(urls)}

rows=[]; groups=collections.defaultdict(list)
for f in sorted((ROOT/'articles').glob('*.json')):
    a=json.loads(f.read_text(encoding='utf-8')); html=ROOT/'html'/(f.stem+'.html')
    body=BeautifulSoup(html.read_text(encoding='utf-8'),'html.parser').select_one('.article .bd')
    paragraphs=[p.get_text(' ',strip=True) for p in body.select('p,h1,h2,h3,h4,h5,h6,li,td') if p.get_text(' ',strip=True)] if body else []
    a['paragraphs']=paragraphs
    a['categories']=sorted(article_categories[a['url']])
    a['outline_candidates']=[p for p in paragraphs if 3<len(p)<130 and re.match(r'^(?:[一二三四五六七八九十]+[、.．]|[（(][一二三四五六七八九十]+[)）]|\d+(?:\.\d+)*[.、\s]|摘要|关键词|结语|总结|痛点|方案|价值)',p)]
    t=a['text']; title=a['title']; signals={}
    for key,pat in {'工况/问题':r'工况|痛点|失效|问题|难题|腐蚀','原因/机理':r'机理|机制|原因|原理','方案/工艺':r'方案|工艺|路线|流程','比较/选择':r'对比|比较|选择|选型|适用','验证/证据':r'测试|检测|试验|验证|标准|数据','应用/落地':r'应用|量产|产业化|交付|成本'}.items(): signals[key]=len(re.findall(pat,t))
    if '信息公开' in title: family='信息公开（不作写作范本）'
    elif any(x in title for x in ['招聘','诚聘']): family='招聘（不作技术写作范本）'
    elif any(x in title for x in ['举办','召开','成立','获奖','荣获','入选','受邀','发布实施']): family='事件/成果'
    elif any(x in title for x in ['技术','工艺','方案','应用','性能','研究']): family='技术/应用'
    elif any(x in title for x in ['为什么','如何','怎么','区别','问题','难题','不踩坑']): family='问题/选型'
    else: family='其他/待人工归类'
    a['rule_assisted_family']=family;a['structure_keyword_counts']=signals
    key_material=re.sub(r'\s+','',a['text']) if a['text'].strip() else json.dumps(a['images'],ensure_ascii=False)
    groups[hashlib.sha256(key_material.encode()).hexdigest()].append({'url':a['url'],'title':title,'has_text':bool(a['text'].strip())})
    f.write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
    rows.append({'url':a['url'],'title':title,'categories':' / '.join(a['categories']),'family_rule_assisted':family,'text_characters':len(t),'image_count':len(a['images']),'outline_count':len(a['outline_candidates']),**signals})

(ROOT/'category-coverage.json').write_text(json.dumps(categories,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'article-method-inventory.csv').open('w',encoding='utf-8-sig',newline='') as h:
    w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={'articles':len(rows),'empty_text':sum(x['text_characters']==0 for x in rows),'short_or_image_dominated_under_100_characters':sum(x['text_characters']<100 for x in rows),'total_text_characters':sum(x['text_characters'] for x in rows),'families_rule_assisted':dict(collections.Counter(x['family_rule_assisted'] for x in rows)),'note':'自动规则归类和关键词次数用于检索，不是技术事实核查或逐篇人工评价。正文为空或极短时保留图片URL，未做OCR。'}
summary['distinct_normalized_text_or_image_sets']=len(groups)
(ROOT/'deduplicated-corpus.json').write_text(json.dumps([{'key':k,'representative':v[0],'aliases':v[1:]} for k,v in groups.items()],ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'corpus-statistics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
