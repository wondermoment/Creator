"""Local operator export, containing only customer-review content and referenced images."""
import hashlib,json,zipfile
import server as s
from sample_review import render_article,CSS
from html import escape

def run(batch='hetuo-20261002'):
 folder=s.ROOT/('deliverables/hetuo-client-review' if batch=='hetuo-20261002' else 'deliverables/hetuo-feishu-review');folder.mkdir(parents=True,exist_ok=True)
 with s.db() as c:
  pid=c.execute('SELECT id FROM projects WHERE name=?',('和拓实业',)).fetchone()[0]
  rows=sorted([x for x in s.items(c,pid,'content') if x.get('layout') and x.get('import_batch')==batch],key=lambda x:int(x['title'].split('、')[0]))
  mapping={x['id']:f'article-{n+1:02d}.html' for n,x in enumerate(rows)}
  assets={a['id']:a for a in s.items(c,pid,'asset')};used=set()
  def url(aid):
   used.add(aid);return 'images/'+aid+'.'+assets[aid]['storage_key'].rsplit('.',1)[-1]
  for row in rows:
   text=render_article(s.project(c,pid),row,s.items(c,pid,'evidence_claim'),url,rows,lambda rid:'index.html' if rid=='review' else mapping[rid])
   (folder/mapping[row['id']]).write_text(text,encoding='utf-8')
  (folder/'images').mkdir(exist_ok=True)
  for aid in used:(folder/url(aid)).write_bytes((s.DB_PATH.parent/'assets'/pid/assets[aid]['storage_key']).read_bytes())
  (folder/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>和拓内容客户审阅包</title><style>'+CSS+'</style><main style="display:block"><h1>和拓实业 · '+str(len(rows))+'篇内容客户审阅包</h1><p class="notice">原稿排版与配图候选，尚未批准发送。客户需核准技术事实、图片、渠道版本与咨询入口。此离线包不提供在线审批。</p>'+''.join('<p><a href="'+mapping[x['id']]+'">'+escape(x['title'])+'</a> · v'+str(x['revision'])+'</p>' for x in rows)+'</main>',encoding='utf-8')
  manifest={'type':'review_only','published':False,'articles':[{'title':x['title'],'revision':x['revision'],'status':x['status'],'sha256':hashlib.sha256(x['body'].encode()).hexdigest()} for x in rows],'image_count':len(used)}
  (folder/'manifest.json').write_text(s.dump(manifest),encoding='utf-8')
 with zipfile.ZipFile(folder.parent/('和拓实业-8篇图文客户审阅包.zip' if batch=='hetuo-20261002' else '和拓实业-飞书新增15篇客户审阅包.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  for f in folder.rglob('*'):
   if f.is_file():z.write(f,f.relative_to(folder))
 print(json.dumps({'articles':len(rows),'images':len(used),'folder':str(folder)},ensure_ascii=False))
if __name__=='__main__':
 run()
 run('hetuo-feishu-0924-20261002')
