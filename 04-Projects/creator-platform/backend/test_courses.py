import uuid
from backend import test_commerce

class CourseTest(test_commerce.CommerceTest):
    def test_publish_unpublish_and_video_validation(self):
        route='/api/courses/'+str(uuid.uuid4())
        body=dict(title='测试课程',teacher='测试讲师',intro='课程说明',status='draft',lessons=[dict(title='第一课',url='https://example.com/video.mp4')])
        self.assertEqual(self.client.put(route,json=body).status_code,200)
        self.assertEqual(self.client.get('/api/courses').json(),[])
        self.assertEqual(len(self.client.get('/api/courses?admin=true').json()),1)
        body['status']='published'
        self.assertEqual(self.client.put(route,json=body).status_code,200)
        self.assertEqual(len(self.client.get('/api/courses').json()),1)
        body['status']='draft'
        self.assertEqual(self.client.put(route,json=body).status_code,200)
        self.assertEqual(self.client.get('/api/courses').json(),[])
        body['lessons'][0]['url']='javascript:alert(1)'
        self.assertEqual(self.client.put(route,json=body).status_code,422)
