"""Read-only pilot acceptance audit. Does not approve or publish customer content."""
import hashlib,json,re
from pathlib import Path
from bs4 import BeautifulSoup
import server as s

def run():
 checks=[]
 def check(name,condition):
  checks.append({'name':name,'passed':bool(condition)})
  if not condition:raise AssertionError(name)
 with s.db() as c:
  ps=c.execute('SELECT * FROM projects WHERE name=?',('和拓实业',)).fetchall();check('和拓企业空间唯一',len(ps)==1);pid=ps[0]['id']
  check('官网域名正确',ps[0]['website']=='https://www.heroto.com.cn')
  check('和拓批次未出现在其他企业',c.execute("SELECT count(*) FROM resources WHERE project_id!=? AND data LIKE '%hetuo-20261002%'",(pid,)).fetchone()[0]==0)
  assets=s.items(c,pid,'asset');ids={a['id'] for a in assets};docs=s.items(c,pid,'knowledge');docids={k['id'] for k in docs}
  check('隔离资料不在可用知识中',not any(k['title']=='方案' for k in docs))
  check('第三方事实未混入企业知识',not any(k.get('source','').startswith('https://www.hqhf.com') for k in docs))
  check('每份归档文件存在且哈希正确',all((s.DB_PATH.parent/'assets'/pid/a['storage_key']).is_file() and hashlib.sha256((s.DB_PATH.parent/'assets'/pid/a['storage_key']).read_bytes()).hexdigest()==a['sha256'] for a in assets))
  check('每项素材有分类',all(a.get('collection') for a in assets))
  check('每份提炼稿可追溯',all(k.get('source_ids') and set(k['source_ids'])<=docids for k in docs if k.get('derived')))
  rows=[x for x in s.items(c,pid,'content') if x.get('import_batch')=='hetuo-20261002'];check('首批待发稿数量为8',len(rows)==8)
  check('未自行批准或发送',all(x['status']=='pending' and x['approved_revision'] is None for x in rows) and len(s.items(c,pid,'publication'))==0)
  check('正文与排版快照一致',all(hashlib.sha256(x['body'].encode()).hexdigest()==x['layout']['body_sha256'] for x in rows))
  check('封面和所有原图有企业资产',all(set([x['layout']['cover_id']]+[a for b in x['layout']['blocks'] for a in b.get('image_ids',[])]+[f['asset_id'] for f in x['layout']['figures']])<=ids for x in rows))
  newrows=[x for x in s.items(c,pid,'content') if x.get('import_batch')=='hetuo-feishu-0924-20261002']
  check('飞书新增15篇且来源不重复',len(newrows)==15 and len({x['source_url'] for x in newrows})==15)
  check('飞书批次未串企业',c.execute("SELECT count(*) FROM resources WHERE project_id!=? AND data LIKE '%hetuo-feishu-0924-20261002%'",(pid,)).fetchone()[0]==0)
  check('新增稿件保持待审且表格完整',all(x['status']=='pending' and not x['channels'] and x['approved_revision'] is None and '暂时无法在飞书文档外展示此内容' not in x['body'] for x in newrows))
  check('10个企业Soul已配置',len(s.items(c,pid,'soul'))==10)
  check('3个企业Skill已配置',len(s.items(c,pid,'skill'))==3)
  check('Soul不混用企业身份',all(pid in a['markdown'] and 'www.heroto.com.cn' in a['markdown'] for a in s.items(c,pid,'soul')))
 folder=s.ROOT/'deliverables/hetuo-client-review'
 for page in folder.glob('article-*.html'):
  soup=BeautifulSoup(page.read_text(encoding='utf-8'),'html.parser')
  check(page.name+'所有本地图像存在',all((folder/i['src']).is_file() for i in soup.find_all('img')))
 report={'at':s.now(),'checks':checks,'summary':{'knowledge_documents':len(docs),'source_documents':sum(k.get('origin')=='customer_source' for k in docs),'derived_documents':sum(bool(k.get('derived')) for k in docs),'assets':len(assets),'images':sum(a['category']=='图片' for a in assets),'articles':len(rows)+len(newrows),'first_batch':len(rows),'new_feishu_batch':len(newrows)},'limits':['真实模型生成与平台发布尚无客户凭证验收','知识与稿件未获客户批准','图像参数表仍需技术人员核对','独立账号已开通且仅关联和拓；生产环境账号归属验证待接入']}
 (s.ROOT/'deliverables/hetuo-audit.json').write_text(s.dump(report),encoding='utf-8');print(s.dump(report['summary']));print('Passed checks:',len(checks))
if __name__=='__main__':run()
