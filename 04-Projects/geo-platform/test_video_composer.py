import json
import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from test_workflow import server, WorkflowTests
import video_composer as vc


class VideoComposerTests(unittest.TestCase):
    def setUp(self):
        fixture = WorkflowTests('runTest'); fixture.setUp()
        self.a, self.b, self.pid = fixture.a, fixture.b, fixture.pid
        self.url = fixture.url + '/video-composer'
        with server.db() as c:
            self.source = server.put(c, self.pid, 'content', {'title':'素材演示测试', 'body':'核对素材与字幕，不代表真实客户案例。', 'revision':1, 'status':'draft'})
            folder = server.DB_PATH.parent/'assets'/self.pid
            folder.mkdir(parents=True, exist_ok=True)
            Image.new('RGB',(640,360),'#236478').save(folder/'video-test.png')
            self.asset = server.put(c,self.pid,'asset',{'title':'测试图片','mime':'image/png','category':'图片','storage_key':'video-test.png'})
        self.body = {'source_id':self.source,'source_revision':1,'title':'素材演示测试','aspect':'landscape',
                     'scenes':[{'text':'先核对工况，再验证适用条件','asset_id':self.asset,'seconds':3,'start':0}]}

    def create(self):
        r=self.a.post(self.url+'/plans',json=self.body)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def test_save_script_before_selecting_media(self):
        self.body['scenes'][0]['asset_id']=''
        plan=self.create()
        self.assertEqual(plan['scenes'][0]['asset_id'],'')
        response=self.a.post(self.url+'/plans/'+plan['id']+'/render',json={'revision':1})
        self.assertEqual(response.status_code,422)
        self.assertIn('素材',response.json()['detail'])
        self.assertEqual(self.a.get(self.url).json()['renders'],[])
        self.body['scenes'][0]['asset_id']=self.asset
        updated=self.a.put(self.url+'/plans/'+plan['id'],json={**self.body,'revision':1})
        self.assertEqual(updated.status_code,200,updated.text)
        self.assertEqual(updated.json()['revision'],2)
        self.assertEqual(updated.json()['scenes'][0]['asset_id'],self.asset)
        self.assertEqual(self.a.post(self.url+'/plans',json={**self.body,'scenes':[
            {**self.body['scenes'][0],'asset_id':'not-in-this-project'}]}).status_code,404)

    def test_new_demo_source_has_current_evidence(self):
        demo=self.a.get(self.url.removesuffix('/video-composer')+'/state').json()['content']
        source=next(x for x in demo if x.get('generator')=='示例内容')
        self.body.update(source_id=source['id'],source_revision=source['revision'])
        self.body['scenes'][0]['asset_id']=''
        self.create()

    def wait(self, jid):
        for _ in range(120):
            j=next(j for j in self.a.get(self.url).json()['renders'] if j['id']==jid)
            if j['status'] not in ('queued','running'): return j
            time.sleep(.2)
        self.fail('render did not finish')

    def test_scope_versions_and_validation(self):
        p=self.create()
        self.assertEqual(self.b.get(self.url).status_code,404)
        self.assertEqual(self.b.put(self.url+'/plans/'+p['id'],json={**self.body,'revision':1}).status_code,404)
        self.assertEqual(self.b.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1}).status_code,404)
        self.assertEqual(self.b.get(self.url+'/renders/anything/file').status_code,404)
        other_pid=self.b.get('/api/me').json()['projects'][0]['id']
        self.assertEqual(self.b.post('/api/projects/'+other_pid+'/video-composer/plans',json=self.body).status_code,404)
        self.assertEqual(self.a.put(self.url+'/plans/'+p['id'],json={**self.body,'revision':0}).status_code,409)
        self.assertEqual(self.a.post(self.url+'/plans',json={**self.body,'scenes':[]}).status_code,422)
        self.assertEqual(self.a.post(self.url+'/plans',json={**self.body,'aspect':'bad'}).status_code,422)
        with server.db() as c:
            source=server.resource(c,self.pid,self.source,'content');source['revision']=2
            server.put(c,self.pid,'content',source,self.source)
        self.assertEqual(self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1}).status_code,409)
        self.assertTrue(self.a.get(self.url).json()['plans'][0]['source_outdated'])
        with self.assertRaises(Exception):
            vc.media_path(server.DB_PATH.parent,self.pid,{'storage_key':'../../geo.db','mime':'image/png'})

    @unittest.skipUnless(vc.capabilities()['available'], 'requires FFmpeg and Chinese font')
    def test_real_image_video_render_download_and_idempotency(self):
        folder=server.DB_PATH.parent/'assets'/self.pid
        vc.run_media([vc.shutil.which('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=c=0x175b47:s=640x360:r=25','-t','4','-c:v','libx264','-pix_fmt','yuv420p','clip.mp4'],folder)
        with server.db() as c:
            aid=server.put(c,self.pid,'asset',{'title':'模拟拍摄片段','mime':'video/mp4','category':'视频','storage_key':'clip.mp4'})
        self.body['scenes'].append({'text':'再结合材料、工艺与验证结果选择方案','asset_id':aid,'start':1,'seconds':3})
        p=self.create();r=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
        self.assertEqual(r.status_code,200,r.text);jid=r.json()['id'];job=self.wait(jid)
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertEqual(job['result']['seconds'],6)
        self.assertEqual(len(job['result']['media_snapshots']),2)
        repeat=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
        self.assertEqual(repeat.json()['id'],jid)
        file=self.a.get(self.url+'/renders/'+jid+'/file',headers={'Range':'bytes=0-99'})
        self.assertEqual(file.status_code,206);self.assertEqual(len(file.content),100)
        self.assertEqual(self.b.get(self.url+'/renders/'+jid+'/file').status_code,404)
        download=self.a.get(self.url+'/renders/'+jid+'/file?download=true')
        self.assertIn('attachment',download.headers['content-disposition'])
        path=server.DB_PATH.parent/'video-renders'/self.pid/jid/'preview.mp4'
        meta=json.loads(vc.run_media([vc.shutil.which('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',str(path)],folder))
        self.assertAlmostEqual(float(meta['format']['duration']),6,delta=.1)
        self.assertEqual((meta['streams'][0]['width'],meta['streams'][0]['height']),(1280,720))

    def test_failure_retry_and_restart_recovery(self):
        p=self.create()
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc,'render_movie',side_effect=ValueError('视频长度不足')):
            r=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
            j=self.wait(r.json()['id']);self.assertEqual(j['status'],'failed');self.assertEqual(j['error'],'视频长度不足')
            retry=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
            self.assertNotEqual(retry.json()['id'],j['id']);self.wait(retry.json()['id'])
        with server.db() as c:
            j['status']='running';server.put(c,self.pid,'video_render',j,j['id'])
        server.video_composition['recover']()
        recovered=next(x for x in self.a.get(self.url).json()['renders'] if x['id']==j['id'])
        self.assertEqual(recovered['status'],'failed');self.assertIn('重启',recovered['error'])

    def add_evidence(self):
        with server.db() as c:
            kid=server.put(c,self.pid,'knowledge',{'title':'模拟待核准资料','body':'核对条件','version':1,'status':'pending'})
            source=server.resource(c,self.pid,self.source,'content')
            source['sources']=[{'id':kid,'version':1,'body':'核对条件'}]
            server.put(c,self.pid,'content',source,self.source)
        return kid

    def change_evidence(self,kid):
        with server.db() as c:
            doc=server.resource(c,self.pid,kid,'knowledge');doc['version']+=1
            server.put(c,self.pid,'knowledge',doc,kid)

    def test_changed_evidence_blocks_plan_render_and_file(self):
        kid=self.add_evidence();p=self.create()
        with server.db() as c:
            job={'plan_id':p['id'],'plan_revision':1,'plan_snapshot':p,'source_id':self.source,
                 'source_revision':1,'status':'succeeded','result':{}}
            jid=server.put(c,self.pid,'video_render',job)
        folder=server.DB_PATH.parent/'video-renders'/self.pid/jid
        folder.mkdir(parents=True);(folder/'preview.mp4').write_bytes(b'isolated fixture')
        self.assertEqual(self.a.get(self.url+'/renders/'+jid+'/file?download=true').status_code,200)
        self.change_evidence(kid)
        self.assertEqual(self.a.post(self.url+'/plans',json=self.body).status_code,409)
        self.assertEqual(self.a.put(self.url+'/plans/'+p['id'],json={**self.body,'revision':1}).status_code,409)
        self.assertEqual(self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1}).status_code,409)
        listing=self.a.get(self.url).json()
        self.assertTrue(listing['plans'][0]['source_outdated'])
        self.assertTrue(listing['renders'][0]['source_outdated'])
        for suffix in ('','?download=true'):
            self.assertEqual(self.a.get(self.url+'/renders/'+jid+'/file'+suffix).status_code,409)
        self.assertTrue((folder/'preview.mp4').exists())

    def test_source_snapshot_checks_body_without_revision_change(self):
        p=self.create()
        with server.db() as c:
            source=server.resource(c,self.pid,self.source,'content');source['body']='正文被替换但版本未变'
            server.put(c,self.pid,'content',source,self.source)
        self.assertTrue(self.a.get(self.url).json()['plans'][0]['source_outdated'])
        self.assertEqual(self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1}).status_code,409)

    def test_changed_evidence_during_render_does_not_succeed(self):
        kid=self.add_evidence();p=self.create()
        def render(*args):
            self.change_evidence(kid)
            return {'seconds':3,'width':1280,'height':720}
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc,'render_movie',side_effect=render):
            response=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
            self.assertEqual(response.status_code,200,response.text)
            job=self.wait(response.json()['id'])
        self.assertEqual(job['status'],'failed')
        self.assertNotIn('result',job)

    def test_queued_video_rechecks_evidence_before_composition(self):
        kid=self.add_evidence();p=self.create()
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc.ThreadPoolExecutor,'submit'):
            response=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
        self.assertEqual(response.status_code,200,response.text)
        jid=response.json()['id'];self.change_evidence(kid)
        with patch.object(vc,'render_movie') as render:
            server.video_composition['execute'](self.pid,jid)
            render.assert_not_called()
        self.assertEqual(self.wait(jid)['status'],'failed')

    def change_render_actor_role(self, jid, role):
        with server.db() as c:
            job=server.resource(c,self.pid,jid,'video_render')
            if role is None:
                c.execute('DELETE FROM members WHERE project_id=? AND user_id=?',(self.pid,job['created_by']))
            else:
                c.execute('UPDATE members SET role=? WHERE project_id=? AND user_id=?',(role,self.pid,job['created_by']))

    def test_queued_video_rechecks_actor_permissions(self):
        p=self.create()
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc.ThreadPoolExecutor,'submit'):
            response=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
        self.assertEqual(response.status_code,200,response.text)
        jid=response.json()['id'];self.change_render_actor_role(jid,'reviewer')
        with patch.object(vc,'render_movie',return_value={}) as render:
            server.video_composition['execute'](self.pid,jid)
            render.assert_not_called()
        job=self.wait(jid)
        self.assertEqual(job['status'],'failed')
        self.assertIn('权限',job['error'])
        self.assertEqual(self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1}).status_code,403)
        self.change_render_actor_role(jid,'editor')
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc.ThreadPoolExecutor,'submit'):
            retry=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
        self.assertEqual(retry.status_code,200,retry.text)
        retry_id=retry.json()['id'];self.assertNotEqual(retry_id,jid)
        with patch.object(vc,'render_movie',return_value={'seconds':3}) as render:
            server.video_composition['execute'](self.pid,retry_id)
            render.assert_called_once()
        self.assertEqual(self.wait(retry_id)['status'],'succeeded')

    def test_video_rechecks_actor_membership_after_composition(self):
        p=self.create()
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc.ThreadPoolExecutor,'submit'):
            response=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
        self.assertEqual(response.status_code,200,response.text)
        jid=response.json()['id']
        def render(*args):
            self.change_render_actor_role(jid,None)
            return {'seconds':3,'width':1280,'height':720}
        with patch.object(vc,'render_movie',side_effect=render):
            server.video_composition['execute'](self.pid,jid)
        with server.db() as c:
            job=server.resource(c,self.pid,jid,'video_render')
        self.assertEqual(job['status'],'failed')
        self.assertNotIn('result',job)
        self.assertIn('权限',job['error'])
        self.assertEqual(self.a.get(self.url+'/renders/'+jid+'/file').status_code,404)

    def queued_render(self):
        p=self.create()
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc.ThreadPoolExecutor,'submit'):
            response=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['id']

    def replace_media(self):
        Image.new('RGB',(640,360),'red').save(server.DB_PATH.parent/'assets'/self.pid/'video-test.png')

    def test_queued_render_rejects_replaced_media(self):
        jid=self.queued_render();self.replace_media()
        with patch.object(vc,'render_movie',return_value={}) as render:
            server.video_composition['execute'](self.pid,jid)
            render.assert_not_called()
        job=self.wait(jid)
        self.assertEqual(job['status'],'failed');self.assertIn('素材',job['error'])

    def test_render_rejects_media_changed_during_composition(self):
        jid=self.queued_render()
        def changed(*args):
            self.replace_media()
            return {'seconds':3}
        with patch.object(vc,'render_movie',side_effect=changed):
            server.video_composition['execute'](self.pid,jid)
        job=self.wait(jid)
        self.assertEqual(job['status'],'failed');self.assertNotIn('result',job)

    def test_copy_receipt_must_match_queued_media(self):
        import hashlib
        folder=server.DB_PATH.parent/'assets'/self.pid
        path=folder/'video-test.png'
        plan={**self.body,'media_snapshots':{self.asset:{'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}}
        original_copy=vc.shutil.copyfile
        def changed_copy(src,dst):
            original_copy(src,dst)
            Image.new('RGB',(640,360),'red').save(dst)
        with patch.object(vc.shutil,'copyfile',side_effect=changed_copy),patch.object(vc,'run_media') as media:
            with self.assertRaisesRegex(ValueError,'素材'):
                vc.render_movie(plan,[(path,{'title':'模拟图片','mime':'image/png'})],folder/'copy-test','隔离测试')
            media.assert_not_called()

    def test_changed_media_does_not_reuse_previous_success(self):
        jid=self.queued_render()
        with patch.object(vc,'render_movie',return_value={'seconds':3}):
            server.video_composition['execute'](self.pid,jid)
        job=self.wait(jid);self.assertEqual(job['status'],'succeeded')
        self.replace_media()
        with patch.object(vc,'capabilities',return_value={'available':True}),patch.object(vc.ThreadPoolExecutor,'submit'):
            response=self.a.post(self.url+'/plans/'+job['plan_id']+'/render',json={'revision':1})
        self.assertEqual(response.status_code,200,response.text)
        retry=response.json()['id'];self.assertNotEqual(retry,jid)
        with patch.object(vc,'render_movie',return_value={'seconds':3}):
            server.video_composition['execute'](self.pid,retry)
        self.assertEqual(self.wait(retry)['status'],'succeeded')

    def test_queue_rejects_asset_record_hash_mismatch(self):
        p=self.create()
        with server.db() as c:
            asset=server.resource(c,self.pid,self.asset,'asset');asset['sha256']='0'*64
            server.put(c,self.pid,'asset',asset,self.asset)
        with patch.object(vc.ThreadPoolExecutor,'submit') as submit:
            response=self.a.post(self.url+'/plans/'+p['id']+'/render',json={'revision':1})
            self.assertEqual(response.status_code,409);submit.assert_not_called()


if __name__=='__main__': unittest.main()
