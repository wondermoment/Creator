"""Trusted local render recipes adapted from the installed Remotion/HyperFrames skills.

Customer text is data, never source code. No arbitrary HTML, JS or command input.
"""
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).parent
RUNTIME = ROOT / '.runtime' / 'video-skills'
RECIPE_VERSION = '2026-10-05.1'
ENGINES = {'remotion': ('Remotion 动画', '@remotion/cli', 'remotion-cli.js'),
           'hyperframes': ('HyperFrames 动效', 'hyperframes', 'bin/hyperframes.mjs')}


def browser_path():
    return RUNTIME/'node_modules/.remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe'


def capabilities():
    rows = []
    for key, (name, package, entry) in ENGINES.items():
        folder = RUNTIME/'node_modules'/package
        try:
            version = json.loads((folder/'package.json').read_text(encoding='utf-8'))['version']
        except (OSError, ValueError, KeyError):
            version = ''
        ready = bool(version and (folder/entry).is_file() and browser_path().is_file() and shutil.which('node'))
        if key == 'hyperframes':
            ready = ready and (RUNTIME/'node_modules/gsap/dist/gsap.min.js').is_file()
        rows.append({'id': key, 'name': name, 'available': ready, 'version': version,
                     'recipe_version': RECIPE_VERSION, 'audio': False,
                     'message': '可生成动画预览，配音待接入' if ready else '渲染依赖未就绪'})
    return rows


