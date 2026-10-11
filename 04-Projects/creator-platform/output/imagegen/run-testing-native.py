import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='Use built-in image_gen only through ChatGPT login, no API keys. Generate ONE square editorial medical illustration contact sheet, exactly 3 columns x 3 rows of equal square panels, no gutters, no text, no letters, no numbers. Refined premium 3D clay and translucent glass scientific still lifes, ivory and lavender backgrounds, soft studio light, pastel purple mint peach, elegant realistic proportions. Row1: blood sample tubes and four small biomarker spheres; DNA double helix; colorful friendly microbiome bacteria magnified. Row2: vitamin capsule with citrus and green leaf; molecular structure with small laboratory glass vessels; hormone molecular spheres with gentle circadian sun moon motif. Row3: diverse fresh foods fish egg milk nuts vegetables, still life; healthy anatomical liver educational model; environmental water drop leaf and laboratory vial. Each panel single centered composition with large margins, tasteful health editorial art, no logos, no claims, no people, no scary imagery. Return actual generated image path. Do not edit project files.'
Path('output/imagegen/testing-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-']
r=subprocess.run(args,input=prompt.encode(),capture_output=True,env=environment('.runtime'),timeout=360)
Path('output/imagegen/testing-result.txt').write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode('utf-8',errors='replace')[-3500:])
