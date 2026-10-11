import json
from unittest.mock import patch
from test_wechat_export import WechatExportTests
from test_workflow import server
import wechat_sync as wx


class WechatSyncTests(WechatExportTests):
    def test_draft_links_must_survive_sync(self):
        article = {'title': 'title', 'content': '<a href="https://mp.weixin.qq.com/s?id=1&amp;x=2">directory</a>', 'thumb_media_id': 'cover'}
        expected = wx.article_signature(article)
        self.assertTrue(wx.draft_matches({'news_item': [article]}, expected))
        changed = {**article, 'content': article['content'].replace('id=1', 'id=3')}
        self.assertFalse(wx.draft_matches({'news_item': [changed]}, expected))
        missing = {**article, 'content': 'directory'}
        self.assertFalse(wx.draft_matches({'news_item': [missing]}, expected))
        legacy = dict(expected); legacy.pop('links')
        self.assertTrue(wx.draft_matches({'news_item': [changed]}, legacy))

    def test_confirmation_binds_exact_account_and_config_version_before_upload(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        endpoint = self.url + '/contents/' + rid + '/wechat-draft'
        with patch.object(wx, 'call', side_effect=self.remote):
            self.a.post(self.url + '/wechat/test')
            binding = self.a.get(endpoint).json()['binding']
            self.assertEqual(set(binding), {'appid', 'name', 'version'})
            self.assertEqual(binding['version'], 1)
            for fields in ({}, {'appid': binding['appid'], 'binding_version': 2},
                           {'appid': 'wx0000000000000000', 'binding_version': 1}):
                with self.subTest(fields=fields):
                    self.calls.clear()
                    response = self.a.post(endpoint, json={'revision': 1, 'confirm': True, **fields})
                    self.assertEqual(response.status_code, 409)
                    self.assertEqual(self.calls, [], 'reject before token request or uploads')
                    self.assertEqual(self.a.get(endpoint).json()['records'], [])
            self.a.put(self.url + '/wechat', json={'appid': binding['appid'], 'version': 1, 'name': 'Updated'})
            self.a.post(self.url + '/wechat/test')
            self.calls.clear()
            old = self.a.post(endpoint, json={'revision': 1, 'confirm': True,
                                             'appid': binding['appid'], 'binding_version': 1})
            self.assertEqual(old.status_code, 409)
            self.assertEqual(self.calls, [])
            current = self.a.post(endpoint, json={'revision': 1, 'confirm': True,
                                                 'appid': binding['appid'], 'binding_version': 2})
            self.assertEqual(current.json()['status'], 'synced')

    def test_plain_digest_skips_title_decodes_entities_and_caps_length(self):
        content={'title':'测试标题','body':'测试标题\n\n“文字” &amp; 图片\n继续说明'+('长'*160)}
        digest=wx.article_digest(content)
        self.assertEqual(len(digest),120)
        self.assertTrue(digest.startswith('“文字” & 图片 继续说明'))
        self.assertNotIn('测试标题',digest)
        self.assertEqual(wx.article_digest({'title':'仅标题','body':'仅标题'}),'')

    def test_digest_sent_and_verified_without_breaking_legacy_receipts(self):
        self.bind();rid,_,_=self.fixture();self.calls=[]
        with patch.object(wx,'call',side_effect=self.remote):
            self.a.post(self.url+'/wechat/test')
            endpoint=self.url+'/contents/'+rid+'/wechat-draft'
            preview=self.a.get(endpoint).json()
            result=self.a.post(endpoint,json={'revision':1,'confirm':True,'appid':'wx1234567890abcdef','binding_version':1}).json()
        self.assertEqual(result['status'],'synced')
        self.assertEqual(self.article['digest'],preview['next_digest'])
        self.assertEqual(preview['revision'],1)
        changed={**self.article,'digest':'wrong summary'}
        self.assertFalse(wx.draft_matches({'news_item':[changed]},result['expected']))
        legacy=dict(result['expected']);legacy.pop('digest')
        self.assertTrue(wx.draft_matches({'news_item':[changed]},legacy))

    def test_wechat_lazy_image_rewrite_preserves_identity(self):
        article={'title':'title','content':'<p>text</p><img src="http://mmecoa.qpic.cn/mmecoa_png/asset-a/0?from=appmsg">','thumb_media_id':'cover'}
        actual={**article,'content':'<p>text</p><img data-src="https://mmecoa.qpic.cn/mmecoa_png/asset-a/640?from=appmsg">'}
        self.assertTrue(wx.draft_matches({'news_item':[actual]},wx.article_signature(article)))
        actual['content']=actual['content'].replace('asset-a','asset-b')
        self.assertFalse(wx.draft_matches({'news_item':[actual]},wx.article_signature(article)))

    def test_official_image_domains_and_spoof_rejection(self):
        for url in ('http://mmecoa.qpic.cn/mmecoa_jpg/example/0', 'https://mmbiz.qpic.cn/fixture/0'):
            self.assertTrue(wx.valid_image_url(url))
        for url in ('https://mmecoa.qpic.cn.attacker.test/a', 'https://mmecoa.qpic.cn@evil.test/a',
                    'https://mmecoa.qpic.cn:9000/a', 'javascript:alert(1)', None):
            self.assertFalse(wx.valid_image_url(url))

    def bind(self):
        r = self.a.put(self.url + '/wechat', json={'appid': 'wx1234567890abcdef', 'secret': 'fixture-secret', 'version': 0})
        self.assertEqual(r.status_code, 200, r.text)
        return r

    def remote(self, path, token='', data=None, files=None):
        self.calls.append(path)
        if path.endswith('stable_token'): return {'access_token': 'fixture-token', 'expires_in': 7200}
        if path.endswith('draft/batchget'): return {'total_count': 0, 'item_count': 0, 'item': []}
        if path.endswith('uploadimg'): return {'url': 'https://mmbiz.qpic.cn/fixture/0'}
        if 'add_material' in path: return {'media_id': 'fixture-cover'}
        if path.endswith('draft/add'):
            self.article = data['articles'][0]
            return {'media_id': 'fixture-draft'}
        if path.endswith('draft/get'): return {'news_item': [self.article]}
        raise AssertionError(path)

    def test_binding_encrypts_and_redacts_and_requires_owner(self):
        r = self.bind()
        self.assertNotIn('fixture-secret', r.text)
        self.assertTrue(r.json()['has_secret'])
        with server.db() as c:
            cfg = wx.config(c, vars(server), self.pid)
            self.assertNotIn('fixture-secret', json.dumps(cfg))
            self.assertEqual(wx.cipher(vars(server)).decrypt(cfg['encrypted_secret'].encode()).decode(), 'fixture-secret')
        self.assertEqual(self.b.get(self.url + '/wechat').status_code, 404)
        self.assertEqual(self.a.put(self.url + '/wechat', json={'appid': 'wx1234567890abcdef', 'version': 0}).status_code, 409)
        self.assertEqual(self.a.post(self.url + '/wechat/test', headers={'x-csrf-token': 'bad'}).status_code, 403)
        with server.db() as c: c.execute("UPDATE members SET role='editor' WHERE project_id=?", (self.pid,))
        self.assertEqual(self.a.get(self.url + '/wechat').status_code, 403)

    def test_connection_error_only_exposes_safe_ip(self):
        self.bind()
        with patch.object(wx, 'call', side_effect=wx.WechatError('IP blocked', 40164, '203.0.113.1')):
            result = self.a.post(self.url + '/wechat/test').json()
        self.assertEqual(result['required_ip'], '203.0.113.1')
        self.assertEqual(result['status'], 'blocked')
        self.assertNotIn('encrypted_secret', result)

    def test_draft_images_readback_and_duplicate_prevention(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        with patch.object(wx, 'call', side_effect=self.remote):
            self.assertEqual(self.a.post(self.url + '/wechat/test').json()['status'], 'verified_read')
            endpoint = self.url + '/contents/' + rid + '/wechat-draft'
            self.assertEqual(self.a.post(endpoint, json={'revision': 1}).status_code, 400)
            r = self.a.post(endpoint, json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()['status'], 'synced', r.text)
            self.assertFalse(r.json()['published'])
            self.assertEqual(self.a.post(endpoint, json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1}).json()['id'], r.json()['id'])
        self.assertEqual(self.calls.count('/cgi-bin/draft/add'), 1)
        self.assertEqual(self.calls.count('/cgi-bin/media/uploadimg'), 1)
        self.assertNotIn('images/', self.article['content'])
        self.assertIn('https://mmbiz.qpic.cn/fixture/0', self.article['content'])
        with server.db() as c:
            content = server.resource(c, self.pid, rid, 'content')
            cfg = wx.config(c, vars(server), self.pid)
        self.assertEqual(content['status'], 'pending')
        self.assertNotIn('fixture-token', json.dumps(cfg))
        self.assertNotIn('fixture-token', self.a.get(self.url + '/wechat').text)

    def test_render_change_cannot_duplicate_synced_revision(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        endpoint = self.url + '/contents/' + rid + '/wechat-draft'
        payload = {'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1}
        prepare = wx.wechat_export.prepare
        def changed_render(*args, **kwargs):
            fragment, assets, manifest = prepare(*args, **kwargs)
            return fragment + '<p>New template footer</p>', assets, manifest
        with patch.object(wx, 'call', side_effect=self.remote):
            self.a.post(self.url + '/wechat/test')
            first = self.a.post(endpoint, json=payload).json()
            self.assertEqual(first['status'], 'synced')
            self.calls.clear()
            with patch.object(wx.wechat_export, 'prepare', side_effect=changed_render):
                duplicate = self.a.post(endpoint, json=payload)
            self.assertEqual(duplicate.status_code, 409, duplicate.text)
            self.assertIn('已同步', duplicate.json()['detail'])
            self.assertEqual(self.calls, [], 'no uploads or remote writes for a changed rendering')
            records = self.a.get(endpoint).json()['records']
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['id'], first['id'])
            self.assertEqual(records[0]['fingerprint'], first['fingerprint'])
            self.assertEqual(self.a.post(endpoint, json=payload).json()['id'], first['id'])

    def test_unknown_write_does_not_retry(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        def remote(path, *args, **kwargs):
            if path.endswith('draft/add'):
                self.calls.append(path)
                raise wx.WechatError('connection lost')
            return self.remote(path, *args, **kwargs)
        with patch.object(wx, 'call', side_effect=remote):
            self.a.post(self.url + '/wechat/test')
            endpoint = self.url + '/contents/' + rid + '/wechat-draft'
            first = self.a.post(endpoint, json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1})
            self.assertEqual(first.json()['status'], 'needs_review')
            second = self.a.post(endpoint, json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1})
            self.assertEqual(second.status_code, 409)
        self.assertEqual(self.calls.count('/cgi-bin/draft/add'), 1)

    def test_changed_article_after_upload_prevents_draft_write(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        def remote(path, *args, **kwargs):
            result = self.remote(path, *args, **kwargs)
            if path.endswith('uploadimg'):
                with server.db() as c:
                    item = server.resource(c, self.pid, rid, 'content'); item['revision'] += 1
                    server.put(c, self.pid, 'content', item, rid)
            return result
        with patch.object(wx, 'call', side_effect=remote):
            self.a.post(self.url + '/wechat/test')
            r = self.a.post(self.url + '/contents/' + rid + '/wechat-draft', json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1})
        self.assertEqual(r.json()['status'], 'failed')
        self.assertNotIn('/cgi-bin/draft/add', self.calls)

    def test_transport_preserves_material_type_and_sanitizes_error(self):
        import httpx
        def response(request):
            self.assertEqual(request.url.host, 'api.weixin.qq.com')
            self.assertEqual(request.url.params['type'], 'image')
            self.assertEqual(request.url.params['access_token'], 'secret-token')
            return httpx.Response(200, json={'errcode':40164, 'errmsg':'invalid ip 223.166.33.17 ipv6 ::ffff:223.166.33.17, secret-token'})
        original = httpx.Client
        with patch.object(wx.httpx, 'Client', side_effect=lambda **kwargs: original(transport=httpx.MockTransport(response), **kwargs)):
            with self.assertRaises(wx.WechatError) as exc:
                wx.call('/cgi-bin/material/add_material?type=image', 'secret-token', files={'media':('a.png',b'png','image/png')})
        self.assertEqual(exc.exception.ip, '223.166.33.17')
        self.assertNotIn('secret-token', str(exc.exception))

    def test_receipt_mismatch_retains_id_without_success(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        def remote(path, *args, **kwargs):
            result = self.remote(path, *args, **kwargs)
            if path.endswith('draft/get'): return {'news_item': [{**self.article, 'content': 'truncated'}]}
            return result
        with patch.object(wx, 'call', side_effect=remote):
            self.a.post(self.url + '/wechat/test')
            endpoint = self.url + '/contents/' + rid + '/wechat-draft'
            self.assertEqual(self.b.post(endpoint, json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1}).status_code, 404)
            result = self.a.post(endpoint, json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1}).json()
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(result['media_id'], 'fixture-draft')

    def test_revoked_editor_during_upload_cannot_create_draft(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        def remote(path, *args, **kwargs):
            result = self.remote(path, *args, **kwargs)
            if path.endswith('uploadimg'):
                with server.db() as c: c.execute("UPDATE members SET role='viewer' WHERE project_id=?", (self.pid,))
            return result
        with patch.object(wx, 'call', side_effect=remote):
            self.a.post(self.url + '/wechat/test')
            result = self.a.post(self.url + '/contents/' + rid + '/wechat-draft', json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1}).json()
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('/cgi-bin/draft/add', self.calls)

    def test_recheck_synced_draft_preserves_external_edits_and_history(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        with patch.object(wx, 'call', side_effect=self.remote):
            self.a.post(self.url + '/wechat/test')
            endpoint = self.url + '/contents/' + rid + '/wechat-draft'
            original = self.a.post(endpoint, json={'revision': 1, 'confirm': True, 'appid': 'wx1234567890abcdef', 'binding_version': 1}).json()
            self.assertEqual(original['status'], 'synced')
            self.article = {**self.article, 'title': '用户在公众号修改后的标题'}
            self.calls.clear()
            response = self.a.post(endpoint + '/' + original['id'] + '/reconcile')
            self.assertEqual(response.status_code, 409)
            self.assertIn('远端内容与提交快照不一致', response.text)
            self.assertEqual(self.calls, ['/cgi-bin/draft/get'])
            recorded = self.a.get(endpoint).json()['records'][0]
            self.assertEqual(recorded['synced_at'], original['synced_at'])
            self.assertEqual(recorded['expected'], original['expected'])
            self.assertEqual(self.article['title'], '用户在公众号修改后的标题')

    def test_reconcile_lost_receipt_without_second_write(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        def remote(path, token='', data=None, files=None):
            if path.endswith('draft/add'):
                self.remote(path, token, data, files)
                raise wx.WechatError('lost response')
            if path.endswith('draft/batchget') and data.get('no_content') == 0:
                return {'total_count':1,'item':[{'media_id':'fixture-draft','content':{'news_item':[self.article]}}]}
            return self.remote(path, token, data, files)
        with patch.object(wx, 'call', side_effect=remote):
            self.a.post(self.url + '/wechat/test')
            endpoint = self.url + '/contents/' + rid + '/wechat-draft'
            result = self.a.post(endpoint, json={'revision':1,'confirm':True,'appid':'wx1234567890abcdef','binding_version':1}).json()
            self.assertEqual(result['status'],'needs_review')
            recovered = self.a.post(endpoint+'/'+result['id']+'/reconcile')
            self.assertEqual(recovered.status_code,200,recovered.text)
            self.assertEqual(recovered.json()['status'],'synced')
            self.assertTrue(recovered.json()['reconciled'])
            self.assertEqual(self.a.post(endpoint,json={'revision':1,'confirm':True,'appid':'wx1234567890abcdef','binding_version':1}).json()['id'],result['id'])
        self.assertEqual(self.calls.count('/cgi-bin/draft/add'),1)

    def test_reconcile_mismatched_remote_stays_blocked(self):
        self.bind(); rid, _, _ = self.fixture(); self.calls = []
        def remote(path, *args, **kwargs):
            result=self.remote(path,*args,**kwargs)
            if path.endswith('draft/get'):return {'news_item':[{**self.article,'thumb_media_id':'wrong-cover'}]}
            return result
        with patch.object(wx,'call',side_effect=remote):
            self.a.post(self.url+'/wechat/test')
            endpoint=self.url+'/contents/'+rid+'/wechat-draft'
            result=self.a.post(endpoint,json={'revision':1,'confirm':True,'appid':'wx1234567890abcdef','binding_version':1}).json()
            self.assertEqual(result['status'],'needs_review')
            self.assertEqual(self.a.post(endpoint+'/'+result['id']+'/reconcile').status_code,409)
            self.assertEqual(self.b.post(endpoint+'/'+result['id']+'/reconcile').status_code,404)
            self.assertEqual(self.a.post(endpoint,json={'revision':1,'confirm':True,'appid':'wx1234567890abcdef','binding_version':1}).status_code,409)
