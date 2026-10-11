from PIL import Image,ImageDraw
from pathlib import Path
import json
paths=sorted(Path(r'C:/Users/pc02a/Creator/04-Projects/geo-platform/.runtime/codex-local/generated_images/01a10747-d0a0-7541-ae22-8f5144d3dcf4').glob('*.png'),key=lambda p:p.stat().st_mtime)
canvas=Image.new('RGB',(1000,((len(paths)+3)//4)*275),'white');d=ImageDraw.Draw(canvas)
for i,p in enumerate(paths):
 im=Image.open(p);im.thumbnail((245,245));x=i%4*250;y=i//4*275;canvas.paste(im,(x,y));d.text((x,y+245),str(i+1)+' '+p.name[5:13],fill='black')
canvas.save('output/imagegen/recipe-progress.jpg');Path('output/imagegen/recipe-image-order.json').write_text(json.dumps([str(p) for p in paths]),encoding='utf-8')