def run(args, folder, env=None):
    try:
        result = subprocess.run(args, cwd=folder, env=env, capture_output=True, timeout=900,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (subprocess.TimeoutExpired, OSError):
        raise ValueError('动画渲染未完成，请检查本机环境或缩短镜头后重试') from None
    (folder/'render.log').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError('动画引擎渲染失败，制作稿已保留；请检查素材和渲染环境')


def remotion_source(data):
    # JSON.parse of a JSON string keeps user text out of JSX and JS syntax.
    react = json.dumps((RUNTIME/'node_modules/react').as_posix())
    remotion = json.dumps((RUNTIME/'node_modules/remotion').as_posix())
    source = '''import React from REACT;
import {AbsoluteFill,Composition,Sequence,Img,OffthreadVideo,registerRoot,useCurrentFrame,interpolate,staticFile} from REMOTION;
const d=JSON.parse(DATA);
const Shot=({s,i})=>{const f=useCurrentFrame(),n=s.seconds*30;
const enter=interpolate(f,[0,18],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const media={width:'100%',height:'100%',objectFit:'contain'};
return <AbsoluteFill style={{background:'#12343a',fontFamily:'Microsoft YaHei',color:'white',overflow:'hidden'}}>
<AbsoluteFill style={{height:'75%',transform:`scale(${1+f/n*.035})`,justifyContent:'center',alignItems:'center'}}>
{s.video?<OffthreadVideo src={staticFile(s.file)} startFrom={Math.round(s.start*30)} muted style={media}/>:<Img src={staticFile(s.file)} style={media}/>}
</AbsoluteFill>
<div style={{position:'absolute',top:34,left:42,fontSize:24,padding:'10px 18px',background:'#12343acc',borderLeft:'4px solid #009168'}}>{d.brand}</div>
<div style={{position:'absolute',bottom:0,left:0,right:0,minHeight:'25%',padding:'26px 42px 38px',boxSizing:'border-box',background:'#f4f8f6',color:'#174557'}}>
<div style={{fontSize:20,color:'#009168',marginBottom:14}}>{String(i+1).padStart(2,'0')} / {String(d.scenes.length).padStart(2,'0')} · 动画预览</div>
<div style={{fontSize:d.width===1280?38:32,lineHeight:1.4,whiteSpace:'pre-wrap',overflowWrap:'anywhere',opacity:enter,transform:`translateY(${(1-enter)*22}px)`}}>{s.text}</div></div>
<div style={{position:'absolute',bottom:0,left:0,height:6,width:`${(f+1)/n*100}%`,background:'#009168'}}/>
</AbsoluteFill>};
const Movie=()=>{let start=0;return <AbsoluteFill>{d.scenes.map((s,i)=>{const from=start;start+=s.seconds*30;return <Sequence key={i} from={from} durationInFrames={s.seconds*30}><Shot s={s} i={i}/></Sequence>})}</AbsoluteFill>};
registerRoot(()=> <Composition id="GeoVideo" component={Movie} width={d.width} height={d.height} fps={30} durationInFrames={d.seconds*30}/>);
'''
    return source.replace('REACT', react).replace('REMOTION', remotion).replace('DATA', json.dumps(json.dumps(data, ensure_ascii=False)))


def hyperframes_source(data):
    scenes, animations, offset = [], [], 0
    for i, s in enumerate(data['scenes']):
        src = 'media/' + s['file']
        timing = f'id="media-{i}" class="clip media" src="{src}" data-start="{offset}" data-duration="{s["seconds"]}" data-track-index="1"'
        media = (f'<video {timing} data-media-start="{s["start"]}" data-volume="0" muted></video>' if s['video'] else f'<img {timing} alt="">')
        # Media is a direct child of the stage: nesting two timed elements shifts video extraction.
        scenes.append(media + f'<section id="scene-{i}" class="clip scene" data-start="{offset}" data-duration="{s["seconds"]}" data-track-index="0"><div class="brand">{html.escape(data["brand"])}</div><div class="caption"><p class="count">{i+1:02d} / {len(data["scenes"]):02d} · 动画预览</p><p id="text-{i}" class="text">{html.escape(s["text"])}</p></div><div id="progress-{i}" class="progress"></div></section>')
        animations.append(f"tl.fromTo('#text-{i}',{{y:22,opacity:0}},{{y:0,opacity:1,duration:.6}}, {offset});tl.fromTo('#progress-{i}',{{scaleX:0}},{{scaleX:1,duration:{s['seconds']},ease:'none'}},{offset});")
        offset += s['seconds']
    size = 38 if data['width'] == 1280 else 32
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Microsoft YaHei';src:local('Microsoft YaHei')}}
body{{margin:0}}#root{{width:{data['width']}px;height:{data['height']}px;position:relative;overflow:hidden;font-family:'Microsoft YaHei',sans-serif;background:#12343a}}
.scene{{position:absolute;inset:0;z-index:1}}.media{{position:absolute;top:0;left:0;width:100%;height:75%;object-fit:contain;z-index:0}}
.brand{{position:absolute;top:34px;left:42px;padding:10px 18px;background:#12343acc;border-left:4px solid #009168;color:white;font-size:24px}}
.caption{{position:absolute;bottom:0;left:0;right:0;min-height:25%;padding:26px 42px 38px;box-sizing:border-box;background:#f4f8f6;color:#174557}}
p{{margin:0}}.count{{font-size:20px;color:#009168;margin-bottom:14px}}.text{{font-size:{size}px;line-height:1.4;white-space:pre-wrap;overflow-wrap:anywhere}}.progress{{position:absolute;bottom:0;left:0;width:100%;height:6px;background:#009168;transform-origin:left}}
</style></head><body><div id="root" data-composition-id="root" data-start="0" data-duration="{offset}" data-width="{data['width']}" data-height="{data['height']}" data-fps="30">{''.join(scenes)}</div><script src="gsap.min.js"></script><script>const tl=gsap.timeline({{paused:true}});{''.join(animations)}window.__timelines={{root:tl}};</script></body></html>'''


def render(plan, assets, folder, brand):
    from PIL import Image
    from video_composer import run_media, file_digest
    engine = plan['engine']
    cap = next((x for x in capabilities() if x['id'] == engine and x['available']), None)
    if not cap:
        raise ValueError('所选动画引擎未就绪，请检查本机依赖')
    folder = folder.resolve(); media = folder/'media'; media.mkdir(parents=True, exist_ok=True)
    width, height = {'landscape': (1280, 720), 'portrait': (720, 1280), 'square': (720, 720)}[plan['aspect']]
    data = {'brand': brand[:22], 'width': width, 'height': height,
            'seconds': sum(s['seconds'] for s in plan['scenes']), 'scenes': []}
    receipts = []
    for i, (scene, (original, asset)) in enumerate(zip(plan['scenes'], assets)):
        video = asset['mime'] == 'video/mp4'
        name = f'media-{i}' + ('.mp4' if video else '.png')
        raw = original.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
        if digest != plan['media_snapshots'][scene['asset_id']]['sha256']:
            raise ValueError('素材已变化，请重新核对并生成')
        if video:
            (media/name).write_bytes(raw)
            probe=json.loads(run_media([shutil.which('ffprobe'),'-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration','-of','json',name],media,20))
            if float(probe.get('format',{}).get('duration',0)) < scene['start']+scene['seconds']:
                raise ValueError(f'镜头 {i+1} 的视频长度不足')
        else:
            import io
            with Image.open(io.BytesIO(raw)) as image:
                if image.width*image.height>40_000_000: raise ValueError('图片像素过大，请先压缩素材')
                image.convert('RGB').save(media/name)
        data['scenes'].append({**scene, 'file': name, 'video': video})
        receipts.append({'asset_id': scene['asset_id'], 'sha256': digest, 'title': asset['title']})
    (folder/'plan.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    output=folder/'preview.mp4'
    env={**os.environ,'HYPERFRAMES_BROWSER_PATH':str(browser_path())}
    node=shutil.which('node'); _, package, entry=ENGINES[engine]
    cli=RUNTIME/'node_modules'/package/entry
    if engine=='remotion':
        source=folder/'index.tsx';source.write_text(remotion_source(data),encoding='utf-8')
        run([node,str(cli),'render',str(source),'GeoVideo',str(output),'--public-dir='+str(media),
             '--browser-executable='+str(browser_path()),'--concurrency=1','--log=error'],folder,env)
    else:
        (folder/'index.html').write_text(hyperframes_source(data),encoding='utf-8')
        shutil.copyfile(RUNTIME/'node_modules/gsap/dist/gsap.min.js',folder/'gsap.min.js')
        run([node,str(cli),'render',str(folder),'--output',str(output),'--workers','1','--no-browser-gpu','--strict'],folder,env)
    probe=json.loads(run_media([shutil.which('ffprobe'),'-v','error','-show_streams','-show_format','-of','json',str(output)],folder,30))
    video=next((x for x in probe['streams'] if x['codec_type']=='video'),{})
    if (video.get('width'),video.get('height'))!=(width,height) or abs(float(probe['format']['duration'])-data['seconds'])>.15:
        raise ValueError('成片尺寸或时长不符，暂不交付')
    return {'width':width,'height':height,'seconds':data['seconds'],'bytes':output.stat().st_size,
            'sha256':file_digest(output),'media_snapshots':receipts,'engine':engine,
            'engine_version':cap['version'],'recipe_version':RECIPE_VERSION,'audio':False}
