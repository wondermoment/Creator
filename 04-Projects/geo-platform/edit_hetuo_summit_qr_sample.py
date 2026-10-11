"""One customer-requested white QR mask, preserving the original asset."""
import copy
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import server as s
from sample_review import layout_current, require_current_sources, render_reader, embedded_asset_url

ROOT = Path(__file__).resolve().parent
PID = 'a46fb911b04fbf0b783c7bf5'
RID = 'abcdc847b779a9ebfbe1c3d4'
AID = 'cc4e80da25067ca54f4a7330'
BOX = (980, 630, 1080, 720)

def main():
    out = ROOT / 'outputs' / 'hetuo-qr-sample'
    out.mkdir(parents=True, exist_ok=True)
    with s.db() as c:
        assert s.project(c, PID)['website'].rstrip('/') == 'https://www.heroto.com.cn'
        baseline = {r['id']: r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        row = s.resource(c, PID, RID, 'content')
        assert row['revision'] == 5 and row['status'] == 'pending' and layout_current(row)
        require_current_sources(vars(s), c, PID, row)
        assert not any(j.get('status') in ('queued', 'running') for j in s.items(c, PID, 'execution'))
        assert not any(p.get('content_id') == RID and p['status'] != 'cancelled' for p in s.items(c, PID, 'publication'))
        original = s.resource(c, PID, AID, 'asset')
        source = ROOT / '.runtime/assets' / PID / original['storage_key']
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original['sha256']
        im = Image.open(source).convert('RGB')
        assert im.size == (1080, 720)
        edited = im.copy()
        ImageDraw.Draw(edited).rectangle((BOX[0], BOX[1], BOX[2]-1, BOX[3]-1), fill='white')
        diff = ImageChops.difference(im, edited).getbbox()
        assert diff and diff[0] >= BOX[0] and diff[1] >= BOX[1] and diff[2] <= BOX[2] and diff[3] <= BOX[3]
        assert edited.crop(BOX).getextrema() == ((255,255),(255,255),(255,255))
        target = out / '峰会交流-右下角去二维码-样版.png'
        edited.save(target)
        raw = target.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        key = 'summit-qr-white-' + sha[:20] + '.png'
        (source.parent / key).write_bytes(raw)
        asset = {k: copy.deepcopy(v) for k,v in original.items() if k not in ('id','kind','created','updated')}
        asset.update(title=original['title'] + ' · 右下角白底去二维码样版', storage_key=key, sha256=sha, size=len(raw), mime='image/png',
                     derived_from_asset_id=AID, edit_provenance={'operation':'white_rectangle','box':list(BOX),'original_sha256':original['sha256'],'requested_scope':'one-image-sample'})
        new_id = s.put(c, PID, 'asset', asset)
        before = copy.deepcopy(row)
        hits = 0
        for figure in row['layout']['figures']:
            if figure['asset_id'] == AID:
                figure['asset_id'] = new_id
                hits += 1
        assert hits == 1
        for variant in row.get('platform_payloads',{}).values():
            variant['attachment_ids'] = [new_id if aid == AID else aid for aid in variant.get('attachment_ids',[])]
        row.setdefault('history',[]).append({k:copy.deepcopy(before.get(k)) for k in ('revision','title','body','channels','status','layout','platform_payloads')})
        row['layout'].setdefault('asset_edits',[]).append({'original_asset_id':AID,'asset_id':new_id,'operation':'右下角二维码区域填白','box':list(BOX)})
        row.update(revision=6, approved_revision=None, review_note='')
        row.pop('quality',None)
        s.put(c, PID, 'content', row, RID)
        after = {r['id']:r['data'] for r in c.execute("SELECT id,data FROM resources WHERE kind='content'")}
        assert [k for k in baseline if baseline[k] != after[k]] == [RID]
        for k in ('title','body','sources','channels'): assert row[k] == before[k]
        assert len(row['layout']['figures']) == len(before['layout']['figures'])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original['sha256']
        s.event(c,PID,'local-design-assistant','峰会照片去二维码单图样版',RID+' · v5 → v6 · 只替换末尾一张照片的右下角二维码；原图保留；未发布')
        document = render_reader(s.project(c,PID),row,embedded_asset_url(vars(s),c,PID))
    (out/'客户预览-v6.html').write_text(document,encoding='utf-8')
    (out/'verification.json').write_text(json.dumps({'article_id':RID,'revision':6,'old_asset_id':AID,'new_asset_id':new_id,'box':BOX,'pixel_difference_bbox':diff,'original_preserved':True,'other_articles_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'revision':6,'new_asset_id':new_id,'output':str(target)},ensure_ascii=False))

if __name__ == '__main__':
    main()
