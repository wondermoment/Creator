"""Read-only remote draft verification for the user-authorized batch."""
from sync_hetuo_batch85 import *

if __name__ == '__main__':
    plan = preflight()
    results = json.loads(RESULT.read_text(encoding='utf-8'))['items']
    assert len(results) == 21 and len({x['media_id'] for x in results}) == 21
    with s.db() as c:
        cfg, template = guard(c, plan)
        jobs = s.items(c, PID, 'wechat_draft')
        local = {}
        for item in plan['items']:
            content = s.resource(c, PID, item['id'], 'content')
            before = next(x for x in content['history'] if x['revision'] == item['before_revision'])
            expected_body = before['body']
            if expected_body.startswith(before['title']): expected_body = clean_title(before['title']) + expected_body[len(before['title']):]
            assert content['title'] == item['title'] and content['body'] == expected_body
            assert content['status'] == before['status'] == 'pending' and content['approved_revision'] is None
            assert content['layout']['figures'] == before['layout']['figures']
            local[item['id']] = content
    token = wx.access_token(G, PID, cfg)
    audit = []
    for result in results:
        job = next(x for x in jobs if x.get('batch') == 85 and x['content_id'] == result['id'] and x['status'] == 'synced')
        remote = wx.call('/cgi-bin/draft/get', token, {'media_id': job['media_id']})
        assert wx.draft_matches(remote, job['expected']), result['id'] + ' remote changed'
        soup = BeautifulSoup(remote['news_item'][0]['content'], 'html.parser')
        numbers = [x for x in soup.find_all(['span','strong','b']) if not x.find(['span','strong','b']) and re.fullmatch(r'NO\.\d+\s*', x.get_text())]
        def inherited(node, name):
            for element in [node, *node.parents]:
                styles = dict(part.split(':',1) for part in element.get('style','').replace(' ','').split(';') if ':' in part)
                if name in styles: return styles[name].lower().replace('!important','')
        assert all(inherited(x,'font-size') == '45px' for x in numbers)
        assert all(inherited(x,'color') in ('rgb(0,145,104)','#009168') for x in numbers)
        assert len(soup.select('a[href]')) == 7
        assert len(soup.select('a[linktype="image"][data-linktype="1"]')) == 7
        audit.append(dict(content_id=result['id'], title=result['title'], status='verified', images=len(soup.select('img')), links=7, chapters=len(numbers), source_body_preserved=True, status_still_pending=True))
        print('VERIFIED',len(audit),result['title'],flush=True)
    second = json.loads((ROOT / 'iteration85-second-title.json').read_text(encoding='utf-8'))
    remote_second = wx.call('/cgi-bin/draft/get',token,{'media_id':second['media_id']})
    assert wx.draft_matches(remote_second,second['expected'])
    first_job = next(x for x in jobs if x['content_id'] == FIRST and x['status'] == 'synced')
    remote_first = wx.call('/cgi-bin/draft/get',token,{'media_id':first_job['media_id']})
    # The manually edited source includes original CDN fragments; compare its
    # exact recorded signature, rather than applying the upload URL validator.
    assert wx.article_signature(remote_first['news_item'][0]) == second['first_remote_signature'], 'Protected first draft changed'
    with s.db() as c: guard(c,plan)
    output = dict(verified_at=s.now(), items=audit, count=21, second_title_updated=True, first_local_and_remote_unchanged=True, published=False)
    (ROOT/'iteration85-final-audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print('AUDIT COMPLETE 21/21; second title verified; first unchanged',flush=True)
