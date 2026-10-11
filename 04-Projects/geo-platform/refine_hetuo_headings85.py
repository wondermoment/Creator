"""Correct three detected heading hierarchies in their existing drafts only."""
from sync_hetuo_batch85 import *

TARGETS = {'e06542aadbb310b1e53c4954':3, 'abcdc847b779a9ebfbe1c3d4':6, '96cfcaef3678f7e609e28562':7}

if __name__ == '__main__':
    plan=preflight()
    proof=ROOT/'iteration85-heading-refinement.json'
    records=json.loads(proof.read_text(encoding='utf-8')) if proof.exists() else []
    for rid,count in TARGETS.items():
        prior=next((x for x in records if x['id']==rid),None)
        if prior:
            assert prior['status']=='verified','Uncertain update: reconcile before retry'
            continue
        with s.db() as c:
            cfg,template=guard(c,plan)
            old=s.resource(c,PID,rid,'content')
            job=next(x for x in s.items(c,PID,'wechat_draft') if x['content_id']==rid and x['status']=='synced')
            _,_,before_manifest=export.prepare(G,c,PID,old)
            assert len(export.heading_indices(old))==count
        token=wx.access_token(G,PID,cfg)
        remote=wx.call('/cgi-bin/draft/get',token,{'media_id':job['media_id']})
        assert wx.draft_matches(remote,job['expected']),'Remote edited by user: preserve and stop'
        article=remote['news_item'][0]
        original_soup=BeautifulSoup(article['content'],'html.parser')
        remote_images=[x.get('data-src') or x['src'] for x in original_soup.select('img')]
        paths=[x['file'] for x in before_manifest['images'] if x['role']=='body']
        assert len(paths)==len(remote_images)
        image_map={}
        for path,url in zip(paths,remote_images):
            assert path not in image_map or image_map[path]==url
            image_map[path]=url
        with s.db() as c:
            guard(c,plan)
            assert sha(s.resource(c,PID,rid,'content'))==sha(old)
            updated=layout.apply_to_content(G,c,PID,old,template)
            assert updated['body']==old['body'] and updated['title']==old['title']
            body,assets,manifest=export.prepare(G,c,PID,updated)
            assert [x['file'] for x in manifest['images'] if x['role']=='body']==paths
        outgoing=body
        for path,url in image_map.items(): outgoing=outgoing.replace('src="'+path+'"','src="'+html.escape(url,quote=True)+'"')
        new_soup=BeautifulSoup(outgoing,'html.parser')
        anchors=new_soup.select('a[href]'); previous=original_soup.select('a[href]')
        assert len(anchors)==len(previous)==7
        for new,old_anchor in zip(anchors,previous):
            assert new['href']==old_anchor['href']
            new.replace_with(BeautifulSoup(str(old_anchor),'html.parser'))
        outgoing=str(new_soup)
        allowed=('title','author','digest','content','content_source_url','thumb_media_id','show_cover_pic','need_open_comment','only_fans_can_comment')
        payload={k:article[k] for k in allowed if k in article};payload['content']=outgoing
        expected=wx.article_signature(payload)
        assert expected['images']==wx.article_signature(article)['images']
        assert expected['links']==wx.article_signature(article)['links']
        entry=dict(id=rid,media_id=job['media_id'],status='sending',chapters=count,revision=updated['revision'])
        records.append(entry);proof.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        job.update(status='sending',expected=expected,revision=updated['revision'],operation='update_layout',
                   fingerprint=hashlib.sha256(json.dumps([cfg['appid'],rid,updated['revision'],body,manifest],sort_keys=True,ensure_ascii=False).encode()).hexdigest())
        with s.db() as c:s.put(c,PID,'wechat_draft',job,job['id'])
        wx.call('/cgi-bin/draft/update',token,{'media_id':job['media_id'],'index':0,'articles':payload})
        actual=wx.call('/cgi-bin/draft/get',token,{'media_id':job['media_id']})
        assert wx.draft_matches(actual,expected)
        with s.db() as c:
            guard(c,plan)
            job.update(status='synced',synced_at=s.now(),error='')
            s.put(c,PID,'wechat_draft',job,job['id'])
            s.event(c,PID,plan['actor'],'修正公众号章节层级',rid+' · 保留图片和链接 · 原草稿更新')
        entry.update(status='verified');proof.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        result=json.loads(RESULT.read_text(encoding='utf-8'))
        next(x for x in result['items'] if x['id']==rid)['revision']=updated['revision']
        RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('VERIFIED',rid,'chapters',count,flush=True)
