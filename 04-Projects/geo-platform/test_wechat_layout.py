import hashlib
from unittest.mock import patch
from bs4 import BeautifulSoup
from fastapi import HTTPException
from test_wechat_export import WechatExportTests
from test_wechat_sync import WechatSyncTests
from test_workflow import server
import wechat_layout as layout
import wechat_sync as wx
import wechat_export

SAMPLE = '''<section style="font-size:16px;color:#202a35;line-height:1.9">
<section><img data-src="https://mmbiz.qpic.cn/banner/640"/></section>
<section><img data-src="https://mmbiz.qpic.cn/photo/640"/></section>
<p style="font-size:12px">图片说明</p><p style="font-size:16px;margin:18px 0">样稿专有正文</p>
<p style="font-size:19px;color:#217d9c"><strong style="color:rgb(0, 145, 104);font-size:45px">NO.1 </strong><span>样稿专有章节</span></p>
<p>修改后的微信正文</p><section><img src="https://mmbiz.qpic.cn/footer/640"/></section>
<p>示例有限公司是一家技术公司</p></section>'''


class LayoutTests(WechatExportTests):
    bind = WechatSyncTests.bind
    remote = WechatSyncTests.remote

    def test_primary_heading_detection_preserves_hierarchy_and_cases(self):
        def content(lines): return {'title':'标题','body':'\n\n'.join(lines)}
        self.assertEqual(wechat_export.heading_indices(content(['一、成本','1、节水','2、节电','二、环保'])), {0,3})
        self.assertEqual(wechat_export.heading_indices(content(['案例一：改进质量','说明','案例二：降低成本'])), {0,2})
        self.assertEqual(wechat_export.heading_indices(content(['1、工艺','2、成本','2026年行业报告'])), {0,1})

    def test_image_links_have_native_metadata_and_resolved_image(self):
        fragment = '<a href="https://mp.weixin.qq.com/s?id=1"><span><img src="asset:photo"></span></a>'
        prepared = layout.resolve_fragment(fragment, lambda *args: 'https://mmecoa.qpic.cn/new/640')
        anchor = BeautifulSoup(prepared, 'html.parser').a
        self.assertEqual(anchor['href'], 'https://mp.weixin.qq.com/s?id=1')
        self.assertEqual(anchor['data-linktype'], '1')
        self.assertEqual(anchor['linktype'], 'image')
        self.assertEqual(anchor['imgurl'], anchor.img['src'])
        self.assertEqual(layout.image_link_markup(prepared), prepared)
        unsafe = '<a href="javascript:alert(1)"><img src="x"></a>'
        self.assertNotIn('data-linktype', layout.image_link_markup(unsafe))

    def test_cdn_webp_is_uploaded_as_compatible_png_preserving_pixels(self):
        import io
        from PIL import Image
        stream=io.BytesIO();Image.new('RGBA',(12,8),(4,120,80,170)).save(stream,format='WEBP',lossless=True)
        filename,raw,mime=wx.upload_image({'file':'images/03.webp','raw':stream.getvalue(),'mime':'image/webp'})
        self.assertEqual((filename,mime),('03.png','image/png'))
        with Image.open(io.BytesIO(raw)) as im:
            self.assertEqual(im.format,'PNG');self.assertEqual(im.getpixel((0,0)),(4,120,80,170))

    def setup_draft(self):
        self.bind(); rid, _, raw = self.fixture(); self.calls=[]
        with patch.object(wx, 'call', side_effect=self.remote):
            self.a.post(self.url+'/wechat/test')
            endpoint=self.url+'/contents/'+rid+'/wechat-draft'
            job=self.a.post(endpoint,json={'revision':1,'confirm':True,'appid':'wx1234567890abcdef','binding_version':1}).json()
        self.article['content']=SAMPLE;self.article['author']='编辑';self.article['title']='微信已修改标题'
        return rid, raw, endpoint+'/'+job['id']+'/import-layout'

    def payload(self):
        return {'revision':1,'appid':'wx1234567890abcdef','binding_version':1,'make_default':True}

    def test_roundtrip_default_future_preview_and_sync_share_template(self):
        rid,raw,url=self.setup_draft()
        with server.db() as c: original=server.resource(c,self.pid,rid,'content')
        self.calls=[]
        with patch.object(wx,'call',side_effect=self.remote),patch.object(layout,'fetch_image',return_value=raw):
            response=self.a.post(url,json=self.payload())
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(self.calls,['/cgi-bin/draft/get'])
            again=self.a.post(url,json=self.payload()).json()
            self.assertEqual(response.json()['id'],again['id'])
        with server.db() as c:
            self.assertEqual(original,server.resource(c,self.pid,rid,'content'))
            self.assertEqual(len(server.items(c,self.pid,'wechat_layout')),1)
        page=self.a.get(self.url+'/contents/'+rid+'/wechat-preview?revision=1')
        self.assertEqual(page.status_code,200,page.text)
        self.assertIn('修改后的微信正文',page.text);self.assertIn('微信已修改标题',page.text)
        self.assertIn('data:image/png;base64,',page.text);self.assertNotIn('src="https:',page.text)
        duplicate=self.a.post(self.url+'/contents/'+rid+'/wechat-draft',json={**self.payload(),'confirm':True,'template_version':1})
        self.assertEqual(duplicate.status_code,409)
        new,_,_=self.fixture()
        with server.db() as c:
            content=server.resource(c,self.pid,new,'content')
            body,assets,manifest=wechat_export.prepare(vars(server),c,self.pid,content)
        self.assertNotIn('样稿专有',body);self.assertIn('NO.1',body);self.assertIn('font-size:45px',body)
        self.assertIn('示例有限公司',body);self.assertEqual(manifest['template_version'],1)
        self.calls=[]
        with patch.object(wx,'call',side_effect=self.remote):
            stale=self.a.post(self.url+'/contents/'+new+'/wechat-draft',json={**self.payload(),'confirm':True})
            self.assertEqual(stale.status_code,409);self.assertEqual(self.calls,[])
            sent=self.a.post(self.url+'/contents/'+new+'/wechat-draft',json={**self.payload(),'confirm':True,'template_version':1})
            self.assertEqual(sent.json()['status'],'synced',sent.text)
            self.assertIn('font-size:45px',self.article['content']);self.assertEqual(self.article['author'],'编辑')

    def test_no_save_on_download_failure_or_midflight_revision_permission_change(self):
        for change in ('download','revision','permission'):
            self.setUp();rid,raw,url=self.setup_draft()
            def download(_):
                if change=='download': raise HTTPException(409,'failed')
                with server.db() as c:
                    if change=='revision':
                        item=server.resource(c,self.pid,rid,'content');item['revision']=2;server.put(c,self.pid,'content',item,rid)
                    else: c.execute("UPDATE members SET role='viewer' WHERE project_id=?",(self.pid,))
                return raw
            with patch.object(wx,'call',side_effect=self.remote),patch.object(layout,'fetch_image',side_effect=download):
                result=self.a.post(url,json=self.payload())
                self.assertIn(result.status_code,(403,409))
            with server.db() as c:self.assertEqual(server.items(c,self.pid,'wechat_layout'),[])

    def test_scope_binding_and_sanitizer(self):
        rid,raw,url=self.setup_draft()
        self.assertEqual(self.b.post(url,json=self.payload()).status_code,404)
        self.assertEqual(self.a.post(url,json={**self.payload(),'binding_version':3}).status_code,409)
        with self.assertRaises(HTTPException):layout.sanitize('<img src="https://evil.test/a">')
        with self.assertRaises(HTTPException):layout.image_url('ftp://mmbiz.qpic.cn/a')
        soup,warnings=layout.sanitize('<section onclick="bad()" style="color:red;background-color:url(https://evil.test);position:fixed"><script>bad()</script><a href="javascript:bad()">safe</a><mp-common-videosnap data-url="private-token"/></section>')
        self.assertNotIn('bad()',str(soup));self.assertNotIn('private-token',str(soup));self.assertNotIn('evil.test',str(soup))
        self.assertNotIn('position:',str(soup));self.assertTrue(warnings)

    def test_template_changes_during_render_rejected(self):
        rid,raw,url=self.setup_draft()
        with patch.object(wx,'call',side_effect=self.remote),patch.object(layout,'fetch_image',return_value=raw):self.a.post(url,json=self.payload())
        original=wechat_export.document
        def alter(*args):
            result=original(*args)
            with server.db() as c:
                t=layout.selected(vars(server),c,self.pid);t['version']+=1;server.put(c,self.pid,'wechat_layout',t,t['id'])
            return result
        with patch.object(wechat_export,'document',side_effect=alter):
            self.assertEqual(self.a.get(self.url+'/contents/'+rid+'/wechat-preview?revision=1').status_code,409)

    def test_apply_one_article_updates_workspace_reader_export_without_touching_source(self):
        rid,raw,url=self.setup_draft()
        with patch.object(wx,'call',side_effect=self.remote),patch.object(layout,'fetch_image',return_value=raw):self.a.post(url,json=self.payload())
        second,_,_=self.fixture()
        with server.db() as c:
            source=server.resource(c,self.pid,rid,'content')
            old=server.resource(c,self.pid,second,'content')
            old['channels']=['微信公众号'];server.put(c,self.pid,'content',old,second)
            updated=layout.apply_to_content(vars(server),c,self.pid,old,layout.selected(vars(server),c,self.pid))
            self.assertEqual(updated['revision'],2);self.assertEqual(updated['body'],old['body'])
            self.assertEqual(updated['status'],'pending');self.assertIsNone(updated['approved_revision'])
            self.assertEqual(updated['history'][-1]['layout'],old['layout'])
            self.assertEqual(source,server.resource(c,self.pid,rid,'content'))
        for route in ('proof','client-preview','wechat-preview'):
            result=self.a.get(self.url+'/contents/'+second+'/'+route+'?revision=2')
            self.assertEqual(result.status_code,200,result.text)
            self.assertIn('font-size:45px',result.text);self.assertIn('NO.1',result.text)
            self.assertIn('示例有限公司',result.text)
            self.assertNotIn('样稿专有',result.text)
        self.assertEqual(self.a.get(self.url+'/contents/'+second+'/proof?revision=1').status_code,409)
