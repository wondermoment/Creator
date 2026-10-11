"""Apply the already imported first-article layout locally; no WeChat calls."""
import hashlib
import json
from pathlib import Path
import server as s
import wechat_layout as layout
from bs4 import BeautifulSoup

PID='a46fb911b04fbf0b783c7bf5'
RID='9c8fd4efd0f7de9f21b0c97a'

if __name__=='__main__':
    with s.db() as c:
        old=s.resource(c,PID,RID,'content')
        template=layout.selected(vars(s),c,PID)
        assert old['revision']==8 and layout.is_source(template,old)
        assert template['version']==3 and not old['layout'].get('wechat_html')
        before=c.execute('SELECT id,kind,data FROM resources WHERE project_id=? AND id<>? ORDER BY id',(PID,RID)).fetchall()
        backup=Path('.runtime/iteration101-first-v8.json')
        assert not backup.exists(), 'Backup exists: inspect before running again'
        backup.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
        updated=layout.apply_to_content(vars(s),c,PID,old,template)
        assert updated['body']==old['body'] and updated['title']==old['title']
        assert updated['revision']==9 and updated['status']=='pending'
        assert updated['history'][-1]['layout']==old['layout']
        assert before==c.execute('SELECT id,kind,data FROM resources WHERE project_id=? AND id<>? ORDER BY id',(PID,RID)).fetchall()
        soup=BeautifulSoup(updated['layout']['wechat_html'],'html.parser')
        assert len(soup.select('img'))==20
        assert all('NO.'+str(i) in soup.get_text() for i in range(1,8))
        result={'content_id':RID,'revision':9,'template_version':3,'images':20,'chapters':7,'status':updated['status'],'other_records_unchanged':True,'remote_calls':0}
    Path('outputs/iteration101-first-layout.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result))
