import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='Use native built-in image_gen with attached original Cyber Qiao character reference. Generate one 2x2 sheet, four equal square panels separated at exact center, no gutters. Preserve same purple tousled short hair, transparent glasses, blue eyes, white sporty shirt and purple shorts, cute detailed chibi anime rendering. Top left: Qiao composing AI music, wearing headphones, hands on small MIDI keyboard beside laptop with abstract audio tracks. Top right: Qiao painting watercolor landscape at easel with brush and palette. Bottom left: Qiao making scrapbook, arranging colored paper photographs stickers washi tape in open journal with both hands. Bottom right: Qiao writing diary with pen in open notebook at cozy desk, tea nearby. Character face prominently visible in each, medium wide view includes head hands and task props, generous margins. Sophisticated warm ivory lavender pastel studio backgrounds, luminous, joyful, clean professional detailed illustration, no lettering logos or watermarks, no extra limbs, each action unambiguous. Use only image_gen, no API keys or code drawings. Return actual generated file path, do not modify project files.'
Path('output/imagegen/qiao-creative-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-i',str(Path('output/imagegen/qiao-original-reference.jpg').resolve()),'-']
r=subprocess.run(args,input=prompt.encode(),capture_output=True,env=environment('.runtime'),timeout=420)
Path('output/imagegen/qiao-creative-result.txt').write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode('utf-8',errors='replace')[-2000:])
