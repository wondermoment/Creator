import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='Use your built-in image_gen tool to generate ONE square watercolor recipe illustration sheet with four equal square panels in a clean 2x2 grid, wide ivory gutters. No text, letters or numbers. Elegant hand-painted watercolor on warm white paper, appetizing realistic food, sage green, salmon coral and lemon yellow, delicate pigment blooms. Top left: ingredients on board, raw salmon fillet, broccoli florets, small bowl dry quinoa, lemon. Top right: quinoa simmering in saucepan and broccoli steaming in basket, no hands. Bottom left: salmon on baking tray with oven mitt beside a small oven, cooked salmon golden surface. Bottom right: finished salmon quinoa broccoli bowl with lemon wedge. Overhead/three-quarter consistent editorial cookbook style. Each panel is independent and centered with generous white margins. Do not use API keys, shell, SVG, or tools other than built-in image_gen. Return actual generated file path.'
Path('output/imagegen/salmon-watercolor-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-c','features.image_gen=true','-']
r=subprocess.run(args,input=prompt.encode(),capture_output=True,env=environment('.runtime'),timeout=360)
Path('output/imagegen/salmon-watercolor-result.txt').write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode('utf-8',errors='replace')[-4500:])
