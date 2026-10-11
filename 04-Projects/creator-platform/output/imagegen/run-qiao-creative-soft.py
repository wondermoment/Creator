import sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('backend').resolve()))
from app.local_codex import command,environment
prompt='Use built-in image_gen to EDIT the attached 2x2 Cyber Qiao creative scene sheet. Keep EXACT same recognizable character, purple hair, clear glasses, face, clothing, four poses and task layout. Preserve top left music keyboard/laptop/headphones, top right easel painting/brush/palette, bottom left making scrapbook, bottom right writing diary. Main change: make backgrounds MUCH quieter and softly defocused. Remove busy plants, wall photos, shelves, speakers, small bottles, extra stationery and decorative clutter. Replace distant backgrounds with luminous warm ivory and very pale lavender smooth softly blurred studio walls, subtle soft daylight only. Keep character face hands and essential creative tools crisp. Simplify foreground desk to necessary objects; scrapbook has only a few tasteful paper pieces. Pastel low contrast background, sophisticated calm editorial illustration, ample negative space. Four equal square panels exact 2x2 split at center with no gutters, no words or logos. Do not blur whole image or character. Generate actual edited image with image_gen only, no paid API keys, no project edits. Return generated path.'
Path('output/imagegen/qiao-creative-soft-prompt.txt').write_text(prompt,encoding='utf-8')
args=command()+['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-C',str(Path.cwd()),'-c','forced_login_method="chatgpt"','-c','approval_policy="never"','-i','C:/Users/pc02a/Creator/04-Projects/geo-platform/.runtime/codex-local/generated_images/01a107cb-8336-7441-9764-2951c1526bb1/exec-ecd3b80a-177e-4fc7-9159-e11cc03cd7e8.png','-']
r=subprocess.run(args,input=prompt.encode(),capture_output=True,env=environment('.runtime'),timeout=420)
Path('output/imagegen/qiao-creative-soft-result.txt').write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode('utf-8',errors='replace')[-2000:])
