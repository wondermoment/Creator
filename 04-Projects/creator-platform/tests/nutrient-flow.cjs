const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const c={document:{addEventListener(){}},esc:x=>String(x),location:{hash:''}};
vm.createContext(c);
for(const file of ['nutrient-articles.js','nutrient-flow.js','nutrients.js'])vm.runInContext(fs.readFileSync('frontend/'+file,'utf8'),c);
const all=new Set();
for(let i=0;i<6;i++){
 const html=c.nutrientArticlePage(i),lesson=c.nutrientFlowLesson(i);
 assert.ok(html.includes(lesson));
 assert.ok(html.includes('全球期刊')&&html.includes('https://doi.org/')&&html.includes('营养素咨询'));
 const imgs=[...lesson.matchAll(/src="([^"\s]+)"/g)].map(m=>m[1]);
 assert.equal(imgs.length,3);assert.equal(new Set(imgs).size,3);
 for(const src of imgs){assert.ok(fs.existsSync('frontend/'+src.replace('/static/','')));assert.ok(!all.has(src));all.add(src)}
 assert.ok(lesson.includes('不是真实研究数据'));
}
assert.equal(all.size,18);
console.log('PASS: 6 nutrient articles, 18 distinct local process illustrations, captions, journal sources and consultation retained. No model or medical validation.');
