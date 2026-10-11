import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
kind=sys.argv[1]
if kind=='process':
 rows=json.loads(Path('output/imagegen/recipe-handwritten-manifest.json').read_text('utf-8'))
 rows=[x for x in rows if x['id'] in ['bean-salad','tomato-egg','broccoli-chicken','pumpkin-millet']]
 prompt='''Use native built-in image_gen via ChatGPT login ONLY, no API keys. Generate FOUR separate watercolor recipe process strips, one image_gen call per recipe below. Each strip landscape 3:1, exactly THREE equal square panels left to right with no gutters. Each panel depicts ONE corresponding actual cooking step, not static ingredient inventory. Warm ivory watercolor paper, delicate realistic food illustration, sage ceramics, warm brown small handwritten Chinese operation label. Match attached approved watercolor style. For each recipe show steps[0],steps[1],steps[2] in order. No extra title across panels, no text straddling panels; ample inside margins. Show cooking hands/actions, distinct correct tools, clear ingredients. For bean-salad: rinse COOKED canned whitebeans in colander, steam broccoli with cut tomatoes separate, toss bowl and plate with wholewheat bread. For tomato egg: chop tomatoes and tofu and beat egg, simmer tomato/tofu soup, pour egg then finished fully cooked egg soup alongside grain rice. For chicken: separate raw meat board and vegetable board, cook chicken and mushrooms, cooked chicken broccoli rice with food thermometer marking 74°C. For millet: rinse millet/cut pumpkin, simmer porridge, steam fully set egg and serve with porridge. Do not imply raw beans are safe or undercooked chicken/egg. Return each recipe id and actual image path immediately. No project edits. Data:\n'''+json.dumps(rows,ensure_ascii=False)
else:
 prompt='''Use native built-in image_gen via ChatGPT login ONLY, no API keys. Generate SIX separate square high quality Chinese science editorial illustrations, one image_gen call per item. For mobile nutrient educational cards and full article header. Sophisticated realistic watercolor with clean scientific cutaway, warm ivory paper, muted golden yellow accents and lavender details, generous space, crisp legible Chinese labels (few words), not icons, no fake molecular structures, no pills as main subject, no clinical benefit promises. Each has large exact title, beautiful main scientific subject, at most two labels, small bottom evidence boundary. Scientific pathways are simplified illustrations not literal size relationships. Return id and actual path immediately after each. No project edits.
1 id nad: title NAD+; detailed cell and mitochondrial cutaway, circular NAD+ / NADH cofactor recycling concept with tasteful arrows; label 参与细胞能量代谢; footer 补充延寿尚未证实.
2 id q10: title 辅酶 Q10; detailed inner mitochondrial membrane with Q10 carrying electrons between membrane complexes; label 线粒体电子传递; footer 不替代标准治疗.
3 id nmn: title NMN; readable simple precursor pathway NMN → NAD+ beside illustrated cell, do not imply direct life extension; label NAD+ 合成前体; footer 人体长期证据有限.
4 id pqq: title PQQ; research microscope and translucent cell/mitochondria, restrained dotted research connectors, do not imply guaranteed mitochondrial biogenesis in people; label 氧化还原机制研究; footer 机制研究不等于人体疗效.
5 id omega3: title Omega-3; realistically illustrated oily fish and cutaway cell membrane with stylized lipid tails, labels EPA · DHA and 脂肪酸与细胞膜; footer 食物与处方制剂需区分.
6 id vitamin-d: title 维生素 D; tasteful sunlight/skin cue, intestine calcium absorption and bone cutaway as a clear three-part educational composition, label 钙吸收与骨骼健康; footer 纠正缺乏，避免过量.
'''
Path('output/imagegen/'+kind+'-science-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"']
if kind=='process': args+=['-i',str(Path('output/imagegen/tofu-handwritten-preview.png').resolve())]
args+=['-']
with Path('output/imagegen/'+kind+'-science-result.txt').open('wb') as out:
 r=subprocess.run(args,input=prompt.encode(),stdout=out,stderr=out,env=environment('.runtime'),timeout=3600)
print(kind,r.returncode)
