"""Deterministic editorial covers using supplied brand artwork, no generated claims."""
import io
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import server as s
from source_import import store_asset

TITLES=[('硅晶前处理','是什么？适不适合你的产线？'),('掉漆 · 返锈 · 盐雾','从前处理环节排查产线问题'),('工艺怎么选','磷化、发黑、镀锌与硅晶'),('前处理的成本与价值','从产线条件到综合成本'),('成本与落地','老板关心的 6 个问题'),('品控与环保','先看检测条件，再看工艺边界'),('硅晶靠不靠谱','采购与工程师的验证清单'),('供应商怎么选','从行业判断到企业评估')]

def run():
 with s.db() as c:
  pid=c.execute('SELECT id FROM projects WHERE name=?',('和拓实业',)).fetchone()[0]
  original=Image.open(Path('C:/Users/pc02a/Desktop/和拓宣传册2025/和拓宣传册2025/1.png')).convert('RGB')
  # User supplied brandmark from the brochure, intact at this crop.
  logo=original.crop((860,293,1272,575));logo.thumbnail((300,205))
  for item in s.items(c,pid,'content'):
   if item.get('origin')!='customer_prepublication':continue
   n=int(item['title'].split('、')[0]);t,sub=TITLES[n-1]
   image=Image.new('RGB',(1200,630),'#f8fafb');d=ImageDraw.Draw(image)
   d.rectangle((0,0,26,630),fill='#278caf');d.rectangle((26,0,40,630),fill='#36b3ab')
   font=lambda size:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)
   d.text((88,64),'HEROTO  /  和拓化学',font=font(27),fill='#247d95')
   d.text((88,180),t,font=font(62),fill='#16364d')
   d.text((90,278),sub,font=font(34),fill='#46616f')
   d.line((90,375,710,375),fill='#cfdbdf',width=2)
   d.text((90,416),'制造业 · 技术与采购参考',font=font(24),fill='#657983')
   d.text((90,475),f'内容系列  {n:02d} / 08',font=font(23),fill='#278caf')
   image.paste(logo,(865,395))
   data=io.BytesIO();image.save(data,format='PNG')
   aid=store_asset(vars(s),c,pid,data.getvalue(),f'和拓待发稿-{n:02d}-封面.png',{'type':'editorial_cover','brand_source':'宣传册2025/1.png','content_id':item['id']},'图片')
   a=s.resource(c,pid,aid,'asset');a.update(collection='待发布原稿与配图',tags=['和拓实业','HEROTO','封面'],description='原企业Logo搭配编辑标题；1200×630，发布端裁切需预览确认。');s.put(c,pid,'asset',a,aid)
   if item['layout'].get('cover_id')==aid:continue
   item['history'].append({'revision':item['revision'],'title':item['title'],'body':item['body'],'status':item['status'],'layout':item['layout']})
   item['layout']={**item['layout'],'cover_id':aid};item['revision']+=1;item['approved_revision']=None;item['status']='pending'
   for variant in item.get('platform_payloads',{}).values():variant['cover_id']=aid
   s.put(c,pid,'content',item,item['id'])
  print('8 editorial covers prepared; approvals remain pending.')

if __name__=='__main__':run()
