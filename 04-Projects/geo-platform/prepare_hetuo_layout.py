"""Compose customer-provided template and exact article excerpts, with versioned approval."""
from sample_review import layout_current, current_blocks
import hashlib
import io
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import server as s
from source_import import store_asset

PROJECT='a46fb911b04fbf0b783c7bf5'
TEMPLATE=Path('C:/Users/pc02a/Desktop/和拓-配图模版.png')
FONT='C:/Windows/Fonts/msyh.ttc'

def lines(draw,text,font,width):
    out=[];line=''
    for char in text:
        if char=='\n' or (line and draw.textlength(line+char,font=font)>width):
            out.append(line);line='' if char=='\n' else char
        else: line+=char
    if line:out.append(line)
    return out

def card(template,title,excerpt,index):
    im=template.copy().convert('RGB');d=ImageDraw.Draw(im)
    sx,sy=im.width/2048,im.height/593
    # All added pixels remain in the supplied right white panel.
    x,y,w=int(450*sx),int(48*sy),int(1510*sx)
    def text(value,top,size,color,limit):
        font=ImageFont.truetype(FONT,max(12,int(size*sy)))
        wrapped=lines(d,value,font,w)
        if len(wrapped)>limit:wrapped=wrapped[:limit];wrapped[-1]=wrapped[-1].rstrip('，。；')+'…'
        for n,line in enumerate(wrapped):d.text((x,top+n*int(size*1.42*sy)),line,font=font,fill=color)
    text('HEROTO  /  技术与采购参考' if index==0 else f'内容要点  {index:02d}',y,25,'#168779',1)
    text(title,int(112*sy),47 if index==0 else 40,'#153d51',3 if index==0 else 2)
    d.line((x,int(322*sy),x+w,int(322*sy)),fill='#a8d9d2',width=max(1,int(2*sy)))
    text(excerpt,int(350*sy),28,'#365d66',4)
    out=io.BytesIO();im.save(out,format='PNG');return out.getvalue()

def run():
    raw=TEMPLATE.read_bytes();digest=hashlib.sha256(raw).hexdigest();template=Image.open(io.BytesIO(raw))
    changed=[]
    with s.db() as c:
        project=s.project(c,PROJECT)
        assert project['website'].rstrip('/')=='https://www.heroto.com.cn'
        actor=c.execute('SELECT user_id FROM members WHERE project_id=? AND role="owner"',(PROJECT,)).fetchone()[0]
        tid=store_asset(vars(s),c,PROJECT,raw,'和拓-配图模板.png',{'type':'customer_brand_template'},'图片')
        for content in s.items(c,PROJECT,'content'):
            if content.get('origin')!='customer_prepublication':continue
            body_hash=hashlib.sha256(content['body'].encode()).hexdigest()
            if content.get('layout',{}).get('template_sha256')==digest and layout_current(content):continue
            assert content['status'] in ('draft','pending','rejected'), '已审批或执行中稿件须另行处理'
            assert not any(p.get('content_id')==content['id'] and p['status'] not in ('cancelled',) for p in s.items(c,PROJECT,'publication'))
            original_blocks=current_blocks(content)
            blocks=[{**b,'image_ids':[]} for b in original_blocks]
            meaningful=[(i,re.sub(r'\[正文块\s*\d+\]','',b.get('text','')).strip()) for i,b in enumerate(blocks)]
            meaningful=[(i,t) for i,t in meaningful if len(t)>25 and t!=content['title']]
            if not meaningful:continue
            selections=[meaningful[min(len(meaningful)-1,int(n*len(meaningful)/4))] for n in range(4)]
            title=re.sub(r'^\d+[、.．]\s*','',content['title'])
            assets=[]
            for index in range(5):
                if index==0:heading=title;excerpt='从企业资料出发，梳理技术要点、适用条件与采购关注项。'
                else:
                    _,paragraph=selections[index-1]
                    first=re.split(r'[。！？\n]',paragraph)[0].strip()
                    heading=first if 3<len(first)<=45 else ['原理与应用','工况与选择','验证与依据','采购与落地'][index-1]
                    excerpt=paragraph[:155]+('…' if len(paragraph)>155 else '')
                png=card(template,heading,excerpt,index)
                aid=store_asset(vars(s),c,PROJECT,png,f'{content["id"]}-品牌配图-{index+1}.png',{'type':'article_brand_card','content_id':content['id'],'body_sha256':body_hash,'template_asset_id':tid,'excerpt':excerpt,'source_block':None if index==0 else selections[index-1][0]},'图片')
                asset=s.resource(c,PROJECT,aid,'asset');asset.update(collection='和拓文章品牌配图',tags=['和拓实业','文章配图','客户审阅'],description='客户模板右侧排版；正文摘录不代表事实核准。');s.put(c,PROJECT,'asset',asset,aid);assets.append(aid)
            content.setdefault('history',[]).append({k:content.get(k) for k in ('revision','title','body','status','layout','platform_payloads')})
            content['layout']={'cover_id':assets[0],'blocks':blocks,'body_sha256':body_hash,'title_sha256':hashlib.sha256(content['title'].encode()).hexdigest(),'template_sha256':digest,'template_asset_id':tid,'figures':[{'asset_id':aid,'caption':f'文章要点 {i+1} · 原文摘录，技术结论待核准','after':selections[i][0]} for i,aid in enumerate(assets[1:])]}
            content.update(revision=content['revision']+1,status='pending',approved_revision=None,preparation_status='5 张品牌配图已排版 · 待客户核准图文')
            content['review_notes']=[n for n in content.get('review_notes',[]) if '未选定' not in n and '待选' not in n]+['本版使用客户提供的和拓配图模板，共5张品牌图；请核准摘录、技术依据与最终渠道裁切。']
            for variant in content.get('platform_payloads',{}).values():variant.update(cover_id=assets[0],attachment_ids=assets[1:])
            s.put(c,PROJECT,'content',content,content['id']);changed.append(content['id'])
        if changed:s.event(c,PROJECT,actor,'完成客户图文排版',f'{len(changed)}篇，每篇5张和拓模板配图；更新稿件版本，保持待审核；未发布')
    print({'updated_articles':len(changed),'images_per_article':5,'published':False})

if __name__=='__main__':run()
