import json
import os
import shutil
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from test_video_composer import VideoComposerTests
import video_skill_render as skills
import video_composer as vc


class VideoSkillTests(unittest.TestCase):
    def setUp(self):
        self.fixture=VideoComposerTests('runTest');self.fixture.setUp()
        self.a,self.url=self.fixture.a,self.fixture.url

    def test_engine_validation_and_missing_runtime(self):
        self.assertEqual(self.a.post(self.url+'/plans',json={**self.fixture.body,'engine':'shell'}).status_code,422)
        self.fixture.body['engine']='hyperframes';plan=self.fixture.create()
        with patch.object(skills,'capabilities',return_value=[]):
            r=self.a.post(self.url+'/plans/'+plan['id']+'/render',json={'revision':1})
        self.assertEqual(r.status_code,503)
        self.assertEqual(self.a.get(self.url).json()['renders'],[])

    def test_text_cannot_become_executable_markup(self):
        data={'brand':'<script>alert(1)</script>','width':720,'height':1280,'seconds':3,
              'scenes':[{'text':'</p><script>alert(2)</script>','file':'media-0.png','seconds':3,'video':False}]}
        out=skills.hyperframes_source(data)
        self.assertNotIn('<script>alert',out)
        self.assertIn('&lt;script&gt;',out)
        out=skills.remotion_source(data)
        self.assertIn('JSON.parse(',out)
        self.assertIn('{s.text}',out)

    @unittest.skipUnless(os.environ.get('GEO_TEST_VIDEO_SKILLS')=='1','explicit local engine render test')
    def test_real_engines_through_api(self):
        from test_workflow import server
        from PIL import Image
        folder=server.DB_PATH.parent/'assets'/self.fixture.pid
        vc.run_media([shutil.which('ffmpeg'),'-v','error','-y','-f','lavfi','-i',
                      'color=c=red:s=640x360:r=30:d=1','-f','lavfi','-i',
                      'color=c=0x175b47:s=640x360:r=30:d=4','-filter_complex',
                      '[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]',
                      '-c:v','libx264','-pix_fmt','yuv420p','skill-test.mp4'],folder)
        with server.db() as c:
            aid=server.put(c,self.fixture.pid,'asset',{'title':'合成偏移测试片段','mime':'video/mp4',
                           'category':'视频','storage_key':'skill-test.mp4'})
        self.fixture.body['scenes'].append({'text':'第二镜头验证素材切换与视频起点','asset_id':aid,'start':1,'seconds':3})
        for engine in ('remotion','hyperframes'):
            with self.subTest(engine=engine):
                self.fixture.body['engine']=engine;plan=self.fixture.create()
                r=self.a.post(self.url+'/plans/'+plan['id']+'/render',json={'revision':1})
                self.assertEqual(r.status_code,200,r.text);jid=r.json()['id']
                for _ in range(360):
                    job=next(x for x in self.a.get(self.url).json()['renders'] if x['id']==jid)
                    if job['status'] not in ('queued','running'):break
                    time.sleep(.5)
                render_folder=server.DB_PATH.parent/'video-renders'/self.fixture.pid/jid
                detail=(render_folder/'render.log').read_text(encoding='utf-8',errors='replace') if (render_folder/'render.log').exists() else ''
                self.assertEqual(job['status'],'succeeded',str(job.get('error'))+'\n'+detail[-5000:])
                self.assertEqual(job['result']['engine'],engine)
                self.assertEqual(job['result']['seconds'],6)
                self.assertEqual(len(job['result']['media_snapshots']),2)
                self.assertEqual(job['result']['recipe_version'],skills.RECIPE_VERSION)
                again=self.a.post(self.url+'/plans/'+plan['id']+'/render',json={'revision':1})
                self.assertEqual(again.json()['id'],jid)
                self.assertEqual(self.fixture.b.get(self.url+'/renders/'+jid+'/file').status_code,404)
                response=self.a.get(self.url+'/renders/'+jid+'/file',headers={'Range':'bytes=0-99'})
                self.assertEqual(response.status_code,206)
                self.assertEqual(len(response.content),100)
                from test_workflow import server
                path=server.DB_PATH.parent/'video-renders'/self.fixture.pid/jid/'preview.mp4'
                dest=Path('outputs/iteration102-video-engines');dest.mkdir(exist_ok=True,parents=True)
                shutil.copyfile(path,dest/(engine+'.mp4'))
                (dest/(engine+'.json')).write_text(json.dumps(job['result'],ensure_ascii=False,indent=2),encoding='utf-8')
                for label,at,expected in [('image',1,(35,100,120)),('video',3.2,(23,91,71))]:
                    frame=(dest/(engine+'-'+label+'.png')).resolve()
                    vc.run_media([shutil.which('ffmpeg'),'-v','error','-y','-ss',str(at),'-i',str(path),
                                  '-frames:v','1',str(frame)],folder)
                    with Image.open(frame) as img:
                        actual=img.convert('RGB').getpixel((640,260))
                    self.assertTrue(all(abs(a-b)<10 for a,b in zip(actual,expected)),(engine,label,actual))
