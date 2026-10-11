import io
import zipfile
import hashlib
from pathlib import Path
import test_workflow
from test_workflow import server
import source_import
import delivery_runtime

class SourceTests(test_workflow.WorkflowTests):
    # Reuse only fixtures, not the inherited workflow tests.
    def make_doc(self,body='<w:p><w:r><w:t>参数 10 MPa</w:t></w:r></w:p>'):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>')
        return out.getvalue()

    def test_extract_and_reject_unsafe_packages(self):
        p=source_import.parse(self.make_doc(),'.docx')
        self.assertIn('10 MPa',p['body']); self.assertEqual(p['blocks'][0]['location'],'正文块 1')
        with self.assertRaises(ValueError): source_import.xml(b'<!DOCTYPE x [<!ENTITY a "x">]><x/>')
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('../outside','bad')
        with self.assertRaises(ValueError):source_import.parse(out.getvalue(),'.docx')

    def test_idempotence_and_tenant_isolation(self):
        path=server.DB_PATH.parent/'fixture.docx';path.write_bytes(self.make_doc())
        with server.db() as c:
            one=source_import.ingest(vars(server),c,self.pid,path,'产品','test')
            two=source_import.ingest(vars(server),c,self.pid,path,'产品','test')
        self.assertTrue(two['duplicate']);self.assertEqual(one['knowledge_id'],two['knowledge_id'])
        self.assertEqual(self.b.get(self.url+'/assets/'+one['asset_id']+'/file').status_code,404)
        state=self.a.get(self.url+'/state').json()
        self.assertEqual(next(k for k in state['knowledge'] if k['id']==one['knowledge_id'])['status'],'pending')

    def test_review_pack_and_image_preservation(self):
        from PIL import Image
        image=io.BytesIO();Image.new('RGB',(40,20),'green').save(image,format='PNG')
        with server.db() as c:
            aid=source_import.store_asset(vars(server),c,self.pid,image.getvalue(),'test.png',{'batch':'test'},'图片')
            body='<script>alert(1)</script>\n\n一、技术说明'
            item={'title':'客户原稿测试','body':body,'status':'pending','revision':1,'approved_revision':None,'sources':[{'id':self.kid,'version':1}], 'channels':['搜狐号'],'layout':{'cover_id':aid,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'blocks':[{'text':body}],'figures':[{'asset_id':aid,'caption':'原图','after':0}]}}
            rid=server.put(c,self.pid,'content',item)
        result=self.a.get(self.url+'/contents/'+rid+'/proof')
        self.assertEqual(result.status_code,200);self.assertIn('&lt;script&gt;',result.text)
        self.assertNotIn('<script>alert',result.text)
        self.assertEqual(result.headers['cache-control'],'no-store')
        bound=self.a.get(self.url+'/contents/'+rid+'/proof?revision=1')
        self.assertEqual(bound.status_code,200)
        self.assertEqual(bound.headers['x-content-revision'],'1')
        self.assertEqual(self.b.get(self.url+'/contents/'+rid+'/proof?revision=1').status_code,404)
        self.assertEqual(self.a.get(self.url+'/contents/'+rid+'/proof?revision=0').status_code,422)
        self.assertEqual(self.b.get(self.url+'/contents/'+rid+'/proof').status_code,404)
        self.assertEqual(self.b.get(self.url+'/review-pack').status_code,404)
        out=self.a.get(self.url+'/review-pack');self.assertEqual(out.status_code,200)
        with zipfile.ZipFile(io.BytesIO(out.content)) as z:
            self.assertIn('index.html',z.namelist());self.assertTrue(any(n.startswith('images/') for n in z.namelist()))
        payload=delivery_runtime.payload_for(item,'搜狐号')
        self.assertEqual(payload['cover_id'],aid);self.assertIn(aid,payload['attachment_ids'])
        with server.db() as c:
            k=server.resource(c,self.pid,self.kid,'knowledge');k['status']='pending';server.put(c,self.pid,'knowledge',k,self.kid)
        self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':'approve'}).status_code,409)
        with server.db() as c:
            updated=server.resource(c,self.pid,rid,'content')
            updated.update(revision=2,body='修改后的正文',status='pending')
            server.put(c,self.pid,'content',updated,rid)
        self.assertEqual(self.a.get(self.url+'/contents/'+rid+'/proof?revision=1').status_code,409)
        current=self.a.get(self.url+'/contents/'+rid+'/proof?revision=2')
        self.assertEqual(current.status_code,200)
        self.assertIn('修改后的正文',current.text)
        self.assertEqual(current.headers['x-content-revision'],'2')
        self.assertEqual(current.headers['x-layout-status'],'stale')
        self.assertNotIn('<img', current.text)
        self.assertEqual(self.a.get(self.url+'/review-pack').status_code,409)
        self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':1,'action':'approve'}).status_code,409)

    def test_layout_title_body_changes_block_review_and_delivery(self):
        import sample_review
        from fastapi import HTTPException
        for changed_field in ('title', 'body'):
            with self.subTest(field=changed_field):
                body='有效正文，用于核对原有配图。'
                item={'title':'原有标题','body':body,'status':'draft','revision':1,
                      'approved_revision':None,'sources':[], 'channels':['搜狐号'],'history':[],
                      'layout':{'cover_id':'old-cover','body_sha256':hashlib.sha256(body.encode()).hexdigest(),
                                'blocks':[{'text':body,'image_ids':['old-inline']}],
                                'figures':[{'asset_id':'old-card','caption':'旧摘录','after':0}]}}
                with server.db() as c:
                    rid=server.put(c,self.pid,'content',item)
                # Scheduling/channel-only edits preserve the valid layout.
                edit={'revision':1,'title':item['title'],'body':body,'channels':['搜狐号'],'scheduled':'2026-10-05T10:00'}
                self.assertEqual(self.a.put(self.url+'/contents/'+rid,json=edit).status_code,200)
                with server.db() as c:
                    unchanged=server.resource(c,self.pid,rid,'content')
                self.assertTrue(sample_review.layout_current(unchanged))
                edit.update(revision=2)
                edit[changed_field]='修改后的完整标题或正文'
                self.assertEqual(self.a.put(self.url+'/contents/'+rid,json=edit).status_code,200)
                with server.db() as c:
                    updated=server.resource(c,self.pid,rid,'content')
                    self.assertFalse(sample_review.layout_current(updated))
                    updated.update(status='approved',approved_revision=3)
                    self.assertFalse(server.content_approval_summary(c,self.pid,updated)['effective_approved'])
                for action in ('submit','approve'):
                    result=self.a.post(self.url+'/contents/'+rid+'/review',json={'revision':3,'action':action})
                    self.assertEqual(result.status_code,409)
                    self.assertIn('排版已过期', result.text)
                self.assertEqual(self.a.post(self.url+'/contents/'+rid+'/publish',json={'revision':3}).status_code,409)
                with self.assertRaises(HTTPException): delivery_runtime.payload_for(updated,'搜狐号')
                proof=self.a.get(self.url+'/contents/'+rid+'/proof?revision=3')
                self.assertEqual(proof.status_code,200)
                self.assertNotIn('<img',proof.text)
                self.assertEqual(sample_review.current_blocks(updated),[{'text':updated['body']}])
                self.assertEqual(self.a.get(self.url+'/review-pack').status_code,409)

    def test_portable_client_preview_is_complete_scoped_and_versioned(self):
        from PIL import Image
        raw=io.BytesIO();Image.new('RGB',(40,20),'green').save(raw,format='PNG')
        with server.db() as c:
            aid=source_import.store_asset(vars(server),c,self.pid,raw.getvalue(),'reader.png',{'type':'fixture'},'图片')
            body='第一段正文 <script>禁止脚本</script>'
            item={'title':'手机预览测试','body':body,'revision':1,'status':'pending','approved_revision':None,
                  'channels':[],'sources':[],'review_notes':['PRIVATE-NOTE'], 'prompt_snapshot':'SECRET-PROMPT',
                  'layout':{'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'cover_id':aid,
                            'blocks':[{'text':body}],'figures':[{'asset_id':aid,'after':0,'caption':'图片说明'}]}}
            rid=server.put(c,self.pid,'content',item)
        path=self.url+'/contents/'+rid+'/client-preview?revision=1'
        r=self.a.get(path)
        self.assertEqual(r.status_code,200)
        self.assertIn('手机',r.text)
        self.assertIn('data:image/png;base64,',r.text)
        self.assertIn('&lt;script&gt;',r.text)
        self.assertNotIn('<script>',r.text)
        self.assertNotIn('SECRET-PROMPT',r.text)
        self.assertNotIn('PRIVATE-NOTE',r.text)
        self.assertNotIn('<aside>',r.text)
        self.assertEqual(r.headers['x-content-revision'],'1')
        self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertIn("default-src &apos;none&apos;",r.text)
        offline=self.a.get(path+'&download=true')
        self.assertIn('attachment;',offline.headers['content-disposition'])
        self.assertNotIn('/api/',offline.text)
        self.assertIn('data:image/png;base64,',offline.text)
        self.assertEqual(self.b.get(path).status_code,404)
        self.assertEqual(self.a.get(path.replace('revision=1','revision=2')).status_code,409)
        self.assertEqual(self.a.get(path.replace('?revision=1','')).status_code,422)
        proof=self.a.get(self.url+'/contents/'+rid+'/proof').text
        self.assertIn('手机阅读预览',proof)
        self.assertIn('下载客户预览稿',proof)
        self.assertIn('下载预览长图',proof)
        image_path=path+'&format=png'
        self.assertEqual(self.b.get(image_path).status_code,404)
        self.assertEqual(self.a.get(image_path.replace('revision=1','revision=2')).status_code,409)
        png=self.a.get(image_path)
        self.assertEqual(png.status_code,200,png.text[:200] if png.status_code!=200 else '')
        self.assertEqual(png.headers['content-type'],'image/png')
        self.assertIn('.png',png.headers['content-disposition'])
        with Image.open(io.BytesIO(png.content)) as preview:
            self.assertEqual(preview.width,860)
            self.assertGreater(preview.height,900)
            preview.verify()
        # Recheck authorization/version after rendering, not just before it.
        from unittest.mock import patch
        def changed_during_render(document):
            with server.db() as c:
                latest=server.resource(c,self.pid,rid,'content')
                latest['revision']=2
                server.put(c,self.pid,'content',latest,rid)
            return png.content
        with patch('preview_images.render_images',side_effect=changed_during_render):
            self.assertEqual(self.a.get(image_path).status_code,409)
        with server.db() as c:
            server.put(c,self.pid,'content',item,rid)
        with server.db() as c:
            asset=server.resource(c,self.pid,aid,'asset')
            target=server.DB_PATH.parent/'assets'/self.pid/asset['storage_key']
            target.write_bytes(b'broken-image')
        self.assertEqual(self.a.get(path+'&download=true').status_code,409)
        with server.db() as c:
            target.write_bytes(raw.getvalue())
            item['body']='正文修改后必须重做排版'
            server.put(c,self.pid,'content',item,rid)
        self.assertEqual(self.a.get(path+'&download=true').status_code,409)

    def test_client_exports_reject_stale_evidence_before_and_after_render(self):
        from unittest.mock import patch
        body='基于资料快照的客户审阅稿'
        with server.db() as c:
            source=server.resource(c,self.pid,self.kid,'knowledge')
            source_record=tuple(c.execute('SELECT * FROM resources WHERE id=?',(self.kid,)).fetchone())
            source['status']='pending'
            server.put(c,self.pid,'knowledge',source,self.kid)
            item={'title':'资料版本校验','body':body,'revision':1,'status':'pending',
                  'channels':[],'sources':[{'id':self.kid,'version':source['version'],'body':source['body']}],
                  'layout':{'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'blocks':[{'text':body}]}}
            rid=server.put(c,self.pid,'content',item)
        base=self.url+'/contents/'+rid+'/client-preview?revision=1'
        pack=self.url+'/review-pack'
        # A current, unconfirmed source is permitted for customer review.
        self.assertEqual(self.a.get(base+'&download=true').status_code,200)
        self.assertEqual(self.a.get(pack).status_code,200)
        for mutation in ('version','body','missing','flag','transitive'):
            with self.subTest(mutation=mutation):
                with server.db() as c:
                    changed=dict(source)
                    if mutation=='version':changed['version']+=1
                    if mutation=='body':changed['body']+='新增资料'
                    if mutation=='flag':changed['knowledge_outdated']=True
                    if mutation=='transitive':
                        changed.update(derived=True,source_ids=['absent'],source_snapshots=[{'id':'absent','version':1}])
                    server.put(c,self.pid,'knowledge',changed,self.kid)
                    if mutation=='missing':c.execute('DELETE FROM resources WHERE id=?',(self.kid,))
                with patch('preview_images.render_images') as renderer:
                    for path in (base,base+'&download=true',base+'&format=png',pack):
                        response=self.a.get(path)
                        self.assertEqual(response.status_code,409,response.text)
                        self.assertIn('引用资料',response.text)
                    renderer.assert_not_called()
                with server.db() as c:
                    c.execute('INSERT OR IGNORE INTO resources VALUES(?,?,?,?,?,?)',source_record)
                    server.put(c,self.pid,'knowledge',source,self.kid)
        def update_evidence_during_render(document):
            with server.db() as c:
                changed=dict(source);changed['version']+=1
                server.put(c,self.pid,'knowledge',changed,self.kid)
            return b'mocked-image-output'
        with patch('preview_images.render_images',side_effect=update_evidence_during_render):
            self.assertEqual(self.a.get(base+'&format=png').status_code,409)
        # Inspection remains possible internally, while external export is blocked.
        self.assertEqual(self.a.get(self.url+'/contents/'+rid+'/proof').status_code,200)

    def test_png_export_rejects_asset_changes_during_render(self):
        from unittest.mock import patch
        from PIL import Image
        def image_bytes(color):
            stream=io.BytesIO();Image.new('RGB',(40,20),color).save(stream,format='PNG');return stream.getvalue()
        raw=image_bytes('green');replacement=image_bytes('blue')
        with server.db() as c:
            aid=source_import.store_asset(vars(server),c,self.pid,raw,'snapshot.png',{'type':'fixture'},'图片')
            original=server.resource(c,self.pid,aid,'asset')
            original_record=tuple(c.execute('SELECT * FROM resources WHERE id=?',(aid,)).fetchone())
            target=server.DB_PATH.parent/'assets'/self.pid/original['storage_key']
            body='图片快照审阅'
            item={'title':'图片快照','body':body,'revision':1,'status':'pending','channels':[],'sources':[],
                  'layout':{'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'cover_id':aid,'blocks':[{'text':body}]}}
            rid=server.put(c,self.pid,'content',item)
        base=self.url+'/contents/'+rid+'/client-preview?revision=1'
        for mutation in ('unchanged','file_replace','file_delete','record_delete','record_replace','path_change','layout_change'):
            with self.subTest(mutation=mutation):
                def render(document):
                    with server.db() as c:
                        if mutation=='file_replace':target.write_bytes(replacement)
                        if mutation=='file_delete':target.unlink()
                        if mutation=='record_delete':c.execute('DELETE FROM resources WHERE id=?',(aid,))
                        if mutation=='record_replace':
                            target.write_bytes(replacement)
                            changed=dict(original);changed['sha256']=hashlib.sha256(replacement).hexdigest()
                            server.put(c,self.pid,'asset',changed,aid)
                        if mutation=='path_change':
                            alternative=target.with_name('alternate.png');alternative.write_bytes(raw)
                            changed=dict(original);changed['storage_key']=alternative.name
                            server.put(c,self.pid,'asset',changed,aid)
                        if mutation=='layout_change':
                            current=server.resource(c,self.pid,rid,'content')
                            current['layout']['figures']=[{'asset_id':aid,'after':0,'caption':'new layout'}]
                            server.put(c,self.pid,'content',current,rid)
                    return b'fixture-rendered-png'
                with patch('preview_images.render_images',side_effect=render):
                    response=self.a.get(base+'&format=png')
                self.assertEqual(response.status_code,200 if mutation=='unchanged' else 409,response.text)
                if mutation!='unchanged':self.assertNotIn(b'fixture-rendered-png',response.content)
                with server.db() as c:
                    target.write_bytes(raw)
                    c.execute('INSERT OR IGNORE INTO resources VALUES(?,?,?,?,?,?)',original_record)
                    server.put(c,self.pid,'asset',original,aid)
                    server.put(c,self.pid,'content',item,rid)
        # Valid raster bytes must still match the asset record before embedding.
        target.write_bytes(replacement)
        with patch('preview_images.render_images') as render:
            self.assertEqual(self.a.get(base+'&format=png').status_code,409)
            self.assertEqual(self.a.get(base+'&download=true').status_code,409)
            render.assert_not_called()

    def test_review_pack_validates_image_bytes_paths_and_tenant(self):
        import json
        from PIL import Image
        from unittest.mock import patch
        stream=io.BytesIO();Image.new('RGB',(40,20),'green').save(stream,format='PNG');raw=stream.getvalue()
        other=self.b.get('/api/me').json()['projects'][0]['id']
        with server.db() as c:
            aid=source_import.store_asset(vars(server),c,self.pid,raw,'pack.png',{'type':'fixture'},'图片')
            original=server.resource(c,self.pid,aid,'asset')
            record=tuple(c.execute('SELECT * FROM resources WHERE id=?',(aid,)).fetchone())
            foreign=source_import.store_asset(vars(server),c,other,raw,'foreign.png',{'type':'fixture'},'图片')
            target=server.DB_PATH.parent/'assets'/self.pid/original['storage_key']
            body='可追溯审阅包'
            item={'title':'审阅包素材检查','body':body,'revision':1,'status':'pending','channels':[],'sources':[],
                  'layout':{'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'cover_id':aid,'blocks':[{'text':body}],
                            'figures':[{'asset_id':aid,'after':0,'caption':'重复引用'}]}}
            rid=server.put(c,self.pid,'content',item)
            project_name=server.project(c,self.pid)['name']
        url=self.url+'/review-pack'
        out=self.a.get(url);self.assertEqual(out.status_code,200,out.text[:100] if out.status_code!=200 else '')
        with zipfile.ZipFile(io.BytesIO(out.content)) as z:
            manifest=json.loads(z.read('manifest.json'));self.assertEqual(len(manifest['assets']),1)
            entry=manifest['assets'][0]
            self.assertEqual(z.read(entry['file']),raw)
            self.assertEqual(entry['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertTrue(entry['file'].endswith('.png'))
            self.assertIn(project_name,z.read('index.html').decode())
            self.assertNotIn('和拓实业',z.read('index.html').decode())
            self.assertNotIn('storage_key',z.read('manifest.json').decode())
        for mutation in ('hash','file_missing','record_missing','cross_tenant','traversal','invalid_raster','svg','oversize'):
            with self.subTest(mutation=mutation):
                with server.db() as c:
                    changed=dict(original)
                    if mutation=='hash':target.write_bytes(b'changed-image-bytes')
                    if mutation=='file_missing':target.unlink()
                    if mutation=='traversal':
                        outside=target.parent.parent/'outside.png';outside.write_bytes(raw);changed['storage_key']='../outside.png'
                    if mutation in ('invalid_raster','svg','oversize'):
                        data={'invalid_raster':b'not-an-image','svg':b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
                              'oversize':b'x'*(15*1024*1024+1)}[mutation]
                        target.write_bytes(data);changed['sha256']=hashlib.sha256(data).hexdigest()
                    server.put(c,self.pid,'asset',changed,aid)
                    if mutation=='record_missing':c.execute('DELETE FROM resources WHERE id=?',(aid,))
                    if mutation=='cross_tenant':
                        bad=json.loads(json.dumps(item));bad['layout']['cover_id']=foreign;server.put(c,self.pid,'content',bad,rid)
                response=self.a.get(url)
                self.assertEqual(response.status_code,409,response.text)
                self.assertNotEqual(response.headers.get('content-type'),'application/zip')
                with server.db() as c:
                    target.write_bytes(raw);c.execute('INSERT OR IGNORE INTO resources VALUES(?,?,?,?,?,?)',record)
                    server.put(c,self.pid,'asset',original,aid);server.put(c,self.pid,'content',item,rid)
        # Simulate a filesystem replacement after bytes are added to the archive.
        write=zipfile.ZipFile.writestr
        def replace_after_write(archive,name,data,*args,**kwargs):
            result=write(archive,name,data,*args,**kwargs)
            if str(name).startswith('images/'):target.write_bytes(b'replaced-during-export')
            return result
        with patch.object(zipfile.ZipFile,'writestr',replace_after_write):
            result=self.a.get(url)
        self.assertEqual(result.status_code,409,result.text)
        self.assertIn('生成期间',result.text)

    def test_activation_is_single_use_and_only_one_project(self):
        from fastapi.testclient import TestClient
        with server.db() as c:
            token=server.create_account_invite(c,'customer-'+server.uid()+'@example.com',self.pid)
        client=TestClient(server.app)
        short=client.post('/api/activation',json={'token':token,'password':'short'})
        self.assertEqual(short.status_code,422)
        result=client.post('/api/activation',json={'token':token,'password':'Fixture-password-739'})
        self.assertEqual(result.status_code,200)
        me=client.get('/api/me').json();self.assertEqual([p['id'] for p in me['projects']],[self.pid])
        self.assertEqual(client.post('/api/activation',json={'token':token,'password':'Another-password-999'}).status_code,404)
        other=self.b.get('/api/me').json()['projects'][0]['id']
        self.assertEqual(client.get('/api/projects/'+other+'/state').status_code,404)

    def test_feishu_import_preserves_tables_is_idempotent_and_blocks_empty_channels(self):
        import import_feishu as f
        raw = ('<div data-lark-html-role="root"><h1>稿件内容-0924</h1>'
               '<h2 class="old-record-id-known">1、客户原文</h2><div>' + '制造业实际工况需要逐项验证。' * 50 + '</div>'
               '<div><table><tr><td>材质</td><td>条件</td></tr><tr><td>钢</td><td>配套涂层</td></tr></table></div></div>').encode()
        rows = f.extract_articles(raw)
        self.assertIn('材质 | 条件', rows[0]['body'])
        with server.db() as c:
            one = f.import_rows(vars(server), c, self.pid, rows, raw)
            two = f.import_rows(vars(server), c, self.pid, rows, raw)
            self.assertEqual(one['imported'], two['skipped'])
            self.assertEqual(two['imported'], [])
            rid = one['imported'][0]
            item = server.resource(c, self.pid, rid, 'content')
            self.assertEqual(item['status'], 'pending')
            k = server.resource(c, self.pid, item['original_knowledge_id'], 'knowledge')
            k['status'] = 'confirmed'; server.put(c, self.pid, 'knowledge', k, k['id'])
        self.assertEqual(self.b.get(self.url+'/contents/'+rid+'/proof').status_code, 404)
        proof = self.a.get(self.url+'/contents/'+rid+'/proof')
        self.assertEqual(proof.status_code, 200)
        self.assertIn('<table>', proof.text)
        self.assertIn('封面及配图待选', proof.text)
        result = self.a.post(self.url+'/contents/'+rid+'/review', json={'revision':1,'action':'approve'})
        self.assertEqual(result.status_code, 409)
        self.assertIn('渠道', result.text)
        out = self.a.get(self.url+'/review-pack?batch='+f.BATCH)
        self.assertEqual(out.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(out.content)) as z:
            import json
            self.assertEqual(len(json.loads(z.read('manifest.json'))['articles']), 1)
        self.assertEqual(self.a.get(self.url+'/review-pack?batch=nonexistent').status_code, 404)

# Avoid rerunning inherited methods; keep the shared setup helper.
for name in list(test_workflow.WorkflowTests.__dict__):
    if name.startswith('test_') and name not in SourceTests.__dict__: setattr(SourceTests,name,None)
