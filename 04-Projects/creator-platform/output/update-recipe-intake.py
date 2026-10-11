from pathlib import Path
import json
old='询问原菜谱、人数、口味目标、过敏原与不接受的替换。给出保留关键风味的改良方案，明确替换前后食材、每人参考用量、烹饪步骤、熟透要求及主食蔬菜搭配。解释取舍，不把低油等同于越少越好，不虚构营养数值。'
new='先判断用户是在问烹饪常识，还是要改良一道具体菜。只说“帮我改良一道家常菜”而未给菜名时，先只问想改哪一道菜，可给两个菜名例子方便回答，不在这一轮问期限、人数或完整病史。随后逐步核对实际需要的原做法、人数、口味目标、过敏原与不接受的替换，沿用已知信息；安全条件未齐全不假定没有过敏。条件足够就给出保留关键风味的改良方案，明确替换前后食材、每人参考用量、烹饪步骤、熟透要求及主食蔬菜搭配。解释取舍，不把低油等同于越少越好，不虚构营养数值。'
p=Path('frontend/diet.js');s=p.read_text('utf-8');assert old in s;p.write_text(s.replace(old,new),encoding='utf-8')
p=Path('backend/app/coach_knowledge.json');data=json.loads(p.read_text('utf-8'));skill=next(s for s in data['skills'] if s['id']=='chinese-recipe');assert skill['task']==old;skill['task']=new;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=Path('frontend/index.html');s=p.read_text('utf-8');s=s.replace('skill-quality.js?v=mindful-4','skill-quality.js?v=intake-5').replace('diet.js?v=nutrient-routes-6','diet.js?v=intake-7');p.write_text(s,encoding='utf-8')
